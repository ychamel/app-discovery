"""The single write path for subscriptions (DESIGN.md §5a/§6.1) — the only place
``Subscription`` rows are created or deleted, and the only module that imports
``signals.capture``.

The load-bearing seam is the **transactional coupling** in ``follow_app`` (DESIGN §6.1/§14):
the follow row and its one D-7 ``subscribe`` corpus event are written in **one**
``transaction.atomic()``, so a committed follow ⟺ a committed ``subscribe`` event — M5's 1:1
is *structural*, not merely measured (AC5). If the corpus emit raises, the follow row rolls
back with it (no orphan state); the durable result is correctly *not-followed* (AC7), and
``signals``' own ``_guard`` has already counted ``CAPTURE_ERROR{kind=subscribe}``.

A catalog read that *raises* (DB down) propagates **loud** — a follow has no subject without
its app (DESIGN §8). A *None* (not accepted) is the ``UnknownAppError`` (AC1).
"""

import logging
from uuid import UUID

from django.db import transaction

from apps.catalog import selectors as catalog
from apps.core import observability
from apps.signals import capture as signals_capture
from apps.subscriptions.errors import SelfFollowError, UnknownAppError
from apps.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


def follow_app(user, app_id: UUID) -> bool:
    """Follow ``app_id`` for ``user``; return ``True`` iff a **new** follow was created.

    Idempotent: re-following a current follow is a no-op that emits no second event and
    returns ``False`` (AC1). Re-following *after* an unfollow (the row was deleted) is a
    genuine new follow → one new event — each act of following is its own corpus fact
    (append-only D-7).
    """
    _require_catalogued_app(app_id)
    _require_non_owner(user, app_id)
    with transaction.atomic():
        # The follow row + its corpus event are ONE unit. record_subscribe opens its own
        # atomic block; nested here it becomes a savepoint, so if capture raises BOTH the
        # row and the (uncommitted) event roll back — never a follow without its event,
        # never an event without a follow (M5 by construction, DESIGN §6.1/§14).
        _, created = Subscription.objects.get_or_create(user=user, app_id=app_id)
        if created:
            # No impression link at MVP — optional in D-7, additive later (DESIGN §6.1/§15).
            signals_capture.record_subscribe(user, app_id)
    # Outside the txn so a rolled-back follow never counts (DESIGN §6.1).
    observability.increment(
        observability.SUBSCRIPTION_FOLLOWED
        if created
        else observability.SUBSCRIPTION_FOLLOW_NOOP
    )
    if created:
        logger.info("app followed app_id=%s", app_id)
    return created


def unfollow_app(user, app_id: UUID) -> bool:
    """Unfollow ``app_id`` for ``user`` (hard delete, idempotent); report if a row existed.

    No app-validity check — a user may unfollow an app that was later withdrawn (let them
    clean up). **No corpus event** (OQ-3 = no D-7 ``unfollow`` kind, DESIGN §8). Addressed
    by ``user`` + ``app_id`` only, so a user can never remove another's follow (no IDOR).
    """
    deleted_count, _ = Subscription.objects.filter(user=user, app_id=app_id).delete()
    existed = deleted_count > 0
    if existed:
        observability.increment(observability.SUBSCRIPTION_UNFOLLOWED)
        logger.info("app unfollowed app_id=%s", app_id)
    return existed


# --- Boundaries --------------------------------------------------------------
def _require_catalogued_app(app_id: UUID) -> None:
    """Raise ``UnknownAppError`` unless ``app_id`` is an accepted catalog app (D-6, AC1)."""
    if catalog.get_catalogued_app(app_id) is None:
        raise UnknownAppError(f"No accepted catalog app for id {app_id!r}.")


def _require_non_owner(user, app_id: UUID) -> None:
    """Raise ``SelfFollowError`` if ``user`` owns ``app_id`` — self-follow is not permitted."""
    if catalog.is_app_owner(user, app_id):
        raise SelfFollowError("You can't follow your own app.")
