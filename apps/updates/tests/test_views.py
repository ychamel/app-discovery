"""T-05 — the HTTP layer end-to-end (DESIGN §6.5/§7/§8), via the project URLconf.

Covers AC1 (role + owner gate), AC2/AC3 (post update/early-access → channel + follower feed),
AC4/AC5 (audience-scoped pull delivery; M5 = 0; no impression injected), AC6 (no corpus write),
AC7 (manage/withdraw + feed re-read), AC8 (rate-limit at the HTTP boundary), the method (405)
gate, and the §7 failure split (audience/channel degraded soft; post fail-soft).
"""

import uuid
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.core import observability
from apps.signals.models import EngagementEvent, Impression
from apps.subscriptions.models import Subscription
from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import (
    make_accepted_app,
    make_account,
    make_developer,
    make_tag,
)


class ChannelListGateTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.url = reverse("updates:my-channels")

    def test_non_developer_is_403(self):
        self.client.force_login(make_account("user@example.com"))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_redirects_to_signin(self):
        self.assertIn("/auth/signin", self.client.get(self.url)["Location"])

    def test_lists_only_accepted_owned_apps(self):
        make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Accepted App")
        # A pending (never-accepted) submission must not appear as a channel.
        from apps.catalog import services as catalog_services

        catalog_services.submit_app(
            self.dev,
            name="Pending App",
            description="x",
            url="https://example.com/pending",
            tag_ids=[self.tag.id],
            media=[_png()],
        )
        self.client.force_login(self.dev)
        html = self.client.get(self.url).content.decode()
        self.assertIn("Accepted App", html)
        self.assertNotIn("Pending App", html)

    def test_own_nothing_state_is_200(self):
        self.client.force_login(self.dev)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no accepted apps yet", response.content.decode())


class ChannelViewGateTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.url = reverse("updates:channel", args=[self.app.id])

    def test_non_developer_is_403(self):
        self.client.force_login(make_account("user@example.com"))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_owner_sees_the_post_form(self):
        self.client.force_login(self.dev)
        html = self.client.get(self.url).content.decode()
        self.assertIn("Post an update", html)
        self.assertIn(reverse("updates:post", args=[self.app.id]), html)

    def test_another_devs_app_is_404(self):
        other = make_developer("other@example.com")
        other_app = make_accepted_app(other, tag_ids=[self.tag.id], name="Theirs")
        self.client.force_login(self.dev)
        url = reverse("updates:channel", args=[other_app.id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_app_is_404(self):
        self.client.force_login(self.dev)
        url = reverse("updates:channel", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_audience_hint_shows_follower_count(self):
        Subscription.objects.create(user=make_account("f@example.com"), app_id=self.app.id)
        self.client.force_login(self.dev)
        html = self.client.get(self.url).content.decode()
        self.assertIn("Reaches 1 current follower", html)

    def test_empty_notices_state(self):
        self.client.force_login(self.dev)
        html = self.client.get(self.url).content.decode()
        self.assertIn("No notices yet", html)


class PostViewTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.post_url = reverse("updates:post", args=[self.app.id])
        self.channel_url = reverse("updates:channel", args=[self.app.id])

    def _post(self, **data):
        body = {"kind": "update", "title": "Title", "summary": "Summary"}
        body.update(data)
        return self.client.post(self.post_url, body)

    def test_valid_update_creates_one_notice_and_prg(self):
        self.client.force_login(self.dev)
        response = self._post(kind="update")
        self.assertRedirects(response, self.channel_url)
        self.assertEqual(Notice.objects.filter(kind="update").count(), 1)

    def test_valid_early_access_creates_one_notice(self):
        self.client.force_login(self.dev)
        self._post(kind="early_access", title="Beta")
        self.assertEqual(Notice.objects.filter(kind="early_access").count(), 1)

    def test_posted_notice_appears_in_channel_list(self):
        self.client.force_login(self.dev)
        self._post(title="Channel-visible")
        html = self.client.get(self.channel_url).content.decode()
        self.assertIn("Channel-visible", html)

    def test_invalid_post_prgs_back_with_message_and_creates_nothing(self):
        self.client.force_login(self.dev)
        response = self.client.post(
            self.post_url,
            {"kind": "update", "title": "   ", "summary": "Summary"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notice.objects.count(), 0)
        msgs = [m.message for m in response.context["messages"]]
        self.assertTrue(any("blank" in m for m in msgs))

    def test_non_owner_post_is_404(self):
        other = make_developer("other@example.com")
        other_app = make_accepted_app(other, tag_ids=[self.tag.id], name="Theirs")
        self.client.force_login(self.dev)
        response = self.client.post(
            reverse("updates:post", args=[other_app.id]),
            {"kind": "update", "title": "T", "summary": "S"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Notice.objects.count(), 0)

    def test_non_developer_post_is_403(self):
        self.client.force_login(make_account("user@example.com"))
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Notice.objects.count(), 0)

    def test_get_on_post_route_is_405(self):
        self.client.force_login(self.dev)
        self.assertEqual(self.client.get(self.post_url).status_code, 405)

    def test_unexpected_error_fails_soft_with_message_and_counter(self):
        self.client.force_login(self.dev)
        with (
            mock.patch(
                "apps.updates.views.services.post_notice",
                side_effect=RuntimeError("db down"),
            ),
            mock.patch("apps.updates.views.observability.increment") as increment,
        ):
            response = self._post()
        self.assertRedirects(response, self.channel_url)  # never a 500
        increment.assert_any_call(observability.UPDATES_POST_FAILED)


class RateLimitHttpTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.post_url = reverse("updates:post", args=[self.app.id])

    def _post(self):
        return self.client.post(
            self.post_url, {"kind": "update", "title": "T", "summary": "S"}
        )

    def test_posting_past_the_limit_prgs_back_and_creates_nothing(self):
        from django.test import override_settings

        self.client.force_login(self.dev)
        with override_settings(UPDATES_MAX_POSTS_PER_WINDOW=1):
            self._post()
            response = self.client.post(
                self.post_url,
                {"kind": "update", "title": "T", "summary": "S"},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)  # PRG, not 500
        self.assertEqual(Notice.objects.count(), 1)
        msgs = [m.message for m in response.context["messages"]]
        self.assertTrue(any("limit" in m for m in msgs))


class WithdrawHttpTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.channel_url = reverse("updates:channel", args=[self.app.id])

    def _make_notice(self):
        return Notice.objects.create(
            author=self.dev,
            app_id=self.app.id,
            kind=NoticeKind.UPDATE,
            title="To withdraw",
            summary="body",
        )

    def _withdraw_url(self, notice_id):
        return reverse("updates:withdraw", args=[self.app.id, notice_id])

    def test_withdraw_removes_from_channel_and_prgs(self):
        notice = self._make_notice()
        self.client.force_login(self.dev)
        response = self.client.post(self._withdraw_url(notice.id))
        self.assertRedirects(response, self.channel_url)
        self.assertFalse(Notice.objects.filter(id=notice.id).exists())

    def test_withdraw_unknown_id_is_harmless_noop(self):
        self.client.force_login(self.dev)
        response = self.client.post(self._withdraw_url(uuid.uuid4()))
        self.assertRedirects(response, self.channel_url)

    def test_get_on_withdraw_route_is_405(self):
        notice = self._make_notice()
        self.client.force_login(self.dev)
        self.assertEqual(
            self.client.get(self._withdraw_url(notice.id)).status_code, 405
        )

    def test_channel_lists_notices_newest_first(self):
        from datetime import UTC, datetime

        old = self._make_notice()
        Notice.objects.filter(pk=old.pk).update(
            published_at=datetime(2026, 6, 1, tzinfo=UTC), title="Old"
        )
        new = self._make_notice()
        Notice.objects.filter(pk=new.pk).update(
            published_at=datetime(2026, 6, 5, tzinfo=UTC), title="New"
        )
        self.client.force_login(self.dev)
        html = self.client.get(self.channel_url).content.decode()
        self.assertLess(html.index("New"), html.index("Old"))


class AudienceScopeAndCorpusTests(TestCase):
    """AC4/AC5/AC6 — pull delivery is audience-scoped (M5=0) and never touches the corpus."""

    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Newsy App")
        self.follower = make_account("follower@example.com")
        self.stranger = make_account("stranger@example.com")
        self.feed_url = reverse("subscriptions:feed")

    def _post_notice(self, title="Big news"):
        self.client.force_login(self.dev)
        self.client.post(
            reverse("updates:post", args=[self.app.id]),
            {"kind": "update", "title": title, "summary": "details"},
        )
        self.client.logout()

    def test_notice_reaches_a_follower_but_not_a_non_follower(self):
        Subscription.objects.create(user=self.follower, app_id=self.app.id)
        self._post_notice(title="Followers only")

        self.client.force_login(self.follower)
        self.assertIn("Followers only", self.client.get(self.feed_url).content.decode())
        self.client.logout()

        self.client.force_login(self.stranger)
        self.assertNotIn(
            "Followers only", self.client.get(self.feed_url).content.decode()
        )

    def test_posting_and_viewing_inject_no_corpus_rows(self):
        Subscription.objects.create(user=self.follower, app_id=self.app.id)
        impressions_before = Impression.objects.count()
        events_before = EngagementEvent.objects.count()

        self._post_notice()
        self.client.force_login(self.follower)
        self.client.get(self.feed_url)

        self.assertEqual(Impression.objects.count(), impressions_before)
        self.assertEqual(EngagementEvent.objects.count(), events_before)

    def test_withdrawn_notice_drops_from_follower_feed(self):
        Subscription.objects.create(user=self.follower, app_id=self.app.id)
        self._post_notice(title="Temporary")
        notice = Notice.objects.get()

        self.client.force_login(self.dev)
        self.client.post(
            reverse("updates:withdraw", args=[self.app.id, notice.id])
        )
        self.client.logout()

        self.client.force_login(self.follower)
        self.assertNotIn("Temporary", self.client.get(self.feed_url).content.decode())


class FailureSplitTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.url = reverse("updates:channel", args=[self.app.id])

    def test_audience_hint_degrades_soft(self):
        self.client.force_login(self.dev)
        with (
            mock.patch(
                "apps.updates.views.subscriptions.subscriber_count",
                side_effect=RuntimeError("count down"),
            ),
            mock.patch("apps.updates.views.observability.increment") as increment,
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)  # hint hidden, posting unaffected
        self.assertNotIn("Reaches", response.content.decode())
        increment.assert_any_call(observability.UPDATES_AUDIENCE_DEGRADED)

    def test_channel_notices_degrade_soft(self):
        self.client.force_login(self.dev)
        with (
            mock.patch(
                "apps.updates.views.selectors.notices_for_channel",
                side_effect=RuntimeError("list down"),
            ),
            mock.patch("apps.updates.views.observability.increment") as increment,
        ):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Post an update", body)  # the form still renders
        self.assertIn("Couldn't load your notices", body)
        increment.assert_any_call(observability.UPDATES_CHANNEL_DEGRADED)


def _png():
    """A real, decodable 16x16 PNG (catalog requires ≥1 image)."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(120, 120, 120)).save(buffer, format="PNG")
    return SimpleUploadedFile("shot.png", buffer.getvalue(), content_type="image/png")
