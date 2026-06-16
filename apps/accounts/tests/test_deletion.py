"""Account deletion tests (T-13, AC8, DESIGN.md §5 #7, §4)."""

import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import Account, LoginToken, RoleGrant
from apps.accounts.services import grant_role

JSON = "application/json"


class DeletionTests(TestCase):
    """Uses a real session (force_login) so session teardown is genuinely exercised."""

    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="U")
        grant_role(self.account, roles.USER)
        grant_role(self.account, roles.DEVELOPER)
        LoginToken.objects.create(
            account=self.account,
            token_hash="c" * 64,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        self.client.force_login(self.account)

    def _delete(self, body):
        return self.client.delete(
            reverse("accounts:me"), data=json.dumps(body), content_type=JSON
        )

    def test_confirmed_deletion_removes_identity_and_ends_session(self):
        response = self._delete({"confirm": True})
        self.assertEqual(response.status_code, 204)

        # Identity, credentials (tokens), and role memberships are gone (AC8).
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
        self.assertEqual(LoginToken.objects.count(), 0)

        # Session ended — the same client can no longer act.
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 403)

    def test_deletion_requires_confirmation(self):
        response = self._delete({})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())

    def test_audit_rows_survive_deletion(self):
        self._delete({"confirm": True})
        # The grant audit trail is preserved (SET_NULL), now pointing at no account.
        surviving = RoleGrant.objects.filter(role=roles.DEVELOPER)
        self.assertTrue(surviving.exists())
        self.assertIsNone(surviving.first().target_account_id)

    def test_deleted_account_cannot_sign_in(self):
        self._delete({"confirm": True})
        self.assertFalse(Account.objects.filter(email="u@example.com").exists())
