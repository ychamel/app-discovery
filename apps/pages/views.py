"""The three thin HTTP views for app-pages (DESIGN.md §3/§5a).

Mirrors the catalog server-rendered house pattern: each view parses input, calls the D-6
selector / the ``emission`` policy, and renders or redirects. It holds **no business logic
and no ORM access** — the catalog read is the single source of app content, ``emission`` is
the single capture seam.

The failure split (DESIGN §7) is the load-bearing rule here:
  * the **catalog read** is what makes the page a page → a failure is a **loud 500**
    (uncaught), a non-accepted/unknown id is a **404** (``not_available.html``, AC8);
  * **capture** is a side benefit to the corpus → handled fail-soft inside ``emission`` so
    render and redirect always proceed (AC7).
"""

import logging
import time
from uuid import UUID

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.catalog import selectors as catalog
from apps.core import observability
from apps.pages import emission

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def app_page(request, app_id: UUID):
    """GET /apps/<id>/ — render the uniform public page for an accepted app (AllowAny).

    A non-accepted/unknown id is a 404 (AC8); a catalog read that *raises* propagates as a
    loud 500 (DESIGN §7). For an authenticated visitor a page-view impression is emitted
    (fail-soft) and its id embedded so try-it/share link to this shown instance (DESIGN §6).
    """
    started = time.perf_counter()
    app = catalog.get_catalogued_app(app_id)
    if app is None:
        return _not_available(request)

    impression_id = emission.record_page_view(request, app_id)
    response = render(request, "pages/app_page.html", {"app": app, "imp": impression_id})
    observability.increment(observability.APP_PAGE_RENDERED, app_id=str(app_id))
    logger.info(
        "app_page rendered app_id=%s duration_ms=%.1f",
        app_id,
        (time.perf_counter() - started) * 1000,
    )
    return response


@require_http_methods(["GET"])
def try_redirect(request, app_id: UUID):
    """GET /apps/<id>/try — record a click-through (fail-soft) then 302 to the app's URL.

    The redirect target is the app's **server-side stored** ``url``, never a request param →
    no open redirect (DESIGN §10). The redirect fires even if capture failed (AC7).
    """
    app = catalog.get_catalogued_app(app_id)
    if app is None:
        return _not_available(request)

    emission.record_try_click(request, app_id, _parse_imp(request.GET.get("imp")))
    return redirect(app.url)


@require_http_methods(["POST"])
def share(request, app_id: UUID):
    """POST /apps/<id>/share — record a share (fail-soft); return 204. CSRF-protected.

    Anonymous → still 204, nothing captured (the page stays shareable — AC4/AC7).
    """
    app = catalog.get_catalogued_app(app_id)
    if app is None:
        return _not_available(request)

    emission.record_share(request, app_id, _parse_imp(request.POST.get("imp")))
    return HttpResponse(status=204)


def _not_available(request) -> HttpResponse:
    """The AC8 response: a requested id is not a live catalog entry → 404 + counter."""
    observability.increment(observability.APP_PAGE_NOT_AVAILABLE)
    return render(request, "pages/not_available.html", status=404)


def _parse_imp(raw: str | None) -> UUID | None:
    """Parse the optional ``imp`` impression id; a malformed value is treated as absent.

    Validity (ownership/app linkage) is enforced inside capture (DESIGN §10), so a malformed
    id is simply no link — never an error to the visitor.
    """
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        return None
