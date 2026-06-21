"""The single display read path for ratings (DESIGN.md §5c).

The reviews slot and any future consumer read through here; nothing renders ``Rating`` rows
directly. Two guarantees live in this surface:

  * **No score / average / rank is ever computed (AC6).** The "summary" is the raw count plus
    the *distribution* — how many ratings sit at each score value. A naive public average is
    exactly the gameable number the curated-rating gate exists to neutralize, so it is
    deliberately absent (DESIGN §5c/§14).
  * **All ratings are shown regardless of weight-eligibility (AC7).** The gate flag is internal
    substrate for the future Quality Score, not a public badge — ``ReviewRow`` has no
    eligibility field. The platform stays openly participatory; the gate governs *weight*, not
    *visibility*.

Reads are bounded: the rendered list is capped at ``reviews_display_limit()`` so the slot
stays O(limit) at 100× data (DESIGN §9).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db.models import Count

from apps.ratings.models import Rating

# Shown when a rating's author has been anonymized (account deleted → user=NULL, §4.2).
ANONYMIZED_AUTHOR_DISPLAY = "a former user"


@dataclass(frozen=True)
class ReviewRow:
    """One displayed review. Deliberately carries **no** eligibility field (AC7/DESIGN §5c)."""

    score: int
    review_text: str
    author_display: str
    created_at: datetime


@dataclass(frozen=True)
class AppReviews:
    """The reviews slot's data for one app — count + raw distribution + the capped list (AC4)."""

    app_id: UUID
    total_count: int
    distribution: dict[int, int]  # raw count per score value — DESCRIPTIVE, never an average (AC6)
    reviews: list[ReviewRow]  # most-recent first, capped at the display limit


def reviews_for_app(app_id: UUID, *, limit: int) -> AppReviews:
    """All-ratings summary + the most-recent ``limit`` reviews for ``app_id`` (AC4/AC7).

    Two queries: a grouped count per score value (the distribution; ``total_count`` is its
    sum, so no extra COUNT query), then the capped most-recent-first list. Every rating is
    included regardless of ``weight_eligible``.
    """
    distribution = _score_distribution(app_id)
    total_count = sum(distribution.values())
    reviews = [_to_row(rating) for rating in _recent_ratings(app_id, limit)]
    return AppReviews(
        app_id=app_id,
        total_count=total_count,
        distribution=distribution,
        reviews=reviews,
    )


def user_rating(user, app_id: UUID) -> Rating | None:
    """The viewer's own rating of ``app_id`` (to prefill the form), or ``None``.

    Anonymous viewers have no row — callers pass an unauthenticated user and get ``None``.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return Rating.objects.filter(user=user, app_id=app_id).first()


# --- Internals ---------------------------------------------------------------
def _score_distribution(app_id: UUID) -> dict[int, int]:
    """Raw count of ratings at each score value for ``app_id`` (one grouped query)."""
    rows = (
        Rating.objects.filter(app_id=app_id)
        .values("score")
        .annotate(count=Count("id"))
    )
    return {row["score"]: row["count"] for row in rows}


def _recent_ratings(app_id: UUID, limit: int):
    """The most-recent ``limit`` ratings for ``app_id``, author prefetched (no N+1)."""
    return (
        Rating.objects.filter(app_id=app_id)
        .select_related("user")
        .order_by("-created_at")[:limit]
    )


def _to_row(rating: Rating) -> ReviewRow:
    """Project a ``Rating`` to its public ``ReviewRow`` — without the eligibility flag (AC7)."""
    return ReviewRow(
        score=rating.score,
        review_text=rating.review_text,
        author_display=_author_display(rating.user),
        created_at=rating.created_at,
    )


def _author_display(user) -> str:
    """A display name for the review author, anonymized if the account is gone (§4.2)."""
    if user is None:
        return ANONYMIZED_AUTHOR_DISPLAY
    return user.display_name or user.email
