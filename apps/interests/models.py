"""Interest-profile data model (DESIGN.md §4.1) — one declared tag per user per row.

One feature-owned table, ``interests_interest``. Like subscriptions/ratings (and unlike
the append-only D-7 signals corpus) it is **deliberately mutable**: a declaration is
created and removed, never versioned. The *interest profile* is the SET of a user's rows
— there is **no parent profile row**, so an empty profile is the structural default
(AC6): zero rows *is* the empty profile, needing no marker or create-on-first-visit step.

Three facts are **structural**, not conventions (CLAUDE.md §5.3 — one job per table):

  * **No score / weight / rank column (AC8).** There is nowhere here to store a computed
    value — scoring is the future matcher's job; this layer only records the declaration.
  * **No ``updated_at`` / soft-delete.** A declaration exists or it does not; the set
    changes by row add/remove (one source of truth).
  * **No parent profile row.** The membership-only shape makes "empty" the default.

The model declares the shape only. All invariants (the all-or-nothing validation, the §7
set-replace preserve-on-edit reconcile) are enforced by the single write path
(``apps.interests.services``); the model holds no business logic.
"""

import uuid

from django.conf import settings
from django.db import models


class Interest(models.Model):
    """One interest a user has declared — one row per (user, tag_id), never versioned."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE = IP-4/AC9: the profile is mutable user preference state, so it is removed
    # when the account is, with no edit to `accounts` (account.delete() cascades this FK,
    # DESIGN §4.1/§6). Unlike the D-7 corpus there is no anonymized residue to retain — no
    # corpus row is ever written here (IP-5).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interests",
    )
    # The declared taxonomy Tag.id — a SOFT D-5 ref (no DB FK). Validated active at the
    # write boundary (is_valid_tag); resolved at read (resolve_tag). Stored by id, never
    # by label/slug. A later tag retire must not cascade-erase the row: the meaning is
    # recovered at read via resolve_tag (AC7).
    tag_id = models.UUIDField()
    # when declared (debug/audit; not load-bearing)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interests_interest"
        constraints = [
            # AC1/AC4 — one row per user per tag; declaring an already-declared tag is a
            # no-op. CASCADE means no user=NULL rows, so this is a clean composite unique
            # with no NULL-collision subtlety; its index also backs the per-user read
            # (filter(user=...)) (DESIGN §4.1).
            models.UniqueConstraint(
                fields=["user", "tag_id"], name="interests_one_per_user_tag"
            ),
        ]

    def __str__(self) -> str:
        return f"interest {self.id} → tag {self.tag_id}"
