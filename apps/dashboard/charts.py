"""The pure inline-SVG sparkline helper for the reach trend (DESIGN.md §3/§5.2/§6, DD-DESIGN-5).

A dense trend series → the SVG geometry for two polylines: the **total**-impressions line and
the distinguished **curated** line (AC10). The coordinate math (scale to the series max, step
across the buckets) lives here so the template carries no arithmetic; the same series is
rendered exactly as numbers in a ``<table>`` fallback by the template.

**stdlib only** — no project imports, no I/O, no JS dependency (the D-4 server-rendered
default; alternative 4 — a client-side charting library — was rejected). The input is any
sequence of bucket-like objects exposing ``.total`` and ``.curated`` ints (the ``reception``
``TrendBucket`` DTO), so this module stays free of any app dependency and is unit-testable in
isolation.
"""

from dataclasses import dataclass

# Fixed SVG canvas. The viewBox makes the chart scale to its container; the template need only
# drop these polylines into an <svg viewBox="0 0 WIDTH HEIGHT">.
_WIDTH = 600.0
_HEIGHT = 120.0


@dataclass(frozen=True)
class SparklineSvg:
    """The geometry a template needs to draw the trend — no arithmetic left for the view."""

    width: float
    height: float
    total_points: str  # "x1,y1 x2,y2 …" for the total-impressions polyline
    curated_points: str  # "x1,y1 x2,y2 …" for the curated polyline


def build_sparkline(buckets) -> SparklineSvg | None:
    """Project a dense trend series to two polylines, or ``None`` for an empty window.

    Returns ``None`` when there are no buckets or every total is zero — the view then renders
    "no impressions in this window" rather than a degenerate flat chart (AC4/AC10). A
    single-bucket series is handled without a divide-by-zero (the lone point sits centred).
    """
    if not buckets:
        return None
    max_value = max(bucket.total for bucket in buckets)
    if max_value == 0:
        return None

    count = len(buckets)
    total_points = _polyline(
        [bucket.total for bucket in buckets], max_value=max_value, count=count
    )
    curated_points = _polyline(
        [bucket.curated for bucket in buckets], max_value=max_value, count=count
    )
    return SparklineSvg(
        width=_WIDTH,
        height=_HEIGHT,
        total_points=total_points,
        curated_points=curated_points,
    )


def _polyline(values: list[int], *, max_value: int, count: int) -> str:
    """Format one series of values as an SVG ``points`` string, scaled to ``max_value``."""
    return " ".join(
        f"{_x(index, count):.1f},{_y(value, max_value):.1f}"
        for index, value in enumerate(values)
    )


def _x(index: int, count: int) -> float:
    """The x coordinate for bucket ``index`` of ``count``; a lone bucket sits centred."""
    if count == 1:
        return _WIDTH / 2
    return index * _WIDTH / (count - 1)


def _y(value: int, max_value: int) -> float:
    """The y coordinate for ``value`` (SVG y grows downward, so the max sits at the top)."""
    return _HEIGHT - (value / max_value) * _HEIGHT
