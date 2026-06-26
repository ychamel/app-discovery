"""The single reader of ``widget_reach_count`` (DESIGN §5.2) — reach out, never ORM rows.

Two windowed reads, both pure and bounded, returning frozen ``WidgetReach`` DTOs (the boundary
discipline of ``catalog``/``updates``/``signals`` selectors — nothing past this surface touches
the model):

  * ``widget_reach`` — the impression + click-through totals for one app over a window.
  * ``widget_reach_for_apps`` — the bulk counterpart for the dashboard's K-app summary, in
    **one** grouped query (no N+1 — the ``impression_breakdown_for_apps`` discipline).

The click-through **rate** (M2) is derived at display from these two integers, never stored.
The ``[start, end]`` window is given as datetimes (the dashboard's reporting window); since the
rollup is keyed by UTC day, the bounds are mapped to their UTC calendar days for the
``count_date`` filter.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Sum

from apps.widget.kinds import WidgetEventKind
from apps.widget.models import WidgetReachCount


@dataclass(frozen=True)
class WidgetReach:
    """One app's widget reach within a window (DESIGN §5.2). The rate is derived, not stored."""

    impressions: int
    click_throughs: int


_ZERO = WidgetReach(impressions=0, click_throughs=0)


def widget_reach(app_id: UUID, *, start: datetime, end: datetime) -> WidgetReach:
    """The summed impression + click-through reach for ``app_id`` over ``[start, end]``.

    One grouped query (``SUM(count) GROUP BY kind``) over the window's UTC-day range, zero-filled
    (a kind with no rows ⇒ ``0``).
    """
    rows = (
        WidgetReachCount.objects.filter(
            app_id=app_id, count_date__range=(start.date(), end.date())
        )
        .values("kind")
        .annotate(total=Sum("count"))
    )
    counts = {row["kind"]: row["total"] for row in rows}
    return _reach_from_counts(counts)


def widget_reach_for_apps(
    app_ids: list[UUID], *, start: datetime, end: datetime
) -> dict[UUID, WidgetReach]:
    """Bulk windowed reach for several apps in ONE grouped query — no N+1 (DESIGN §5.2).

    Every requested app is present in the result (an app with no rows gets zero reach); keyed by
    ``app_id``. ``[]`` ⇒ ``{}``. The query count is constant regardless of how many apps are
    asked for — the bulk counterpart to ``widget_reach``.
    """
    if not app_ids:
        return {}
    counts_by_app: dict[UUID, dict[str, int]] = {app_id: {} for app_id in app_ids}
    rows = (
        WidgetReachCount.objects.filter(
            app_id__in=app_ids, count_date__range=(start.date(), end.date())
        )
        .values("app_id", "kind")
        .annotate(total=Sum("count"))
    )
    for row in rows:
        counts_by_app[row["app_id"]][row["kind"]] = row["total"]
    return {
        app_id: _reach_from_counts(counts) for app_id, counts in counts_by_app.items()
    }


def _reach_from_counts(counts: dict[str, int]) -> WidgetReach:
    """Project a ``{kind: total}`` map (possibly partial) to a zero-filled ``WidgetReach``."""
    return WidgetReach(
        impressions=counts.get(WidgetEventKind.IMPRESSION, 0),
        click_throughs=counts.get(WidgetEventKind.CLICK_THROUGH, 0),
    )
