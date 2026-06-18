"""The single write path for the behavioral signal corpus (DESIGN.md §5a/§5d/§10).

**Every** ``signals_*`` row is created here — nothing else writes the corpus (D-7). That
keeps the invariants in exactly one place (illegal states unrepresentable):

  * the ``app_id`` is a real, **accepted** catalog app (D-6) — else ``UnknownAppError`` and
    nothing is written;
  * an impression freezes the app's **capture-time** tag snapshot in the same transaction
    (AC1/AC2);
  * a conversion's ``impression`` belongs to the same app **and** user (AC3) — else
    ``ImpressionMismatchError``;
  * the actor is always the caller's authenticated account (``request.user``) — capture
    never accepts an arbitrary actor id (§10);
  * ``is_proxy`` is **service-set**, never caller-supplied (T-05).

**Fail-loud contract (AC11/§5d).** Each recorder runs its write(s) in
``transaction.atomic()`` so a partial write never persists, and on **any** failure it
increments ``capture_error`` (tagged with the event kind + error type) and logs with
request context **before re-raising** — capture is never silently lossy. How an emitting
surface treats the raise (corpus-critical vs counted-not-blocking) is the surface's policy
(§5d); capture's job is to make the loss loud and counted.

This module is written across two task-sized halves that share this file: the **impression
anchor + visit substrate** here (T-04) and the **engagement events** (T-05).
"""

import logging
from contextlib import contextmanager
from datetime import date, datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog import selectors as catalog
from apps.core import observability
from apps.signals.errors import ImpressionMismatchError, UnknownAppError
from apps.signals.kinds import EventKind, Surface
from apps.signals.models import (
    EngagementEvent,
    Impression,
    ImpressionTag,
    PlatformVisit,
)

logger = logging.getLogger(__name__)


# --- Fail-loud boundary ------------------------------------------------------
@contextmanager
def _guard(kind: str):
    """Count + log any capture failure on ``capture_error{kind}`` before re-raising (§5d).

    The increment is the never-silent guarantee (AC11): a refused or failed capture is
    always observable and alertable, never swallowed. The recorder still raises so a
    half-written corpus never persists.
    """
    try:
        yield
    except Exception as exc:
        observability.increment(
            observability.CAPTURE_ERROR, kind=kind, error=type(exc).__name__
        )
        logger.exception("signal capture failed (kind=%s)", kind)
        raise


def _require_catalogued_app(app_id: UUID) -> catalog.CatalogApp:
    """Return the accepted catalog app for ``app_id`` or raise ``UnknownAppError`` (D-6)."""
    catalogued = catalog.get_catalogued_app(app_id)
    if catalogued is None:
        raise UnknownAppError(f"No accepted catalog app for id {app_id!r}.")
    return catalogued


def _require_surface(surface) -> str:
    """Validate the surface is a known, closed-vocabulary value (fail loud at the boundary)."""
    if surface not in Surface.values:
        raise ValidationError({"surface": f"Unknown surface {surface!r}."})
    return surface


# --- Impression anchor (T-04) ------------------------------------------------
def record_impression(
    user,
    app_id: UUID,
    *,
    surface: Surface,
    occurred_at: datetime | None = None,
) -> Impression:
    """Record one shown instance and freeze its capture-time tag snapshot (AC1/AC2).

    The impression and one ``ImpressionTag`` per the app's **current** resolved tag are
    written in a single transaction, so the snapshot is atomic with the anchor and is then
    frozen (never re-derived at read).
    """
    with _guard("impression"):
        catalogued = _require_catalogued_app(app_id)
        _require_surface(surface)
        moment = occurred_at or timezone.now()
        with transaction.atomic():
            impression = Impression.objects.create(
                user=user, app_id=app_id, surface=surface, occurred_at=moment
            )
            ImpressionTag.objects.bulk_create(
                [
                    ImpressionTag(impression=impression, tag_id=tag.id)
                    for tag in catalogued.tags
                ]
            )
        observability.increment(
            observability.IMPRESSION_CAPTURED, app_id=str(app_id)
        )
        return impression


# --- Return-to-platform substrate (T-04) -------------------------------------
def record_platform_visit(user, *, on_date: date | None = None) -> PlatformVisit:
    """Idempotently record that ``user`` was active on the platform on a given UTC day (AC4).

    One row per user per day (the ``(user, visit_date)`` unique index): a duplicate day is a
    no-op, and a lost race is absorbed by ``get_or_create`` and treated as "already
    recorded". This is the substrate the read path derives returns_3d/14d from (SC-9) — the
    return itself is never stored.
    """
    with _guard("visit"):
        visit_date = on_date or timezone.now().date()
        visit, created = PlatformVisit.objects.get_or_create(
            user=user, visit_date=visit_date
        )
        if created:
            observability.increment(
                observability.PLATFORM_VISIT_CAPTURED, user_id=str(user.pk)
            )
        return visit


