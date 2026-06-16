"""`manage.py purge_expired_tokens` — remove spent login tokens (DESIGN.md §2, §12).

Scheduled regularly (cron) so the token table does not grow without bound. A token
is purgeable once it is expired *or* already consumed — in both cases it can never
authenticate again, so keeping it has no value (data minimization).
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import LoginToken


class Command(BaseCommand):
    help = "Delete expired or already-consumed login tokens and report the count."

    def handle(self, *args, **options):
        now = timezone.now()
        purgeable = LoginToken.objects.filter(
            Q(expires_at__lt=now) | Q(consumed_at__isnull=False)
        )
        deleted, _ = purgeable.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} expired/consumed login tokens."))
