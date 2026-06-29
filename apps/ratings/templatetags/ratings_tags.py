"""The AP-1 reviews-slot inclusion tag (DESIGN.md §5f).

``{% app_reviews app %}`` renders the reviews slot inside the app page. It is the **only**
coupling between the closed-out app-pages template and this feature: app-pages stays ignorant
of ratings internals; it just provides the slot.

**Fail-soft (DESIGN §8 row 4):** any selector error renders a degraded slot and increments
``RATING_DISPLAY_DEGRADED`` — it never raises into the page render, so a reviews outage can
never take down the app page (preserves app-pages AC5 / AP-1).
"""

import logging

from django import template

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.ratings import selectors

logger = logging.getLogger(__name__)
register = template.Library()


@register.inclusion_tag("ratings/_reviews_slot.html", takes_context=True)
def app_reviews(context, app):
    """Build the reviews-slot context for ``app`` — fail-soft (DESIGN §5f)."""
    request = context.get("request")
    user = getattr(request, "user", None)
    scale_max = config.rating_scale_max()
    try:
        reviews = selectors.reviews_for_app(
            app.id, limit=config.reviews_display_limit()
        )
        own_rating = selectors.user_rating(user, app.id)
        is_owner = catalog.is_app_owner(user, app.id)
    except Exception:
        observability.increment(
            observability.RATING_DISPLAY_DEGRADED, app_id=str(app.id)
        )
        logger.warning("reviews slot degraded app_id=%s", app.id, exc_info=True)
        return {
            "request": request,
            "app": app,
            "reviews": None,
            "own_rating": None,
            "is_owner": False,
            "scale_max": scale_max,
            "score_choices": range(1, scale_max + 1),
            "degraded": True,
        }

    return {
        "request": request,
        "app": app,
        "reviews": reviews,
        # The distribution as ordered (score, count) rows, highest score first — so the
        # template renders the raw distribution without dict-key gymnastics (still no average).
        "distribution_rows": [
            (score, reviews.distribution.get(score, 0))
            for score in range(scale_max, 0, -1)
        ],
        "own_rating": own_rating,
        "is_owner": is_owner,
        "scale_max": scale_max,
        "score_choices": range(1, scale_max + 1),
        "degraded": False,
    }
