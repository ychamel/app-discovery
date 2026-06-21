"""The three thin HTTP views for subscriptions (DESIGN.md §5g/§6.4).

Mirrors the pages/ratings house pattern: each view **parses input, calls a service/selector,
and redirects or renders** — it holds no business logic and no ORM access.

Own-data-only is **structural** (DESIGN §8): no subscription id appears in any URL. A follow
is addressed by ``request.user`` + ``app_id``, so a user can only ever touch their own — no
id to tamper with (no IDOR). All three routes are ``login_required``; the mutations are POST
+ CSRF.

The failure split (DESIGN §9): the **write** fails loud where correctness depends on it but
the *view* surfaces a follow/unfollow fault as a user message + PRG (the durable state is
honest — AC7); the **feed read** fails soft so a subscriptions fault never 500s the feed
(AC4 "never an error").
"""

import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core import config, observability
from apps.subscriptions import notices, selectors, services
from apps.subscriptions.errors import UnknownAppError

logger = logging.getLogger(__name__)

_FOLLOW_FAILED_MESSAGE = "Couldn't complete that — please try again."


@login_required
@require_http_methods(["POST"])
def follow(request, app_id: UUID):
    """POST /subscriptions/apps/<id>/follow — follow the app, then PRG to its page (AC1).

    An unknown/non-accepted app is a 404 (AC1). A capture/DB failure surfaces as a message
    and redirects back; the durable state is **not-followed** (the slot still shows Follow —
    AC7). Anonymous POSTs are redirected to sign-in by ``login_required`` (AC2).
    """
    try:
        services.follow_app(request.user, app_id)
    except UnknownAppError as exc:
        raise Http404("No such app to follow.") from exc
    except Exception:
        # The write fails loud inside services (CAPTURE_ERROR counted there); to the user it
        # is a try-again — never a 500, and honestly not-followed (AC7).
        logger.warning("follow failed app_id=%s", app_id, exc_info=True)
        messages.error(request, _FOLLOW_FAILED_MESSAGE)
    return redirect("pages:app-page", app_id=app_id)


@login_required
@require_http_methods(["POST"])
def unfollow(request, app_id: UUID):
    """POST /subscriptions/apps/<id>/unfollow — unfollow the app, then PRG (AC3)."""
    services.unfollow_app(request.user, app_id)
    return redirect("pages:app-page", app_id=app_id)


@login_required
@require_http_methods(["GET"])
def feed(request):
    """GET /subscriptions/feed — the personal followed-apps feed (AC4/AC6/AC8).

    Two regions (notices + followed apps), each read **fail-soft** so a subscriptions fault
    never 500s the feed (DESIGN §9): a ``followed_apps`` error → an empty/degraded feed +
    ``SUBSCRIPTION_FEED_DEGRADED``; a ``notices_for_apps`` error → "No news yet" +
    ``SUBSCRIPTION_NOTICE_DEGRADED``.
    """
    apps = _followed_apps_fail_soft(request.user)
    app_notices = _notices_fail_soft([app.id for app in apps])
    return render(
        request,
        "subscriptions/feed.html",
        {"apps": apps, "notices": app_notices},
    )


def _followed_apps_fail_soft(user):
    """The user's followed apps, or ``[]`` + a counted degradation on any read error."""
    try:
        return selectors.followed_apps(user, limit=config.followed_feed_page_size())
    except Exception:
        observability.increment(observability.SUBSCRIPTION_FEED_DEGRADED)
        logger.warning("followed-apps feed degraded", exc_info=True)
        return []


def _notices_fail_soft(app_ids):
    """Notices for the followed apps, or ``[]`` + a counted degradation on any read error."""
    try:
        return notices.notices_for_apps(app_ids)
    except Exception:
        observability.increment(observability.SUBSCRIPTION_NOTICE_DEGRADED)
        logger.warning("notice feed degraded", exc_info=True)
        return []
