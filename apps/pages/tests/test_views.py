"""T-04 — the three views, end-to-end through the project URLconf (DESIGN.md §5a/§7/§10).

Covers AC5 (open access), AC6 (authenticated capture), AC7 (capture non-blocking), AC8
(only accepted apps render), and the §10 security boundaries (no open redirect, no
attribution forgery, CSRF on share). The template detail is T-05's concern.
"""

import uuid
from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse

from apps.signals.kinds import EventKind, Surface
from apps.signals.models import EngagementEvent, Impression
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user


class AppPageRenderTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.url = reverse("pages:app-page", args=[self.app.id])

    def test_anonymous_gets_full_page_no_auth_wall(self):
        """AC5 — open access: an anonymous visitor gets a 200, no redirect, no capture."""
        response = Client().get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.app.name)
        self.assertEqual(Impression.objects.count(), 0)

    def test_authenticated_view_emits_app_page_impression(self):
        """AC6 — an authenticated page view records an app_page-surface impression (DESIGN §6)."""
        client = Client()
        client.force_login(make_user("viewer@example.com"))
        response = client.get(self.url)

        self.assertEqual(response.status_code, 200)
        impression = Impression.objects.get()
        self.assertEqual(impression.surface, Surface.APP_PAGE)
        self.assertEqual(impression.app_id, self.app.id)

    def test_rendered_counter_emitted(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            Client().get(self.url)
        self.assertTrue(any("app_page_rendered" in line for line in logs.output))


class NotAvailableTests(TestCase):
    """AC8 — only accepted apps render as live; everything else is a 404."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def _submit_only(self, **status):
        from apps.catalog import services as catalog_services
        from apps.signals.tests.helpers import _png_upload

        return catalog_services.submit_app(
            self.owner, name="Pending App", description="x",
            url="https://example.com/pending", tag_ids=[self.tag.id],
            media=[_png_upload()],
        )

    def test_unknown_id_is_404_and_counted(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            response = Client().get(reverse("pages:app-page", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "isn’t available", status_code=404)
        self.assertTrue(any("app_page_not_available" in line for line in logs.output))

    def test_pending_app_is_404(self):
        pending = self._submit_only()
        response = Client().get(reverse("pages:app-page", args=[pending.id]))
        self.assertEqual(response.status_code, 404)

    def test_non_uuid_path_is_404_at_routing(self):
        self.assertEqual(Client().get("/apps/not-a-uuid/").status_code, 404)

    def test_catalog_read_failure_is_a_loud_500(self):
        """A genuine catalog failure is the page's core dependency → loud 500, not hidden."""
        with mock.patch(
            "apps.pages.views.catalog.get_catalogued_app",
            side_effect=RuntimeError("DB down"),
        ):
            with self.assertRaises(RuntimeError):
                Client().get(reverse("pages:app-page", args=[uuid.uuid4()]))


class TryRedirectTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.viewer = make_user("viewer@example.com")

    def _impression_id(self, client):
        client.get(reverse("pages:app-page", args=[self.app.id]))
        return Impression.objects.get().id

    def test_authenticated_try_records_click_through_linked_and_302s(self):
        """AC6 — try-it with a valid imp records a linked click_through and 302s to the app URL."""
        client = Client()
        client.force_login(self.viewer)
        imp = self._impression_id(client)

        response = client.get(reverse("pages:try", args=[self.app.id]) + f"?imp={imp}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.app.url)

        event = EngagementEvent.objects.get(kind=EventKind.CLICK_THROUGH)
        self.assertEqual(event.impression_id, imp)
        self.assertEqual(event.app_id, self.app.id)

    def test_redirect_target_is_server_side_not_a_request_param(self):
        """§10 — no open redirect: the Location is the catalog URL regardless of request input."""
        response = Client().get(
            reverse("pages:try", args=[self.app.id]) + "?imp=&next=https://evil.example"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.app.url)

    def test_foreign_impression_writes_no_event_but_still_redirects(self):
        """§10 — a forged/foreign imp is rejected inside capture → no event, still 302s."""
        other = make_user("other@example.com")
        other_client = Client()
        other_client.force_login(other)
        foreign_imp = self._impression_id(other_client)  # belongs to `other`

        client = Client()
        client.force_login(self.viewer)
        response = client.get(
            reverse("pages:try", args=[self.app.id]) + f"?imp={foreign_imp}"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.app.url)
        self.assertFalse(EngagementEvent.objects.filter(kind=EventKind.CLICK_THROUGH).exists())

    def test_anonymous_try_redirects_without_capture(self):
        response = Client().get(reverse("pages:try", args=[self.app.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.app.url)
        self.assertFalse(EngagementEvent.objects.exists())

    def test_try_on_unknown_app_is_404(self):
        self.assertEqual(
            Client().get(reverse("pages:try", args=[uuid.uuid4()])).status_code, 404
        )


class ShareTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.url = reverse("pages:share", args=[self.app.id])

    def test_authenticated_share_records_event_and_returns_204(self):
        client = Client()
        client.force_login(make_user("viewer@example.com"))
        response = client.post(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(EngagementEvent.objects.filter(kind=EventKind.SHARE).exists())

    def test_anonymous_share_is_204_no_event(self):
        response = Client().post(self.url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(EngagementEvent.objects.exists())

    def test_share_get_is_405(self):
        self.assertEqual(Client().get(self.url).status_code, 405)

    def test_share_without_csrf_is_403(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(make_user("viewer@example.com"))
        self.assertEqual(client.post(self.url).status_code, 403)

    def test_share_on_unknown_app_is_404(self):
        client = Client()
        client.force_login(make_user("viewer@example.com"))
        self.assertEqual(
            client.post(reverse("pages:share", args=[uuid.uuid4()])).status_code, 404
        )


class CaptureFailureIsNonBlockingTests(TestCase):
    """AC7 — when capture is down, render/redirect/share all still succeed; loss is counted."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.viewer = make_user("viewer@example.com")

    def test_render_redirect_share_survive_capture_failure(self):
        client = Client()
        client.force_login(self.viewer)
        broken = mock.patch(
            "apps.pages.emission.capture.record_impression",
            side_effect=RuntimeError("signals down"),
        )
        with broken, self.assertLogs("apps.metrics", level="INFO") as logs:
            page = client.get(reverse("pages:app-page", args=[self.app.id]))
        self.assertEqual(page.status_code, 200)
        self.assertTrue(any("app_page_capture_degraded" in line for line in logs.output))

        with mock.patch(
            "apps.pages.emission.capture.record_click_through",
            side_effect=RuntimeError("signals down"),
        ):
            redirect_response = client.get(reverse("pages:try", args=[self.app.id]) + "?imp=")
        self.assertEqual(redirect_response.status_code, 302)

        with mock.patch(
            "apps.pages.emission.capture.record_share",
            side_effect=RuntimeError("signals down"),
        ):
            share_response = client.post(reverse("pages:share", args=[self.app.id]))
        self.assertEqual(share_response.status_code, 204)
