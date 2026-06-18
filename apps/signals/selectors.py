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

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from django.db.models import (
    Count,
    DateField,
    DateTimeField,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Q,
)
from django.db.models.functions import TruncDate

from apps.core import config
from apps.signals.kinds import EventKind
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
