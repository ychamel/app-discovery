"""T-06 — the thin HTTP views (DESIGN §5e), via the project URLconf + Django test client.

Covers AC1 (signed-in submit + PRG), AC2 (invalid → message + nothing stored; unknown →
404), AC3 (anonymous → sign-in redirect, no write), AC8 (re-submit updates same row; remove
deletes), AC9 (non-accepted/unknown/non-UUID rejected), plus method (405) and CSRF (403).
"""

from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog import services as catalog_services
from apps.ratings.models import Rating
from apps.ratings.tests.helpers import make_accepted_app, make_tag, make_user


class SubmitViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.url = reverse("ratings:submit", args=[self.app.id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    # --- AC1 --------------------------------------------------------------
    def test_signed_in_valid_submit_stores_and_redirects_to_the_page(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"score": "4", "review_text": "good"})
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)
        self.assertEqual(Rating.objects.filter(user=self.user, app_id=self.app.id).count(), 1)

    # --- AC2 --------------------------------------------------------------
    def test_invalid_score_redirects_back_with_a_message_and_stores_nothing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"score": "9"}, follow=True)
        self.assertEqual(Rating.objects.count(), 0)
        msgs = [m.message for m in response.context["messages"]]
        self.assertTrue(msgs)  # a clear error was surfaced

    def test_unknown_app_is_404(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("ratings:submit", args=[uuid4()]), {"score": "3"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Rating.objects.count(), 0)

    # --- AC9 --------------------------------------------------------------
    def test_non_accepted_app_is_404(self):
        # A submitted-but-not-accepted app is not catalogued → not rateable.
        pending = catalog_services.submit_app(
            self.owner,
            name="Pending App",
            description="not yet accepted",
            url="https://example.com/pending",
            tag_ids=[make_tag("draft").id],
            media=[_png()],
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("ratings:submit", args=[pending.id]), {"score": "3"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Rating.objects.count(), 0)

    def test_non_uuid_path_is_404_at_routing(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.post("/ratings/apps/not-a-uuid/rating", {"score": "3"}).status_code,
            404,
        )

    # --- AC3 --------------------------------------------------------------
    def test_anonymous_submit_redirects_to_signin_and_writes_nothing(self):
        response = self.client.post(self.url, {"score": "5"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/signin", response["Location"])
        self.assertIn("next=", response["Location"])
        self.assertEqual(Rating.objects.count(), 0)

    # --- AC8 --------------------------------------------------------------
    def test_resubmit_updates_the_same_row(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"score": "2"})
        self.client.post(self.url, {"score": "5", "review_text": "better now"})
        rows = Rating.objects.filter(user=self.user, app_id=self.app.id)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().score, 5)

    # --- method / CSRF ----------------------------------------------------
    def test_get_is_405_for_authenticated_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_post_without_csrf_is_403(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url, {"score": "3"}).status_code, 403)


class RemoveViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.submit_url = reverse("ratings:submit", args=[self.app.id])
        self.remove_url = reverse("ratings:remove", args=[self.app.id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    def test_remove_deletes_the_row_and_redirects(self):
        self.client.force_login(self.user)
        self.client.post(self.submit_url, {"score": "3"})
        response = self.client.post(self.remove_url)
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)
        self.assertEqual(Rating.objects.count(), 0)

    def test_remove_when_none_exists_still_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(self.remove_url)
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)

    def test_anonymous_remove_redirects_to_signin(self):
        response = self.client.post(self.remove_url)
        self.assertIn("/auth/signin", response["Location"])


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(10, 10, 10)).save(buffer, format="PNG")
    return SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
