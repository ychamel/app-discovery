"""T-06 — the thin HTTP views (DESIGN §5g/§6.4), via the project URLconf + test client.

Covers AC1 (signed-in follow + PRG; unknown → 404), AC2 (anonymous → sign-in redirect, no
write), AC3 (unfollow + PRG), AC4 (feed lists current follows + empty state, never errors),
AC6 (feed app links target the app page), AC7 (capture failure → message + not-followed),
AC8 (notices empty state), the feed/notice fail-soft fallbacks, plus method (405) and CSRF
(403).
"""

from unittest import mock
from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog import services as catalog_services
from apps.subscriptions.models import Subscription
from apps.subscriptions.tests.helpers import make_accepted_app, make_tag, make_user


class FollowViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.url = reverse("subscriptions:follow", args=[self.app.id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    # --- AC1 --------------------------------------------------------------
    def test_signed_in_follow_stores_and_redirects_to_the_page(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)
        self.assertEqual(
            Subscription.objects.filter(user=self.user, app_id=self.app.id).count(), 1
        )

    def test_unknown_app_is_404(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("subscriptions:follow", args=[uuid4()]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_non_accepted_app_is_404(self):
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
            reverse("subscriptions:follow", args=[pending.id])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_non_uuid_path_is_404_at_routing(self):
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.post("/subscriptions/apps/not-a-uuid/follow").status_code, 404
        )

    # --- AC2 --------------------------------------------------------------
    def test_anonymous_follow_redirects_to_signin_and_writes_nothing(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/signin", response["Location"])
        self.assertIn("next=", response["Location"])
        self.assertEqual(Subscription.objects.count(), 0)

    # --- AC7 --------------------------------------------------------------
    def test_capture_failure_shows_a_message_and_leaves_user_not_following(self):
        self.client.force_login(self.user)
        with mock.patch(
            "apps.subscriptions.services.signals_capture.record_subscribe",
            side_effect=RuntimeError("capture down"),
        ):
            response = self.client.post(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        msgs = [m.message for m in response.context["messages"]]
        self.assertTrue(msgs)  # a clear error was surfaced
        self.assertEqual(Subscription.objects.count(), 0)  # honestly not-followed

    # --- method / CSRF ----------------------------------------------------
    def test_get_is_405(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_post_without_csrf_is_403(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url).status_code, 403)


class UnfollowViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.follow_url = reverse("subscriptions:follow", args=[self.app.id])
        self.unfollow_url = reverse("subscriptions:unfollow", args=[self.app.id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    # --- AC3 --------------------------------------------------------------
    def test_unfollow_removes_the_row_and_redirects(self):
        self.client.force_login(self.user)
        self.client.post(self.follow_url)
        response = self.client.post(self.unfollow_url)
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_unfollow_when_not_following_still_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(self.unfollow_url)
        self.assertRedirects(response, self.page_url, fetch_redirect_response=False)

    def test_anonymous_unfollow_redirects_to_signin(self):
        response = self.client.post(self.unfollow_url)
        self.assertIn("/auth/signin", response["Location"])


class FeedViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.feed_url = reverse("subscriptions:feed")

    def _app(self, name):
        return make_accepted_app(self.owner, tag_ids=[self.tag.id], name=name)

    # --- AC4 --------------------------------------------------------------
    def test_feed_lists_current_follows(self):
        app = self._app("Followed App")
        self.client.force_login(self.user)
        self.client.post(reverse("subscriptions:follow", args=[app.id]))

        html = self.client.get(self.feed_url).content.decode()
        self.assertIn("Followed App", html)

    def test_feed_empty_state_when_no_follows(self):
        self.client.force_login(self.user)
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("not following any apps yet", response.content.decode())

    # --- AC6 --------------------------------------------------------------
    def test_feed_app_links_target_the_app_page(self):
        app = self._app("Linked App")
        self.client.force_login(self.user)
        self.client.post(reverse("subscriptions:follow", args=[app.id]))
        html = self.client.get(self.feed_url).content.decode()
        self.assertIn(reverse("pages:app-page", args=[app.id]), html)

    # --- AC8 --------------------------------------------------------------
    def test_feed_renders_the_notices_empty_state(self):
        self.client.force_login(self.user)
        html = self.client.get(self.feed_url).content.decode()
        self.assertIn('aria-label="Notices"', html)
        self.assertIn("No news yet", html)

    def test_anonymous_feed_redirects_to_signin(self):
        response = self.client.get(self.feed_url)
        self.assertIn("/auth/signin", response["Location"])

    # --- fail-soft --------------------------------------------------------
    def test_feed_degrades_when_followed_apps_raises(self):
        from apps.core import observability

        self.client.force_login(self.user)
        with (
            mock.patch(
                "apps.subscriptions.views.selectors.followed_apps",
                side_effect=RuntimeError("read down"),
            ),
            mock.patch(
                "apps.subscriptions.views.observability.increment"
            ) as increment,
        ):
            response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)  # no 500
        increment.assert_any_call(observability.SUBSCRIPTION_FEED_DEGRADED)

    def test_feed_degrades_when_notices_raises(self):
        from apps.core import observability

        self.client.force_login(self.user)
        with (
            mock.patch(
                "apps.subscriptions.views.notices.notices_for_apps",
                side_effect=RuntimeError("notice down"),
            ),
            mock.patch(
                "apps.subscriptions.views.observability.increment"
            ) as increment,
        ):
            response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("No news yet", response.content.decode())
        increment.assert_any_call(observability.SUBSCRIPTION_NOTICE_DEGRADED)


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(10, 10, 10)).save(buffer, format="PNG")
    return SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
