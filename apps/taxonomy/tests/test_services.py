"""Tests for the taxonomy write service (T-03, DESIGN.md §5b/§7/§10).

These exercise the sharpest correctness edges first: the ≥1-cluster invariant,
slug/label de-duplication, and the non-destructive retire rule with successor
validation — all before any HTTP or admin surface depends on them.
"""

from django.test import TestCase

from apps.taxonomy import services
from apps.taxonomy.errors import (
    DuplicateTagError,
    OrphanTagError,
    RetireSuccessorError,
)
from apps.taxonomy.models import Tag


class AddTagTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")

    def test_add_tag_requires_at_least_one_cluster(self):
        with self.assertRaises(OrphanTagError):
            services.add_tag("todo-app", "To-do app", clusters=[])
        self.assertEqual(Tag.objects.count(), 0)  # nothing written (atomic)

    def test_add_tag_creates_active_tag_in_clusters(self):
        tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        self.assertTrue(tag.is_active)
        self.assertEqual(list(tag.clusters.all()), [self.cluster])

    def test_duplicate_slug_is_rejected_and_writes_nothing(self):
        services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        with self.assertRaises(DuplicateTagError):
            services.add_tag("todo-app", "Different label", clusters=[self.cluster])
        self.assertEqual(Tag.objects.count(), 1)

    def test_duplicate_normalized_label_is_rejected(self):
        services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        with self.assertRaises(DuplicateTagError):
            services.add_tag("todo-app-2", "  TO-DO   APP ", clusters=[self.cluster])
        self.assertEqual(Tag.objects.count(), 1)


class RenameTagTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])

    def test_rename_changes_label_only_id_and_slug_unchanged(self):
        original_id, original_slug = self.tag.id, self.tag.slug
        services.rename_tag(self.tag, label="Task manager")
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.label, "Task manager")
        self.assertEqual(self.tag.id, original_id)
        self.assertEqual(self.tag.slug, original_slug)

    def test_rename_into_an_existing_label_is_rejected(self):
        services.add_tag("notes", "Notes", clusters=[self.cluster])
        with self.assertRaises(DuplicateTagError):
            services.rename_tag(self.tag, label="notes")

    def test_rename_to_its_own_label_is_allowed(self):
        services.rename_tag(self.tag, label="To-do app")  # no collision with self
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.label, "To-do app")


class RetireTagTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        self.successor = services.add_tag("tasks", "Tasks", clusters=[self.cluster])

    def test_retire_keeps_the_row_and_sets_status_and_timestamp(self):
        services.retire_tag(self.tag)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.status, Tag.Status.RETIRED)
        self.assertIsNotNone(self.tag.retired_at)
        self.assertTrue(Tag.objects.filter(pk=self.tag.pk).exists())  # never deleted

    def test_retire_with_active_successor(self):
        services.retire_tag(self.tag, replaced_by=self.successor)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.replaced_by_id, self.successor.id)

    def test_retire_into_self_is_rejected(self):
        with self.assertRaises(RetireSuccessorError):
            services.retire_tag(self.tag, replaced_by=self.tag)

    def test_retire_into_a_retired_successor_is_rejected(self):
        services.retire_tag(self.successor)
        with self.assertRaises(RetireSuccessorError):
            services.retire_tag(self.tag, replaced_by=self.successor)

    def test_retire_that_would_form_a_cycle_is_rejected(self):
        # successor already points back at tag; retiring tag into successor closes a loop.
        self.successor.status = Tag.Status.ACTIVE
        self.successor.replaced_by = self.tag
        self.successor.save(update_fields=["replaced_by"])
        with self.assertRaises(RetireSuccessorError):
            services.retire_tag(self.tag, replaced_by=self.successor)

    def test_re_retiring_is_idempotent_keeps_original_timestamp(self):
        services.retire_tag(self.tag)
        self.tag.refresh_from_db()
        first_retired_at = self.tag.retired_at
        services.retire_tag(self.tag)
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.retired_at, first_retired_at)


class UpdateTagTests(TestCase):
    def setUp(self):
        self.c1 = services.add_cluster("productivity", "Productivity")
        self.c2 = services.add_cluster("tools", "Tools")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.c1])
        self.other = services.add_tag("notes", "Notes", clusters=[self.c1])

    def test_update_syncs_label_definition_and_membership(self):
        services.update_tag(
            self.tag, label="Task manager", clusters=[self.c1, self.c2], definition="Manage tasks"
        )
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.label, "Task manager")
        self.assertEqual(self.tag.definition, "Manage tasks")
        self.assertEqual(set(self.tag.clusters.all()), {self.c1, self.c2})

    def test_update_no_change_does_not_bump_updated_at(self):
        before = self.tag.updated_at
        services.update_tag(self.tag, label="To-do app", clusters=[self.c1])
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.updated_at, before)

    def test_update_into_another_tags_label_is_rejected(self):
        with self.assertRaises(DuplicateTagError):
            services.update_tag(self.tag, label="Notes", clusters=[self.c1])

    def test_update_active_tag_to_zero_clusters_is_rejected(self):
        with self.assertRaises(OrphanTagError):
            services.update_tag(self.tag, label="To-do app", clusters=[])


class UpdateClusterTests(TestCase):
    def test_update_syncs_name_and_description_and_is_idempotent(self):
        cluster = services.add_cluster("productivity", "Productivity", description="old")
        services.update_cluster(cluster, name="Productivity!", description="new")
        cluster.refresh_from_db()
        self.assertEqual(cluster.name, "Productivity!")
        self.assertEqual(cluster.description, "new")
        before = cluster.updated_at
        services.update_cluster(cluster, name="Productivity!", description="new")
        cluster.refresh_from_db()
        self.assertEqual(cluster.updated_at, before)  # no-op when unchanged


class ClusterMembershipTests(TestCase):
    def setUp(self):
        self.c1 = services.add_cluster("productivity", "Productivity")
        self.c2 = services.add_cluster("tools", "Tools")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.c1, self.c2])

    def test_remove_from_one_of_two_clusters_is_allowed(self):
        services.remove_from_cluster(self.tag, self.c1)
        self.assertEqual(list(self.tag.clusters.all()), [self.c2])

    def test_remove_from_last_cluster_orphaning_active_tag_is_rejected(self):
        services.remove_from_cluster(self.tag, self.c1)
        with self.assertRaises(OrphanTagError):
            services.remove_from_cluster(self.tag, self.c2)
        self.assertEqual(self.tag.clusters.count(), 1)  # membership unchanged on refusal

    def test_remove_last_cluster_from_retired_tag_is_allowed(self):
        services.retire_tag(self.tag)
        services.remove_from_cluster(self.tag, self.c1)
        services.remove_from_cluster(self.tag, self.c2)  # retired tags may be orphaned
        self.assertEqual(self.tag.clusters.count(), 0)


class CheckIntegrityTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")

    def test_clean_vocabulary_reports_clean(self):
        services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        report = services.check_integrity()
        self.assertTrue(report.is_clean)
        self.assertEqual(report.orphan_active_tags, [])

    def test_orphan_active_tag_is_reported_and_unclean(self):
        # Bypass the service to manufacture an illegal state, then detect it.
        orphan = Tag.objects.create(slug="orphan", label="Orphan")
        report = services.check_integrity()
        self.assertIn(orphan, report.orphan_active_tags)
        self.assertFalse(report.is_clean)

    def test_empty_cluster_is_warned_but_not_unclean(self):
        report = services.check_integrity()  # self.cluster has no tags
        self.assertIn(self.cluster, report.empty_clusters)
        self.assertTrue(report.is_clean)  # empty cluster is a warning, not a violation
