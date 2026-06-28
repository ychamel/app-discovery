"""The two HTTP views (developer-dashboard §5.3/§6) — integration via the Django test client.

Drives the real project URLconf (with the ``dashboard/`` include) and asserts the role gate
(AC2), owner-scope 404 (AC2/AC8), the rendered reach/trend/funnel/reviews sections
(AC3–AC6/AC10), window coercion (AC7), read-only behaviour (AC8), bounded query counts (AC9),
and the loud/soft failure split with its counters (§7).
"""

from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts import roles
from apps.signals import capture
from apps.signals.kinds import Surface
from apps.signals.models import EngagementEvent, Impression
from apps.signals.tests.helpers import make_accepted_app, make_account, make_tag


class DashboardViewTestCase(TestCase):
    def setUp(self):
        self.dev = make_account("dev@example.com", role=roles.DEVELOPER)
        self.tag = make_tag("notes")
        self.now = timezone.now()
        self.client.force_login(self.dev)

    def _impress(self, app, surface, *, days_ago=2, count=1):
        when = self.now - timedelta(days=days_ago)
        for _ in range(count):
            capture.record_impression(self.dev, app.id, surface=surface, occurred_at=when)

    def _my_apps_url(self, window=None):
        url = reverse("dashboard:my-apps")
        return f"{url}?window={window}" if window else url

    def _app_url(self, app_id, window=None):
        url = reverse("dashboard:app", kwargs={"app_id": app_id})
        return f"{url}?window={window}" if window else url


