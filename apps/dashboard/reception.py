"""The composition layer: assemble an app's reception view-model (DESIGN.md §3/§5.2).

This is the one place that *assembles* reception. It calls the four read surfaces
(catalog D-6, signals D-7, ratings D-8), orders the reach surfaces **curated-first** via
``ratings.gate.CURATED_SURFACES`` (the single D-8 source — never re-defined here), densifies
the sparse trend onto a continuous axis, and projects everything to frozen view-model DTOs.

It holds **no ORM access** of its own; the dashboard's only business logic is this
composition + ordering. The failure split (DESIGN §7) lives here too:

  * the **core reception read** (``impression_breakdown`` / ``impression_trend`` /
    ``app_funnel``) is left to **raise** — the view turns that into a loud 500, never a
    fake-empty page (a fabricated empty dashboard would lie about H2 / corrupt M1/M3/M4, R1);
  * the **reviews slot** fails **soft** — a ratings read error degrades only that slot
    (``ReviewsView.available=False``), the rest of the view still renders.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from apps.catalog import selectors as catalog
from apps.catalog.models import App
from apps.core import config, observability
from apps.dashboard import charts
from apps.dashboard.windows import REPORTING_WINDOWS, ReportingWindow, ResolvedWindow
from apps.ratings import selectors as ratings
from apps.ratings.gate import CURATED_SURFACES
from apps.signals import selectors as signals
from apps.signals.kinds import Surface
from apps.signals.selectors import TrendGranularity
from apps.widget import selectors as widget

logger = logging.getLogger(__name__)


# --- View-model DTOs (all frozen; template + tests only — DESIGN §5.2/§5.4) --------
@dataclass(frozen=True)
class SurfaceReach:
    """One source's reach within a window — curated sources are flagged (DESIGN §5.2)."""

    surface: str  # the Surface value
    label: str  # Surface.label (human)
    count: int
    is_curated: bool  # surface in CURATED_SURFACES (D-8, reused)


@dataclass(frozen=True)
class TrendBucket:
    """One time bucket on the reach trend axis (DESIGN §5.2). ``curated`` is the AC10 line."""

    label: str  # the axis label, e.g. "2026-06-17", "Wk of 2026-06-15", "Jun 2026"
    total: int
    curated: int  # Σ over CURATED_SURFACES for this bucket


@dataclass(frozen=True)
class TrendView:
    """The reach trend: a dense bucket series + its sparkline geometry (AC10)."""

    granularity_label: str
    buckets: list[TrendBucket]  # DENSE — every bucket in the window, zero-filled
    sparkline: charts.SparklineSvg | None  # None ⇒ the window is empty (AC4)
    is_empty: bool


@dataclass(frozen=True)
class ReachView:
    """The combined reach: total + per-source breakdown (curated-first) + the trend (AC3)."""

    total: int
    surfaces: list[SurfaceReach]  # curated first (DIGEST highlighted), then the rest
    trend: TrendView


@dataclass(frozen=True)
class FunnelView:
    """A presentation projection of ``AppFunnel`` — no new numbers (DESIGN §5.2, AC5)."""

    impressions: int
    click_throughs: int
    returns_short: int
    returns_long: int
    short_days: int  # the configured short return-window length (label, not magic)
    long_days: int
    subscribes: int
    page_reengagements: int
    shares: int
    off_platform_proxy: int  # shown SEPARATELY — never folded into click_throughs (AC5)


@dataclass(frozen=True)
class ReviewsView:
    """The reviews slot — raw count + distribution + capped list, no average (AC6)."""

    available: bool  # False ⇒ the slot degraded (fail-soft, §7)
    total_count: int
    distribution: dict[int, int]  # raw per-score count — NO average
    reviews: list[ratings.ReviewRow]  # capped at reviews_display_limit()


@dataclass(frozen=True)
class WidgetReachView:
    """The off-platform widget slot: reach + the conversion funnel stage (AC9; WCA-DESIGN-8).

    A clearly-distinct fact from the on-platform per-``Surface`` breakdown: anonymous reach driven
    by the embeddable widget (impressions + click-throughs), plus the **downstream conversions**
    that reach produced — ``follows`` of the app and new ``accounts`` credited to the widget
    (widget-conversion-attribution AC3). Both halves come from separate tables (one source of truth
    per fact) and are read **together**, so the whole slot degrades as one on any read error
    (``available=False``, fail-soft §8) while the rest of the reception still renders.

    The two **rates** — the click-through rate and the M2 conversion rate — are derived at display
    from these integers, never stored. ``conversions_total`` (``follows + accounts``) is the M2
    numerator, computed here at request time (not persisted) so the template can derive the rate.
    """

    available: bool
    impressions: int
    click_throughs: int
    follows: int
    accounts: int
    conversions_total: int


