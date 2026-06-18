"""Tests for the review HTTP API — endpoints 9–10 (T-10, DESIGN.md §5c).

Queue ordering/shape (FIFO, no priority field, AC3), accept, reject (≥1 floor + note),
the 400/403/409 paths, and that the developer notification fires after a committed decision.
"""

import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog import services, views
from apps.catalog.models import App, ReviewDecision
from apps.catalog.tests.helpers import make_admin, make_developer, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag():
    cluster = taxonomy_services.add_cluster("c-todo", "Cluster")
    return taxonomy_services.add_tag("todo-app", "To-do app", clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ReviewApiTests(TestCase):
    def setUp(self):
        self.admin = make_admin("admin@example.com")
        self.dev = make_developer("dev@example.com")
        self.tag = _valid_tag()
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def _submit(self, url="https://demo.example.com"):
        return services.submit_app(
            self.dev,
            name="Demo",
            description="A demo app.",
            url=url,
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )

    # --- endpoint 9: GET /api/review/queue ---
    def test_queue_is_fifo_with_hint_and_no_priority(self):
        first = self._submit("https://a.example.com")
        second = self._submit("https://b.example.com")
        response = self.api.get(reverse("catalog:api-review-queue"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([row["app"]["id"] for row in data], [str(first.id), str(second.id)])
        self.assertIn("duplicate_hint", data[0])
        self.assertNotIn("priority", data[0])

    def test_queue_requires_admin(self):
        self.api.force_authenticate(self.dev)  # a developer is not an admin
        response = self.api.get(reverse("catalog:api-review-queue"))
        self.assertEqual(response.status_code, 403)

    # --- endpoint 10: POST /api/apps/{id}/decision ---
    def test_accept_decision(self):
        app = self._submit()
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "accepted")
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.ACCEPTED)

    def test_reject_decision_records_criteria(self):
        app = self._submit()
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "rejected", "failed_criteria": ["works"], "note": "Broken."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReviewDecision.objects.filter(app=app).count(), 1)
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.REJECTED)

    def test_reject_with_zero_criteria_is_400(self):
        app = self._submit()
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "rejected", "failed_criteria": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reject_with_unknown_criterion_is_400(self):
        app = self._submit()
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "rejected", "failed_criteria": ["quality"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_outcome_is_400(self):
        app = self._submit()
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "maybe"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_decision_on_non_pending_app_is_409(self):
        app = self._submit()
        services.accept_app(app, self.admin)  # already decided
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_decision_requires_admin(self):
        app = self._submit()
        self.api.force_authenticate(self.dev)
        response = self.api.post(
            reverse("catalog:api-app-decision", args=[app.id]),
            {"outcome": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_notification_invoked_after_decision(self):
        app = self._submit()
        with mock.patch.object(views.notifications, "notify_decision") as notify:
            self.api.post(
                reverse("catalog:api-app-decision", args=[app.id]),
                {"outcome": "accepted"},
                format="json",
            )
        notify.assert_called_once()
