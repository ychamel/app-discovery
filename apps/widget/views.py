"""The two thin HTTP views for the embeddable widget (DESIGN §5.1/§5.2/§7/§8).

Mirrors the ``apps/pages`` server-rendered house pattern: each view parses input, calls
``content``/``attribution`` and the D-6 catalog selector, and renders or redirects. It holds
**no business logic and no ORM access** beyond rate-limiting and those calls.

Both routes are **AllowAny** (anonymous end users, AC5) and serve **only public content**. The
governing rule (the ``apps/pages`` precedent): the widget lives inside someone else's page, so a
failure must **never** 500 into the host — it degrades to a neutral framable page and is counted
for operators (DESIGN §8). The two side effects (impression + click-through counts) are wrapped
fail-soft so the render/redirect always proceeds (AC9 is best-effort to the user, loud to ops).
"""

import logging
import time
from uuid import UUID

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.core.ratelimit import ip_rate_limited_get
from apps.widget import attribution, content, source

logger = logging.getLogger(__name__)


@ip_rate_limited_get(
    config.widget_render_rate_limit_per_ip_per_minute,
    scope="widget_render",
    window_seconds=60,
    limited_metric=observability.WIDGET_RATE_LIMITED,
    degraded_metric=observability.WIDGET_LIMITER_DEGRADED,
)
@require_http_methods(["GET"])
@xframe_options_exempt
def widget_render(request, app_id: UUID):
    """GET /widget/<id>/ — render the framable widget for an accepted app (AllowAny, AC5/AC7).

    Per-IP rate-limited (AC8, the outer decorator → 429 before any render or count). A catalog
    read that *raises* degrades to the neutral unavailable page (200) rather than 500ing into the
    host (DESIGN §8); an unknown/non-accepted id is a 404. On a successful render one impression
    is counted fail-soft and the response is cacheable (DESIGN §9).
    """
    started = time.perf_counter()
    try:
        view = content.build_widget_view(app_id)
    except Exception:
        logger.exception("widget render degraded app_id=%s", app_id)
        observability.increment(observability.WIDGET_RENDER_DEGRADED)
        return render(request, "widget/unavailable.html", status=200)

    if view is None:
        observability.increment(observability.WIDGET_NOT_AVAILABLE)
        return render(request, "widget/unavailable.html", status=404)

    response = render(request, "widget/widget.html", {"view": view, "app_id": app_id})
    response["Cache-Control"] = f"public, max-age={config.widget_cache_max_age_seconds()}"
    _count_fail_soft(attribution.record_widget_impression, app_id)
    observability.increment(observability.WIDGET_RENDERED, app_id=str(app_id))
    if not view.notices:
        observability.increment(observability.WIDGET_EMPTY)
    logger.info(
        "widget rendered app_id=%s duration_ms=%.1f",
        app_id,
        (time.perf_counter() - started) * 1000,
    )
    return response


@require_http_methods(["GET"])
def widget_view_redirect(request, app_id: UUID):
    """GET /widget/<id>/view — count a click-through (fail-soft) then 302 to the app page.

    The redirect target is **server-derived** (``reverse("pages:app-page", [app_id])``), never a
    request param → no open redirect (F4/§9); the source marker never influences it. A
    non-accepted/unknown id is a 404 *before* any marker is set. The redirect fires even if the
    count or the marker failed (AC9/AC6 best-effort).
    """
    if catalog.get_catalogued_app(app_id) is None:
        observability.increment(observability.WIDGET_NOT_AVAILABLE)
        return render(request, "widget/unavailable.html", status=404)

    _count_fail_soft(attribution.record_widget_click_through, app_id)
    observability.increment(observability.WIDGET_CLICK_THROUGH, app_id=str(app_id))
    response = redirect(reverse("pages:app-page", args=[app_id]))
    # Arm the first-party source marker for downstream conversion attribution (T-04/T-05). The
    # click is a top-level nav onto the platform origin, so the cookie is first-party from birth.
    _set_marker_fail_soft(response, app_id)
    return response


def _count_fail_soft(record, app_id: UUID) -> None:
    """Run an ``attribution`` counter, swallowing any error after counting + logging it.

    Counting is best-effort to the end user (it must never break the host's page) but **loud to
    ops** — a sustained ``WIDGET_COUNT_DEGRADED`` means attribution is silently lossy (DESIGN §8).
    """
    try:
        record(app_id)
    except Exception:
        logger.exception("widget count degraded app_id=%s", app_id)
        observability.increment(observability.WIDGET_COUNT_DEGRADED)


def _set_marker_fail_soft(response, app_id: UUID) -> None:
    """Arm the source marker on the click 302, swallowing any error after counting + logging it.

    Like the reach count, attribution is best-effort to the visitor — a marker failure must never
    break the redirect — but **loud to ops** via ``WIDGET_CONVERSION_DEGRADED`` (DESIGN §9, AC6).
    The reach count is independent: a marker failure does not affect the click-through tally.
    """
    try:
        source.set_marker(response, app_id)
    except Exception:
        logger.exception("widget source marker degraded app_id=%s", app_id)
        observability.increment(observability.WIDGET_CONVERSION_DEGRADED)