@dataclass(frozen=True)
class ReceptionSummary:
    """One row of the my-apps list (S1) — a bounded reception summary per app (AC1/AC9)."""

    app_id: UUID
    app_name: str
    total_impressions: int
    curated_impressions: int
    click_throughs: int
    widget_impressions: int  # off-platform widget reach (embeddable-update-widget AC9)


@dataclass(frozen=True)
class AppReception:
    """The per-app reception view (S2–S5) — reach + funnel + reviews over a window."""

    app_id: UUID
    app_name: str
    window: ReportingWindow
    available_windows: tuple[ReportingWindow, ...]
    reach: ReachView
    funnel: FunnelView
    reviews: ReviewsView
    widget_reach: WidgetReachView  # off-platform widget reach (AC9; fail-soft, §8)


# --- The two composition entry points ----------------------------------------
def build_my_apps_summaries(
    owner, *, window: ResolvedWindow
) -> list[ReceptionSummary]:
    """The S1 list — the owner's accepted apps, each with a bounded reception summary (AC1/AC9).

    Owned, **ACCEPTED-only**. Bounded: ONE ``funnel_for_apps`` (2 queries) + ONE
    ``impression_breakdown_for_apps`` (1 query) for **all** K apps — the total query count is
    independent of K (the AC9 N+1 trap; never a per-app funnel). An owner with no accepted apps
    gets ``[]`` (the own-nothing state, AC2). **Raises** on a signals DB error (fail loud, §7).
    """
    apps = _accepted_owned_apps(owner)
    if not apps:
        return []

    app_ids = [app.id for app in apps]
    funnels = {
        funnel.app_id: funnel
        for funnel in signals.funnel_for_apps(
            app_ids, start=window.start, end=window.end
        )
    }
    breakdowns = signals.impression_breakdown_for_apps(
        app_ids, start=window.start, end=window.end
    )
    widget_impressions = _bulk_widget_impressions(app_ids, window)  # fail-soft column (§8)
    return [
        ReceptionSummary(
            app_id=app.id,
            app_name=app.name,
            total_impressions=breakdowns[app.id].total,
            curated_impressions=_curated_total(breakdowns[app.id].by_surface),
            click_throughs=funnels[app.id].click_throughs,
            widget_impressions=widget_impressions.get(app.id, 0),
        )
        for app in apps
    ]


def build_app_reception(
    owner, app_id: UUID, *, window: ResolvedWindow
) -> AppReception | None:
    """The S2–S5 per-app view, or ``None`` if it is not the caller's accepted app (AC1/AC2/AC8).

    ``None`` when ``get_owned_app`` is ``None`` **or** the app is not ACCEPTED — a non-owner's
    id is indistinguishable from not-found (the view 404s; no enumeration, R3). Reach and funnel
    are left to **raise** loud on a signals DB error (§7); the reviews slot degrades soft.
    """
    app = catalog.get_owned_app(owner, app_id)
    if app is None or app.status != App.Status.ACCEPTED:
        return None

    return AppReception(
        app_id=app.id,
        app_name=app.name,
        window=window.window,
        available_windows=REPORTING_WINDOWS,
        reach=_build_reach(app_id, window),  # raises loud on a signals error (§7)
        funnel=_build_funnel(app_id, window),  # raises loud on a signals error (§7)
        reviews=_build_reviews(app_id),  # fails soft (§7)
        widget_reach=_build_widget_reach(app_id, window),  # fails soft (§8)
    )


# --- Reach (breakdown + trend) -----------------------------------------------
def _build_reach(app_id: UUID, window: ResolvedWindow) -> ReachView:
    """Assemble the reach view: per-source breakdown (curated-first) + the densified trend."""
    breakdown = signals.impression_breakdown(
        app_id, start=window.start, end=window.end
    )
    return ReachView(
        total=breakdown.total,
        surfaces=_curated_first_surfaces(breakdown.by_surface),
        trend=_build_trend(app_id, window),
    )


