"""App-subscriptions data model (DESIGN.md §4) — one current follow per user per app.

One feature-owned table, ``subscriptions_subscription``. Like ratings (and unlike the
append-only D-7 signals corpus) it is **deliberately mutable**: a follow is created and
removed, never versioned. The *current* follow is this row; the *act of following* is the
append-only D-7 ``subscribe`` event written alongside it (services.follow_app, §6.1).

Three facts are **structural**, not conventions (CLAUDE.md §5.3 — one job per table):

  * **No score / weight / rank column (AC5).** There is nowhere here to store a computed
    value — scoring is a downstream consumer's job; this layer only records the relationship.
  * **No ``updated_at``.** A follow has no mutable attribute — it exists or it does not.
  * **No ``unfollowed_at`` / soft-delete.** Unfollow is a hard delete, so the store is
    *exactly* the current relationship (one source of truth). Churn (M6) is read from the
    ``SUBSCRIPTION_UNFOLLOWED`` metric.

The model declares the shape only. All invariants (idempotency, the atomic corpus emit) are
enforced by the single write path (``apps.subscriptions.services``); the model holds no
business logic.
"""

import uuid

from django.conf import settings
from django.db import models


class Subscription(models.Model):
    """One user's current follow of one accepted app — created and removed, never versioned."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE = the AS-5/AC9 contrast with ratings' SET_NULL: a follow is live relationship
    # state, not corpus, so it is removed when the account is — with no edit to `accounts`
    # (account.delete() cascades to this FK, DESIGN §4.2). The behavioral residue of "once
    # followed X" survives as the retained, anonymized `subscribe` event (signals SC-10).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    # The accepted catalog.App.id followed — a SOFT D-6 ref (no DB FK), validated at the
    # write boundary via get_catalogued_app. A later app withdrawal must not cascade-erase
    # the follow (the user can still clean it up; the feed silently drops it, §6.2).
    app_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)  # when followed — drives feed order

    class Meta:
        db_table = "subscriptions_subscription"
        ordering = ["-created_at"]
        constraints = [
            # AC1 — one follow per user per app; following an already-followed app is a no-op.
            # CASCADE means no anonymized user=NULL rows, so (unlike ratings) this is a clean
            # composite unique with no NULL-collision subtlety (DESIGN §4.1).
            models.UniqueConstraint(
                fields=["user", "app_id"], name="subscriptions_one_per_user_app"
            ),
        ]
        indexes = [
            # Backs the feed read (selectors.followed_apps), most-recent-followed first.
            models.Index(
                fields=["user", "created_at"], name="subscriptions_user_created_idx"
            ),
            # Backs the reverse-audience read (selectors.subscriber_count) added by
            # developer-updates (DESIGN §5.2/§6.3, DU-DESIGN-6). The unique (user, app_id)
            # index leads with `user`, so an app_id-only COUNT was unindexed — this additive,
            # app_id-only index covers it. No new column, no behaviour change to existing reads.
            models.Index(fields=["app_id"], name="subscriptions_app_idx"),
        ]

    def __str__(self) -> str:
        return f"subscription {self.id} → app {self.app_id}"
