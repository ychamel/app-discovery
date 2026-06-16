"""Manager for the custom Account model.

Centralizes account creation so the passwordless invariant (DESIGN.md §3/§8) is
enforced in exactly one place: every account is created with an *unusable*
password — there is no code path that sets a real one.
"""

from django.contrib.auth.base_user import BaseUserManager


class AccountManager(BaseUserManager):
    use_in_migrations = True

    def create_account(self, email: str, display_name: str = "", **extra_fields):
        """Create an account with a normalized email and no usable password."""
        if not email:
            raise ValueError("An email address is required to create an account.")
        email = self.normalize_email(email)
        account = self.model(email=email, display_name=display_name, **extra_fields)
        account.set_unusable_password()  # passwordless — auth is magic-link only
        account.save(using=self._db)
        return account

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Django hook. Password is ignored — accounts are passwordless by design."""
        return self.create_account(email, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Bootstrap a Django-admin-capable account (cold start, DESIGN.md §10).

        Grants staff + superuser so the operator can reach the built-in admin site;
        product roles are still granted through the audited role service, not here.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_account(email, **extra_fields)
