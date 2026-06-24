"""The single write path for developer-updates (DESIGN.md §6.2) — the only place a notice
is created or withdrawn.

Every create / delete of a ``Notice`` goes through here, so the store's invariants live in
exactly one place (illegal states unrepresentable):

  * the ``app_id`` is one the ``author`` **owns** (D-6, AC1) — else ``AppNotOwnedError`` and
    nothing is written (the view 404s; no ownership oracle);
  * ``kind`` / ``title`` / ``summary`` are validated at the boundary **before** any write —
    else ``InvalidNoticeError`` and nothing is written (AC2/AC3);
  * posting is rate-limited from the **durable notice rows** (count own recent rows in a config
    window) — exact and multi-worker-correct without cache infra (AC8, DU-DESIGN-4).

This module **imports nothing from ``signals.capture``** (AC6, the structural transparency
line — DESIGN §8, asserted by ``tests/test_imports.py``): a notice is *content*, never a
score-bearing corpus signal. Posting confers no reach.
"""

import logging
from datetime import timedelta
from uuid import UUID

from django.utils import timezone

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.updates.errors import AppNotOwnedError, InvalidNoticeError, RateLimitedError
from apps.updates.models import Notice, NoticeKind
from apps.updates.selectors import PublishedNotice

logger = logging.getLogger(__name__)

_VALID_KINDS = frozenset(NoticeKind.values)


def post_notice(
    author, app_id: UUID, *, kind: str, title: str, summary: str
) -> PublishedNotice:
    """Create one notice on an app ``author`` owns (AC1/AC2/AC3/AC8).

    Gates ownership (AC1), validates the input (AC2/AC3), and enforces the durable per-app
    rate-limit (AC8) — each **before** any write, so a rejected post leaves no row. On success
    writes one ``updates_notice`` row (``published_at = now``) and counts
    ``UPDATES_NOTICE_POSTED{kind}``.
    """
    _require_owned_app(author, app_id)
    clean_title, clean_summary = _validate(kind, title, summary)
    _enforce_rate_limit(author, app_id)

    notice = Notice.objects.create(
        author=author,
        app_id=app_id,
        kind=kind,
        title=clean_title,
        summary=clean_summary,
    )
    observability.increment(observability.UPDATES_NOTICE_POSTED, kind=kind)
    logger.info("notice posted app_id=%s notice_id=%s kind=%s", app_id, notice.id, kind)
    return PublishedNotice.from_model(notice)


def withdraw_notice(author, app_id: UUID, notice_id: UUID) -> bool:
    """Hard-delete the ``author``'s own notice, scoped by author + app_id + id (AC7, no IDOR).

    Idempotent: a foreign/unknown ``notice_id`` matches no row, so it deletes nothing and
    returns ``False`` (no error, no leak, no counter). A real delete returns ``True`` and
    counts ``UPDATES_NOTICE_WITHDRAWN``.
    """
    deleted_count, _ = Notice.objects.filter(
        author=author, app_id=app_id, id=notice_id
    ).delete()
    existed = deleted_count > 0
    if existed:
        observability.increment(observability.UPDATES_NOTICE_WITHDRAWN)
        logger.info("notice withdrawn app_id=%s notice_id=%s", app_id, notice_id)
    return existed


# --- Boundaries --------------------------------------------------------------
def _require_owned_app(author, app_id: UUID) -> None:
    """Raise ``AppNotOwnedError`` unless ``author`` owns ``app_id`` (D-6, AC1).

    ``get_owned_app`` returns ``None`` for an unknown id *and* for another developer's app —
    indistinguishable, so the view 404 leaks no ownership oracle.
    """
    if catalog.get_owned_app(author, app_id) is None:
        raise AppNotOwnedError(f"App {app_id!r} is not owned by this author.")


def _validate(kind: str, title: str, summary: str) -> tuple[str, str]:
    """Reject a bad kind or a blank/over-length title/summary at the boundary (AC2/AC3).

    Returns the stripped title/summary on success; raises ``InvalidNoticeError`` (counting
    ``UPDATES_POST_REJECTED{reason=invalid}``) before any write otherwise.
    """
    if kind not in _VALID_KINDS:
        _reject(f"unknown notice kind {kind!r}.")

    clean_title = (title or "").strip()
    clean_summary = (summary or "").strip()
    if not clean_title:
        _reject("title must not be blank.")
    if not clean_summary:
        _reject("summary must not be blank.")

    title_max = config.updates_title_max_length()
    if len(clean_title) > title_max:
        _reject(f"title exceeds the {title_max}-character limit ({len(clean_title)}).")

    summary_max = config.updates_summary_max_length()
    if len(clean_summary) > summary_max:
        _reject(
            f"summary exceeds the {summary_max}-character limit ({len(clean_summary)})."
        )
    return clean_title, clean_summary


def _enforce_rate_limit(author, app_id: UUID) -> None:
    """Raise ``RateLimitedError`` if the author is at the per-app post limit for the window (AC8).

    Counts the author's own recent ``updates_notice`` rows for this app — the durable,
    table-derived limit (exact + multi-worker-correct without cache infra, DU-DESIGN-4). The
    count→create TOCTOU is an accepted, bounded spam-guardrail trade-off (DESIGN §5.3) — the
    limit is not a correctness invariant, so no row lock is taken.
    """
    window_start = timezone.now() - timedelta(hours=config.updates_post_window_hours())
    recent = Notice.objects.filter(
        author=author, app_id=app_id, published_at__gte=window_start
    ).count()
    if recent >= config.updates_max_posts_per_window():
        observability.increment(
            observability.UPDATES_POST_REJECTED, reason="rate_limited"
        )
        raise RateLimitedError(
            f"post limit reached for this app ({recent} in the last "
            f"{config.updates_post_window_hours()}h)."
        )


def _reject(message: str) -> None:
    """Count the boundary rejection and raise — invalid input fails loud, never silent (AC2)."""
    observability.increment(observability.UPDATES_POST_REJECTED, reason="invalid")
    raise InvalidNoticeError(message)
