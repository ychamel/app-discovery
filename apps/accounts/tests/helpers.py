"""Shared helpers for account tests (magic-link flow utilities)."""

from urllib.parse import parse_qs, urlparse

from django.core import mail


def latest_magic_link_token() -> str:
    """Extract the raw token from the most recently sent magic-link email."""
    message = mail.outbox[-1]
    for line in message.body.splitlines():
        if "/auth/verify?token=" in line:
            return parse_qs(urlparse(line.strip()).query)["token"][0]
    raise AssertionError("No magic-link found in the last email body.")
