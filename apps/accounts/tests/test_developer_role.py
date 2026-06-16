"""Self-serve developer role tests (T-12, AC6, DESIGN.md §5 #8)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.models import Account, RoleGrant
from apps.accounts.permissions import account_has_role
from apps.accounts.services import grant_role


class DeveloperSelfServeTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="U")
        grant_role(self.account, roles.USER)
        self.api = APIClient()
        self.api.force_authenticate(self.account)

    def test_user_can_become_developer_on_same_account(self):
        # Before: a developer-gated check fails.
        self.assertFalse(account_has_role(self.account, roles.DEVELOPER))

        response = self.api.post(reverse("accounts:developer-role"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(roles.DEVELOPER, response.json()["roles"])

        # After: the SAME account now passes the developer gate — no second login (AC6).
        self.account.refresh_from_db()
        self.assertTrue(account_has_role(self.account, roles.DEVELOPER))

    def test_developer_grant_is_audited(self):
        self.api.post(reverse("accounts:developer-role"))
        grant = RoleGrant.objects.get(role=roles.DEVELOPER, action=RoleGrant.Action.GRANT)
        self.assertEqual(grant.target_account, self.account)

    def test_unauthenticated_cannot_take_developer_role(self):
        self.assertEqual(
            APIClient().post(reverse("accounts:developer-role")).status_code, 403
        )
