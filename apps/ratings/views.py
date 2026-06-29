"""The two thin HTTP views for ratings (DESIGN.md §5e).

Mirrors the pages/catalog house pattern: each view **parses input, calls a service, and
redirects** — it holds no business logic and no ORM access. ``services`` is the single write
path; the gate, validation, and the store all live behind it.

Own-data-only is **structural** (DESIGN §7): the URL carries no rating id. A rating is
addressed by ``request.user`` + ``app_id``, so a user can only ever touch their own — there
is no id to tamper with (no IDOR). Both routes are POST + ``login_required`` + CSRF.
"""

import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from apps.ratings import services
from apps.ratings.errors import RatingValidationError, SelfRatingError, UnknownAppError

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def submit(request, app_id: UUID):
    """POST /ratings/apps/<id>/rating — create or update the caller's rating (AC1/AC2/AC8/AC9).

    Validation failures (AC2) surface as a message and redirect back to the page (PRG); an
    unknown/non-accepted app is a 404 (AC9). On success, PRG-redirect to the app page so a
    refresh never re-submits.
    """
    score = _parse_score(request.POST.get("score"))
    review_text = request.POST.get("review_text", "")
    try:
        services.submit_rating(
            request.user, app_id, score=score, review_text=review_text
        )
    except UnknownAppError as exc:
        raise Http404("No such app to rate.") from exc
    except SelfRatingError as exc:
        messages.error(request, str(exc))
    except RatingValidationError as exc:
        messages.error(request, str(exc))
    return redirect("pages:app-page", app_id=app_id)


@login_required
@require_http_methods(["POST"])
def remove(request, app_id: UUID):
    """POST /ratings/apps/<id>/rating/remove — delete the caller's rating, then PRG (AC8)."""
    services.remove_rating(request.user, app_id)
    return redirect("pages:app-page", app_id=app_id)


def _parse_score(raw: str | None) -> int:
    """Parse the posted score to an int; a missing/non-numeric value becomes 0.

    Range validity is the service's boundary job (AC2) — 0 is simply out of range and is
    rejected there, so the view never duplicates the validation rule.
    """
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0
