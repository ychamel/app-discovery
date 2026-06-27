"""T-05 — the widget HTTP layer (DESIGN §5.1/§5.2/§7/§8), via the project URLconf.

End-to-end over the live ``widget/`` routes (Django test client): anonymous render (AC5), the
no-build embed shape (AC7), the capped/empty/live notice list (AC1/AC2/AC3), the no-open-redirect
click-through (AC4), the firewall re-asserted over HTTP (AC6), the per-IP rate limit +
Cache-Control (AC8), attribution + xframe exemption (AC9), the fail-soft degrade paths (§8), and
the method gate.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest import mock

from django.core import signing
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core import observability
from apps.ratings.gate import CURATED_SURFACES
from apps.signals.models import EngagementEvent, Impression
from apps.signals.selectors import has_impression
from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import make_accepted_app, make_developer, make_tag
from apps.widget import selectors, source, views


def _render_url(app_id):
    return reverse("widget:render", args=[app_id])


def _view_url(app_id):
    return reverse("widget:view", args=[app_id])


def _window():
    now = timezone.now()
    return {"start": now - timedelta(days=1), "end": now + timedelta(days=1)}


class WidgetViewTestCase(TestCase):
    """Shared fixture: one accepted app owned by a developer, plus a clean cache per test."""

    def setUp(self):
        cache.clear()  # the per-IP limiter counts live in the cache — isolate each test
        self.addCleanup(cache.clear)
        self.developer = make_developer()
        self.app = make_accepted_app(
            self.developer, tag_ids=[make_tag("notes").id], name="Widget Demo"
        )

    def _seed_notice(self, *, title="Notice", kind=NoticeKind.UPDATE, when=None):
        notice = Notice.objects.create(
            author=self.developer, app_id=self.app.id, kind=kind, title=title, summary="body"
        )
        if when is not None:
            Notice.objects.filter(pk=notice.pk).update(published_at=when)
        return notice


class RenderTests(WidgetViewTestCase):
    def test_anonymous_render_returns_200_with_notices_and_link(self):
        self._seed_notice(title="Shipped dark mode")
        response = self.client.get(_render_url(self.app.id))  # no auth (AC5)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Widget Demo", body)
        self.assertIn("Shipped dark mode", body)
        self.assertIn(_view_url(self.app.id), body)  # the view-on-platform link

    def test_render_is_self_contained_no_build(self):
        # AC7: a complete HTML page with no JavaScript and no external asset references.
        self._seed_notice()
        body = self.client.get(_render_url(self.app.id)).content.decode().lower()
        self.assertIn("<!doctype html>", body)
        self.assertNotIn("<script", body)
        self.assertNotIn("http://", body)
        self.assertNotIn("https://", body)

    def test_notices_newest_first_capped(self):
        for day in range(1, 8):  # 7 notices, default limit 5
            self._seed_notice(title=f"Day {day}", when=datetime(2026, 6, day, tzinfo=UTC))
        body = self.client.get(_render_url(self.app.id)).content.decode()
        self.assertIn("Day 7", body)
        self.assertNotIn("Day 1", body)  # capped out
        self.assertLess(body.index("Day 7"), body.index("Day 3"))  # newest-first

    def test_empty_state_shows_message_and_link(self):
        body = self.client.get(_render_url(self.app.id)).content.decode()  # AC2
        self.assertIn("No updates yet.", body)
        self.assertIn(_view_url(self.app.id), body)

    def test_withdrawn_notice_is_gone_on_next_render(self):
        notice = self._seed_notice(title="Temporary")  # AC3 (live read)
        self.assertIn("Temporary", self.client.get(_render_url(self.app.id)).content.decode())
        Notice.objects.filter(pk=notice.pk).delete()
        self.assertNotIn("Temporary", self.client.get(_render_url(self.app.id)).content.decode())

    def test_cache_control_present_on_render(self):
        with override_settings(WIDGET_CACHE_MAX_AGE_SECONDS=42):
            response = self.client.get(_render_url(self.app.id))
        self.assertEqual(response["Cache-Control"], "public, max-age=42")

    def test_xframe_exempt_no_deny_header(self):
        # AC9 / §5.1: the render must be framable cross-origin (no X-Frame-Options: DENY).
        response = self.client.get(_render_url(self.app.id))
        self.assertNotEqual(response.get("X-Frame-Options"), "DENY")

    def test_unknown_id_is_404_unavailable(self):
        response = self.client.get(_render_url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertIn("isn't available", response.content.decode())

    def test_post_is_405(self):
        self.assertEqual(self.client.post(_render_url(self.app.id)).status_code, 405)


class ClickThroughTests(WidgetViewTestCase):
    def test_view_302s_to_the_app_page(self):
        response = self.client.get(_view_url(self.app.id))  # AC4
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("pages:app-page", args=[self.app.id]))

    def test_view_unknown_id_is_404(self):
        self.assertEqual(self.client.get(_view_url(uuid.uuid4())).status_code, 404)

    def test_view_post_is_405(self):
        self.assertEqual(self.client.post(_view_url(self.app.id)).status_code, 405)

    def test_view_arms_a_signed_source_marker_for_the_app(self):
        # T-05: the 302 carries the first-party widget_src cookie, decoding to this app (DESIGN §3).
        response = self.client.get(_view_url(self.app.id))
        self.assertEqual(response.status_code, 302)
        raw = response.cookies[source.COOKIE_NAME].value
        payload = signing.loads(raw, salt=source._SALT, max_age=source._window_seconds())
        self.assertEqual(payload["src"], str(self.app.id))

    def test_a_later_click_for_another_app_overwrites_the_marker(self):
        # Last-touch (WCA-2): the most recent click-through wins.
        other = make_accepted_app(
            self.developer, tag_ids=[make_tag("tools").id], name="Other"
        )
        client = self.client
        client.get(_view_url(self.app.id))
        response = client.get(_view_url(other.id))
        raw = response.cookies[source.COOKIE_NAME].value
        payload = signing.loads(raw, salt=source._SALT, max_age=source._window_seconds())
        self.assertEqual(payload["src"], str(other.id))

    def test_unknown_id_404s_before_any_marker_is_set(self):
        response = self.client.get(_view_url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(source.COOKIE_NAME, response.cookies)

    def test_marker_failure_is_fail_soft_redirect_and_count_unaffected(self):
        # AC6: a marker error must not break the 302 or the click-through reach count.
        with mock.patch.object(
            source, "set_marker", side_effect=RuntimeError("cookie boom")
        ):
            with mock.patch.object(views.observability, "increment") as inc:
                response = self.client.get(_view_url(self.app.id))
        self.assertEqual(response.status_code, 302)  # redirect still fires
        self.assertNotIn(source.COOKIE_NAME, response.cookies)  # no marker armed
        inc.assert_any_call(observability.WIDGET_CONVERSION_DEGRADED)
        # The click-through reach count landed regardless (separate, independent side effect).
        self.assertEqual(
            selectors.widget_reach(self.app.id, **_window()).click_throughs, 1
        )


class AttributionTests(WidgetViewTestCase):
    def test_render_counts_an_impression_and_view_counts_a_click_through(self):
        self.client.get(_render_url(self.app.id))
        self.client.get(_render_url(self.app.id))
        self.client.get(_view_url(self.app.id))
        reach = selectors.widget_reach(self.app.id, **_window())  # AC9
        self.assertEqual(reach.impressions, 2)
        self.assertEqual(reach.click_throughs, 1)


class FirewallHttpTests(WidgetViewTestCase):
    def test_render_and_view_write_no_signals_rows(self):
        self._seed_notice()
        self.client.get(_render_url(self.app.id))  # AC6 end-to-end
        self.client.get(_view_url(self.app.id))
        self.assertEqual(Impression.objects.count(), 0)
        self.assertEqual(EngagementEvent.objects.count(), 0)
        self.assertFalse(
            has_impression(uuid.uuid4(), self.app.id, surfaces=CURATED_SURFACES)
        )


@override_settings(WIDGET_RENDER_RATE_LIMIT_PER_IP_PER_MINUTE=1)
class RateLimitTests(WidgetViewTestCase):
    def test_over_limit_returns_429_with_no_render_and_no_count(self):
        first = self.client.get(_render_url(self.app.id))
        self.assertEqual(first.status_code, 200)
        with mock.patch("apps.core.ratelimit.observability.increment") as inc:
            second = self.client.get(_render_url(self.app.id))
        self.assertEqual(second.status_code, 429)  # AC8
        inc.assert_any_call("widget_rate_limited")
        # The 429 counted no impression: only the first (allowed) render did.
        self.assertEqual(selectors.widget_reach(self.app.id, **_window()).impressions, 1)


class FailSoftTests(WidgetViewTestCase):
    def test_impression_count_failure_still_renders_200(self):
        with mock.patch(
            "apps.widget.views.attribution.record_widget_impression",
            side_effect=RuntimeError("db down"),
        ), mock.patch("apps.widget.views.observability.increment") as inc:
            response = self.client.get(_render_url(self.app.id))
        self.assertEqual(response.status_code, 200)  # host page never breaks
        inc.assert_any_call("widget_count_degraded")

    def test_build_failure_renders_neutral_unavailable_200(self):
        with mock.patch(
            "apps.widget.views.content.build_widget_view",
            side_effect=RuntimeError("catalog down"),
        ), mock.patch("apps.widget.views.observability.increment") as inc:
            response = self.client.get(_render_url(self.app.id))
        self.assertEqual(response.status_code, 200)  # degraded, not a 500 into the host
        self.assertIn("isn't available", response.content.decode())
        inc.assert_any_call("widget_render_degraded")

    def test_limiter_cache_error_fails_open(self):
        with mock.patch(
            "apps.core.ratelimit.cache.add", side_effect=RuntimeError("cache down")
        ), mock.patch("apps.core.ratelimit.observability.increment") as inc:
            response = self.client.get(_render_url(self.app.id))
        self.assertEqual(response.status_code, 200)  # served despite the cache outage
        inc.assert_any_call("widget_limiter_degraded")
