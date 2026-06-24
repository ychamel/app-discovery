"""The read path for developer-updates (DESIGN.md §6.1) — notices out, never ORM rows.

Two reads, both pure and bounded:

  * ``published_notices_for_apps`` — the **AS-3 producer feed read**: the notices for a set of
    apps, newest-first, capped at ``limit``. The followed-apps feed pulls this for the apps a
    user already follows (delivery is *pull* — DESIGN §4/§13), so the read is bounded by
    ``limit`` and **independent of follower count** (R3); it never enumerates followers.
  * ``notices_for_channel`` — the owner's own notices for one app, newest-first (the AC7 manage
    list rendered with a Withdraw control).

Both return frozen ``PublishedNotice`` DTOs, never ``Notice`` ORM rows — the same boundary
discipline as ``catalog.selectors``/``subscriptions.selectors``: nothing past this surface
touches the model. This module imports nothing from ``apps.subscriptions``; the cross-package
reference is one-directional (``subscriptions.notices`` → here), keeping the dependency a DAG
(DESIGN §4/§13, proven in ``tests/test_seam.py``).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.updates.models import Notice


@dataclass(frozen=True)
class PublishedNotice:
    """One published notice as the read contract — the producer's output shape (DESIGN §6.1)."""

    id: UUID  # for the owner's Withdraw control (AC7); dropped by the feed seam adapter
    app_id: UUID
    kind: str  # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime

    @classmethod
    def from_model(cls, notice: "Notice") -> "PublishedNotice":
        """Map one ``Notice`` ORM row to its frozen DTO — the single mapping point.

        Used by both reads here and by ``services`` (which returns the DTO of a row it just
        created), so the model→DTO shape lives in exactly one place and cannot drift.
        """
        return cls(
            id=notice.id,
            app_id=notice.app_id,
            kind=notice.kind,
            title=notice.title,
            summary=notice.summary,
            published_at=notice.published_at,
        )


def published_notices_for_apps(app_ids: list[UUID], *, limit: int) -> list[PublishedNotice]:
    """Notices for ``app_ids``, newest-first, capped at ``limit`` — the AS-3 producer read.

    One query (``app_id IN (...) ORDER BY -published_at LIMIT limit``), ``[]`` for empty input.
    Bounded by ``limit`` and independent of follower count (R3) — the feed passes the apps it
    already resolved, so this never reads the follow graph.
    """
    if not app_ids:
        return []
    rows = Notice.objects.filter(app_id__in=app_ids).order_by("-published_at")[:limit]
    return [PublishedNotice.from_model(row) for row in rows]


def notices_for_channel(owner, app_id: UUID) -> list[PublishedNotice]:
    """The ``owner``'s own notices for ``app_id``, newest-first (AC7 manage list). One query.

    Scoped by ``author`` + ``app_id`` so a developer only ever sees their own notices for an
    app they own (the view gates ownership before calling this).
    """
    rows = Notice.objects.filter(author=owner, app_id=app_id).order_by("-published_at")
    return [PublishedNotice.from_model(row) for row in rows]
