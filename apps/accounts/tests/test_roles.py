"""Tests for the role service and the fail-closed gate (T-06, DESIGN.md §3/§5/§11)."""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.models import Account, RoleGrant
from apps.accounts.permissions import HasRole, account_has_role, require_role
from apps.accounts.services import UnknownRoleError, grant_role, revoke_role


class _Request:
    """Minimal stand-in for an HTTP request carrying a user."""

    def __init__(self, user):
        self.user = user


class GateTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com")
        grant_role(self.account, roles.DEVELOPER)

    def test_allows_when_account_holds_role(self):
        self.assertTrue(account_has_role(self.account, roles.DEVELOPER))

    def test_denies_when_account_lacks_role(self):
        self.assertFalse(account_has_role(self.account, roles.ADMIN))

    def test_anonymous_denied(self):
        self.assertFalse(account_has_role(AnonymousUser(), roles.DEVELOPER))

    def test_none_user_denied(self):
        self.assertFalse(account_has_role(None, roles.DEVELOPER))

    def test_unknown_role_denied(self):
        # A role with no group must deny, not error (fail closed).
        self.assertFalse(account_has_role(self.account, "nonexistent-role"))

    def test_lookup_error_fails_closed(self):
        class _Boom:
            is_authenticated = True

            @property
            def groups(self):
                raise RuntimeError("simulated DB outage")

        self.assertFalse(account_has_role(_Boom(), roles.ADMIN))


class HasRolePermissionTests(TestCase):
    def setUp(self):
        self.admin = Account.objects.create_account("admin@example.com")
        grant_role(self.admin, roles.ADMIN)
        self.plain = Account.objects.create_account("plain@example.com")

    def test_permission_grants_role_holder(self):
        permission = HasRole(roles.ADMIN)()
        self.assertTrue(permission.has_permission(_Request(self.admin), None))

    def test_permission_denies_non_holder(self):
        permission = HasRole(roles.ADMIN)()
        self.assertFalse(permission.has_permission(_Request(self.plain), None))


class RequireRoleDecoratorTests(TestCase):
    def setUp(self):
        self.admin = Account.objects.create_account("admin@example.com")
        grant_role(self.admin, roles.ADMIN)
        self.plain = Account.objects.create_account("plain@example.com")

        @require_role(roles.ADMIN)
        def view(request):
            return "ok"

        self.view = view

    def test_allows_role_holder(self):
        self.assertEqual(self.view(_Request(self.admin)), "ok")

    def test_denies_non_holder(self):
        with self.assertRaises(PermissionDenied):
            self.view(_Request(self.plain))


class GrantRevokeAuditTests(TestCase):
    def setUp(self):
        self.target = Account.objects.create_account("t@example.com")
        self.actor = Account.objects.create_account("a@example.com")

    def test_grant_adds_group_and_writes_audit_row(self):
        grant_role(self.target, roles.DEVELOPER, granted_by=self.actor)
        self.assertIn(roles.DEVELOPER, roles.account_roles(self.target))
        row = RoleGrant.objects.get()
        self.assertEqual(row.action, RoleGrant.Action.GRANT)
        self.assertEqual(row.role, roles.DEVELOPER)
        self.assertEqual(row.granted_by, self.actor)
        self.assertEqual(row.target_account, self.target)

    def test_revoke_removes_group_and_writes_audit_row(self):
        grant_role(self.target, roles.DEVELOPER)
        revoke_role(self.target, roles.DEVELOPER, granted_by=self.actor)
        self.assertNotIn(roles.DEVELOPER, roles.account_roles(self.target))
        actions = list(RoleGrant.objects.order_by("created_at").values_list("action", flat=True))
        self.assertEqual(actions, [RoleGrant.Action.GRANT, RoleGrant.Action.REVOKE])

    def test_audit_rows_are_never_mutated(self):
        grant = grant_role(self.target, roles.DEVELOPER)
        original_id, original_created = grant.id, grant.created_at
        revoke_role(self.target, roles.DEVELOPER)
        grant.refresh_from_db()
        # The original grant row is untouched; the revoke is a new append-only row.
        self.assertEqual(grant.id, original_id)
        self.assertEqual(grant.created_at, original_created)
        self.assertEqual(grant.action, RoleGrant.Action.GRANT)
        self.assertEqual(RoleGrant.objects.count(), 2)

    def test_grant_unknown_role_raises(self):
        with self.assertRaises(UnknownRoleError):
            grant_role(self.target, "wizard")

    def test_only_developer_is_self_serve(self):
        # Guards the privilege-escalation invariant (DL-2): admin is never self-serve.
        self.assertEqual(roles.SELF_SERVE_ROLES, frozenset({roles.DEVELOPER}))
