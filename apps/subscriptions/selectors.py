"""The single read path for subscriptions (DESIGN.md §5c/§6.2).

The inclusion tag and the feed read through here; nothing renders ``Subscription`` rows
directly. No write, no scoring. Two reads:

  * ``is_following`` — one indexed ``EXISTS`` for the follow control (AC1).
  * ``followed_apps`` — the personal feed: the most-recent ``limit`` follows resolved to
    their D-6 render shape in a **bounded number of queries independent of the follow count**
    (the indexed follow read + the bulk catalog read), so the feed is N+1-free at 100×
    follows (DESIGN §3.2).

A followed app that was later withdrawn is **silently dropped** (the bulk catalog read is
accepted-only) — the feed never errors on it (AC4).
"""

from uuid import UUID

from apps.catalog import selectors as catalog
from apps.catalog.selectors import CatalogApp
from apps.subscriptions.models import Subscription


def is_following(user, app_id: UUID) -> bool:
    """Whether ``user`` currently follows ``app_id`` — ``False`` for anonymous/``None`` (AC1)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return Subscription.objects.filter(user=user, app_id=app_id).exists()


def subscriber_count(app_id: UUID) -> int:
    """How many users currently follow ``app_id`` — one indexed COUNT (developer-updates §6.3).

    The reverse of the user-scoped ``is_following``/``followed_apps``: instead of "what does
    this user follow", "how many follow this app". Backed by ``subscriptions_app_idx`` so it is
    one query, bounded and follower-count-independent in query terms. Backs the developer's
    post-form audience hint and the M2 reach metric (developer-updates DESIGN §5.2/§6.3,
    DU-DESIGN-6). Not used for delivery — the AS-3 feed seam is pull (DESIGN §13).
    """
    return Subscription.objects.filter(app_id=app_id).count()


def followed_apps(user, *, limit: int) -> list[CatalogApp]:
    """``user``'s current follows, most-recent first, as their D-6 shape (AC4).

    Bounded by ``limit`` and resolved in two queries (no N+1). Non-accepted (withdrawn)
    followed apps are silently absent — the bulk catalog read returns accepted-only, and we
    re-order its result to follow-recency.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    followed_ids = list(
        Subscription.objects.filter(user=user)
        .order_by("-created_at")
        .values_list("app_id", flat=True)[:limit]
    )
    if not followed_ids:
        return []
    by_id = {app.id: app for app in catalog.get_catalogued_apps(followed_ids)}
    # Re-order to follow-recency and drop any non-accepted app (absent from `by_id`).
    return [by_id[app_id] for app_id in followed_ids if app_id in by_id]
