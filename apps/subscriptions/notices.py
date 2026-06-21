"""The empty-until-producer notice seam (DESIGN.md §5d/§6.3 — AS-3 = option A).

The followed-apps feed has a "reason to come back" region: update / early-access notices
about the apps a user follows. Authoring those notices is a *future* feature
(``developer-updates``, Phase 3), so today there is no producer — but the **shape** and the
**single call site** ship now, so the feed renders the region (with its empty state) and
``developer-updates`` has a pinned contract to build against (AC8).

This is deliberately the minimum honest surface: a frozen DTO + one repointable function.
No producer, registry, or pluggable-provider machinery is built — that would be speculative
(CLAUDE.md §5.5); the producer is one named future feature, so a single function is the
right seam. When it ships, ``notices_for_apps`` is **the one place** to repoint; the feed
template renders ``Notice``s unchanged.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Notice:
    """One update/early-access notice about a followed app — the render contract.

    This is the shape ``developer-updates`` (Phase 3) must honor — pinned now, no "TBD",
    so the producer and the feed never have to negotiate it later.
    """

    app_id: UUID  # which followed app the news is about
    kind: str  # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime


def notices_for_apps(app_ids: list[UUID]) -> list[Notice]:
    """Notices for the given followed apps, newest first — ``[]`` until a producer exists.

    No producer ships at MVP (``developer-updates``, Phase 3) → returns ``[]`` for any input.
    This is the one place to repoint when that producer lands; the feed template renders
    ``Notice``s unchanged.
    """
    return []
