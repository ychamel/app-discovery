"""T-03 — the curated-rating gate (DESIGN §5b).

The gate is tested in isolation against a **faked evidence seam** (the ``has_impression``
selector is patched), so these assert the gate's *judgement and failure posture*, not the
signals query (which has its own tests in ``apps.signals.tests.test_has_impression``).
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from django.test import SimpleTestCase

from apps.ratings import gate
from apps.ratings.models import EligibilityBasis
from apps.signals.kinds import Surface

AS_OF = datetime(2026, 6, 21, 12, tzinfo=UTC)


class CuratedSurfacesTests(SimpleTestCase):
    def test_pins_the_d8_definition_to_digest_only(self):
        # The single source of truth for "what counts as curation" (D-8). An open APP_PAGE
        # view must never count.
        self.assertEqual(gate.CURATED_SURFACES, frozenset({Surface.DIGEST}))
        self.assertNotIn(Surface.APP_PAGE, gate.CURATED_SURFACES)


class DetermineEligibilityTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=uuid4())
        self.app_id = uuid4()

    def test_curated_when_a_qualifying_impression_exists(self):
        with mock.patch(
            "apps.signals.selectors.has_impression", return_value=True
        ) as has_impression:
            result = gate.determine_eligibility(self.user, self.app_id, as_of=AS_OF)

        self.assertTrue(result.weight_eligible)
        self.assertEqual(result.basis, EligibilityBasis.CURATED_DIGEST_IMPRESSION)
        self.assertEqual(result.determined_at, AS_OF)
        # The gate reads through the neutral D-7 selector with its own surface judgement.
        has_impression.assert_called_once_with(
            self.user.id, self.app_id, surfaces=gate.CURATED_SURFACES, as_of=AS_OF
        )

    def test_not_curated_when_no_qualifying_impression(self):
        with mock.patch("apps.signals.selectors.has_impression", return_value=False):
            result = gate.determine_eligibility(self.user, self.app_id, as_of=AS_OF)

        self.assertFalse(result.weight_eligible)
        self.assertEqual(result.basis, EligibilityBasis.NO_CURATED_IMPRESSION)

    def test_fails_closed_and_loud_when_the_evidence_read_raises(self):
        with (
            mock.patch(
                "apps.signals.selectors.has_impression",
                side_effect=RuntimeError("signals down"),
            ),
            mock.patch("apps.ratings.gate.observability.increment") as increment,
        ):
            # The exception must NOT propagate — a determination is always returned (AC5).
            result = gate.determine_eligibility(self.user, self.app_id, as_of=AS_OF)

        self.assertFalse(result.weight_eligible)
        self.assertEqual(result.basis, EligibilityBasis.CURATION_UNVERIFIED)
        increment.assert_called_once()
        self.assertEqual(
            increment.call_args.args[0], gate.observability.RATING_GATE_UNVERIFIED
        )
