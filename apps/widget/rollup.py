"""The one concurrency-correct daily-rollup increment, shared by every widget count writer.

Extracted from the reach writer (embeddable-update-widget, EUW-IMPL-1) so both the reach writer
(``record_widget_impression`` / ``record_widget_click_through``) and the conversion writer
(``record_widget_conversion``) share **exactly one** implementation of the atomic per-day
increment + create-race retry — widget-conversion-attribution DESIGN §6.2. Two concrete callers
justify the extraction (it is not speculative).

Parameterized by the rollup model class: every such model has the same
``(app_id, kind, count_date, count)`` shape and a ``unique(app_id, kind, count_date)`` constraint,
which is what turns a concurrent first-of-day create into the caught ``IntegrityError`` this
retries as an increment.

Imports nothing from ``apps.signals`` (the firewall — AST-proven in ``tests/test_imports.py``,
which walks this module automatically).
"""

from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone


def _increment_daily(model, app_id: UUID, kind: str) -> None:
    """Add one to ``model``'s ``(app_id, kind, today)`` rollup row, correct under concurrency.

    ``F("count") + 1`` is evaluated **in the database**, so concurrent increments never lose an
    update. The model's ``unique(app_id, kind, count_date)`` constraint turns a concurrent
    first-of-day create into a caught ``IntegrityError`` we resolve by re-incrementing the
    now-existing row — so the create path is a one-time-per-day cold start, not a lock. No
    cache/queue infra (the ``developer-updates`` durable-table precedent). Raises on any other DB
    error; the caller decides whether to wrap it fail-soft.
    """
    today = timezone.now().date()  # the UTC day (USE_TZ=True, TIME_ZONE=UTC)
    with transaction.atomic():
        if _increment_existing_row(model, app_id, kind, today):
            return
        try:
            # A nested atomic() is a SAVEPOINT: on Postgres an IntegrityError marks the whole
            # transaction for rollback, so a failed create must be isolated — without this the
            # except branch could not query the DB ("current transaction is aborted").
            with transaction.atomic():
                model.objects.create(
                    app_id=app_id, kind=kind, count_date=today, count=1
                )
        except IntegrityError:
            # Lost the create race to a concurrent writer; the row now exists, so increment it.
            _increment_existing_row(model, app_id, kind, today)


def _increment_existing_row(model, app_id: UUID, kind: str, count_date) -> bool:
    """Atomically ``count += 1`` for the rollup row; return whether a row was updated."""
    updated = model.objects.filter(
        app_id=app_id, kind=kind, count_date=count_date
    ).update(count=F("count") + 1)
    return bool(updated)
