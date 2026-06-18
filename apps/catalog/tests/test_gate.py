"""Tests for the intake gate (T-02 / DESIGN.md §6).

The load-bearing assertion is that ``Criterion`` has *exactly* the five objective floors
and **no catch-all value** — that is the structural guarantee a taste rejection (AC6/R1)
cannot be recorded. A future "other" slipped into the enum would fail this test loudly.
"""

from django.test import SimpleTestCase

from apps.catalog import gate


class CriterionEnumTests(SimpleTestCase):
    def test_exactly_the_five_objective_floors(self):
        # Pinning the member set means adding a 6th value (e.g. "other"/"quality") is a
        # deliberate, test-breaking change — never an unreviewed slip (AC6).
        self.assertEqual(
            set(gate.Criterion.values),
            {"works", "not_spam", "not_duplicate", "honest_metadata", "policy"},
        )

    def test_no_catch_all_value(self):
        forbidden = {"other", "quality", "low_quality", "not_for_us", "taste"}
        self.assertEqual(set(gate.Criterion.values) & forbidden, set())


class ChecklistTests(SimpleTestCase):
    def test_every_criterion_has_non_empty_wording(self):
        for criterion in gate.Criterion:
            self.assertIn(criterion, gate.CHECKLIST)
            self.assertTrue(gate.CHECKLIST[criterion].strip())

    def test_checklist_has_no_extra_keys(self):
        self.assertEqual(set(gate.CHECKLIST.keys()), set(gate.Criterion))

    def test_duplicate_floor_wording_references_url_signal(self):
        # The duplicate floor stays deterministic by pointing the reviewer at the
        # URL-collision hint (DESIGN.md §6c).
        self.assertIn("URL", gate.CHECKLIST[gate.Criterion.NOT_DUPLICATE])


class GateRelevantFieldsTests(SimpleTestCase):
    def test_equals_documented_set(self):
        self.assertEqual(
            gate.GATE_RELEVANT_FIELDS,
            frozenset({"name", "description", "url", "tags", "media"}),
        )
