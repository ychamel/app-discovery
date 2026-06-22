"""T-02 — the single write path ``set_interests`` / ``clear_interests`` (DESIGN §5.1/§7).

Every test runs against the **real taxonomy D-5 surface** (real seeded tags + real
``retire_tag`` to create the no-successor state) — no mocking of ``is_valid_tag`` /
``resolve_tag`` — so the §7 preserve-on-edit seam is exercised against genuine states.
"""

import uuid
from unittest import mock

from django.test import TestCase

from apps.core import observability
from apps.interests import services
from apps.interests.errors import InterestValidationError
from apps.interests.models import Interest
from apps.interests.tests.helpers import make_tag, make_user
from apps.taxonomy import services as taxonomy_services


def _stored_ids(user) -> set:
    return set(Interest.objects.filter(user=user).values_list("tag_id", flat=True))


class SetInterestsHappyPathTests(TestCase):
    def test_first_declaration_persists_exactly_the_submitted_tags(self):
        # AC1: a first declaration of active tags persists exactly those rows.
        user = make_user()
        a, b = make_tag("calm"), make_tag("focus")
        with mock.patch.object(observability, "increment") as inc:
            result = services.set_interests(user, [a.id, b.id])
        self.assertEqual(_stored_ids(user), {a.id, b.id})
        self.assertEqual((result.added, result.removed, result.total), (2, 0, 2))
        inc.assert_called_once_with(observability.INTEREST_DECLARED)

    def test_set_replace_adds_and_removes_on_an_existing_profile(self):
        # AC4: the stored set becomes exactly the new set (additions in, removals gone).
        user = make_user()
        a, b, c = make_tag("calm"), make_tag("focus"), make_tag("zen")
        services.set_interests(user, [a.id, b.id])
        with mock.patch.object(observability, "increment") as inc:
            result = services.set_interests(user, [b.id, c.id])  # drop a, add c
        self.assertEqual(_stored_ids(user), {b.id, c.id})
        self.assertEqual((result.added, result.removed, result.total), (1, 1, 2))
        inc.assert_called_once_with(observability.INTEREST_PROFILE_UPDATED)

    def test_saving_the_identical_set_is_an_idempotent_noop(self):
        user = make_user()
        a, b = make_tag("calm"), make_tag("focus")
        services.set_interests(user, [a.id, b.id])
        with mock.patch.object(observability, "increment") as inc:
            result = services.set_interests(user, [a.id, b.id])
        self.assertEqual(_stored_ids(user), {a.id, b.id})
        self.assertEqual((result.added, result.removed), (0, 0))
        inc.assert_not_called()  # no row churn, no metric

    def test_save_to_empty_on_a_non_empty_profile_counts_cleared(self):
        user = make_user()
        a = make_tag("calm")
        services.set_interests(user, [a.id])
        with mock.patch.object(observability, "increment") as inc:
            result = services.set_interests(user, [])
        self.assertEqual(_stored_ids(user), set())
        self.assertEqual(result.total, 0)
        inc.assert_called_once_with(observability.INTEREST_PROFILE_CLEARED)


class SetInterestsValidationTests(TestCase):
    def test_one_invalid_id_rejects_the_whole_save_with_no_partial_write(self):
        # AC2 all-or-nothing: a single off-vocabulary id → nothing persisted, prior intact.
        user = make_user()
        a, b = make_tag("calm"), make_tag("focus")
        services.set_interests(user, [a.id])  # prior state
        with mock.patch.object(observability, "increment") as inc:
            with self.assertRaises(InterestValidationError):
                services.set_interests(user, [b.id, uuid.uuid4()])  # one unknown id
        self.assertEqual(_stored_ids(user), {a.id})  # prior set unchanged
        inc.assert_called_once_with(
            observability.INTEREST_DECLARATION_REJECTED, reason="invalid_tag"
        )

    def test_a_retired_tag_id_is_rejected_at_the_write_boundary(self):
        # is_valid_tag is active-only — a retired id can't be (re-)declared via the picker.
        user = make_user()
        retired = make_tag("legacy")
        taxonomy_services.retire_tag(retired, replaced_by=None)
        with self.assertRaises(InterestValidationError):
            services.set_interests(user, [retired.id])
        self.assertEqual(_stored_ids(user), set())

    def test_a_malformed_id_is_rejected_not_crashed(self):
        user = make_user()
        with self.assertRaises(InterestValidationError):
            services.set_interests(user, ["not-a-uuid"])
        self.assertEqual(_stored_ids(user), set())

    def test_over_size_submit_is_rejected_with_no_write(self):
        from django.test import override_settings

        user = make_user()
        a, b, c = make_tag("a"), make_tag("b"), make_tag("c")
        with override_settings(INTEREST_DECLARATION_MAX=2):
            with mock.patch.object(observability, "increment") as inc:
                with self.assertRaises(InterestValidationError):
                    services.set_interests(user, [a.id, b.id, c.id])
        self.assertEqual(_stored_ids(user), set())
        inc.assert_called_once_with(
            observability.INTEREST_DECLARATION_REJECTED, reason="over_size"
        )


