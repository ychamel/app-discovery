"""The Follow-slot inclusion tag (DESIGN.md §5f — resolves OQ-4).

``{% app_follow app %}`` renders the follow control inside the app page. Like the ratings
``{% app_reviews app %}`` tag, it is the **only** coupling between the closed-out app-pages
template and this feature: app-pages stays ignorant of subscriptions internals; it just
provides the slot.

**Fail-soft (DESIGN §5f/§9):** any selector error renders a degraded slot (no control) and
increments ``SUBSCRIPTION_CONTROL_DEGRADED`` — it never raises into the page render, so a
subscriptions outage can never take down the app page (preserves app-pages AC5).
"""

import logging

from django import template

from apps.core import observability
from apps.subscriptions import selectors

logger = logging.getLogger(__name__)
register = template.Library()


@register.inclusion_tag("subscriptions/_follow_slot.html", takes_context=True)
def app_follow(context, app):
    """Build the Follow-slot context for ``app`` and the current viewer — fail-soft (§5f)."""
    request = context.get("request")
    user = getattr(request, "user", None)
    try:
        following = selectors.is_following(user, app.id)
    except Exception:
        observability.increment(
            observability.SUBSCRIPTION_CONTROL_DEGRADED, app_id=str(app.id)
        )
        logger.warning("follow slot degraded app_id=%s", app.id, exc_info=True)
        return {"request": request, "app": app, "is_following": False, "degraded": True}

    return {
        "request": request,
        "app": app,
        "is_following": following,
        "degraded": False,
    }
