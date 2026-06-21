"""The curated-rating gate (DESIGN.md §5b) — the integrity core of this feature.

This module is the **one place** the platform's §4.1 rule lives: *only an organically
curated rater may give a rating weight.* It answers, for one rating, "was this author
curated to this app?" and records the answer (+ the reason) so a bought or farmed rating
can never silently count.

Two responsibilities, kept apart on purpose:

  * **The judgement** — *which surfaces count as curation* — lives here, in
    ``CURATED_SURFACES`` (the global D-8 definition). Changing it (e.g. adding an editorial
    assignment surface) is one line here.
  * **The evidence** — *did such an impression happen* — is read through the neutral D-7
    selector ``signals.selectors.has_impression``. Signals stays a raw store that never
    judges what its rows mean (DESIGN §5d, alt 3).

Failure posture is **fail-closed and loud** (DESIGN §8): if the evidence read raises, the
rating is recorded *not* weight-eligible with basis ``CURATION_UNVERIFIED`` and a metric is
incremented — never silently granted weight, and never blocked (a determination is always
returned, so AC5 holds even when the gate can't verify).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from apps.core import observability
from apps.ratings.models import EligibilityBasis
from apps.signals import selectors as signals
from apps.signals.kinds import Surface

logger = logging.getLogger(__name__)

# THE gate definition (global D-8). An impression on one of these surfaces is organic
# curation; an open APP_PAGE view or any other surface is NOT (DESIGN §4.1/§5b). This is the
# single source of truth for "what counts as curation" — see DECISIONS.md D-8.
CURATED_SURFACES: frozenset[str] = frozenset({Surface.DIGEST})


@dataclass(frozen=True)
class EligibilityDetermination:
    """The recorded outcome of one gate check — stored on the rating row (AC5)."""

    weight_eligible: bool
    basis: EligibilityBasis
    determined_at: datetime


def determine_eligibility(
    user, app_id: UUID, *, as_of: datetime
) -> EligibilityDetermination:
    """Decide whether ``user``'s rating of ``app_id`` is weight-eligible, as of ``as_of``.

    Weight-eligible **iff** the user has an impression of this app on a ``CURATED_SURFACES``
    surface at/before ``as_of``. The evidence read is wrapped: on any failure we fail
    **closed** — not eligible, basis ``CURATION_UNVERIFIED``, ``RATING_GATE_UNVERIFIED``
    incremented — and still return a determination (the rating always stores; integrity is
    never silently granted).
    """
    try:
        is_curated = signals.has_impression(
            user.id, app_id, surfaces=CURATED_SURFACES, as_of=as_of
        )
    except Exception:
        # Fail closed + loud: the gate could not verify curation, so it grants no weight, but
        # the rating is not blocked. Re-derivable later once the read recovers (R1).
        observability.increment(
            observability.RATING_GATE_UNVERIFIED, app_id=str(app_id)
        )
        logger.warning(
            "curated-rating gate read failed; recording CURATION_UNVERIFIED app_id=%s",
            app_id,
            exc_info=True,
        )
        return EligibilityDetermination(
            weight_eligible=False,
            basis=EligibilityBasis.CURATION_UNVERIFIED,
            determined_at=as_of,
        )

    if is_curated:
        return EligibilityDetermination(
            weight_eligible=True,
            basis=EligibilityBasis.CURATED_DIGEST_IMPRESSION,
            determined_at=as_of,
        )
    return EligibilityDetermination(
        weight_eligible=False,
        basis=EligibilityBasis.NO_CURATED_IMPRESSION,
        determined_at=as_of,
    )