class PreserveOnEditTests(TestCase):
    """The load-bearing §7 seam (AC7 / M5 = 0) — built against real retire_tag states."""

    def test_no_successor_retired_ref_survives_a_later_edit(self):
        # A stored id whose tag is later retired with NO successor: the active-only picker
        # can't show it, so a save that doesn't include it must PRESERVE it (never dropped).
        user = make_user()
        kept, doomed = make_tag("calm"), make_tag("soon-retired")
        services.set_interests(user, [kept.id, doomed.id])
        taxonomy_services.retire_tag(doomed, replaced_by=None)  # no successor

        # The user re-saves only the active tag they can still see.
        services.set_interests(user, [kept.id])

        # The un-showable retired ref survived the re-save (AC7 / M5 = 0 across edits).
        self.assertEqual(_stored_ids(user), {kept.id, doomed.id})

    def test_renamed_ref_normalizes_toward_the_active_successor(self):
        # A stored id whose tag is retired WITH a successor resolves to the active successor
        # (which the picker shows + pre-checks). Re-saving with the successor checked drops
        # the old id (not preserved) — meaning preserved, store normalized toward active.
        user = make_user()
        old = make_tag("old-name")
        successor = make_tag("new-name")
        services.set_interests(user, [old.id])
        taxonomy_services.retire_tag(old, replaced_by=successor)

        services.set_interests(user, [successor.id])  # picker shows the successor, checked

        self.assertEqual(_stored_ids(user), {successor.id})  # old id dropped, meaning kept

    def test_preserved_ref_does_not_block_adding_new_active_tags(self):
        user = make_user()
        active, doomed = make_tag("calm"), make_tag("soon-retired")
        added = make_tag("focus")
        services.set_interests(user, [active.id, doomed.id])
        taxonomy_services.retire_tag(doomed, replaced_by=None)

        services.set_interests(user, [active.id, added.id])

        self.assertEqual(_stored_ids(user), {active.id, added.id, doomed.id})


class ClearInterestsTests(TestCase):
    def test_clear_deletes_all_rows_including_a_preserved_non_active_ref(self):
        # AC9: an explicit full wipe bypasses the §7 preserve rule — even the un-showable ref.
        user = make_user()
        active, doomed = make_tag("calm"), make_tag("soon-retired")
        services.set_interests(user, [active.id, doomed.id])
        taxonomy_services.retire_tag(doomed, replaced_by=None)

        with mock.patch.object(observability, "increment") as inc:
            deleted = services.clear_interests(user)

        self.assertEqual(deleted, 2)
        self.assertEqual(_stored_ids(user), set())
        inc.assert_called_once_with(observability.INTEREST_PROFILE_CLEARED)

    def test_clearing_an_empty_profile_is_a_zero_noop(self):
        user = make_user()
        with mock.patch.object(observability, "increment") as inc:
            self.assertEqual(services.clear_interests(user), 0)
        inc.assert_not_called()


class NoSignalsCaptureImportTests(TestCase):
    def test_services_module_does_not_import_signals_capture(self):
        # IP-5 (DESIGN §17): the cleanest proof declaration is preference state, not behavior,
        # is that the write path never imports the corpus emitter. We parse the module's
        # import statements (not its prose) so the docstring may name the invariant freely.
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(services))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imported.add(module)
                imported.update(f"{module}.{alias.name}" for alias in node.names)

        signals_imports = {name for name in imported if "signals" in name}
        self.assertEqual(
            signals_imports, set(), f"interests.services must not import signals: {signals_imports}"
        )
