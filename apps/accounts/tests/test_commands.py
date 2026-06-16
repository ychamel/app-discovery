"""Management command tests (T-15, DESIGN.md §10/§12)."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import Account, LoginToken, RoleGrant
from apps.accounts.permissions import account_has_role


class CreateAdminTests(TestCase):
    def _run(self, email):
        out = StringIO()
        call_command("create_admin", email, stdout=out)
        return out.getvalue()

    def test_creates_account_grants_admin_and_records_bootstrap_audit(self):
        self._run("boss@example.com")
        account = Account.objects.get(email="boss@example.com")
        self.assertTrue(account_has_role(account, roles.ADMIN))
        self.assertTrue(account.is_staff)
        self.assertTrue(account.is_superuser)

        grant = RoleGrant.objects.get(role=roles.ADMIN, action=RoleGrant.Action.GRANT)
        self.assertIsNone(grant.granted_by)  # cold-start marker
        self.assertEqual(grant.target_account, account)

    def test_promotes_existing_account(self):
        Account.objects.create_account("existing@example.com")
        self._run("existing@example.com")
        account = Account.objects.get(email="existing@example.com")
        self.assertTrue(account_has_role(account, roles.ADMIN))

    def test_is_idempotent_on_rerun(self):
        self._run("boss@example.com")
        output = self._run("boss@example.com")
        self.assertIn("already an admin", output)
        # No duplicate grant rows / accounts.
        self.assertEqual(RoleGrant.objects.filter(role=roles.ADMIN).count(), 1)
        self.assertEqual(Account.objects.filter(email="boss@example.com").count(), 1)


class PurgeExpiredTokensTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com")
        now = timezone.now()
        self.valid = LoginToken.objects.create(
            account=self.account, token_hash="v" * 64, expires_at=now + timedelta(minutes=15)
        )
        self.expired = LoginToken.objects.create(
            account=self.account, token_hash="e" * 64, expires_at=now - timedelta(minutes=1)
        )
        self.consumed = LoginToken.objects.create(
            account=self.account,
            token_hash="c" * 64,
            expires_at=now + timedelta(minutes=15),
            consumed_at=now,
        )

    def test_purges_expired_and_consumed_keeps_valid(self):
        out = StringIO()
        call_command("purge_expired_tokens", stdout=out)
        remaining = set(LoginToken.objects.values_list("token_hash", flat=True))
        self.assertEqual(remaining, {"v" * 64})
        self.assertIn("Purged 2", out.getvalue())
