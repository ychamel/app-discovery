"""Tests for the developer HTTP API — endpoints 1–8 (T-09, DESIGN.md §5c).

Each endpoint's success shape/status plus its documented error statuses: a non-developer
gets 403, a valid-but-not-owner id gets 404 (no enumeration), a bad lifecycle transition
gets 409, and a missing field / off-vocab tag / bad media gets 400 with no partial write.
"""

import tempfile
import uuid

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog import services
from apps.catalog.models import App
from apps.catalog.tests.helpers import (
    make_account,
    make_developer,
    make_image_upload,
)
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag(slug="todo-app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, "To-do app", clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DeveloperApiTests(TestCase):
    def setUp(self):
        self.dev = make_developer("dev@example.com")
        self.tag = _valid_tag()
        self.api = APIClient()
        self.api.force_authenticate(self.dev)

    def _submit_via_service(self, owner=None, **overrides):
        kwargs = {
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "tag_ids": [self.tag.id],
            "media": [make_image_upload()],
        }
        kwargs.update(overrides)
        return services.submit_app(owner or self.dev, **kwargs)

    # --- endpoint 1: POST /api/apps ---
    def test_create_app_returns_201_pending(self):
        response = self.api.post(
            reverse("catalog:api-app-create"),
            {
                "name": "Demo",
                "description": "A demo app.",
                "url": "https://demo.example.com",
                "tag_ids": [str(self.tag.id)],
                "media": [make_image_upload()],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "pending")

    def test_create_requires_developer_role(self):
        plain = make_account("plain@example.com")
        self.api.force_authenticate(plain)
        response = self.api.post(
            reverse("catalog:api-app-create"),
            {"name": "x", "description": "y", "url": "https://e.com",
             "media": [make_image_upload()]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_create_is_403(self):
        self.api.force_authenticate(None)
        response = self.api.post(reverse("catalog:api-app-create"), {}, format="multipart")
        self.assertEqual(response.status_code, 403)

    def test_create_missing_field_returns_400_no_write(self):
        response = self.api.post(
            reverse("catalog:api-app-create"),
            {"description": "y", "url": "https://e.com", "tag_ids": [str(self.tag.id)],
             "media": [make_image_upload()]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())
        self.assertEqual(App.objects.count(), 0)

    def test_create_off_vocabulary_tag_returns_400(self):
        response = self.api.post(
            reverse("catalog:api-app-create"),
            {"name": "Demo", "description": "y", "url": "https://e.com",
             "tag_ids": [str(uuid.uuid4())], "media": [make_image_upload()]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(App.objects.count(), 0)

    # --- endpoint 2: GET /api/apps/mine ---
    def test_mine_lists_only_callers_apps(self):
        self._submit_via_service(self.dev)
        other = make_developer("other@example.com")
        self._submit_via_service(other, url="https://other.example.com")
        response = self.api.get(reverse("catalog:api-app-mine"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    # --- endpoint 3: GET /api/apps/{id} ---
    def test_detail_of_own_app(self):
        app = self._submit_via_service()
        response = self.api.get(reverse("catalog:api-app-detail", args=[app.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(app.id))

    def test_detail_of_another_owners_app_is_404(self):
        other = make_developer("other@example.com")
        app = self._submit_via_service(other, url="https://other.example.com")
        response = self.api.get(reverse("catalog:api-app-detail", args=[app.id]))
        self.assertEqual(response.status_code, 404)

    # --- endpoint 4: PATCH /api/apps/{id} ---
    def test_patch_edits_metadata(self):
        app = self._submit_via_service()
        response = self.api.patch(
            reverse("catalog:api-app-detail", args=[app.id]),
            {"name": "Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Renamed")

    def test_patch_invalid_value_returns_400(self):
        app = self._submit_via_service()
        response = self.api.patch(
            reverse("catalog:api-app-detail", args=[app.id]),
            {"url": "not-a-url"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    # --- endpoint 5/6: media ---
    def test_add_and_remove_media(self):
        app = self._submit_via_service()
        add = self.api.post(
            reverse("catalog:api-app-media", args=[app.id]),
            {"image": make_image_upload("b.png")},
            format="multipart",
        )
        self.assertEqual(add.status_code, 201)
        media_id = add.json()["id"]
        remove = self.api.delete(
            reverse("catalog:api-app-media-item", args=[app.id, media_id])
        )
        self.assertEqual(remove.status_code, 204)

    def test_remove_last_media_returns_400(self):
        app = self._submit_via_service()
        only = app.media.first()
        response = self.api.delete(
            reverse("catalog:api-app-media-item", args=[app.id, only.id])
        )
        self.assertEqual(response.status_code, 400)

    # --- endpoint 7/8: withdraw / resubmit ---
    def test_withdraw_then_resubmit(self):
        app = self._submit_via_service()
        w = self.api.post(reverse("catalog:api-app-withdraw", args=[app.id]))
        self.assertEqual(w.status_code, 200)
        self.assertEqual(w.json()["status"], "withdrawn")
        r = self.api.post(reverse("catalog:api-app-resubmit", args=[app.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "pending")

    def test_double_withdraw_returns_409(self):
        app = self._submit_via_service()
        self.api.post(reverse("catalog:api-app-withdraw", args=[app.id]))
        again = self.api.post(reverse("catalog:api-app-withdraw", args=[app.id]))
        self.assertEqual(again.status_code, 409)
