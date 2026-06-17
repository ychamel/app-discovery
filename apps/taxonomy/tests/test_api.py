"""Tests for the taxonomy JSON read API (T-05, DESIGN.md §5c)."""

import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Account
from apps.taxonomy import services


class TaxonomyApiTestCase(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("reader@example.com")
        self.api = APIClient()
        self.api.force_authenticate(self.account)

        self.cluster = services.add_cluster(
            "productivity", "Productivity", description="Get stuff done"
        )
        self.tag = services.add_tag(
            "todo-app", "To-do app", clusters=[self.cluster], definition="Manage a task list"
        )
        self.retired = services.add_tag("legacy", "Legacy", clusters=[self.cluster])
        services.retire_tag(self.retired)


class TagListEndpointTests(TaxonomyApiTestCase):
    def test_lists_active_tags_with_clusters(self):
        response = self.api.get(reverse("taxonomy:tag-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)  # retired tag excluded
        tag = data[0]
        self.assertEqual(tag["id"], str(self.tag.id))
        self.assertEqual(tag["slug"], "todo-app")
        self.assertEqual(tag["label"], "To-do app")
        self.assertEqual(tag["definition"], "Manage a task list")
        self.assertEqual(tag["clusters"][0]["slug"], "productivity")
        self.assertEqual(tag["clusters"][0]["name"], "Productivity")

    def test_unauthenticated_is_rejected(self):
        response = APIClient().get(reverse("taxonomy:tag-list"))
        self.assertEqual(response.status_code, 403)  # DRF SessionAuth: no challenge → 403


class TagDetailEndpointTests(TaxonomyApiTestCase):
    def test_returns_active_tag_detail(self):
        response = self.api.get(reverse("taxonomy:tag-detail", args=[self.tag.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "active")
        self.assertIsNone(data["replaced_by"])

    def test_returns_retired_tag_with_successor_reference(self):
        services.retire_tag(self.retired, replaced_by=self.tag)
        response = self.api.get(reverse("taxonomy:tag-detail", args=[self.retired.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "retired")
        self.assertEqual(data["replaced_by"], str(self.tag.id))

    def test_unknown_id_is_404(self):
        response = self.api.get(reverse("taxonomy:tag-detail", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_is_rejected(self):
        response = APIClient().get(reverse("taxonomy:tag-detail", args=[self.tag.id]))
        self.assertEqual(response.status_code, 403)  # DRF SessionAuth: no challenge → 403


class ClusterListEndpointTests(TaxonomyApiTestCase):
    def test_lists_clusters_with_active_tags_only(self):
        response = self.api.get(reverse("taxonomy:cluster-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        cluster = next(c for c in data if c["slug"] == "productivity")
        self.assertEqual(cluster["name"], "Productivity")
        self.assertEqual(cluster["description"], "Get stuff done")
        labels = {t["label"] for t in cluster["tags"]}
        self.assertEqual(labels, {"To-do app"})  # retired "Legacy" excluded

    def test_unauthenticated_is_rejected(self):
        response = APIClient().get(reverse("taxonomy:cluster-list"))
        self.assertEqual(response.status_code, 403)  # DRF SessionAuth: no challenge → 403
