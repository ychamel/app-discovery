"""The app-page devlog-slot inclusion tag (app-page-redesign DESIGN.md §4/§6/§9.3/§9.5).

``{% app_devlog app %}`` renders the on-page devlog — the app's most recent published notices,
newest-first. It mirrors ``ratings_tags``/``subscriptions_tags``: a thin, fail-soft adapter the
closed app-page template fills a slot with, ignorant of the ``updates`` internals.

**Fail-soft (DESIGN §9.2 row 3):** any read error renders **nothing** and increments
``APP_PAGE_DEVLOG_DEGRADED`` — it never raises into the page render, so a devlog outage can
never 500 the app page. **Firewall (AC-6/M5=0):** this is a pure read of
``updates.published_notices_for_apps`` and imports **nothing** from ``signals`` — surfacing the
slot adds no score-affecting event (asserted in the updates import test).
"""

import logging

from django import template

from apps.core import config, observability
from apps.updates import selectors

logger = logging.getLogger(__name__)
register = template.Library()


@register.inclusion_tag("updates/_devlog_slot.html")
def app_devlog(app):
    """Build the devlog-slot context for ``app`` — newest-first, capped, fail-soft (DESIGN §6)."""
    try:
        notices = selectors.published_notices_for_apps(
            [app.id], limit=config.app_page_devlog_limit()
        )
    except Exception:
        observability.increment(
            observability.APP_PAGE_DEVLOG_DEGRADED, app_id=str(app.id)
        )
        logger.warning("devlog slot degraded app_id=%s", app.id, exc_info=True)
        return {"notices": None, "degraded": True}

    return {"notices": notices, "degraded": False}
