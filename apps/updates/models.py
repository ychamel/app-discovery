"""developer-updates data model (DESIGN.md §5.1) — one posted notice about an app.

One feature-owned table, ``updates_notice``. It is the single AS-3 producer: a developer
posts an **update** or **early-access** notice about an app they own, and the followed-apps
feed pulls those notices for the apps a user follows (developer-updates DESIGN §4).

Three facts are **structural**, not conventions (CLAUDE.md §5.3 — one job per table):

  * **No score / weight / rank column (AC6).** A notice is *content*, never a corpus signal —
    there is nowhere here to store a value the Quality Score could trust. Posting confers no
    reach; the reach a developer already earned (their followers) is all a notice gets.
  * **No ``updated_at``.** A notice is immutable — editing is out of scope at MVP; the correct
    edit is withdraw + repost (DESIGN §1/§5.3, a named future seam).
  * **No ``withdrawn_at`` / soft-delete.** Withdraw is a hard delete (DESIGN §5.3), so the
    store is *exactly* the currently-published set (one source of truth, mirrors unfollow).

The model declares the shape only. All invariants (the owner gate, boundary validation, the
durable rate-limit) are enforced by the single write path (``apps.updates.services``); the
model holds no business logic.
"""

import uuid

from django.conf import settings
from django.db import models


class NoticeKind(models.TextChoices):
    """The two notice kinds — exactly the pinned ``subscriptions.notices.Notice.kind`` enum.

    A notice is either a general **update** about a followed app or an **early-access** offer.
    No other kind exists at MVP; a new kind is a deliberate, additive choices change.
    """

    UPDATE = "update", "update"
    EARLY_ACCESS = "early_access", "early access"


class Notice(models.Model):
    """One published update/early-access notice about an app — created and withdrawn, not edited."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The accepted catalog.App.id the notice is about — a SOFT D-6 ref (no DB FK), validated
    # at the write boundary via get_owned_app (mirrors subscriptions/ratings). A later app
    # withdrawal must not cascade-erase posted notices; the feed silently drops a withdrawn
    # app upstream (the followed-apps read is accepted-only).
    app_id = models.UUIDField()
    # CASCADE = the AS-5 pattern: a notice is withdrawable *content*, not retained D-7 corpus,
    # so account deletion removes the author's notices with no edit to `accounts`. The
    # behavioral residue of any engagement survives as the followers' own anonymized returns.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notices",
    )
    kind = models.CharField(max_length=20, choices=NoticeKind.choices)
    # Defensive DB cap; the *product* limit is config.updates_title_max_length() (≤200),
    # validated at the write boundary (DESIGN §5.1).
    title = models.CharField(max_length=200)
    summary = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)  # immediate post; drives feed order

    class Meta:
        db_table = "updates_notice"
        ordering = ["-published_at"]
        indexes = [
            # One composite index backs all three reads — the AS-3 feed read
            # (app_id IN (...) ORDER BY published_at DESC LIMIT n), the owner manage list
            # (app_id= + author= residual), and the rate-limit window count (app_id= +
            # author= + published_at >= t) — because app_id leads every query and author is a
            # cheap residual on the inherently small, rate-limited per-app notice set.
            # Growth seam (named, not built — DESIGN §5.1/§5.5): a global published_at index if
            # cross-app feed ordering ever dominates.
            models.Index(
                fields=["app_id", "published_at"], name="updates_app_published_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"notice {self.id} ({self.kind}) → app {self.app_id}"
