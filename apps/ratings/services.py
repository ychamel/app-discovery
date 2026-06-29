"""The single write path for ratings (DESIGN.md §5a) — the only place ``Rating`` rows change.

Every create / update / delete of a ``Rating`` goes through here, so the store's invariants
live in exactly one place (illegal states unrepresentable):

  * the ``app_id`` is a real, **accepted** catalog app (D-6) — else ``UnknownAppError`` and
    nothing is written (AC9);
  * ``score`` and ``review_text`` are validated at the boundary **before** any write — else
    ``RatingValidationError`` and nothing is written (AC2);
  * the curated-gate determination is stamped on **every** write (AC5), in the same atomic
    transaction as the score/text, so ``weight_eligible`` and ``eligibility_basis`` can never
    drift from each other or from the row (DESIGN §4.1 invariant).

A catalog read that *raises* (DB down) propagates **loud** — a rating has no subject without
its app (DESIGN §8 row 1). A *None* (not accepted) is the AC9 ``UnknownAppError``.
"""

import logging
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.ratings import gate
from apps.ratings.errors import RatingValidationError, SelfRatingError, UnknownAppError
from apps.ratings.models import Rating

logger = logging.getLogger(__name__)


def submit_rating(user, app_id: UUID, *, score: int, review_text: str = "") -> Rating:
    """Create or update ``user``'s rating of ``app_id``, stamping the curated-gate determination.

    Validates the app (AC9) and the input (AC2) before touching the DB, determines weight
    eligibility (AC5/AC7), then writes score + text + the gate columns together in one atomic
    ``update_or_create`` keyed on ``(user, app_id)`` — so a re-rate updates the same row
    rather than duplicating it (AC8).
    """
    _require_catalogued_app(app_id)
    _require_non_owner(user, app_id)
    _validate(score, review_text)

    determined_at = timezone.now()
    determination = gate.determine_eligibility(user, app_id, as_of=determined_at)

    with transaction.atomic():
        rating, created = Rating.objects.update_or_create(
            user=user,
            app_id=app_id,
            defaults={
                "score": score,
                "review_text": review_text,
                "weight_eligible": determination.weight_eligible,
                "eligibility_basis": determination.basis,
                "eligibility_determined_at": determination.determined_at,
            },
        )

    metric = observability.RATING_SUBMITTED if created else observability.RATING_UPDATED
    observability.increment(
        metric,
        weight_eligible=determination.weight_eligible,
        basis=determination.basis,
    )
    logger.info(
        "rating %s app_id=%s weight_eligible=%s basis=%s",
        "created" if created else "updated",
        app_id,
        determination.weight_eligible,
        determination.basis,
    )
    return rating


def remove_rating(user, app_id: UUID) -> bool:
    """Delete ``user``'s rating of ``app_id`` (hard-delete, DESIGN §4.2); report if one existed.

    Addressed by ``user`` + ``app_id`` only — a user can never remove another's rating (AC8,
    no IDOR).
    """
    deleted_count, _ = Rating.objects.filter(user=user, app_id=app_id).delete()
    existed = deleted_count > 0
    if existed:
        observability.increment(observability.RATING_REMOVED)
        logger.info("rating removed app_id=%s", app_id)
    return existed


# --- Boundaries --------------------------------------------------------------
def _require_catalogued_app(app_id: UUID) -> None:
    """Raise ``UnknownAppError`` unless ``app_id`` is an accepted catalog app (D-6, AC9)."""
    if catalog.get_catalogued_app(app_id) is None:
        raise UnknownAppError(f"No accepted catalog app for id {app_id!r}.")


def _require_non_owner(user, app_id: UUID) -> None:
    """Raise ``SelfRatingError`` if ``user`` owns ``app_id`` — self-rating is not permitted."""
    if catalog.is_app_owner(user, app_id):
        raise SelfRatingError("You can't review your own app.")


def _validate(score: int, review_text: str) -> None:
    """Reject an out-of-range score or over-length review at the boundary (AC2).

    Raises ``RatingValidationError`` (and increments ``RATING_REJECTED``) before any write, so
    a bad submission stores nothing.
    """
    scale_max = config.rating_scale_max()
    if not isinstance(score, int) or not (1 <= score <= scale_max):
        _reject(f"score must be an integer in 1..{scale_max}, got {score!r}.", reason="score")

    text_max = config.review_text_max_length()
    if len(review_text) > text_max:
        _reject(
            f"review text exceeds the {text_max}-character limit ({len(review_text)}).",
            reason="review_length",
        )


def _reject(message: str, *, reason: str) -> None:
    """Count the rejection and raise — boundary failures are loud, never silent (AC2)."""
    observability.increment(observability.RATING_REJECTED, reason=reason)
    raise RatingValidationError(message)