def _curated_first_surfaces(by_surface: dict[str, int]) -> list[SurfaceReach]:
    """Project the per-surface counts to ``SurfaceReach`` rows, **curated sources first** (AC3).

    Iterates the whole ``Surface`` vocabulary (so a zero source is present, AC4), then a stable
    sort floats the curated sources to the front while preserving declaration order within each
    group — DIGEST first, then APP_PAGE and any later surface.
    """
    reaches = [
        SurfaceReach(
            surface=value,
            label=Surface(value).label,
            count=by_surface[value],
            is_curated=value in CURATED_SURFACES,
        )
        for value in Surface.values
    ]
    return sorted(reaches, key=lambda reach: not reach.is_curated)


def _build_trend(app_id: UUID, window: ResolvedWindow) -> TrendView:
    """Read the sparse trend, densify it onto the continuous axis, and build the sparkline."""
    sparse = signals.impression_trend(
        app_id, start=window.start, end=window.end, granularity=window.granularity
    )
    dense = _densify(sparse, window)
    sparkline = charts.build_sparkline(dense)
    return TrendView(
        granularity_label=window.granularity.label,
        buckets=dense,
        sparkline=sparkline,
        is_empty=sparkline is None,
    )


def _densify(
    sparse: list[signals.ImpressionBucket], window: ResolvedWindow
) -> list[TrendBucket]:
    """Map the sparse selector buckets onto the full ordered axis the window implies (AC10).

    The inverse of the selector's sparseness — every bucket in the window is present, with
    explicit zeros where there were no impressions. The axis runs from the window's start
    bucket to its end bucket; for **all-time** (no fixed start) it is anchored at the first
    bucket that actually has data, so the axis stays bounded by data age (M6), not by the epoch.
    """
    if not sparse:
        return []

    granularity = window.granularity
    upper = _truncate(window.end, granularity)
    if window.window.duration is None:
        lower = sparse[0].bucket_start  # all-time: anchor at the first data bucket
    else:
        lower = _truncate(window.start, granularity)

    by_start = {bucket.bucket_start: bucket for bucket in sparse}
    return [
        _to_trend_bucket(start, by_start.get(start), granularity)
        for start in _bucket_axis(lower, upper, granularity)
    ]


def _to_trend_bucket(
    start: datetime,
    bucket: "signals.ImpressionBucket | None",
    granularity: TrendGranularity,
) -> TrendBucket:
    """Project one axis position to a ``TrendBucket`` — zero-filled when there was no data."""
    if bucket is None:
        return TrendBucket(label=_bucket_label(start, granularity), total=0, curated=0)
    return TrendBucket(
        label=_bucket_label(start, granularity),
        total=bucket.total,
        curated=_curated_total(bucket.by_surface),
    )


# --- Funnel + reviews --------------------------------------------------------
def _build_funnel(app_id: UUID, window: ResolvedWindow) -> FunnelView:
    """Project the raw ``AppFunnel`` to its presentation view — no new numbers (AC5)."""
    funnel = signals.app_funnel(app_id, start=window.start, end=window.end)
    return FunnelView(
        impressions=funnel.impressions,
        click_throughs=funnel.click_throughs,
        returns_short=funnel.returns_3d,
        returns_long=funnel.returns_14d,
        short_days=config.return_window_short_days(),
        long_days=config.return_window_long_days(),
        subscribes=funnel.subscribes,
        page_reengagements=funnel.page_reengagements,
        shares=funnel.shares,
        off_platform_proxy=funnel.off_platform_proxy,
    )


def _build_reviews(app_id: UUID) -> ReviewsView:
    """The reviews slot, degrading **soft** on a ratings read error (§7/DD-DESIGN-4)."""
    try:
        reviews = ratings.reviews_for_app(
            app_id, limit=config.reviews_display_limit()
        )
    except Exception:
        observability.increment(
            observability.DASHBOARD_REVIEWS_DEGRADED, app_id=str(app_id)
        )
        logger.warning(
            "dashboard reviews read failed; degrading the reviews slot app_id=%s",
            app_id,
            exc_info=True,
        )
        return ReviewsView(
            available=False, total_count=0, distribution={}, reviews=[]
        )
    return ReviewsView(
        available=True,
        total_count=reviews.total_count,
        distribution=reviews.distribution,
        reviews=reviews.reviews,
    )


