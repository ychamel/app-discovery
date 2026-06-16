"""Role grant/revoke services and account deletion (DESIGN.md §3/§4).

Granting or revoking a role is the *only* way roles change, and every change writes
an immutable ``RoleGrant`` audit row in the same transaction — so authorization
state and its audit trail can never drift (one source of truth).

There is deliberately **no generic "grant myself any role" function**: callers pass
an explicit target and role, and the privileged-role policy (admin is grant-only,
developer is the sole self-serve role) lives in the views that call these.
"""

from django.contrib.auth.models import Group
from django.db import transaction

from apps.accounts.models import Account, RoleGrant


class UnknownRoleError(ValueError):
    """Raised when a role name has no corresponding group (DESIGN.md §11 → 400)."""


def _role_group(role: str) -> Group:
    try:
        return Group.objects.get(name=role)
    except Group.DoesNotExist as exc:
        raise UnknownRoleError(role) from exc


def grant_role(target: Account, role: str, *, granted_by: Account | None = None) -> RoleGrant:
    """Add ``role`` to ``target`` and append a grant audit row, atomically.

    ``granted_by`` is None only for the cold-start bootstrap (DESIGN.md §10).
    """
    group = _role_group(role)
    with transaction.atomic():
        target.groups.add(group)
        return RoleGrant.objects.create(
            target_account=target,
            role=role,
            action=RoleGrant.Action.GRANT,
            granted_by=granted_by,
        )


def revoke_role(target: Account, role: str, *, granted_by: Account | None = None) -> RoleGrant:
    """Remove ``role`` from ``target`` and append a revoke audit row, atomically."""
    group = _role_group(role)
    with transaction.atomic():
        target.groups.remove(group)
        return RoleGrant.objects.create(
            target_account=target,
            role=role,
            action=RoleGrant.Action.REVOKE,
            granted_by=granted_by,
        )


def delete_account(account: Account) -> None:
    """Hard-delete an account and everything that *is* its identity (AC8, DESIGN.md §4).

    In one transaction: drop role (group) memberships, then delete the account row —
    which cascade-deletes its login tokens. ``RoleGrant`` audit rows are preserved
    (their FKs are SET_NULL), so the deletion is attributable but unblocked.
    """
    with transaction.atomic():
        account.groups.clear()
        account.delete()
