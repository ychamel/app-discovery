"""Tests for the identity data model and seed migration (T-05, DESIGN.md §4)."""

from datetime import timedelta

from django.contrib.auth.models import Group
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, LoginToken, RoleGrant


class AccountModelTests(TestCase):
    def test_created_account_has_no_usable_password(self):
        account = Account.objects.create_account("dev@example.com", display_name="Dev")
        self.assertFalse(account.has_usable_password())

    def test_email_uniqueness_is_case_insensitive(self):
        Account.objects.create_account("Person@Example.com")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Account.objects.create_account("person@example.com")

    def test_email_lookup_is_case_insensitive(self):
        Account.objects.create_account("Mixed@Case.com")
        self.assertTrue(Account.objects.filter(email="mixed@case.com").exists())

    def test_email_required(self):
        with self.assertRaises(ValueError):
            Account.objects.create_account("")

    def test_is_email_confirmed_property(self):
        account = Account.objects.create_account("u@example.com")
        self.assertFalse(account.is_email_confirmed)
        account.email_confirmed_at = timezone.now()
        self.assertTrue(account.is_email_confirmed)


class GroupSeedTests(TestCase):
    def test_three_role_groups_seeded_by_migration(self):
        self.assertEqual(
            set(Group.objects.values_list("name", flat=True)),
            {"user", "developer", "admin"},
        )


class LoginTokenTests(TestCase):
    def test_token_hash_is_unique(self):
        account = Account.objects.create_account("u@example.com")
        expires = timezone.now() + timedelta(minutes=15)
        LoginToken.objects.create(account=account, token_hash="a" * 64, expires_at=expires)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LoginToken.objects.create(
                    account=account, token_hash="a" * 64, expires_at=expires
                )

    def test_tokens_cascade_delete_with_account(self):
        account = Account.objects.create_account("u@example.com")
        LoginToken.objects.create(
            account=account, token_hash="b" * 64, expires_at=timezone.now()
        )
        account.delete()
        self.assertEqual(LoginToken.objects.count(), 0)


class RoleGrantAuditTests(TestCase):
    def test_granted_by_is_nullable_for_bootstrap(self):
        target = Account.objects.create_account("target@example.com")
        grant = RoleGrant.objects.create(
            target_account=target, role="admin", action=RoleGrant.Action.GRANT
        )
        self.assertIsNone(grant.granted_by)

    def test_audit_row_survives_account_deletion_via_set_null(self):
        admin = Account.objects.create_account("admin@example.com")
        target = Account.objects.create_account("target@example.com")
        grant = RoleGrant.objects.create(
            target_account=target,
            role="developer",
            action=RoleGrant.Action.GRANT,
            granted_by=admin,
        )
        # Deleting either referenced account must NOT delete the audit row.
        admin.delete()
        target.delete()
        grant.refresh_from_db()
        self.assertIsNone(grant.granted_by_id)
        self.assertIsNone(grant.target_account_id)
        self.assertEqual(grant.role, "developer")


class SchemaIndexTests(TestCase):
    def _constraints(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_account_email_has_unique_index(self):
        constraints = self._constraints("accounts_account")
        unique_on_email = [
            c for c in constraints.values() if c["columns"] == ["email"] and c["unique"]
        ]
        self.assertTrue(unique_on_email)

    def test_login_token_hash_has_unique_index(self):
        constraints = self._constraints("accounts_logintoken")
        unique_on_hash = [
            c for c in constraints.values() if c["columns"] == ["token_hash"] and c["unique"]
        ]
        self.assertTrue(unique_on_hash)

    def test_login_token_account_fk_is_indexed(self):
        constraints = self._constraints("accounts_logintoken")
        indexed_account = [
            c for c in constraints.values() if c["columns"] == ["account_id"] and c["index"]
        ]
        self.assertTrue(indexed_account)
