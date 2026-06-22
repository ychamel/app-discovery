"""The onboarding-nudge inclusion tag (DESIGN.md §5.4 — AC3).

``{% interest_prompt %}`` renders a gentle, non-gating nudge to declare interests on the
post-registration ``accounts/profile.html`` landing. Like the ratings/subscriptions slot
tags, it is the **only** coupling between another feature's template and this one: accounts
stays ignorant of interests internals; it just renders one content line.

**Fail-soft (DESIGN §5.4/§9):** any error renders nothing and increments
``INTEREST_PROMPT_DEGRADED`` — it never raises into the page render, so an interests outage
can never 500 the profile page.
"""

import logging

from django import template

from apps.core import observability
from apps.interests import selectors

logger = logging.getLogger(__name__)
register = template.Library()


@register.inclusion_tag("interests/_prompt_slot.html", takes_context=True)
def interest_prompt(context):
    """Show the nudge iff the current user has declared no interests yet — fail-soft (§5.4)."""
    request = context.get("request")
    user = getattr(request, "user", None)
    try:
        show = not selectors.has_declared_interests(user)
    except Exception:
        observability.increment(observability.INTEREST_PROMPT_DEGRADED)
        logger.warning("interest prompt degraded", exc_info=True)
        return {"request": request, "show": False}
    return {"request": request, "show": show}
