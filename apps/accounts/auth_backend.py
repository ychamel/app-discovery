"""Magic-link issuing and verification (DESIGN.md §4 concurrency, §8 auth flow).

This is the sharpest correctness edge in the feature, so it is built and tested in
isolation before any endpoint wires it. Two guarantees matter most:

  * **The raw token is never stored.** Only its SHA-256 hash is persisted; the raw
    value exists solely in the emailed link and the verifying request.
  * **A token is consumed exactly once.** Verification consumes atomically with a
    single conditional UPDATE, so two concurrent clicks can never both succeed
    (DESIGN.md §4 token double-spend).
"""

import hashlib
import secrets

from django.utils import timezone

from apps.accounts.models import Account, LoginToken
from apps.core import config
from apps.core.email import EmailSender, get_email_sender

# The verify endpoint path. T-09 mounts the route here; kept as one constant so the
# emailed link and the URL route cannot drift apart.
VERIFY_PATH = "/auth/verify"

# 32 random bytes of entropy, URL-safe encoded (DESIGN.md §8).
_TOKEN_NBYTES = 32


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def build_verify_link(raw_token: str, base_url: str) -> str:
    """Absolute magic-link URL for the emailed token."""
    return f"{base_url.rstrip('/')}{VERIFY_PATH}?token={raw_token}"


def issue_login_link(
    account: Account,
    purpose: str,
    *,
    base_url: str,
    email_sender: EmailSender | None = None,
) -> LoginToken:
    """Create a single-use token for ``account`` and email its link.

    Stores only the token hash; the raw token leaves this function only inside the
    emailed link. A send failure propagates (EmailSendError) so the caller can
    surface it (AC2) — it is never swallowed.
    """
    raw_token = secrets.token_urlsafe(_TOKEN_NBYTES)
    ttl = config.login_token_ttl()
    token = LoginToken.objects.create(
        account=account,
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + ttl,
    )

    sender = email_sender or get_email_sender()
    sender.send(
        to=account.email,
        template="magic_link",
        context={
            "link": build_verify_link(raw_token, base_url),
            "purpose": purpose,
            "ttl_minutes": int(ttl.total_seconds() // 60),
        },
    )
    return token


def verify_token(raw_token: str) -> Account | None:
    """Consume ``raw_token`` and return its account, or None if it is not usable.

    The conditional UPDATE is the single point of truth for single-use + TTL: it
    matches only an unconsumed, unexpired row and marks it consumed in one atomic
    statement. If zero rows match (unknown, expired, or already consumed) the token
    is rejected. Concurrency-safe: at most one caller's UPDATE can match the row.
    """
    token_hash = _hash_token(raw_token)
    now = timezone.now()
    consumed_count = (
        LoginToken.objects.filter(
            token_hash=token_hash,
            consumed_at__isnull=True,
            expires_at__gt=now,
        ).update(consumed_at=now)
    )
    if consumed_count == 0:
        return None
    return LoginToken.objects.select_related("account").get(token_hash=token_hash).account
