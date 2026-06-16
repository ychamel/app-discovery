"""Admin grant/revoke API tests (T-14, AC9, DESIGN.md §5 #9/#10)."""

import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.models import Account, RoleGrant
from apps.accounts.permissions import account_has_role
from apps.accounts.services import grant_role


class AdminRoleApiTests(TestCase):
    def setUp(self):
        self.admin = Account.objects.create_account("admin@example.com")
        grant_role(self.admin, roles.ADMIN)
        self.target = Account.objects.create_account("target@example.com")
        grant_role(self.target, roles.USER)

        self.as_admin = APIClient()
        self.as_admin.force_authenticate(self.admin)

    def _grant_url(self, account_id):
        return reverse("accounts:admin-account-roles", args=[account_id])

    def _revoke_url(self, account_id, role):
        return reverse("accounts:admin-account-role", args=[account_id, role])

    def test_admin_can_grant_role_and_it_is_audited(self):
        response = self.as_admin.post(
            self._grant_url(self.target.id), {"role": roles.DEVELOPER}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(account_has_role(self.target, roles.DEVELOPER))
        grant = RoleGrant.objects.get(action=RoleGrant.Action.GRANT, role=roles.DEVELOPER)
        self.assertEqual(grant.granted_by, self.admin)
        self.assertEqual(grant.target_account, self.target)

    def test_admin_can_revoke_role(self):
        grant_role(self.target, roles.DEVELOPER)
        response = self.as_admin.delete(self._revoke_url(self.target.id, roles.DEVELOPER))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(account_has_role(self.target, roles.DEVELOPER))
        self.assertTrue(
            RoleGrant.objects.filter(action=RoleGrant.Action.REVOKE, role=roles.DEVELOPER).exists()
        )

    def test_non_admin_is_refused(self):
        as_target = APIClient()
        as_target.force_authenticate(self.target)  # only holds user role
        response = as_target.post(
            self._grant_url(self.target.id), {"role": roles.ADMIN}, format="json"
        )
        # A non-admin cannot grant admin — this is also why admin is not self-grantable (AC9).
        self.assertEqual(response.status_code, 403)
        self.assertFalse(account_has_role(self.target, roles.ADMIN))

    def test_unknown_target_returns_404(self):
        response = self.as_admin.post(
            self._grant_url(uuid.uuid4()), {"role": roles.DEVELOPER}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_role_returns_400(self):
        response = self.as_admin.post(
            self._grant_url(self.target.id), {"role": "wizard"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_granted_admin_can_then_act_as_admin(self):
        # Grant admin to a fresh account, then it succeeds via the same sign-in (AC9).
        newcomer = Account.objects.create_account("new@example.com")
        grant_role(newcomer, roles.USER)
        self.as_admin.post(self._grant_url(newcomer.id), {"role": roles.ADMIN}, format="json")

        as_newcomer = APIClient()
        as_newcomer.force_authenticate(newcomer)
        response = as_newcomer.post(
            self._grant_url(self.target.id), {"role": roles.DEVELOPER}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_is_denied(self):
        response = APIClient().post(
            self._grant_url(self.target.id), {"role": roles.DEVELOPER}, format="json"
        )
        self.assertEqual(response.status_code, 403)
