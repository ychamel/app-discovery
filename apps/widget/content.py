"""The widget render contract assembler (DESIGN §5.2/§7/§8) — pure, HTTP-free.

``build_widget_view`` gathers everything the template needs — the app name, the server-derived
"view on platform" link, and the capped newest-first notices — into one frozen ``WidgetView``,
so the view layer stays thin (rate-limit, call this, render). It owns exactly one fail-soft
decision: a *notice read* failure degrades to link-only (``notices_degraded=True``) rather than
fabricating a "no updates" state we could not verify. A *catalog* failure is **not** caught here
— it surfaces to the view wrapper, which renders the neutral unavailable page (DESIGN §8).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.urls import reverse

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.updates import selectors as updates


@dataclass(frozen=True)
class WidgetNotice:
    """One notice as the widget renders it (DESIGN §5.2) — a projection of ``PublishedNotice``."""

    kind: str  # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime


@dataclass(frozen=True)
class WidgetView:
    """The full render contract for an accepted app's widget (DESIGN §5.2)."""

    app_name: str
    app_page_path: str  # reverse("pages:app-page", [app_id]) — server-derived, never a param
    notices: list[WidgetNotice]  # capped at config.widget_notice_limit(), newest-first
    notices_degraded: bool  # True ⇒ the notice read errored → link-only, not a fake "no updates"


def build_widget_view(app_id: UUID) -> WidgetView | None:
    """Assemble the widget view for ``app_id``, or ``None`` if it is unknown/non-accepted (D-6).

    The catalog read is the availability gate (``None`` ⇒ the view renders the neutral
    unavailable page; a catalog *exception* is left to surface to the view wrapper). The notice
    read is wrapped fail-soft so a degraded ``updates`` never blanks the widget — the app name
    and link still render.
    """
    app = catalog.get_catalogued_app(app_id)
    if app is None:
        return None

    app_page_path = reverse("pages:app-page", args=[app_id])
    notices, notices_degraded = _load_notices(app_id)
    return WidgetView(
        app_name=app.name,
        app_page_path=app_page_path,
        notices=notices,
        notices_degraded=notices_degraded,
    )


def _load_notices(app_id: UUID) -> tuple[list[WidgetNotice], bool]:
    """Read the capped, newest-first notices fail-soft → ``(notices, degraded)``.

    A *truthful* empty (the app has posted nothing) returns ``([], False)``; a read *failure*
    returns ``([], True)`` after counting ``WIDGET_NOTICES_DEGRADED``, so the template can show a
    quiet "temporarily unavailable" rather than asserting "no updates" it could not verify.
    """
    try:
        published = updates.published_notices_for_apps(
            [app_id], limit=config.widget_notice_limit()
        )
    except Exception:
        observability.increment(observability.WIDGET_NOTICES_DEGRADED)
        return [], True
    notices = [
        WidgetNotice(
            kind=notice.kind,
            title=notice.title,
            summary=notice.summary,
            published_at=notice.published_at,
        )
        for notice in published
    ]
    return notices, False
