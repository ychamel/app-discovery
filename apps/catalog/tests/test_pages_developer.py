"""Tests for the server-rendered developer pages (T-11, DESIGN.md §8).

The pages post to the same services as the API: a complete submit creates a pending app
and redirects; an invalid one re-renders with errors and creates nothing (AC1); my-apps
shows the empty state and per-app status, with a rejected app's reasons + a resubmit path
(AC7); and the edit/withdraw/resubmit controls drive the lifecycle (AC8).
"""

import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.catalog import services
from apps.catalog.gate import Criterion
from apps.catalog.models import App
from apps.catalog.tests.helpers import make_developer, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag():
    cluster = taxonomy_services.add_cluster("c-todo", "Cluster")
    return taxonomy_services.add_tag("todo-app", "To-do app", clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DeveloperPagesTests(TestCase):
    def setUp(self):
        self.dev = make_developer("dev@example.com")
        self.tag = _valid_tag()
        self.client = Client()
        self.client.force_login(self.dev)

    def _submit_via_service(self, url="https://demo.example.com"):
        return services.submit_app(
            self.dev,
            name="Demo",
            description="A demo app.",
            url=url,
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )

    # --- submit ---
    def test_submit_page_renders(self):
        response = self.client.get(reverse("catalog:submit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submit an app")

    def test_submit_valid_creates_pending_and_redirects(self):
        response = self.client.post(
            reverse("catalog:submit"),
            {
                "name": "Demo",
                "description": "A demo app.",
                "url": "https://demo.example.com",
                "tags": [str(self.tag.id)],
                "media": [make_image_upload()],
            },
        )
        self.assertEqual(response.status_code, 302)
        app = App.objects.get()
        self.assertEqual(app.status, App.Status.PENDING)
        self.assertEqual(response.headers["Location"], reverse("catalog:app-detail", args=[app.id]))

    def test_submit_invalid_rerenders_and_creates_nothing(self):
        response = self.client.post(
            reverse("catalog:submit"),
            {
                "description": "A demo app.",
                "url": "https://demo.example.com",
                "tags": [str(self.tag.id)],
                "media": [make_image_upload()],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(App.objects.count(), 0)

    def test_submit_requires_developer_role(self):
        from apps.catalog.tests.helpers import make_account

        plain = make_account("plain@example.com")
        self.client.force_login(plain)
        response = self.client.get(reverse("catalog:submit"))
        self.assertEqual(response.status_code, 403)

    # --- my apps ---
    def test_my_apps_empty_state(self):
        response = self.client.get(reverse("catalog:my-apps"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "haven't submitted")

    def test_my_apps_links_to_dashboard(self):
        # UX-003 reciprocal link: the submissions list must reach the analytics dashboard
        # so both developer surfaces are mutually discoverable.
        response = self.client.get(reverse("catalog:my-apps"))
        self.assertContains(response, f'href="{reverse("dashboard:my-apps")}"')

    def test_my_apps_shows_status_and_rejection_reasons(self):
        app = self._submit_via_service()
        reviewer = make_developer("rev@example.com")
        services.reject_app(app, reviewer, failed_criteria=[Criterion.WORKS], note="Broken.")
        response = self.client.get(reverse("catalog:my-apps"))
        self.assertContains(response, "rejected")
        # The label is HTML-escaped in the page (Reachable &amp; functional).
        self.assertContains(response, "Reachable &amp; functional")
        self.assertContains(response, "Broken.")

    # --- detail / edit / withdraw / resubmit ---
    def test_detail_edit_updates_app(self):
        app = self._submit_via_service()
        response = self.client.post(
            reverse("catalog:app-detail", args=[app.id]),
            {
                "action": "edit",
                "name": "Renamed",
                "description": "A demo app.",
                "url": "https://demo.example.com",
                "tags": [str(self.tag.id)],
            },
        )
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.name, "Renamed")

    def test_accepted_app_detail_shows_return_to_review_warning(self):
        app = self._submit_via_service()
        app.status = App.Status.ACCEPTED
        app.save(update_fields=["status"])
        response = self.client.get(reverse("catalog:app-detail", args=[app.id]))
        self.assertContains(response, "returns it to review")

    def test_withdraw_and_resubmit(self):
        app = self._submit_via_service()
        self.client.post(
            reverse("catalog:app-detail", args=[app.id]), {"action": "withdraw"}
        )
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.WITHDRAWN)
        self.client.post(
            reverse("catalog:app-detail", args=[app.id]), {"action": "resubmit"}
        )
        app.refresh_from_db()
        self.assertEqual(app.status, App.Status.PENDING)

    def test_detail_of_another_owners_app_is_404(self):
        other = make_developer("other@example.com")
        app = services.submit_app(
            other,
            name="Other",
            description="d",
            url="https://other.example.com",
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )
        response = self.client.get(reverse("catalog:app-detail", args=[app.id]))
        self.assertEqual(response.status_code, 404)
