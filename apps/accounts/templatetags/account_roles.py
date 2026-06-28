"""Template-side reads of the role gate (UX-003 patch, PATCH.md §2A).

Roles are Django ``Group`` rows and the one authorization decision lives in
``account_has_role`` (apps/accounts/permissions.py). Views reach it via ``require_role`` /
``HasRole``; templates had no equivalent. ``{% is_developer user as flag %}`` is that
template-side read — it *delegates* to the same gate so the role decision stays in one
place, and inherits its fail-closed behaviour (anonymous / unknown role / lookup error
all return False). Use it only to gate presentation, never as a security boundary.
"""

from django import template

from apps.accounts import roles
from apps.accounts.permissions import account_has_role

register = template.Library()


@register.simple_tag
def is_developer(user) -> bool:
    """True iff ``user`` holds the developer role (the template-side read of the gate)."""
    return account_has_role(user, roles.DEVELOPER)
