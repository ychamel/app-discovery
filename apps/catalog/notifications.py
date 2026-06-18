"""Decision notification — turns a committed gate decision into the developer email (AC7).

``notify_decision`` is called by the review surface **after** the decision transaction
commits (T-10/T-12): the **decision is authoritative, the email is a notification**. A
send failure is logged and counted (``EMAIL_SEND_FAILURE``) but does **not** roll back the
decision — the developer still sees the outcome and reason in "my apps". This keeps the
email from being a single point of failure for the gate (DESIGN.md §5d/§10).

This module performs **no** status mutation — it only renders and sends (one job).
"""

import logging

from apps.catalog.gate import Criterion
from apps.catalog.models import ReviewDecision
from apps.core import observability
from apps.core.email import EmailSendError, get_email_sender

logger = logging.getLogger("apps.catalog.notifications")

_TEMPLATES = {
    ReviewDecision.Outcome.ACCEPTED: "app_accepted",
    ReviewDecision.Outcome.REJECTED: "app_rejected",
}


def notify_decision(decision: ReviewDecision) -> bool:
    """Email the app owner the decision outcome + reason. Returns True if sent.

    On a transport failure this logs, counts ``EMAIL_SEND_FAILURE``, and returns False —
    it never raises, so a notification problem cannot undo a committed decision (§5d).
    """
    app = decision.app
    recipient = app.owner.email
    template = _TEMPLATES[decision.outcome]
    context = _build_context(decision)

    try:
        get_email_sender().send(recipient, template, context)
    except EmailSendError:
        logger.error("Decision email send failed for app %s", app.id, exc_info=True)
        observability.increment(
            observability.EMAIL_SEND_FAILURE, purpose="decision", outcome=decision.outcome
        )
        return False
    return True


def _build_context(decision: ReviewDecision) -> dict:
    """The template context: app identity, and on rejection the failing floors + note (AC7)."""
    context = {
        "app_name": decision.app.name,
        "app_url": decision.app.url,
    }
    if decision.outcome == ReviewDecision.Outcome.REJECTED:
        context["failed_criteria"] = [
            Criterion(value).label for value in decision.failed_criteria
        ]
        context["note"] = decision.note
    return context
