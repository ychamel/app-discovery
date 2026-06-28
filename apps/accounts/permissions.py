"""The single authorization gate (DESIGN.md §3/§5/§11).

Every role check in the platform goes through ``account_has_role`` — one place,
**fail-closed**: an unauthenticated user, an unknown role, or any lookup error all
deny. There is intentionally no "default allow" branch.

Two surfaces wrap the same decision:
  * ``HasRole(role)``    — a DRF permission class, for API views.
  * ``require_role(role)`` — a decorator, for Django function views.
"""

import logging
from functools import wraps

from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.accounts import roles as _roles
from apps.core import observability

logger = logging.getLogger("apps.accounts.authz")


def account_has_role(user, role: str) -> bool:
    """True only if ``user`` is an authenticated account holding ``role``.

    Any failure — anonymous user, missing/unknown role, DB error — returns False
    (fail closed). The decision is never allowed to leak as an exception to the
    caller, and never defaults to allow. Every decision is counted for the
    role-gate-correctness metric.
    """
    allowed = False
    try:
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        user_groups = set(user.groups.values_list("name", flat=True))
        # Direct membership, or implied by a higher role (e.g. admin implies developer).
        allowed = role in user_groups or any(
            role in _roles.ROLE_IMPLIES.get(g, frozenset()) for g in user_groups
        )
        return allowed
    except Exception:
        # A lookup error must deny, not crash or allow. Logged for the auth-error metric.
        logger.warning("Role check failed closed for role=%s", role, exc_info=True)
        allowed = False
        return False
    finally:
        observability.increment(
            observability.ROLE_GATE_DECISION,
            role=role,
            result="allow" if allowed else "deny",
        )


def HasRole(role: str) -> type[BasePermission]:
    """Build a DRF permission class that allows only accounts holding ``role``."""

    class _HasRole(BasePermission):
        message = f"This action requires the '{role}' role."

        def has_permission(self, request, view) -> bool:
            return account_has_role(request.user, role)

    _HasRole.__name__ = f"HasRole_{role}"
    return _HasRole


def require_role(role: str):
    """Decorator for Django function views: deny (403) unless the caller holds ``role``."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not account_has_role(request.user, role):
                raise PermissionDenied(f"This action requires the '{role}' role.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