class MyAppsListTests(DashboardViewTestCase):
    def test_lists_only_the_callers_accepted_apps(self):
        mine_a = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Mine A")
        mine_b = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Mine B")
        other_dev = make_account("other@example.com", role=roles.DEVELOPER)
        make_accepted_app(other_dev, tag_ids=[self.tag.id], name="Theirs")

        response = self.client.get(self._my_apps_url())

        self.assertEqual(response.status_code, 200)
        listed = {s.app_id for s in response.context["summaries"]}
        self.assertEqual(listed, {mine_a.id, mine_b.id})
        self.assertContains(response, "Mine A")
        self.assertNotContains(response, "Theirs")

    def test_own_nothing_state_is_200(self):
        response = self.client.get(self._my_apps_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no accepted apps")

    def test_empty_state_links_to_submissions(self):
        # UX-003 regression: a developer with no *accepted* apps must not dead-end on the
        # dashboard — the empty state guides them to catalog:my-apps where their pending/
        # rejected submissions actually live.
        response = self.client.get(self._my_apps_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View my submissions")
        self.assertContains(response, f'href="{reverse("catalog:my-apps")}"')


class AccessControlTests(DashboardViewTestCase):
    def test_non_developer_gets_403_on_both_routes(self):
        user = make_account("plainuser@example.com")  # no developer role
        client = Client()
        client.force_login(user)
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])

        self.assertEqual(client.get(self._my_apps_url()).status_code, 403)
        self.assertEqual(client.get(self._app_url(app.id)).status_code, 403)

    def test_another_devs_app_is_404_indistinguishable(self):
        other_dev = make_account("other@example.com", role=roles.DEVELOPER)
        theirs = make_accepted_app(other_dev, tag_ids=[self.tag.id], name="Theirs")
        response = self.client.get(self._app_url(theirs.id))
        self.assertEqual(response.status_code, 404)

    def test_post_is_405_read_only(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self.assertEqual(self.client.post(self._my_apps_url()).status_code, 405)
        self.assertEqual(self.client.post(self._app_url(app.id)).status_code, 405)

    def test_viewing_writes_no_signal_rows(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self._impress(app, Surface.DIGEST)
        before_impressions = Impression.objects.count()
        before_events = EngagementEvent.objects.count()

        self.client.get(self._app_url(app.id))
        self.client.get(self._my_apps_url())

        self.assertEqual(Impression.objects.count(), before_impressions)
        self.assertEqual(EngagementEvent.objects.count(), before_events)


class ReachRenderTests(DashboardViewTestCase):
    def test_total_and_curated_first_breakdown_render(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self._impress(app, Surface.DIGEST, count=5)
        self._impress(app, Surface.APP_PAGE, count=20)

        response = self.client.get(self._app_url(app.id, window="all"))

        self.assertEqual(response.status_code, 200)
        reach = response.context["reception"].reach
        self.assertEqual(reach.total, 25)
        self.assertTrue(reach.surfaces[0].is_curated)
        self.assertContains(response, "weekly digest")

    def test_empty_digest_shows_honest_zero_affordance(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self._impress(app, Surface.APP_PAGE, count=3)
        response = self.client.get(self._app_url(app.id, window="all"))
        self.assertContains(response, "no curated shows yet")


class TrendRenderTests(DashboardViewTestCase):
    def test_svg_and_table_render_with_exact_numbers(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self._impress(app, Surface.DIGEST, days_ago=2, count=4)

        response = self.client.get(self._app_url(app.id, window="1m"))

        self.assertContains(response, "<svg")
        self.assertContains(response, "<table")
        buckets = response.context["reception"].reach.trend.buckets
        data_bucket = next(b for b in buckets if b.total > 0)
        self.assertEqual(data_bucket.total, 4)
        self.assertEqual(data_bucket.curated, 4)
        self.assertContains(response, f"<td>{data_bucket.label}</td>", html=False)

    def test_empty_window_shows_no_chart(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        response = self.client.get(self._app_url(app.id, window="1m"))
        self.assertContains(response, "No impressions in this window")
        self.assertNotContains(response, "<svg")


class FunnelRenderTests(DashboardViewTestCase):
    def test_funnel_counts_and_separate_proxy_line(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        impression = capture.record_impression(
            self.dev, app.id, surface=Surface.DIGEST, occurred_at=self.now - timedelta(days=2)
        )
        capture.record_click_through(
            self.dev, app.id, impression=impression, occurred_at=self.now - timedelta(days=2)
        )
        capture.record_off_platform_proxy(
            self.dev, app.id, impression=impression, occurred_at=self.now - timedelta(days=2)
        )

        response = self.client.get(self._app_url(app.id, window="all"))

        funnel = response.context["reception"].funnel
        self.assertEqual(funnel.click_throughs, 1)
        self.assertEqual(funnel.off_platform_proxy, 1)
        self.assertContains(response, "Off-platform proxy")


class ReviewsRenderTests(DashboardViewTestCase):
    def test_reviews_render_without_an_average(self):
        from apps.ratings import services as rating_services

        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        rater = make_account("rater@example.com")
        rating_services.submit_rating(rater, app.id, score=5, review_text="great")

        response = self.client.get(self._app_url(app.id, window="all"))

        reviews = response.context["reception"].reviews
        self.assertTrue(reviews.available)
        self.assertEqual(reviews.total_count, 1)
        self.assertNotContains(response, "average")


class WindowCoercionTests(DashboardViewTestCase):
    def test_in_and_out_of_window_figures_and_all(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        self._impress(app, Surface.DIGEST, days_ago=3)  # inside 1w
        self._impress(app, Surface.DIGEST, days_ago=200)  # outside 1w, inside 1y

        recent = self.client.get(self._app_url(app.id, window="1w"))
        everything = self.client.get(self._app_url(app.id, window="all"))

        self.assertEqual(recent.context["reception"].reach.total, 1)
        self.assertEqual(everything.context["reception"].reach.total, 2)

    def test_bad_window_falls_back_to_default_without_500(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        response = self.client.get(self._app_url(app.id, window="not-a-window"))
        self.assertEqual(response.status_code, 200)
        from apps.dashboard import windows

        self.assertEqual(
            response.context["reception"].window.key, windows.DEFAULT_WINDOW_KEY
        )


class BoundedQueryTests(DashboardViewTestCase):
    def test_my_apps_query_count_independent_of_app_count(self):
        for i in range(2):
            make_accepted_app(self.dev, tag_ids=[self.tag.id], name=f"A{i}")
        # Warm up session/content-type caches so the first measured request does not pay
        # one-time per-process query costs that would mask the (constant) reception cost.
        self.client.get(self._my_apps_url())
        with CaptureQueriesContext(connection) as few:
            self.client.get(self._my_apps_url())

        for i in range(18):
            make_accepted_app(self.dev, tag_ids=[self.tag.id], name=f"B{i}")
        with CaptureQueriesContext(connection) as many:
            self.client.get(self._my_apps_url())

        self.assertEqual(len(few.captured_queries), len(many.captured_queries))


class FailureSplitTests(DashboardViewTestCase):
    def _no_reraise_client(self):
        client = Client(raise_request_exception=False)
        client.force_login(self.dev)
        return client

    def test_core_read_error_is_a_loud_500_with_alert_counter(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        client = self._no_reraise_client()
        with patch(
            "apps.dashboard.reception.signals.impression_breakdown",
            side_effect=RuntimeError("db down"),
        ), patch("apps.dashboard.views.observability.increment") as increment:
            response = client.get(self._app_url(app.id))

        self.assertEqual(response.status_code, 500)
        fired = {call.args[0] for call in increment.call_args_list}
        from apps.core import observability

        self.assertIn(observability.DASHBOARD_RECEPTION_DEGRADED, fired)

    def test_reviews_error_is_soft_200_with_degraded_counter(self):
        app = make_accepted_app(self.dev, tag_ids=[self.tag.id])
        with patch(
            "apps.dashboard.reception.ratings.reviews_for_app",
            side_effect=RuntimeError("ratings down"),
        ), patch("apps.dashboard.reception.observability.increment") as increment:
            response = self.client.get(self._app_url(app.id, window="all"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["reception"].reviews.available)
        self.assertContains(response, "Reviews unavailable")
        from apps.core import observability

        fired = {call.args[0] for call in increment.call_args_list}
        self.assertIn(observability.DASHBOARD_REVIEWS_DEGRADED, fired)

    def test_nonempty_reception_counter_only_on_nonzero_funnel(self):
        from apps.core import observability

        empty = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Empty")
        with patch("apps.dashboard.views.observability.increment") as increment:
            self.client.get(self._app_url(empty.id))
        fired = {call.args[0] for call in increment.call_args_list}
        self.assertNotIn(observability.DASHBOARD_NONEMPTY_RECEPTION, fired)

        live = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="Live")
        self._impress(live, Surface.DIGEST)
        with patch("apps.dashboard.views.observability.increment") as increment:
            self.client.get(self._app_url(live.id, window="all"))
        fired = {call.args[0] for call in increment.call_args_list}
        self.assertIn(observability.DASHBOARD_NONEMPTY_RECEPTION, fired)
