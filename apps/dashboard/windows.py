"""The reporting-window vocabulary for the developer-dashboard (DESIGN.md §4.3, DD-DESIGN-3).

The fixed set of 8 reporting windows the developer chooses between, plus each window's trend
**bucket granularity**, as a **code-fixed declarative table** — the change-cheap place: add
or remove a window by editing one tuple. It lives here (in the feature app), not in
``apps/core/config``, because it is a closed vocabulary like ``Surface`` or
``ratings.gate.CURATED_SURFACES``, not an env-tunable knob.

Granularity is chosen per window to keep the trend's bucket count bounded (the M6/AC9 lever):
DAY for ≤1-month windows (≤31 points), WEEK for the 3–6-month windows (≤26), MONTH for the
≥1-year and all-time windows (≤12·years — all-time is bounded by data age *because* it is
monthly).

``resolve_window`` is **fail-safe**: an unknown or blank key resolves to the default window
rather than raising, so a stale bookmark or hand-typed ``?window=`` can never 500 (DESIGN §7).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from apps.signals.selectors import TrendGranularity


@dataclass(frozen=True)
class ReportingWindow:
    """One selectable reporting window. ``duration is None`` ⇒ all-time (DESIGN.md §4.3)."""

    key: str  # the URL/query value, e.g. "1m"
    label: str  # the human selector label, e.g. "Last month"
    duration: timedelta | None  # None ⇒ all-time
    granularity: TrendGranularity  # the trend bucket grain for this window


@dataclass(frozen=True)
class ResolvedWindow:
    """A ``ReportingWindow`` resolved to a concrete ``[start, end]`` for the read surfaces."""

    window: ReportingWindow
    start: datetime
    end: datetime

    @property
    def granularity(self) -> TrendGranularity:
        return self.window.granularity


_DAY = TrendGranularity.DAY
_WEEK = TrendGranularity.WEEK
_MONTH = TrendGranularity.MONTH

# The 8 windows in selector display order (DESIGN.md §4.3). Order here = order on screen.
REPORTING_WINDOWS: tuple[ReportingWindow, ...] = (
    ReportingWindow("1w", "Last week", timedelta(days=7), _DAY),
    ReportingWindow("2w", "Last 2 weeks", timedelta(days=14), _DAY),
    ReportingWindow("1m", "Last month", timedelta(days=30), _DAY),
    ReportingWindow("3m", "Last 3 months", timedelta(days=90), _WEEK),
    ReportingWindow("6m", "Last 6 months", timedelta(days=180), _WEEK),
    ReportingWindow("1y", "Last year", timedelta(days=365), _MONTH),
    ReportingWindow("3y", "Last 3 years", timedelta(days=1095), _MONTH),
    ReportingWindow("all", "All time", None, _MONTH),
)

DEFAULT_WINDOW_KEY = "1m"

# Predates any possible event, so all-time is just a very early lower bound — the existing
# range-based selectors are reused unchanged rather than via a special all-time code path.
ALL_TIME_START = datetime(1970, 1, 1, tzinfo=UTC)

_WINDOWS_BY_KEY: dict[str, ReportingWindow] = {w.key: w for w in REPORTING_WINDOWS}


def resolve_window(key: str | None, *, now: datetime) -> ResolvedWindow:
    """Resolve a window ``key`` to a concrete ``[start, end]`` as of ``now`` (DESIGN.md §4.3).

    An unknown or blank key resolves to ``DEFAULT_WINDOW_KEY`` — never raises (AC7 fail-safe).
    ``end`` is ``now``; ``start`` is ``now − duration``, or ``ALL_TIME_START`` for all-time.
    """
    window = _WINDOWS_BY_KEY.get(key or "", _WINDOWS_BY_KEY[DEFAULT_WINDOW_KEY])
    start = ALL_TIME_START if window.duration is None else now - window.duration
    return ResolvedWindow(window=window, start=start, end=now)
