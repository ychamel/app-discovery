"""Role-name constants and helpers (DESIGN.md §3/§4).

Roles are Django ``Group`` rows; these constants are the canonical names every
feature uses to refer to them. Adding a future role means seeding a new group and
applying ``HasRole('new-role')`` to new actions — no change here is required for the
auth path (AC10).
"""

# Canonical role names (must match the groups seeded in migration 0001).
USER = "user"
DEVELOPER = "developer"
ADMIN = "admin"

# The base role every account holds; assigned in the account-creation transaction.
BASE_ROLE = USER

# The only role an account may grant itself (DESIGN.md §5 #8, DL-2). Admin and any
# future privileged role are grant-only via the audited admin path — never self-serve.
SELF_SERVE_ROLES = frozenset({DEVELOPER})


def account_roles(account) -> list[str]:
    """The role names an account currently holds, sorted for stable output."""
    return sorted(account.groups.values_list("name", flat=True))