# --- Engagement events (T-05) ------------------------------------------------
# Each kind → its success metric. The single map keeps the kind↔metric pairing in one
# place (one source of truth) rather than scattered through the recorders.
_KIND_METRIC = {
    EventKind.CLICK_THROUGH: observability.CLICK_THROUGH_CAPTURED,
    EventKind.SUBSCRIBE: observability.SUBSCRIBE_CAPTURED,
    EventKind.PAGE_REENGAGEMENT: observability.PAGE_REENGAGEMENT_CAPTURED,
    EventKind.SHARE: observability.SHARE_CAPTURED,
    EventKind.OFF_PLATFORM_PROXY: observability.OFF_PLATFORM_PROXY_CAPTURED,
}


def _require_linked_impression(impression, user, app_id: UUID) -> None:
    """Assert a supplied impression belongs to this app **and** user, else raise (AC3/§10).

    A conversion can never be pinned to another app's or user's shown instance. ``None`` is
    handled by the caller (required vs optional per kind) — this only validates a supplied one.
    """
    if impression.app_id != app_id or impression.user_id != user.pk:
        raise ImpressionMismatchError(
            f"Impression {impression.id} does not belong to app {app_id} / this user."
        )


def _record_event(
    kind: EventKind,
    user,
    app_id: UUID,
    *,
    impression,
    occurred_at,
    impression_required: bool,
    is_proxy: bool,
) -> EngagementEvent:
    """Write one append-only ``EngagementEvent`` of ``kind`` — atomic, counted, fail-loud.

    The single place every engagement recorder funnels through: app validity (D-6),
    impression linkage (AC3), the service-set ``is_proxy`` (AC7), and the §5d fail-loud
    contract are enforced once here, so an illegal state cannot be written by any recorder.
    """
    with _guard(kind.value):
        _require_catalogued_app(app_id)
        if impression_required and impression is None:
            raise ValidationError(
                {"impression": f"{kind.label} requires the originating impression."}
            )
        if impression is not None:
            _require_linked_impression(impression, user, app_id)
        with transaction.atomic():
            event = EngagementEvent.objects.create(
                kind=kind,
                user=user,
                app_id=app_id,
                impression=impression,
                is_proxy=is_proxy,
                occurred_at=occurred_at or timezone.now(),
            )
        tags = {"app_id": str(app_id)}
        if is_proxy:
            tags["channel"] = "secondary"  # the proxy is a flagged secondary signal (AC7)
        observability.increment(_KIND_METRIC[kind], **tags)
        return event


def record_click_through(
    user, app_id: UUID, *, impression: Impression, occurred_at: datetime | None = None
) -> EngagementEvent:
    """Record a click-through, **linked to its originating impression** (AC3 — required)."""
    return _record_event(
        EventKind.CLICK_THROUGH, user, app_id,
        impression=impression, occurred_at=occurred_at,
        impression_required=True, is_proxy=False,
    )


def record_subscribe(
    user, app_id: UUID, *, impression: Impression | None = None,
    occurred_at: datetime | None = None,
) -> EngagementEvent:
    """Record a subscribe/follow, optionally linked to an impression (AC5)."""
    return _record_event(
        EventKind.SUBSCRIBE, user, app_id,
        impression=impression, occurred_at=occurred_at,
        impression_required=False, is_proxy=False,
    )


def record_page_reengagement(
    user, app_id: UUID, *, impression: Impression | None = None,
    occurred_at: datetime | None = None,
) -> EngagementEvent:
    """Record on-page re-engagement, optionally linked to an impression (AC5)."""
    return _record_event(
        EventKind.PAGE_REENGAGEMENT, user, app_id,
        impression=impression, occurred_at=occurred_at,
        impression_required=False, is_proxy=False,
    )


def record_share(
    user, app_id: UUID, *, impression: Impression | None = None,
    occurred_at: datetime | None = None,
) -> EngagementEvent:
    """Record a share, optionally linked to an impression (AC6)."""
    return _record_event(
        EventKind.SHARE, user, app_id,
        impression=impression, occurred_at=occurred_at,
        impression_required=False, is_proxy=False,
    )


def record_off_platform_proxy(
    user, app_id: UUID, *, impression: Impression, occurred_at: datetime | None = None
) -> EngagementEvent:
    """Record an off-platform proxy signal — the flagged **secondary** seam (AC7/§8).

    The only off-platform mechanism shipped (no detector is built — OQ-1). ``is_proxy`` is
    set **here**, by the service, never by the caller; the impression is required so the
    secondary signal still attributes to a shown instance.
    """
    return _record_event(
        EventKind.OFF_PLATFORM_PROXY, user, app_id,
        impression=impression, occurred_at=occurred_at,
        impression_required=True, is_proxy=True,
    )
