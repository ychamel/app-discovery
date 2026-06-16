"""Identity data model (DESIGN.md §4).

Three tables, one source of truth each:
  * ``Account``    — the canonical cross-feature identity (no password stored).
  * ``LoginToken`` — the single-use, short-lived magic-link credential.
  * ``RoleGrant``  — an append-only audit row for every role grant/revoke.

Roles themselves are Django ``Group`` rows (seeded by the initial migration), so
adding a role never touches this schema or the auth path (AC10).
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import AccountManager


class CIEmailField(models.EmailField):
    """An EmailField stored as PostgreSQL ``citext`` for case-insensitive uniqueness.

    Django removed the old ``contrib.postgres`` case-insensitive fields in 5.1; the
    citext extension (enabled by the initial migration) remains the boring, explicit
    way to get one-account-per-email regardless of case (DESIGN.md §4).
    """

    def db_type(self, connection) -> str:
        return "citext"


class Account(AbstractBaseUser, PermissionsMixin):
    """The canonical identity. ``email`` is the username; there is no usable password."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = CIEmailField(unique=True)
    display_name = models.CharField(max_length=80, blank=True)

    # NULL => email not yet confirmed => NOT digest-eligible (AC2).
    email_confirmed_at = models.DateTimeField(null=True, blank=True)

    # Django sign-in gate / admin-site access.
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_account"

    def __str__(self) -> str:
        return self.email

    @property
    def is_email_confirmed(self) -> bool:
        return self.email_confirmed_at is not None


class LoginToken(models.Model):
    """A single-use magic-link credential. The raw token is never stored — only its hash."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="login_tokens"
    )
    # SHA-256 hex digest of a 32-byte random token (DESIGN.md §4/§8).
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_logintoken"

    def __str__(self) -> str:
        return f"LoginToken({self.account_id}, consumed={self.consumed_at is not None})"


class RoleGrant(models.Model):
    """Immutable audit row: who gave/removed which role to/from whom, and when.

    ``target_account`` and ``granted_by`` are SET_NULL so the audit trail survives a
    hard account deletion (AC8) without blocking it. ``granted_by`` is also NULL for
    the cold-start bootstrap grant (DESIGN.md §10). Rows are append-only — never
    updated or deleted.
    """

    class Action(models.TextChoices):
        GRANT = "grant", "grant"
        REVOKE = "revoke", "revoke"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name="role_grants_received",
    )
    role = models.CharField(max_length=64)
    action = models.CharField(max_length=6, choices=Action.choices)
    granted_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        related_name="role_grants_made",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_rolegrant"

    def __str__(self) -> str:
        return f"RoleGrant({self.action} {self.role} -> {self.target_account_id})"
