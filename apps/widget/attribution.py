"""The single writers of the widget rollup tables (DESIGN §5.2/§5.4/§6) — atomic daily increments.

**Reach** (embeddable-update-widget): ``record_widget_impression`` and
``record_widget_click_through`` each add one to today's ``(app_id, kind, count_date)`` row of
``widget_reach_count``. **Conversion** (widget-conversion-attribution): ``record_widget_conversion``
adds one to today's row of ``widget_conversion_count``. All three delegate to the shared
``rollup._increment_daily`` (DESIGN §6.2), so the concurrency-correct write lives in exactly one
place and each writer here is a one-line, single-responsibility entry point.

**The firewall (AC6 / M5 = 0) is structural here:** this module imports nothing from
``apps.signals``. A widget interaction or conversion therefore creates no D-7 corpus row and can
never be ``signals.has_impression(surfaces=CURATED_SURFACES)`` evidence — it does not exist in the
corpus to be read (DESIGN §3; AST-proven in ``tests/test_imports.py``).

Every entry point **trusts an ``app_id`` the caller already validated** — the reach writers an
ACCEPTED catalog id from the view (EUW-11); the conversion writer the marker's ``src``, which is
only ever a value we ourselves signed (``widget.source``). They **raise on a DB failure**; the
caller wraps the call fail-soft (the views, T-05/T-06) so counting can never break the host page,
a follow, or a registration.
"""

from uuid import UUID

from apps.widget.kinds import WidgetEventKind
from apps.widget.models import WidgetConversionCount, WidgetReachCount
from apps.widget.rollup import _increment_daily


def record_widget_impression(app_id: UUID) -> None:
    """Count one widget render for ``app_id`` against today's impression rollup row."""
    _increment_daily(WidgetReachCount, app_id, WidgetEventKind.IMPRESSION)


def record_widget_click_through(app_id: UUID) -> None:
    """Count one view-on-platform click for ``app_id`` against today's click-through row."""
    _increment_daily(WidgetReachCount, app_id, WidgetEventKind.CLICK_THROUGH)


def record_widget_conversion(app_id: UUID, kind: str) -> None:
    """Add one to today's ``(app_id, kind)`` ``widget_conversion_count`` row (DESIGN §5.4).

    The **single writer** of the conversion rollup. ``kind`` is a ``WidgetConversionKind`` value;
    ``app_id`` is the credited widget **source** — the marker's ``src``, which is only ever a value
    we ourselves signed, so it is trusted here (the validation boundary is the signature in
    ``widget.source``). Concurrency-correct via the shared ``_increment_daily``. **Raises** on a DB
    error; the fail-soft hook (T-06) wraps it so a conversion miss never breaks a follow or a
    registration.
    """
    _increment_daily(WidgetConversionCount, app_id, kind)
