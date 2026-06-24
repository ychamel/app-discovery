"""The followed-apps notice seam (DESIGN.md §5d/§6.3 — AS-3 = option A).

The followed-apps feed has a "reason to come back" region: update / early-access notices
about the apps a user follows. As of ``developer-updates`` (Phase 3) the producer exists:
``apps/updates`` owns the notices, and this seam is the **single adapter** that delegates to
it and maps the producer's ``PublishedNotice`` → the ``subscriptions``-owned render ``Notice``
(developer-updates DESIGN §6.4, DU-DESIGN-2).

The dependency stays one-directional — ``subscriptions.notices`` imports ``updates.selectors``,
never the reverse — so the two packages form a DAG with no import cycle (developer-updates
DESIGN §4/§13; ``apps/updates`` imports nothing from ``subscriptions``). Keeping the render
``Notice`` owned here (rather than importing the producer's DTO) is what keeps that direction
clean. ``notices_for_apps`` remains the one repoint point promised at AS-3, and its single call
site (``subscriptions.views._notices_fail_soft``) and the ``Notice`` shape are unchanged — the
feed template renders ``Notice``s exactly as before.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.core import config
from apps.updates import selectors as updates


@dataclass(frozen=True)
class Notice:
    """One update/early-access notice about a followed app — the render contract.

    Owned by ``subscriptions`` (the feed's package): the producer returns its own
    ``PublishedNotice`` and this seam maps to ``Notice``, so neither package imports the
    other's DTO and the dependency graph stays a DAG (DU-DESIGN-2).
    """

    app_id: UUID  # which followed app the news is about
    kind: str  # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime


def notices_for_apps(app_ids: list[UUID]) -> list[Notice]:
    """Notices for the given followed apps, newest first — the AS-3 producer read.

    Delegates to ``updates.selectors.published_notices_for_apps`` (bounded by
    ``config.updates_feed_notice_limit()``) and maps each ``PublishedNotice`` → the render
    ``Notice``, dropping the notice ``id`` the feed has no use for. ``[]`` when there are none;
    the feed template renders ``Notice``s unchanged.
    """
    published = updates.published_notices_for_apps(
        app_ids, limit=config.updates_feed_notice_limit()
    )
    return [_to_notice(notice) for notice in published]


def _to_notice(published: updates.PublishedNotice) -> Notice:
    """Map a producer ``PublishedNotice`` → the feed's render ``Notice`` (drops ``id``)."""
    return Notice(
        app_id=published.app_id,
        kind=published.kind,
        title=published.title,
        summary=published.summary,
        published_at=published.published_at,
    )
