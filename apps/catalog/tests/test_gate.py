"""Tests for the intake gate (T-02 / DESIGN.md §6).

The load-bearing assertion is that ``Criterion`` has *exactly* the five objective floors
and **no catch-all value** — that is the structural guarantee a taste rejection (AC6/R1)
cannot be recorded. A future "other" slipped into the enum would fail this test loudly.
"""

from django.test import SimpleTestCase, override_settings

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
    _CORE = frozenset({"name", "description", "url", "tags", "media"})
    _NEW = frozenset({"tagline", "deep_dive", "facets", "demo_clip"})

    def test_default_gates_core_floor_plus_all_new_fields(self):
        # Honesty-first default (D-14b): the five core floors AND all four marketing fields.
        self.assertEqual(gate.gate_relevant_fields(), self._CORE | self._NEW)

    @override_settings(APP_PAGE_GATED_FIELDS=["tagline"])
    def test_config_can_relax_a_new_field_without_a_code_change(self):
        # Relax to gate only tagline among the new fields — deep_dive/facets/demo_clip no
        # longer force re-review; the core floor stays gated regardless.
        self.assertEqual(gate.gate_relevant_fields(), self._CORE | {"tagline"})

    @override_settings(APP_PAGE_GATED_FIELDS=[])
    def test_config_can_relax_all_new_fields_but_never_the_core_floor(self):
        self.assertEqual(gate.gate_relevant_fields(), self._CORE)

    @override_settings(APP_PAGE_GATED_FIELDS=["tagline", "bogus", "priority"])
    def test_unknown_names_can_never_widen_the_gate(self):
        # An off-candidate name is intersected out — config can only relax, never widen.
        self.assertEqual(gate.gate_relevant_fields(), self._CORE | {"tagline"})
