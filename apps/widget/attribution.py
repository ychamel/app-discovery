"""The single writer of ``widget_reach_count`` (DESIGN §5.2/§6) — atomic daily increments.

Two entry points, ``record_widget_impression`` and ``record_widget_click_through``, each of
which adds one to today's ``(app_id, kind, count_date)`` rollup row. Both delegate to one
private increment so the concurrency-correct write lives in exactly one place.

**The firewall (AC6 / M5 = 0) is structural here:** this module imports nothing from
``apps.signals``. A widget interaction therefore creates no D-7 corpus row and can never be
``signals.has_impression(surfaces=CURATED_SURFACES)`` evidence — it does not exist in the
corpus to be read (DESIGN §3; AST-proven in ``tests/test_imports.py``).

Both functions **trust an ``app_id`` the calling view already validated as ACCEPTED** (EUW-11 —
the view is the single caller and the validation boundary; re-reading the catalog on every count
would double the hot-path cost for no gain). They **raise on a DB failure**; the caller wraps
the call fail-soft (the view, T-05) so counting can never break the host's page.
"""

from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.widget.kinds import WidgetEventKind
from apps.widget.models import WidgetReachCount


def record_widget_impression(app_id: UUID) -> None:
    """Count one widget render for ``app_id`` against today's impression rollup row."""
    _increment_today(app_id, WidgetEventKind.IMPRESSION)


def record_widget_click_through(app_id: UUID) -> None:
    """Count one view-on-platform click for ``app_id`` against today's click-through row."""
    _increment_today(app_id, WidgetEventKind.CLICK_THROUGH)


def _increment_today(app_id: UUID, kind: str) -> None:
    """Add one to the ``(app_id, kind, today)`` rollup row, correct under concurrency (DESIGN §6).

    ``F("count") + 1`` is evaluated **in the database**, so concurrent increments never lose an
    update. The unique constraint (``widget_reach_count_unique``) turns a concurrent create into
    a caught ``IntegrityError`` we resolve by re-incrementing the now-existing row — so the
    create path is a one-time-per-day cold start, not a lock. No cache/queue infra (the
    ``developer-updates`` durable-table precedent).
    """
    today = timezone.now().date()  # the UTC day (USE_TZ=True, TIME_ZONE=UTC)
    with transaction.atomic():
        if _increment_existing_row(app_id, kind, today):
            return
        try:
            # A nested atomic() is a SAVEPOINT: on Postgres an IntegrityError marks the whole
            # transaction for rollback, so a failed create must be isolated — without this the
            # except branch could not query the DB ("current transaction is aborted").
            with transaction.atomic():
                WidgetReachCount.objects.create(
                    app_id=app_id, kind=kind, count_date=today, count=1
                )
        except IntegrityError:
            # Lost the create race to a concurrent writer; the row now exists, so increment it.
            _increment_existing_row(app_id, kind, today)


def _increment_existing_row(app_id: UUID, kind: str, count_date) -> bool:
    """Atomically ``count += 1`` for the rollup row; return whether a row was updated."""
    updated = WidgetReachCount.objects.filter(
        app_id=app_id, kind=kind, count_date=count_date
    ).update(count=F("count") + 1)
    return bool(updated)
