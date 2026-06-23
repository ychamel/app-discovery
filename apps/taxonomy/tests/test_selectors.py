"""Tests for the taxonomy read/validate/resolve path (T-04, DESIGN.md §5a/§10)."""

import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.taxonomy import selectors, services
from apps.taxonomy.models import Tag


class IsValidTagTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])

    def test_active_tag_is_valid(self):
        self.assertTrue(selectors.is_valid_tag(self.tag.id))

    def test_retired_tag_is_not_valid(self):
        services.retire_tag(self.tag)
        self.assertFalse(selectors.is_valid_tag(self.tag.id))

    def test_unknown_id_is_not_valid(self):
        self.assertFalse(selectors.is_valid_tag(uuid.uuid4()))

    def test_malformed_id_is_not_valid_not_an_error(self):
        self.assertFalse(selectors.is_valid_tag("not-a-uuid"))


class ResolveTagTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        self.successor = services.add_tag("tasks", "Tasks", clusters=[self.cluster])

    def test_renamed_active_tag_resolves_to_itself_with_new_label(self):
        services.rename_tag(self.tag, label="Task manager")
        resolved = selectors.resolve_tag(self.tag.id)
        self.assertEqual(resolved.id, self.tag.id)
        self.assertEqual(resolved.label, "Task manager")

    def test_retired_with_successor_resolves_to_active_successor(self):
        services.retire_tag(self.tag, replaced_by=self.successor)
        resolved = selectors.resolve_tag(self.tag.id)
        self.assertEqual(resolved.id, self.successor.id)

    def test_retired_without_successor_resolves_to_itself(self):
        services.retire_tag(self.tag)
        resolved = selectors.resolve_tag(self.tag.id)
        self.assertEqual(resolved.id, self.tag.id)  # kept, never dropped

    def test_unknown_id_resolves_to_none(self):
        self.assertIsNone(selectors.resolve_tag(uuid.uuid4()))

    def test_multi_hop_chain_resolves_to_final_successor(self):
        final = services.add_tag("work", "Work", clusters=[self.cluster])
        # Chains form over time: retire into a then-active successor, which is itself
        # later retired into the next active successor.
        services.retire_tag(self.tag, replaced_by=self.successor)
        services.retire_tag(self.successor, replaced_by=final)
        resolved = selectors.resolve_tag(self.tag.id)
        self.assertEqual(resolved.id, final.id)

    @override_settings(TAXONOMY_RESOLVE_MAX_STEPS=4)
    def test_replaced_by_cycle_stops_and_counts_reference_break(self):
        # Hand-build a cycle by writing replaced_by directly (bypassing the service's
        # cycle guard) to prove resolve_tag itself never loops.
        Tag.objects.filter(pk=self.tag.pk).update(replaced_by=self.successor)
        Tag.objects.filter(pk=self.successor.pk).update(replaced_by=self.tag)

        with patch.object(selectors.observability, "increment") as increment:
            resolved = selectors.resolve_tag(self.tag.id)

        self.assertIsNotNone(resolved)  # returns last good tag, does not loop/raise
        increment.assert_called_once()
        self.assertEqual(
            increment.call_args.args[0], selectors.observability.TAXONOMY_REFERENCE_BREAK
        )


class TagIdsResolvingToTests(TestCase):
    """The reverse of resolve_tag (open-search-browse §6.2): predecessors that mean a tag now."""

    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")

    def _tag(self, slug, label):
        return services.add_tag(slug, label, clusters=[self.cluster])

    def test_singleton_resolves_to_itself(self):
        tag = self._tag("todo-app", "To-do app")
        self.assertEqual(selectors.tag_ids_resolving_to(tag.id), frozenset({tag.id}))

    def test_merge_chain_includes_all_transitive_predecessors(self):
        # X → W → Y (X merged into W, W merged into Y): resolving to Y matches all three (AC3).
        x = self._tag("x", "X")
        w = self._tag("w", "W")
        y = self._tag("y", "Y")
        services.retire_tag(x, replaced_by=w)
        services.retire_tag(w, replaced_by=y)
        self.assertEqual(
            selectors.tag_ids_resolving_to(y.id), frozenset({x.id, w.id, y.id})
        )

    def test_branching_merges_include_both_predecessors(self):
        # Two tags merged into the same active tag → both predecessors are included.
        a = self._tag("a", "A")
        b = self._tag("b", "B")
        target = self._tag("target", "Target")
        services.retire_tag(a, replaced_by=target)
        services.retire_tag(b, replaced_by=target)
        self.assertEqual(
            selectors.tag_ids_resolving_to(target.id),
            frozenset({a.id, b.id, target.id}),
        )

    def test_unknown_id_returns_empty_set(self):
        self.assertEqual(selectors.tag_ids_resolving_to(uuid.uuid4()), frozenset())

    def test_malformed_id_returns_empty_set_not_an_error(self):
        self.assertEqual(selectors.tag_ids_resolving_to("not-a-uuid"), frozenset())

    def test_query_count_bounded_by_chain_depth_not_catalogue_size(self):
        # The walk touches only the vocabulary (never App): one existence check + one query
        # per frontier level. A 2-hop chain = existence + 3 frontier steps = 4 queries.
        x = self._tag("x", "X")
        w = self._tag("w", "W")
        y = self._tag("y", "Y")
        services.retire_tag(x, replaced_by=w)
        services.retire_tag(w, replaced_by=y)
        with self.assertNumQueries(4):
            selectors.tag_ids_resolving_to(y.id)


class ListSelectorTests(TestCase):
    def setUp(self):
        self.c1 = services.add_cluster("productivity", "Productivity")
        self.c2 = services.add_cluster("tools", "Tools")
        self.active = services.add_tag("todo-app", "To-do app", clusters=[self.c1, self.c2])
        self.retired = services.add_tag("legacy", "Legacy", clusters=[self.c1])
        services.retire_tag(self.retired)

    def test_list_active_tags_excludes_retired(self):
        labels = {t.label for t in selectors.list_active_tags()}
        self.assertEqual(labels, {"To-do app"})

    def test_list_active_tags_prefetches_clusters_no_n_plus_one(self):
        # One query for tags + one for the prefetched M2M, regardless of tag count.
        with self.assertNumQueries(2):
            tags = selectors.list_active_tags()
            [list(t.clusters.all()) for t in tags]

    def test_list_clusters_carries_only_active_tags(self):
        clusters = {c.slug: c for c in selectors.list_clusters()}
        c1_tags = {t.label for t in clusters["productivity"].tags.all()}
        self.assertEqual(c1_tags, {"To-do app"})  # retired "Legacy" excluded
