"""The two thin GET views for the developer-dashboard (DESIGN.md §5.3/§6).

Mirrors the model-less-consumer house pattern (``apps/discovery/``, ``apps/pages/``): each
view parses the trust-boundary ``window`` param, gates (role + GET-only; owner-scope is
enforced *inside* ``reception`` — defence in depth), asks ``reception`` to compose the
view-model, and renders. It holds **no ORM access and no business logic** beyond that, and
**imports nothing from ``signals.capture``** — viewing a dashboard can never emit a D-7
impression of the developer's own app (AC8, enforced by ``tests/test_imports.py``).

The failure split (DESIGN §7) is the load-bearing rule:
  * the **core reception read** fails **loud** — a signals DB error increments
    ``DASHBOARD_RECEPTION_DEGRADED`` (the one alert) and propagates to a normal 500, never a
    fake-empty page that would lie about H2 / corrupt M1/M3/M4 (R1);
  * the **reviews slot** fails **soft** inside ``reception`` (``DASHBOARD_REVIEWS_DEGRADED``)
    and never changes the status code.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts import roles
from apps.accounts.permissions import require_role
from apps.core import observability
from apps.dashboard import reception, windows


@require_http_methods(["GET"])
@login_required
@require_role(roles.DEVELOPER)
def my_apps(request) -> HttpResponse:
    """GET /dashboard/ — the developer's accepted apps + a reception summary each (Screen A).

    Owner-scoped to ``request.user`` inside ``reception``; an owner with no accepted apps gets
    a 200 own-nothing state (AC2). A signals read raising is a loud 500 (§7).
    """
    resolved = windows.resolve_window(request.GET.get("window"), now=timezone.now())
    try:
        summaries = reception.build_my_apps_summaries(request.user, window=resolved)
    except Exception:
        observability.increment(observability.DASHBOARD_RECEPTION_DEGRADED)
        raise

    observability.increment(observability.DASHBOARD_MY_APPS_VIEWED)
    context = {
        "summaries": summaries,
        "windows": windows.REPORTING_WINDOWS,
        "active_window": resolved.window,
    }
    return render(request, "dashboard/my_apps.html", context)


@require_http_methods(["GET"])
@login_required
@require_role(roles.DEVELOPER)
def app_reception(request, app_id) -> HttpResponse:
    """GET /dashboard/apps/<id>/ — one owned app's reception over the window (Screen B).

    ``None`` from ``reception`` (not the caller's accepted app) is a 404 indistinguishable from
    a real not-found (no enumeration, AC8/R3). A core (signals) read raising is a loud 500 (§7);
    the reviews-slot degradation never changes the status code.
    """
    resolved = windows.resolve_window(request.GET.get("window"), now=timezone.now())
    try:
        view_model = reception.build_app_reception(
            request.user, app_id, window=resolved
        )
    except Exception:
        observability.increment(observability.DASHBOARD_RECEPTION_DEGRADED)
        raise

    if view_model is None:
        observability.increment(observability.DASHBOARD_ACCESS_DENIED)
        raise Http404("No such app")

    observability.increment(
        observability.DASHBOARD_RECEPTION_VIEWED, window=resolved.window.key
    )
    if _funnel_is_nonempty(view_model.funnel):
        observability.increment(observability.DASHBOARD_NONEMPTY_RECEPTION)

    context = {"reception": view_model, "windows": windows.REPORTING_WINDOWS}
    return render(request, "dashboard/app_reception.html", context)


def _funnel_is_nonempty(funnel: reception.FunnelView) -> bool:
    """True if any funnel count is non-zero — the M3 ``DASHBOARD_NONEMPTY_RECEPTION`` trigger."""
    return any(
        (
            funnel.impressions,
            funnel.click_throughs,
            funnel.returns_short,
            funnel.returns_long,
            funnel.subscribes,
            funnel.page_reengagements,
            funnel.shares,
            funnel.off_platform_proxy,
        )
    )
