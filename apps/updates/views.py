"""The thin HTTP layer for developer-updates (DESIGN.md §6.5/§7/§8).

Mirrors the pages/ratings/subscriptions house pattern: each view **gates, parses input, calls a
service/selector, and renders or redirects** — it holds no ORM access and no business logic
beyond gating (the gate, validation, rate-limit, and the store all live behind ``services`` /
``selectors``). This module **imports nothing from ``signals.capture``** (AC6, enforced by
``tests/test_imports.py``): viewing or posting a notice never emits a D-7 signal.

All four routes are ``require_role(DEVELOPER)`` (D-3, fail-closed) + ``login_required``; the two
mutations are POST + CSRF. Ownership is enforced **inside** every path by ``get_owned_app`` /
the service owner-gate, addressed by ``request.user`` + ``app_id`` (+ a scoped ``notice_id``),
so a non-owner id is a 404 indistinguishable from not-found (no IDOR, no ownership oracle, AC1).

The failure split (DESIGN §7): a **post write** that fails unexpectedly fails *soft to the user*
(message + PRG, durable state = not-posted; ``UPDATES_POST_FAILED``) — never a 500, no corpus
coupling. The channel's **two read slots** (the audience hint, the owner's notices) each fail
soft independently so a degraded read never blocks the developer from posting.
"""

import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts import roles
from apps.accounts.permissions import require_role
from apps.catalog import selectors as catalog
from apps.catalog.models import App
from apps.core import observability
from apps.subscriptions import selectors as subscriptions
from apps.updates import selectors, services
from apps.updates.errors import (
    AppNotOwnedError,
    InvalidNoticeError,
    RateLimitedError,
)

logger = logging.getLogger(__name__)

_POST_FAILED_MESSAGE = "Couldn't post that update — please try again."
_POST_SUCCESS_MESSAGE = "Update posted."


@require_http_methods(["GET"])
@login_required
@require_role(roles.DEVELOPER)
def my_channels(request) -> HttpResponse:
    """GET /updates/ — the developer's **accepted** apps, each linking to its channel (AC1).

    Only accepted apps can have followers and so are the only postable channels; an owner with
    no accepted apps gets a 200 own-nothing state. Non-developers are 403 via ``require_role``.
    """
    accepted = [
        app
        for app in catalog.list_owned_apps(request.user)
        if app.status == App.Status.ACCEPTED
    ]
    return render(request, "updates/my_channels.html", {"apps": accepted})


@require_http_methods(["GET"])
@login_required
@require_role(roles.DEVELOPER)
def channel(request, app_id: UUID) -> HttpResponse:
    """GET /updates/apps/<id>/ — one channel: the post form, an audience hint, and own notices.

    A non-owner/unknown id is a 404 (indistinguishable, AC1). The audience hint and the notices
    list each fail soft (DESIGN §7) so a degraded read never blocks posting.
    """
    app = _owned_app_or_404(request.user, app_id)
    context = {
        "app": app,
        "subscriber_count": _audience_hint_fail_soft(app_id),
        "notices": _channel_notices_fail_soft(request.user, app_id),
    }
    return render(request, "updates/channel.html", context)


@require_http_methods(["POST"])
@login_required
@require_role(roles.DEVELOPER)
def post(request, app_id: UUID) -> HttpResponse:
    """POST /updates/apps/<id>/post — create a notice, then PRG to the channel (AC2/AC3/AC8).

    A validation/rate-limit reject surfaces as a message and PRGs back with nothing created
    (services already counted ``UPDATES_POST_REJECTED``). An unexpected write error fails soft
    (message + PRG + ``UPDATES_POST_FAILED``) — never a 500. A non-owned app is a 404 (AC1).
    """
    try:
        services.post_notice(
            request.user,
            app_id,
            kind=request.POST.get("kind", ""),
            title=request.POST.get("title", ""),
            summary=request.POST.get("summary", ""),
        )
    except AppNotOwnedError as exc:
        raise Http404("No such app channel.") from exc
    except (InvalidNoticeError, RateLimitedError) as exc:
        messages.error(request, str(exc))
    except Exception:
        observability.increment(observability.UPDATES_POST_FAILED)
        logger.warning("notice post failed app_id=%s", app_id, exc_info=True)
        messages.error(request, _POST_FAILED_MESSAGE)
    else:
        messages.success(request, _POST_SUCCESS_MESSAGE)
    return redirect("updates:channel", app_id=app_id)


@require_http_methods(["POST"])
@login_required
@require_role(roles.DEVELOPER)
def withdraw(request, app_id: UUID, notice_id: UUID) -> HttpResponse:
    """POST /updates/apps/<id>/notices/<nid>/withdraw — remove a notice, then PRG (AC7).

    Scoped to the caller's own notice by ``services.withdraw_notice``; a foreign/unknown id is
    a harmless no-op. The withdrawn notice is gone from the channel and from every follower's
    feed on its next read (the feed re-reads each request — no dangling ref).
    """
    services.withdraw_notice(request.user, app_id, notice_id)
    return redirect("updates:channel", app_id=app_id)


# --- Boundaries / fail-soft read slots ---------------------------------------
def _owned_app_or_404(user, app_id: UUID) -> App:
    """The caller's app, or a 404 indistinguishable from not-found (no ownership oracle, AC1)."""
    app = catalog.get_owned_app(user, app_id)
    if app is None:
        raise Http404("No such app channel.")
    return app


def _audience_hint_fail_soft(app_id: UUID) -> int | None:
    """The current follower count for the hint, or ``None`` (hidden) + a counted degradation.

    The hint is non-essential context; a failure must never block posting (DESIGN §7).
    """
    try:
        return subscriptions.subscriber_count(app_id)
    except Exception:
        observability.increment(observability.UPDATES_AUDIENCE_DEGRADED)
        logger.warning("audience hint degraded app_id=%s", app_id, exc_info=True)
        return None


def _channel_notices_fail_soft(user, app_id: UUID) -> list | None:
    """The owner's notices for the channel, or ``None`` (degraded) + a counted degradation.

    ``None`` signals the template to show a "couldn't load your notices" affordance while still
    rendering the post form — the developer can post even if the list read failed (DESIGN §7).
    """
    try:
        return selectors.notices_for_channel(user, app_id)
    except Exception:
        observability.increment(observability.UPDATES_CHANNEL_DEGRADED)
        logger.warning("channel notices degraded app_id=%s", app_id, exc_info=True)
        return None
