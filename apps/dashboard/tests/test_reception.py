"""The reception composition layer (developer-dashboard §3/§5.2).

Composition-level tests: real selectors + seeded fixtures, the reviews fail-soft path driven
by patching ``reviews_for_app`` to raise. Covers owner-scope (AC1/AC2/AC8), the curated-first
reach breakdown (AC3/AC4), the densified trend (AC10), the funnel projection (AC5), the
no-average reviews slot (AC6), bounded reads (AC9), and the loud/soft failure split (§7).
"""

from dataclasses import fields
from datetime import UTC, datetime
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.catalog import services as catalog_services
from apps.dashboard import reception
from apps.dashboard.windows import resolve_window
from apps.ratings import services as rating_services
from apps.signals import capture
from apps.signals.kinds import Surface
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user

_NOW = datetime(2026, 6, 28, 0, tzinfo=UTC)


def _at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 6, day, hour, tzinfo=UTC)


def _window(key: str = "1m"):
    return resolve_window(key, now=_NOW)


class OwnerScopeTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.other = make_user("other@example.com")
        self.tag = make_tag("notes")
        self.app_a = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="App A")
        self.app_b = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="App B")
        self.other_app = make_accepted_app(
            self.other, tag_ids=[self.tag.id], name="Other App"
        )

    def test_my_apps_lists_only_owned_accepted_apps(self):
        summaries = reception.build_my_apps_summaries(self.owner, window=_window())
        self.assertEqual(
            {s.app_id for s in summaries}, {self.app_a.id, self.app_b.id}
        )

    def test_my_apps_excludes_non_accepted_owned_apps(self):
        pending = catalog_services.submit_app(
            self.owner,
            name="Pending App",
            description="A small vibecoded web app.",
            url="https://example.com/pending",
            tag_ids=[self.tag.id],
            media=[_png()],
        )
        summaries = reception.build_my_apps_summaries(self.owner, window=_window())
        self.assertNotIn(pending.id, {s.app_id for s in summaries})

    def test_my_apps_empty_for_owner_with_no_accepted_apps(self):
        loner = make_user("loner@example.com")
        self.assertEqual(reception.build_my_apps_summaries(loner, window=_window()), [])

    def test_app_reception_none_for_another_devs_app(self):
        self.assertIsNone(
            reception.build_app_reception(
                self.owner, self.other_app.id, window=_window()
            )
        )

    def test_app_reception_none_for_non_accepted_owned_app(self):
        pending = catalog_services.submit_app(
            self.owner,
            name="Pending App",
            description="A small vibecoded web app.",
            url="https://example.com/pending2",
            tag_ids=[self.tag.id],
            media=[_png()],
        )
        self.assertIsNone(
            reception.build_app_reception(self.owner, pending.id, window=_window())
        )

    def test_app_reception_present_for_owned_accepted_app(self):
        result = reception.build_app_reception(
            self.owner, self.app_a.id, window=_window()
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.app_id, self.app_a.id)


class ReachBreakdownTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.user = make_user("viewer@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def _impress(self, surface, count, day=2):
        for _ in range(count):
            capture.record_impression(
                self.user, self.app.id, surface=surface, occurred_at=_at(day)
            )

    def test_total_and_curated_first_breakdown(self):
        self._impress(Surface.DIGEST, 5)
        self._impress(Surface.APP_PAGE, 20)

        reach = reception.build_app_reception(
            self.owner, self.app.id, window=_window()
        ).reach

        self.assertEqual(reach.total, 25)
        self.assertTrue(reach.surfaces[0].is_curated)  # DIGEST first
        self.assertEqual(reach.surfaces[0].surface, Surface.DIGEST)
        self.assertEqual(reach.surfaces[0].count, 5)
        self.assertEqual(reach.surfaces[1].surface, Surface.APP_PAGE)
        self.assertEqual(reach.surfaces[1].count, 20)
        self.assertFalse(reach.surfaces[1].is_curated)

    def test_zero_digest_is_present_as_an_honest_zero(self):
        self._impress(Surface.APP_PAGE, 4)
        reach = reception.build_app_reception(
            self.owner, self.app.id, window=_window()
        ).reach
        digest = next(s for s in reach.surfaces if s.surface == Surface.DIGEST)
        self.assertEqual(digest.count, 0)
        self.assertTrue(digest.is_curated)


class TrendTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.user = make_user("viewer@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def _impress(self, surface, day, count=1):
        for _ in range(count):
            capture.record_impression(
                self.user, self.app.id, surface=surface, occurred_at=_at(day)
            )

    def test_dense_buckets_zero_filled_with_distinct_curated_line(self):
        self._impress(Surface.DIGEST, 20, 2)
        self._impress(Surface.APP_PAGE, 20, 3)

        trend = reception.build_app_reception(
            self.owner, self.app.id, window=_window()
        ).reach.trend

        self.assertFalse(trend.is_empty)
        self.assertIsNotNone(trend.sparkline)
        labels = [b.label for b in trend.buckets]
        # Dense: the gap between the two data days is present as zero buckets.
        self.assertIn("2026-06-20", labels)
        self.assertIn("2026-06-21", labels)  # a gap day with no impressions
        june20 = next(b for b in trend.buckets if b.label == "2026-06-20")
        self.assertEqual(june20.total, 5)  # 2 DIGEST + 3 APP_PAGE
        self.assertEqual(june20.curated, 2)  # only DIGEST is curated
        gap = next(b for b in trend.buckets if b.label == "2026-06-21")
        self.assertEqual(gap.total, 0)

    def test_empty_window_has_no_chart(self):
        trend = reception.build_app_reception(
            self.owner, self.app.id, window=_window()
        ).reach.trend
        self.assertTrue(trend.is_empty)
        self.assertIsNone(trend.sparkline)
        self.assertEqual(trend.buckets, [])


class FunnelProjectionTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.user = make_user("viewer@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def test_funnel_view_matches_app_funnel_and_keeps_proxy_separate(self):
        from apps.signals import selectors as signals

        impression = capture.record_impression(
            self.user, self.app.id, surface=Surface.DIGEST, occurred_at=_at(2)
        )
        capture.record_click_through(
            self.user, self.app.id, impression=impression, occurred_at=_at(2)
        )
        capture.record_off_platform_proxy(
            self.user, self.app.id, impression=impression, occurred_at=_at(2)
        )

        window = _window()
        funnel = signals.app_funnel(self.app.id, start=window.start, end=window.end)
        view = reception.build_app_reception(
            self.owner, self.app.id, window=window
        ).funnel

        self.assertEqual(view.impressions, funnel.impressions)
        self.assertEqual(view.click_throughs, funnel.click_throughs)
        self.assertEqual(view.off_platform_proxy, funnel.off_platform_proxy)
        # The proxy is its own field and is never folded into click-throughs (AC5).
        self.assertEqual(view.click_throughs, 1)
        self.assertEqual(view.off_platform_proxy, 1)


class ReviewsSlotTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.rater = make_user("rater@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def test_reviews_carry_count_distribution_list_and_no_average(self):
        rating_services.submit_rating(
            self.rater, self.app.id, score=4, review_text="solid"
        )
        reviews = reception.build_app_reception(
            self.owner, self.app.id, window=_window()
        ).reviews

        self.assertTrue(reviews.available)
        self.assertEqual(reviews.total_count, 1)
        self.assertEqual(reviews.distribution, {4: 1})
        self.assertEqual(len(reviews.reviews), 1)
        field_names = {f.name for f in fields(reception.ReviewsView)}
        for forbidden in ("average", "score", "rank", "weight_eligible"):
            self.assertNotIn(forbidden, field_names)

    def test_reviews_read_failure_degrades_soft(self):
        with patch.object(
            reception.ratings, "reviews_for_app", side_effect=RuntimeError("db down")
        ):
            result = reception.build_app_reception(
                self.owner, self.app.id, window=_window()
            )
        # The rest of the view still renders; only the reviews slot degrades (§7).
        self.assertIsNotNone(result)
        self.assertFalse(result.reviews.available)
        self.assertIsNotNone(result.reach)
        self.assertIsNotNone(result.funnel)


class FailLoudTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def test_breakdown_read_error_propagates(self):
        with patch.object(
            reception.signals, "impression_breakdown", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                reception.build_app_reception(
                    self.owner, self.app.id, window=_window()
                )

    def test_funnel_read_error_propagates(self):
        with patch.object(
            reception.signals, "app_funnel", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                reception.build_app_reception(
                    self.owner, self.app.id, window=_window()
                )

    def test_my_apps_signals_error_propagates(self):
        with patch.object(
            reception.signals, "funnel_for_apps", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                reception.build_my_apps_summaries(self.owner, window=_window())


class BoundedReadTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.user = make_user("viewer@example.com")
        self.tag = make_tag("notes")

    def _make_apps(self, n):
        return [
            make_accepted_app(self.owner, tag_ids=[self.tag.id], name=f"App {i}")
            for i in range(n)
        ]

    def test_my_apps_query_count_is_independent_of_app_count(self):
        self._make_apps(2)
        with CaptureQueriesContext(connection) as few:
            reception.build_my_apps_summaries(self.owner, window=_window())

        self._make_apps(18)  # now 20 accepted apps
        with CaptureQueriesContext(connection) as many:
            reception.build_my_apps_summaries(self.owner, window=_window())

        self.assertEqual(len(few.captured_queries), len(many.captured_queries))

    def test_app_reception_query_count_is_independent_of_data_volume(self):
        app = self._make_apps(1)[0]
        capture.record_impression(
            self.user, app.id, surface=Surface.DIGEST, occurred_at=_at(2)
        )
        with CaptureQueriesContext(connection) as light:
            reception.build_app_reception(self.owner, app.id, window=_window())

        for day in range(3, 23):
            capture.record_impression(
                self.user, app.id, surface=Surface.APP_PAGE, occurred_at=_at(day)
            )
        with CaptureQueriesContext(connection) as heavy:
            reception.build_app_reception(self.owner, app.id, window=_window())

        self.assertEqual(len(light.captured_queries), len(heavy.captured_queries))


def _png():
    """A real 16x16 PNG upload (catalog requires ≥1 image) — mirrors the signals helper."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(120, 120, 120)).save(buffer, format="PNG")
    return SimpleUploadedFile("shot.png", buffer.getvalue(), content_type="image/png")
