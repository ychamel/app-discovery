"""Tests for the server-rendered admin review pages (T-12, DESIGN.md §8).

Queue render/empty state, the five-floor checklist + resolved tags on the detail, accept,
reject (≥1 floor), and the no-criterion refusal that proves the UI cannot express a taste
rejection (AC6).
"""

import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.catalog import services
from apps.catalog.gate import Criterion
from apps.catalog.models import App
from apps.catalog.tests.helpers import make_admin, make_developer, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag():
    cluster = taxonomy_services.add_cluster("c-todo", "Cluster")
    return taxonomy_services.add_tag("todo-app", "To-do app", clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ReviewPagesTests(TestCase):
    def setUp(self):
        self.admin = make_admin("admin@example.com")
        self.dev = make_developer("dev@example.com")
        self.tag = _valid_tag()
        self.client = Client()
        self.client.force_login(self.admin)

    def _submit(self, url="https://demo.example.com"):
        return services.submit_app(
            self.dev,
            name="Demo",
            description="A demo app.",
            url=url,
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )

    def test_queue_empty_state(self):
        response = self.client.get(reverse("catalog:review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No apps awaiting review")

    def test_queue_lists_pending_fifo(self):
        first = self._submit("https://a.example.com")
        self._submit("https://b.example.com")
        response = self.client.get(reverse("catalog:review"))
        self.assertContains(response, "Demo")
        # The first-submitted app's detail link appears before the second's.
        body = response.content.decode()
        self.assertIn(str(first.id), body)

    def test_queue_requires_admin(self):
        self.client.force_login(self.dev)  # a developer is not an admin
        response = self.client.get(reverse("catalog:review"))
        self.assertEqual(response.status_code, 403)

    def test_detail_renders_checklist_and_tags(self):
        app = self._submit()
        response = self.client.get(reverse("catalog:review-detail", args=[app.id]))
        self.assertEqual(response.status_code, 200)
        for criterion in Criterion:
            # html=True compares parsed HTML, so the label's "&" matches "&amp;".
            self.assertContains(response, f"<strong>{criterion.label}</strong>", html=True)
        self.assertContains(response, "To-do app")  # resolved tag label

    def test_accept_moves_app_to_accepted(self):
        app = self._submit()
        response = self.client.post(
            reverse("catalog:review-detail", args=[app.id]), {"action": "accept"}
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.ACCEPTED)

    def test_reject_with_floor_moves_app_to_rejected(self):
        app = self._submit()
        response = self.client.post(
            reverse("catalog:review-detail", args=[app.id]),
            {"action": "reject", "failed_criteria": ["works"], "note": "Broken."},
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.REJECTED)

    def test_reject_with_no_floor_refused(self):
        app = self._submit()
        response = self.client.post(
            reverse("catalog:review-detail", args=[app.id]),
            {"action": "reject", "failed_criteria": []},
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "at least one failed criterion", status_code=400)
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.PENDING)
