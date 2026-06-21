"""Ratings & reviews data model (DESIGN.md §4) — one mutable rating per user per app.

One feature-owned table, ``ratings_rating``. Unlike the append-only D-7 signals corpus, a
rating is *explicit, mutable* opinion — editable and removable by its author — so this
store is deliberately mutable.

Two facts are **structural**, not conventions:

  * **No score / weight / rank / average / quality column (AC6).** ``weight_eligible`` is an
    *eligibility boolean* (did the gate grant this rating weight), not a quality value. There
    is nowhere here to store a computed score — scoring is a downstream consumer's job.
  * **The curated-rating gate is RECORDED, not computed at read (AC5).** Every row carries the
    determination (``weight_eligible`` + the reason ``eligibility_basis`` + the as-of instant),
    set together by the single write path so they can never drift.

The model declares the shape only. All invariants (score range, the
``weight_eligible == (basis == CURATED_DIGEST_IMPRESSION)`` coupling, the determination
itself) are enforced by the write path (``apps.ratings.services``); the model holds no
business logic — one job per module (CLAUDE.md §5.3).
"""

import uuid

from django.conf import settings
from django.db import models


class EligibilityBasis(models.TextChoices):
    """Why a rating got its curated-gate determination — the recorded reason (the §8.4 metric tag).

    The boolean ``weight_eligible`` answers *whether* a rating counts; this records *why*, so
    a determination is auditable and re-derivable (R1) without re-running the gate.
    """

    CURATED_DIGEST_IMPRESSION = "curated_digest_impression", "curated — DIGEST impression"
    NO_CURATED_IMPRESSION = "no_curated_impression", "not curated — no qualifying impression"
    CURATION_UNVERIFIED = "curation_unverified", "curation unverified (gate read failed)"


class Rating(models.Model):
    """One user's rating (+ optional review) of one accepted app — editable, removable (AC8)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SET_NULL = anonymize-on-deletion, mirroring signals SC-10/D-7: the eligibility-tagged
    # corpus the future Quality Score is backtested on survives a deleted account, unlinked
    # from the person (DESIGN §4.2).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ratings",
    )
    # The accepted catalog.App.id rated — a SOFT D-6 ref (no DB FK), validated at the write
    # boundary via get_catalogued_app (AC9). A later app withdrawal must not cascade-erase
    # that it was rated.
    app_id = models.UUIDField()
    score = models.PositiveSmallIntegerField()  # 1..rating_scale_max(); validated at the boundary
    review_text = models.TextField(blank=True, default="")  # optional (A1)

    # --- the curated-rating gate, RECORDED not computed (AC5/RR-1) ---
    # THE gate determination: queryable, never null. Set together with eligibility_basis from
    # one computation (services.submit_rating) so the two can never drift.
    weight_eligible = models.BooleanField()
    eligibility_basis = models.CharField(max_length=32, choices=EligibilityBasis.choices)
    eligibility_determined_at = models.DateTimeField()  # the as-of instant the determination used

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ratings_rating"
        ordering = ["-created_at"]
        constraints = [
            # AC8 — one active rating per user per app. A deleted user's rows go user=NULL,
            # which Postgres treats as distinct, so anonymized rows never collide with a
            # living user's single rating (DESIGN §4.1).
            models.UniqueConstraint(
                fields=["user", "app_id"], name="ratings_one_active_per_user_app"
            ),
        ]
        indexes = [
            # Backs the per-app display read (selectors.reviews_for_app), most-recent first.
            models.Index(fields=["app_id", "created_at"], name="ratings_app_created_idx"),
        ]

    def __str__(self) -> str:
        return f"rating {self.id} → app {self.app_id} ({self.score})"
