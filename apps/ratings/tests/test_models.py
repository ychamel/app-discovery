"""T-02 — structural facts about the ``Rating`` store (DESIGN §4.1).

These assert the *shape* the design mandates, independent of any write logic:

  * **AC6 (structural):** the table has the gate columns but **no** score/weight/rank/
    average/quality column — ``weight_eligible`` is an eligibility boolean, not a quality value.
  * **AC8:** a unique constraint on ``(user, app_id)`` — one active rating per user per app.
  * **DESIGN §4.2:** the ``user`` FK is ``SET_NULL`` (anonymize-on-deletion).
"""

from django.db import models
from django.test import TestCase

from apps.ratings.models import EligibilityBasis, Rating

# Names that would indicate a computed quality value living in this layer (AC6 forbids it).
# ``weight_eligible`` is deliberately excluded: it is the gate's *eligibility* boolean, not a score.
FORBIDDEN_QUALITY_FIELDS = {"weight", "rank", "average", "avg", "quality", "stars", "rating_value"}


class RatingShapeTests(TestCase):
    def _field_names(self) -> set[str]:
        return {field.name for field in Rating._meta.get_fields()}

    def test_records_the_gate_determination(self):
        names = self._field_names()
        self.assertIn("weight_eligible", names)
        self.assertIn("eligibility_basis", names)
        self.assertIn("eligibility_determined_at", names)

    def test_has_no_score_or_quality_column(self):
        # AC6 is structural: there is nowhere here to store a computed score/rank/average.
        # ``score`` is the user's own 1..N rating input, not a computed quality value.
        names = self._field_names()
        self.assertEqual(names & FORBIDDEN_QUALITY_FIELDS, set())

    def test_score_is_the_users_input_not_a_computed_value(self):
        field = Rating._meta.get_field("score")
        self.assertIsInstance(field, models.PositiveSmallIntegerField)

    def test_user_fk_is_set_null_on_deletion(self):
        field = Rating._meta.get_field("user")
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)

    def test_unique_constraint_on_user_and_app(self):
        constraint_names = {
            c.name
            for c in Rating._meta.constraints
            if isinstance(c, models.UniqueConstraint)
        }
        self.assertIn("ratings_one_active_per_user_app", constraint_names)
        constraint = next(
            c for c in Rating._meta.constraints if c.name == "ratings_one_active_per_user_app"
        )
        self.assertEqual(tuple(constraint.fields), ("user", "app_id"))

    def test_eligibility_basis_records_the_three_reasons(self):
        self.assertEqual(
            {basis.value for basis in EligibilityBasis},
            {"curated_digest_impression", "no_curated_impression", "curation_unverified"},
        )
