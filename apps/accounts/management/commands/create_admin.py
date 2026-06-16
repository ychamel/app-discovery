"""`manage.py create_admin <email>` — bootstrap the first admin (DESIGN.md §10, §12).

This is the only way to mint an admin without an existing admin, closing the
bootstrap hole: it runs server-side by an operator, records a `RoleGrant` with
``granted_by = NULL`` (the cold-start marker), and is idempotent on re-run.

The account is also made Django staff + superuser so the operator can reach the
built-in admin site for further cold-start grants. Because accounts are passwordless,
the operator signs in via the normal magic link; ``is_staff`` then admits them to the
admin site (no separate password).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.permissions import account_has_role
from apps.accounts.services import grant_role


class Command(BaseCommand):
    help = "Grant the admin role to an account (creating it if needed). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Email of the account to make an admin.")

    def handle(self, *args, **options):
        email = options["email"]

        with transaction.atomic():
            account = Account.objects.filter(email=email).first()
            created = account is None
            if created:
                account = Account.objects.create_account(email)

            promoted = not (account.is_staff and account.is_superuser)
            if promoted:
                account.is_staff = True
                account.is_superuser = True
                account.save(update_fields=["is_staff", "is_superuser"])

            granted = not account_has_role(account, roles.ADMIN)
            if granted:
                # granted_by = None marks the out-of-band bootstrap grant.
                grant_role(account, roles.ADMIN, granted_by=None)

        if not (created or promoted or granted):
            self.stdout.write(self.style.SUCCESS(f"{email} is already an admin — no change."))
            return
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} admin account: {email}"))
