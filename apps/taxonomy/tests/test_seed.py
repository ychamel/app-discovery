"""Tests for the seed file format + seed_taxonomy command (T-06, DESIGN.md §6)."""

import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.taxonomy.models import Cluster, Tag


def _write_yaml(text: str) -> str:
    """Write YAML to a temp file and return its path (caller seeds from it)."""
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    handle.write(text)
    handle.close()
    return handle.name


def _seed(text: str) -> None:
    call_command("seed_taxonomy", file=_write_yaml(text))


BASE_VOCAB = """
clusters:
  - slug: productivity
    name: Productivity
    description: Get things done.
tags:
  - slug: todo-app
    label: To-do app
    definition: Track a task list.
    clusters: [productivity]
"""


class SeedApplyTests(TestCase):
    def test_seed_creates_clusters_and_tags(self):
        _seed(BASE_VOCAB)
        self.assertEqual(Cluster.objects.count(), 1)
        tag = Tag.objects.get(slug="todo-app")
        self.assertEqual(tag.label, "To-do app")
        self.assertEqual([c.slug for c in tag.clusters.all()], ["productivity"])

    def test_re_running_unchanged_file_is_a_no_op(self):
        _seed(BASE_VOCAB)
        tag = Tag.objects.get(slug="todo-app")
        original_id, original_updated_at = tag.id, tag.updated_at
        _seed(BASE_VOCAB)
        tag.refresh_from_db()
        self.assertEqual(tag.id, original_id)
        self.assertEqual(tag.updated_at, original_updated_at)  # nothing written
        self.assertEqual(Tag.objects.count(), 1)

    def test_editing_a_label_updates_only_that_label_keeping_id_and_slug(self):
        _seed(BASE_VOCAB)
        tag = Tag.objects.get(slug="todo-app")
        original_id, original_slug = tag.id, tag.slug
        _seed(BASE_VOCAB.replace("label: To-do app", "label: Task manager"))
        tag.refresh_from_db()
        self.assertEqual(tag.label, "Task manager")
        self.assertEqual(tag.id, original_id)
        self.assertEqual(tag.slug, original_slug)


class SeedAbortTests(TestCase):
    def test_malformed_yaml_aborts_and_writes_nothing(self):
        with self.assertRaises(CommandError):
            _seed("clusters: [unterminated")
        self.assertEqual(Cluster.objects.count(), 0)

    def test_tag_referencing_unknown_cluster_aborts_with_no_partial_apply(self):
        bad = """
clusters:
  - slug: productivity
    name: Productivity
tags:
  - slug: todo-app
    label: To-do app
    clusters: [does-not-exist]
"""
        with self.assertRaises(CommandError):
            _seed(bad)
        # No partial apply: the valid cluster before the bad tag was rolled back.
        self.assertEqual(Cluster.objects.count(), 0)
        self.assertEqual(Tag.objects.count(), 0)

    def test_tag_missing_required_label_aborts(self):
        bad = """
clusters:
  - slug: productivity
    name: Productivity
tags:
  - slug: todo-app
    clusters: [productivity]
"""
        with self.assertRaises(CommandError):
            _seed(bad)
        self.assertEqual(Tag.objects.count(), 0)


class SeedRetireTests(TestCase):
    def test_explicit_retire_flag_routes_through_retire_tag(self):
        vocab = """
clusters:
  - slug: productivity
    name: Productivity
tags:
  - slug: tasks
    label: Tasks
    clusters: [productivity]
  - slug: todo-app
    label: To-do app
    clusters: [productivity]
    retired: true
    replaced_by: tasks
"""
        _seed(vocab)
        retired = Tag.objects.get(slug="todo-app")
        successor = Tag.objects.get(slug="tasks")
        self.assertEqual(retired.status, Tag.Status.RETIRED)
        self.assertIsNotNone(retired.retired_at)
        self.assertEqual(retired.replaced_by_id, successor.id)

    def test_tag_dropped_from_file_is_not_deleted(self):
        _seed(BASE_VOCAB)
        # Re-seed without the tag — it must survive (no silent reference breakage, AC6).
        _seed(
            """
clusters:
  - slug: productivity
    name: Productivity
"""
        )
        self.assertTrue(Tag.objects.filter(slug="todo-app").exists())
