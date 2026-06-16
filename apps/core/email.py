"""Shared email-sending surface (DESIGN.md §6).

One send point for the whole platform: the magic-link email now, the weekly digest
later. The *interface* is fixed here; the concrete transport is ops configuration
(`EMAIL_BACKEND`, console in dev), never hardcoded.

Failures **fail loudly** — a send that the backend cannot complete raises, so the
caller (e.g. registration) can surface it (AC2's `503`) instead of a silently lost
link.

Each logical email is a pair of Django templates resolved by name:
    templates/email/<template>.subject.txt   → the subject line
    templates/email/<template>.body.txt      → the plain-text body
"""

from typing import Protocol

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class EmailSendError(RuntimeError):
    """Raised when an email could not be handed off to the transport."""


class EmailSender(Protocol):
    """The cross-feature email contract. Implementations must fail loudly."""

    def send(self, to: str, template: str, context: dict) -> None: ...


class DefaultEmailSender:
    """`EmailSender` backed by Django's configured email backend.

    The transport is whatever ``settings.EMAIL_BACKEND`` selects, so swapping
    console → SMTP/SES/Postmark is pure configuration with no caller change.
    """

    def send(self, to: str, template: str, context: dict) -> None:
        subject = render_to_string(f"email/{template}.subject.txt", context).strip()
        body = render_to_string(f"email/{template}.body.txt", context)
        try:
            delivered = send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
        except Exception as exc:  # transport error — never swallow it
            raise EmailSendError(f"Failed to send {template!r} email to {to}") from exc
        if delivered == 0:
            # Backend reported zero deliveries without raising — still a failure.
            raise EmailSendError(f"Email backend accepted 0 of 1 {template!r} email to {to}")


def get_email_sender() -> EmailSender:
    """Return the configured email sender.

    A single seam so callers depend on the interface, and tests can substitute a
    fake without touching transport configuration.
    """
    return DefaultEmailSender()
