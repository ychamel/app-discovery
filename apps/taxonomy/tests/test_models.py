"""Tests for the taxonomy data model and initial migration (T-02, DESIGN.md §4)."""

import uuid

from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from apps.taxonomy.models import Cluster, Tag


class ClusterModelTests(TestCase):
    def test_uuid_primary_key(self):
        cluster = Cluster.objects.create(slug="tools", name="Tools")
        self.assertIsInstance(cluster.id, uuid.UUID)

    def test_slug_uniqueness_is_case_insensitive(self):
        Cluster.objects.create(slug="Tools", name="Tools")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cluster.objects.create(slug="tools", name="Tools (dup)")


class TagModelTests(TestCase):
    def setUp(self):
        self.cluster = Cluster.objects.create(slug="productivity", name="Productivity")

    def test_uuid_primary_key_is_the_cross_feature_reference(self):
        tag = Tag.objects.create(slug="todo-app", label="To-do app")
        self.assertIsInstance(tag.id, uuid.UUID)

    def test_status_defaults_to_active(self):
        tag = Tag.objects.create(slug="todo-app", label="To-do app")
        self.assertEqual(tag.status, Tag.Status.ACTIVE)
        self.assertTrue(tag.is_active)

    def test_slug_uniqueness_is_case_insensitive(self):
        Tag.objects.create(slug="Todo-App", label="To-do app")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(slug="todo-app", label="Other label")

    def test_labels_differing_only_by_case_cannot_both_exist(self):
        Tag.objects.create(slug="todo-app", label="To-do app")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(slug="todo-app-2", label="TO-DO APP")

    def test_labels_differing_only_by_whitespace_cannot_both_exist(self):
        Tag.objects.create(slug="todo-app", label="To-do app")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(slug="todo-app-2", label="  To-do   app  ")

    def test_distinct_labels_are_allowed(self):
        Tag.objects.create(slug="todo-app", label="To-do app")
        Tag.objects.create(slug="note-app", label="Note app")
        self.assertEqual(Tag.objects.count(), 2)

    def test_replaced_by_is_nullable(self):
        tag = Tag.objects.create(slug="todo-app", label="To-do app")
        self.assertIsNone(tag.replaced_by)

    def test_deleting_successor_sets_replaced_by_null_not_blocked(self):
        successor = Tag.objects.create(slug="tasks", label="Tasks")
        retired = Tag.objects.create(
            slug="todo-app", label="To-do app", replaced_by=successor
        )
        successor.delete()
        retired.refresh_from_db()
        self.assertIsNone(retired.replaced_by_id)
        # The retired tag itself survives — retire is never a delete (AC6).
        self.assertTrue(Tag.objects.filter(pk=retired.pk).exists())

    def test_cluster_membership_is_many_to_many(self):
        other = Cluster.objects.create(slug="tools", name="Tools")
        tag = Tag.objects.create(slug="todo-app", label="To-do app")
        tag.clusters.add(self.cluster, other)
        self.assertEqual(set(tag.clusters.all()), {self.cluster, other})
        self.assertIn(tag, self.cluster.tags.all())


class SchemaTests(TestCase):
    def _constraints(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_tag_slug_has_unique_index(self):
        constraints = self._constraints("taxonomy_tag")
        unique_on_slug = [
            c for c in constraints.values() if c["columns"] == ["slug"] and c["unique"]
        ]
        self.assertTrue(unique_on_slug)

    def test_tag_status_is_indexed(self):
        constraints = self._constraints("taxonomy_tag")
        indexed_status = [
            c for c in constraints.values() if c["columns"] == ["status"] and c["index"]
        ]
        self.assertTrue(indexed_status)
