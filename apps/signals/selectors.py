"""The single read path for the signal corpus — the raw per-app funnel (DESIGN.md §5b/§9/§11).

Every consumer (the future developer-dashboard, the editorial H3 backtest) reads through
these functions; nothing reads ``signals_*`` directly past this surface. The funnel is the
proof the corpus is *backtestable without re-instrumentation* (H3): every field is
reconstructable from stored rows alone, with **no backfill** (AC8).

Three guarantees live here:

  * **Raw only, never scored (AC9/R5):** every field is a count or a derived count. There
    is no normalization, weighting, ranking, or score — turning these into a Quality Score
    is a *consumer's* job, out of scope.
  * **Returns are DERIVED, never stored (AC4/SC-9):** ``returns_3d``/``returns_14d`` are
    computed by joining each in-window impression to the existence of a ``PlatformVisit``
    for that user inside ``(occurred_at_date, +N]``, where N is a config tunable (no magic
    3/14). A *not-returned* outcome is the **absence** of such a visit — which no stored
    "return event" could represent. One ``EXISTS``-aggregate per call, never per-impression
    Python looping.
  * **The off-platform proxy is segregated (AC7):** ``off_platform_proxy`` (is_proxy=True)
    is counted in its own field and never folded into ``click_throughs`` or any on-platform
    count — the funnel is complete from on-platform signal alone.

This is an **internal/admin** surface (§5c/§10): in-process selectors only, no public/DRF
endpoint at MVP. When the developer-dashboard needs HTTP it adds a thin ``HasRole(ADMIN)``-
gated read view over these selectors — a one-feature-later addition, not built here.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from django.db import models
from django.db.models import (
    Count,
    DateField,
    DateTimeField,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Q,
)
from django.db.models.functions import TruncDate, TruncDay, TruncMonth, TruncWeek

from apps.core import config
from apps.signals.kinds import EventKind, Surface
from apps.signals.models import EngagementEvent, Impression, PlatformVisit


@dataclass(frozen=True)
class AppFunnel:
    """The raw per-app funnel over an evaluation window — the H3 backtest shape (AC8/AC9).

    Every field is a count or a derived count. There is deliberately **no** score/weight/
    rank field: scoring is the consumer's job (R5).
    """

    app_id: UUID
    impressions: int
    click_throughs: int
    returns_3d: int            # DERIVED: impressed users active in (impression, +3d]
    returns_14d: int           # DERIVED: … +14d
    subscribes: int
    page_reengagements: int
    shares: int
    off_platform_proxy: int    # SECONDARY (is_proxy=True) — reported separately (AC7)


# --- Returns derivation (the one non-trivial query) --------------------------
def _qualifying_visit(days: int):
    """A correlated subquery: does the impression's user have a return visit within N days?

    "Returned within N days of impression *I*" = ∃ a ``PlatformVisit`` for ``I.user`` with
    ``visit_date ∈ (I.occurred_at_date, I.occurred_at_date + N]`` — strictly after the show
    day (a same-day visit is not a *return*) through N days later, inclusive. All date math
    is in UTC, matching how ``capture.record_platform_visit`` stores ``visit_date``.
    """
    # Wrap the OuterRef so TruncDate can read an output_field, keeping all date math inside
    # the correlated subquery (so it works identically for a single .aggregate and a grouped
    # .values().annotate(), with no per-row annotation leaking into a GROUP BY).
    occurred_at = ExpressionWrapper(
        OuterRef("occurred_at"), output_field=DateTimeField()
    )
    show_date = TruncDate(occurred_at, tzinfo=UTC)
    upper_bound = ExpressionWrapper(
        show_date + timedelta(days=days), output_field=DateField()
    )
    return PlatformVisit.objects.filter(
        user_id=OuterRef("user_id"),
        visit_date__gt=show_date,
        visit_date__lte=upper_bound,
    )


def _returns_annotations() -> dict:
    """The two derived-returns aggregates, with window lengths read from config (no magic N)."""
    short_days = config.return_window_short_days()
    long_days = config.return_window_long_days()
    return {
        "returns_3d": Count("pk", filter=Q(Exists(_qualifying_visit(short_days)))),
        "returns_14d": Count("pk", filter=Q(Exists(_qualifying_visit(long_days)))),
    }


def _event_annotations() -> dict:
    """Per-kind raw counts. Proxy is its own field — never folded into click-throughs (AC7)."""
    return {
        "click_throughs": Count("pk", filter=Q(kind=EventKind.CLICK_THROUGH)),
        "subscribes": Count("pk", filter=Q(kind=EventKind.SUBSCRIBE)),
        "page_reengagements": Count("pk", filter=Q(kind=EventKind.PAGE_REENGAGEMENT)),
        "shares": Count("pk", filter=Q(kind=EventKind.SHARE)),
        "off_platform_proxy": Count("pk", filter=Q(kind=EventKind.OFF_PLATFORM_PROXY)),
    }


def _build_funnel(app_id: UUID, impression_row: dict, event_row: dict) -> AppFunnel:
    """Assemble one ``AppFunnel`` from the impression and event aggregate rows (zeros default)."""
    return AppFunnel(
        app_id=app_id,
        impressions=impression_row.get("impressions", 0),
        returns_3d=impression_row.get("returns_3d", 0),
        returns_14d=impression_row.get("returns_14d", 0),
        click_throughs=event_row.get("click_throughs", 0),
        subscribes=event_row.get("subscribes", 0),
        page_reengagements=event_row.get("page_reengagements", 0),
        shares=event_row.get("shares", 0),
        off_platform_proxy=event_row.get("off_platform_proxy", 0),
    )


# --- Public read surface -----------------------------------------------------
def app_funnel(app_id: UUID, *, start: datetime, end: datetime) -> AppFunnel:
    """The per-app raw funnel over ``[start, end]`` — the H3 backtest (AC8).

    Two queries (impressions+returns, then events), all counts from stored rows — no
    backfill. Returns are derived per ``_qualifying_visit`` (SC-9).
    """
    impression_row = Impression.objects.filter(
        app_id=app_id, occurred_at__range=(start, end)
    ).aggregate(impressions=Count("pk"), **_returns_annotations())

    event_row = EngagementEvent.objects.filter(
        app_id=app_id, occurred_at__range=(start, end)
    ).aggregate(**_event_annotations())

    return _build_funnel(app_id, impression_row, event_row)


def funnel_for_apps(
    app_ids: list[UUID], *, start: datetime, end: datetime
) -> list[AppFunnel]:
    """Bulk funnels for several apps in a **bounded** number of queries — no N+1 (AC9).

    Two grouped queries total regardless of app count. Apps with no signal still return a
    zero-filled funnel, in the order requested.
    """
    impression_by_app = {
        row["app_id"]: row
        for row in (
            Impression.objects.filter(
                app_id__in=app_ids, occurred_at__range=(start, end)
            )
            .values("app_id")
            .annotate(impressions=Count("pk"), **_returns_annotations())
        )
    }
    event_by_app = {
        row["app_id"]: row
        for row in (
            EngagementEvent.objects.filter(
                app_id__in=app_ids, occurred_at__range=(start, end)
            )
            .values("app_id")
            .annotate(**_event_annotations())
        )
    }
    return [
        _build_funnel(
            app_id,
            impression_by_app.get(app_id, {}),
            event_by_app.get(app_id, {}),
        )
        for app_id in app_ids
    ]


def category_impressions(tag_id: UUID, *, start: datetime, end: datetime) -> int:
    """Count in-window impressions whose **frozen** capture-time snapshot includes ``tag_id``.

    The per-category baseline (AC2): how many shown instances carried this tag at show time,
    read from the immutable ``ImpressionTag`` snapshot (never re-resolved).
    """
    return (
        Impression.objects.filter(
            occurred_at__range=(start, end), tags__tag_id=tag_id
        )
        .distinct()
        .count()
    )


# --- Factual existence read (the ratings-reviews gate's evidence, D-7-compliant) ----
def has_impression(
    user_id,
    app_id: UUID,
    *,
    surfaces: Iterable[str],
    as_of: datetime | None = None,
) -> bool:
    """Does ``user_id`` have an impression of ``app_id`` on one of ``surfaces`` by ``as_of``?

    A pure existence check (an ``EXISTS``) over the impression corpus — **raw, never scored
    and never judged** (D-7 raw-only). It answers *whether* a show happened on the given
    surfaces; it does **not** decide what those surfaces *mean*. That judgement (e.g.
    "a DIGEST impression is organic curation") belongs to the consumer — see
    ``apps.ratings.gate.CURATED_SURFACES`` — so signals stays the neutral store.

    This is the missing per-user existence read the ratings-reviews gate needs: D-7 forbids
    reading ``signals_*`` directly past this selector surface, so the gate must read through
    here. Backed by the ``signals_imp_user_app_idx`` index on ``(user, app_id)``.

    ``as_of`` is an inclusive upper bound: an impression exactly at ``as_of`` counts, one
    strictly after does not. Omitting it considers impressions at any time.
    """
    matches = Impression.objects.filter(
        user_id=user_id, app_id=app_id, surface__in=list(surfaces)
    )
    if as_of is not None:
        matches = matches.filter(occurred_at__lte=as_of)
    return matches.exists()


# --- Surface-aware + time-bucketed reach reads (the developer-dashboard, §5.1) ----
# These are additive: the funnel reads above are unchanged, and like every read here
# signals stays NEUTRAL — it counts impressions per Surface and never decides which
# surface "means" curation (that judgement is ratings.gate.CURATED_SURFACES, the D-8
# source, composed by the dashboard). No model/migration/index: both reads are GROUP BY
# aggregates over signals_impression, filtered by (app_id, occurred_at) and so backed by
# the existing signals_imp_app_time_idx.
class TrendGranularity(models.TextChoices):
    """Time-bucket grain for ``impression_trend``. Truncates ``occurred_at`` in UTC."""

    DAY = "day", "day"
    WEEK = "week", "week"
    MONTH = "month", "month"


# Each grain truncates to the start of its period as a *datetime* (UTC midnight / Monday /
# first-of-month), so ImpressionBucket.bucket_start is uniformly a datetime across grains.
# (TruncDate would return a bare date for DAY and break that uniformity.)
_TRUNC_BY_GRANULARITY = {
    TrendGranularity.DAY: TruncDay,
    TrendGranularity.WEEK: TruncWeek,
    TrendGranularity.MONTH: TruncMonth,
}


@dataclass(frozen=True)
class ImpressionBreakdown:
    """Per-``Surface`` impression counts for one app over a window (developer-dashboard §5.1).

    ``by_surface`` enumerates **every** ``Surface`` value zero-filled, so a surface with no
    impressions reads ``0`` (the honest zero, AC4) and a surface added later appears
    automatically with no caller change (AC3). ``total`` equals ``app_funnel(...).impressions``
    for the same window — the §4.2 integrity invariant (both count Impression rows).
    """

    app_id: UUID
    total: int
    by_surface: dict[str, int]


@dataclass(frozen=True)
class ImpressionBucket:
    """One time bucket of an app's impressions, split per ``Surface`` (developer-dashboard §5.1).

    ``bucket_start`` is the truncated UTC bucket key. ``by_surface`` enumerates every
    ``Surface`` value zero-filled; ``total`` is their sum.
    """

    bucket_start: datetime
    total: int
    by_surface: dict[str, int]


def _zero_filled_surfaces() -> dict[str, int]:
    """A fresh per-``Surface`` counter map, every value zero (the honest-zero baseline, AC4)."""
    return {surface: 0 for surface in Surface.values}


def impression_breakdown(
    app_id: UUID, *, start: datetime, end: datetime
) -> ImpressionBreakdown:
    """Per-``Surface`` impression counts over ``[start, end]`` — ONE grouped query (AC3/AC4).

    ``by_surface`` enumerates ``Surface.values`` zero-filled; ``total`` is their sum and equals
    ``app_funnel(app_id, start, end).impressions`` (the §4.2 invariant). Raw counts only — no
    ordering, score, or weight. Backed by ``signals_imp_app_time_idx``.
    """
    by_surface = _zero_filled_surfaces()
    rows = (
        Impression.objects.filter(app_id=app_id, occurred_at__range=(start, end))
        .values("surface")
        .annotate(count=Count("pk"))
    )
    for row in rows:
        by_surface[row["surface"]] = row["count"]
    return ImpressionBreakdown(
        app_id=app_id, total=sum(by_surface.values()), by_surface=by_surface
    )


def impression_breakdown_for_apps(
    app_ids: list[UUID], *, start: datetime, end: datetime
) -> dict[UUID, ImpressionBreakdown]:
    """Bulk per-``Surface`` breakdown for several apps in ONE grouped query — no N+1 (AC9).

    Every requested app is present in the result (apps with no impressions get an all-zero
    breakdown); keyed by ``app_id``. The query count is constant regardless of how many apps
    are asked for — the bulk counterpart to ``funnel_for_apps``.
    """
    by_app = {app_id: _zero_filled_surfaces() for app_id in app_ids}
    rows = (
        Impression.objects.filter(app_id__in=app_ids, occurred_at__range=(start, end))
        .values("app_id", "surface")
        .annotate(count=Count("pk"))
    )
    for row in rows:
        by_app[row["app_id"]][row["surface"]] = row["count"]
    return {
        app_id: ImpressionBreakdown(
            app_id=app_id, total=sum(by_surface.values()), by_surface=by_surface
        )
        for app_id, by_surface in by_app.items()
    }


def impression_trend(
    app_id: UUID,
    *,
    start: datetime,
    end: datetime,
    granularity: TrendGranularity,
) -> list[ImpressionBucket]:
    """Impressions over ``[start, end]`` bucketed by ``granularity``, split per ``Surface`` (AC10).

    ONE grouped query. Returns only buckets with ≥1 impression — **sparse** on the time axis,
    ascending by ``bucket_start`` (the caller densifies to a continuous axis). Truncation is in
    UTC. Bucket count is bounded by the granularity the window chose (windows.py §4.3), so this
    holds at 100× corpus (M6).
    """
    trunc = _TRUNC_BY_GRANULARITY[granularity]
    rows = (
        Impression.objects.filter(app_id=app_id, occurred_at__range=(start, end))
        .annotate(bucket=trunc("occurred_at", tzinfo=UTC))
        .values("bucket", "surface")
        .annotate(count=Count("pk"))
    )
    by_bucket: dict[datetime, dict[str, int]] = {}
    for row in rows:
        surfaces = by_bucket.setdefault(row["bucket"], _zero_filled_surfaces())
        surfaces[row["surface"]] = row["count"]
    return [
        ImpressionBucket(
            bucket_start=bucket, total=sum(surfaces.values()), by_surface=surfaces
        )
        for bucket, surfaces in sorted(by_bucket.items())
    ]
