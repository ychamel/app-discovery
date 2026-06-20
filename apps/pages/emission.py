"""The surface-side non-blocking capture policy for app-pages (DESIGN.md §5b/§7).

This is the **one place** the rule "engagement capture is best-effort *to the visitor*,
loud *to operators*" lives — the complement of the signals fail-loud contract (D-7 §5d,
which counts ``capture_error`` and re-raises *inside* ``apps.signals``). Here we catch that
raise so it never reaches the visitor: the page still renders, the try-it redirect still
fires, the share still returns — and the loss is counted on
``APP_PAGE_CAPTURE_DEGRADED`` and logged with request context (AC7).

Two invariants this module enforces, and nothing else:

  1. **Authenticated-only (AP-4).** ``request.user.is_authenticated`` is the gate. The D-7
     corpus is keyed ``user × App.id``; an anonymous visitor has no actor to attribute to,
     so nothing is captured (the page still renders fully — AC5).
  2. **Fail-soft-but-counted (AC7).** Every ``signals.capture.*`` call is wrapped so any
     failure — infrastructure down, or a forged/foreign ``imp`` raising
     ``ImpressionMismatchError`` — is caught, counted, logged, and swallowed.

There is **no business logic and no ORM here beyond fetching the impression to link**
(DESIGN §5b invariant 3): app validity, the tag snapshot, and impression-ownership
validation all stay enforced inside ``signals.capture`` (one source of truth).
"""

import logging
from uuid import UUID

from apps.core import observability
from apps.signals import capture
from apps.signals.kinds import Surface
from apps.signals.models import Impression

logger = logging.getLogger(__name__)


def record_page_view(request, app_id: UUID) -> UUID | None:
    """Emit an ``app_page``-surface impression for an authenticated visitor; return its id.

    Anonymous → returns ``None`` (nothing captured; the page still renders — AC5). Any
    capture failure → counted + logged, returns ``None`` (AC7). Never raises into the request.
    The returned id is what the page embeds in its try-it/share affordances so a later
    conversion links to this exact shown instance (DESIGN §6).
    """
    if not request.user.is_authenticated:
        return None
    try:
        impression = capture.record_impression(
            request.user, app_id, surface=Surface.APP_PAGE
        )
        return impression.id
    except Exception:
        _degrade("page_view")
        return None


def record_try_click(request, app_id: UUID, impression_id: UUID | None) -> None:
    """Emit a ``click_through`` linked to the visitor's page-view impression (AC6).

    ``click_through`` *requires* its originating impression (D-7), so a missing/unresolvable
    ``impression_id`` means **no event**. A forged/foreign id resolves but is rejected by
    capture's ownership check (``ImpressionMismatchError``) → caught here, no event (§10).
    Anonymous or any failure → no event, no raise (AC7).
    """
    if not request.user.is_authenticated:
        return
    try:
        impression = _resolve_impression(impression_id)
        if impression is None:
            return  # click_through requires an impression; none → no event
        capture.record_click_through(request.user, app_id, impression=impression)
    except Exception:
        _degrade("try_click")


def record_share(request, app_id: UUID, impression_id: UUID | None) -> None:
    """Emit a ``share`` for an authenticated visitor, optionally linked to its impression (AC6).

    ``share`` does not require an impression, so an absent/unresolvable ``imp`` still records
    the share (unlinked). Anonymous or any failure → no event, no raise (AC7).
    """
    if not request.user.is_authenticated:
        return
    try:
        impression = _resolve_impression(impression_id)
        capture.record_share(request.user, app_id, impression=impression)
    except Exception:
        _degrade("share")


def _resolve_impression(impression_id: UUID | None) -> Impression | None:
    """Fetch the impression to link, or ``None``. Ownership is validated inside capture (§10)."""
    if impression_id is None:
        return None
    return Impression.objects.filter(pk=impression_id).first()


def _degrade(action: str) -> None:
    """Count + log a caught capture loss without re-raising — the AC7 fail-soft seam.

    Called only from within an ``except`` block, so ``logger.exception`` captures the
    traceback; the counter makes the loss observable/alertable to operators (DESIGN §7/§9).
    """
    observability.increment(observability.APP_PAGE_CAPTURE_DEGRADED, action=action)
    logger.exception("app-page signal capture degraded (action=%s)", action)