# --- Widget reach (off-platform, AC9; fail-soft like the reviews slot, §8) ----
def _build_widget_reach(app_id: UUID, window: ResolvedWindow) -> WidgetReachView:
    """The Screen-B widget slot (reach + conversions), degrading **soft** as one on error (§8).

    Distinct from the on-platform per-``Surface`` reach — this is anonymous off-platform reach
    driven by the embeddable widget, plus the conversions it produced (AC3). Reach and conversions
    are read **together** so a failure of either degrades the **whole** slot (one consistent
    affordance); the rest of Screen B (the loud signals reads) is unaffected.
    """
    try:
        reach = widget.widget_reach(app_id, start=window.start, end=window.end)
        conversions = widget.widget_conversions(
            app_id, start=window.start, end=window.end
        )
    except Exception:
        observability.increment(
            observability.DASHBOARD_WIDGET_DEGRADED, app_id=str(app_id)
        )
        logger.warning(
            "dashboard widget slot read failed; degrading the slot app_id=%s",
            app_id,
            exc_info=True,
        )
        return WidgetReachView(
            available=False,
            impressions=0,
            click_throughs=0,
            follows=0,
            accounts=0,
            conversions_total=0,
        )
    return WidgetReachView(
        available=True,
        impressions=reach.impressions,
        click_throughs=reach.click_throughs,
        follows=conversions.follows,
        accounts=conversions.accounts,
        conversions_total=conversions.follows + conversions.accounts,
    )


def _bulk_widget_impressions(
    app_ids: list[UUID], window: ResolvedWindow
) -> dict[UUID, int]:
    """Widget impressions per app for the S1 column in ONE bulk read — no N+1 (AC9).

    Fail-soft for the **whole column**: a read error returns ``{}`` (every app shows 0) after
    counting ``DASHBOARD_WIDGET_DEGRADED`` — the rest of the my-apps list still renders.
    """
    try:
        reaches = widget.widget_reach_for_apps(
            app_ids, start=window.start, end=window.end
        )
    except Exception:
        observability.increment(observability.DASHBOARD_WIDGET_DEGRADED)
        logger.warning(
            "dashboard my-apps widget-reach read failed; widget column degraded to 0",
            exc_info=True,
        )
        return {}
    return {app_id: reach.impressions for app_id, reach in reaches.items()}


# --- Helpers -----------------------------------------------------------------
def _accepted_owned_apps(owner) -> list[App]:
    """The owner's apps filtered to ACCEPTED only — the dashboard's reporting scope (AC1)."""
    return [
        app
        for app in catalog.list_owned_apps(owner)
        if app.status == App.Status.ACCEPTED
    ]


def _curated_total(by_surface: dict[str, int]) -> int:
    """Σ the per-surface counts over the curated surfaces (D-8 definition, reused)."""
    return sum(by_surface.get(surface, 0) for surface in CURATED_SURFACES)


# --- Trend-axis arithmetic (matches the selector's UTC Trunc{Day,Week,Month}) -----
def _truncate(moment: datetime, granularity: TrendGranularity) -> datetime:
    """Truncate ``moment`` to the start of its bucket — mirrors the selector's UTC Trunc.

    DAY → UTC midnight; WEEK → the Monday of that week (Django's TruncWeek week start);
    MONTH → the first of the month. Keeps the densify axis aligned with the selector keys.
    """
    day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == TrendGranularity.DAY:
        return day_start
    if granularity == TrendGranularity.WEEK:
        return day_start - timedelta(days=day_start.weekday())
    return day_start.replace(day=1)


def _bucket_axis(
    lower: datetime, upper: datetime, granularity: TrendGranularity
) -> list[datetime]:
    """Every bucket start from ``lower`` to ``upper`` inclusive, at ``granularity`` (ascending)."""
    axis: list[datetime] = []
    current = lower
    while current <= upper:
        axis.append(current)
        current = _next_bucket(current, granularity)
    return axis


def _next_bucket(start: datetime, granularity: TrendGranularity) -> datetime:
    """The next bucket start after ``start`` at ``granularity`` (handles month/year rollover)."""
    if granularity == TrendGranularity.DAY:
        return start + timedelta(days=1)
    if granularity == TrendGranularity.WEEK:
        return start + timedelta(days=7)
    if start.month == 12:
        return start.replace(year=start.year + 1, month=1)
    return start.replace(month=start.month + 1)


def _bucket_label(start: datetime, granularity: TrendGranularity) -> str:
    """The human axis label for a bucket start, by granularity (AC10 table fallback)."""
    if granularity == TrendGranularity.DAY:
        return start.strftime("%Y-%m-%d")
    if granularity == TrendGranularity.WEEK:
        return f"Wk of {start.strftime('%Y-%m-%d')}"
    return start.strftime("%b %Y")
