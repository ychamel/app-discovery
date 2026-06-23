"""The additive surface-aware + time-bucketed reach reads (developer-dashboard §5.1).

These back the developer-dashboard's reach breakdown (AC3/AC4) and impressions-over-time
trend (AC10). They are ORM-level tests: real ``Impression`` rows are seeded through the
capture recorder, then the reads are asserted directly — no HTTP, no mocking. The headline
integrity invariant (``impression_breakdown.total == app_funnel.impressions``) is asserted
here so the dashboard's reach section can never silently disagree with its funnel section.
"""

import random
from datetime import UTC, datetime

from django.test import TestCase

from apps.signals import capture, selectors
from apps.signals.kinds import Surface
from apps.signals.selectors import TrendGranularity
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user


def _at(year: int, month: int, day: int, hour: int = 12) -> datetime:
    """A fixed UTC instant for deterministic window/bucket math."""
    return datetime(year, month, day, hour, tzinfo=UTC)


class ImpressionBreakdownTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def _impress(self, surface, day, count):
        for _ in range(count):
            capture.record_impression(
                self.user, self.app.id, surface=surface, occurred_at=_at(2026, 6, day)
            )

    def test_counts_per_surface_with_total(self):
        self._impress(Surface.DIGEST, 2, 5)
        self._impress(Surface.APP_PAGE, 3, 20)

        breakdown = selectors.impression_breakdown(
            self.app.id, start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
        )

        self.assertEqual(breakdown.total, 25)
        self.assertEqual(breakdown.by_surface[Surface.DIGEST], 5)
        self.assertEqual(breakdown.by_surface[Surface.APP_PAGE], 20)

    def test_every_surface_is_present_zero_filled(self):
        # An app with only APP_PAGE shows DIGEST as a present 0 (the honest zero, AC4), and
        # by_surface enumerates the whole vocabulary so a surface added later auto-appears (AC3).
        self._impress(Surface.APP_PAGE, 3, 4)

        breakdown = selectors.impression_breakdown(
            self.app.id, start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
        )

        self.assertEqual(breakdown.by_surface[Surface.DIGEST], 0)
        self.assertEqual(set(breakdown.by_surface), set(Surface.values))

    def test_window_excludes_out_of_range_events(self):
        self._impress(Surface.DIGEST, 2, 3)  # before the narrow window
        self._impress(Surface.DIGEST, 15, 7)  # inside it
        self._impress(Surface.DIGEST, 25, 2)  # after it

        breakdown = selectors.impression_breakdown(
            self.app.id, start=_at(2026, 6, 10, 0), end=_at(2026, 6, 20, 0)
        )

        self.assertEqual(breakdown.total, 7)

    def test_is_one_query(self):
        self._impress(Surface.DIGEST, 2, 3)
        with self.assertNumQueries(1):
            selectors.impression_breakdown(
                self.app.id, start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
            )


class ImpressionBreakdownForAppsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def _make_apps(self, n):
        return [
            make_accepted_app(self.owner, tag_ids=[self.tag.id], name=f"App {i}")
            for i in range(n)
        ]

    def test_every_requested_app_present_even_with_no_impressions(self):
        apps = self._make_apps(2)
        capture.record_impression(
            self.user, apps[0].id, surface=Surface.DIGEST, occurred_at=_at(2026, 6, 2)
        )

        result = selectors.impression_breakdown_for_apps(
            [a.id for a in apps], start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
        )

        self.assertEqual(set(result), {apps[0].id, apps[1].id})
        self.assertEqual(result[apps[0].id].total, 1)
        self.assertEqual(result[apps[1].id].total, 0)  # present, all-zero
        self.assertEqual(set(result[apps[1].id].by_surface), set(Surface.values))

    def test_query_count_is_constant_in_app_count(self):
        few = self._make_apps(2)
        with self.assertNumQueries(1):
            selectors.impression_breakdown_for_apps(
                [a.id for a in few], start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
            )

        many = self._make_apps(20)
        with self.assertNumQueries(1):
            selectors.impression_breakdown_for_apps(
                [a.id for a in many], start=_at(2026, 6, 1, 0), end=_at(2026, 6, 28, 0)
            )


class ImpressionTrendTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def _impress(self, surface, when, count=1):
        for _ in range(count):
            capture.record_impression(
                self.user, self.app.id, surface=surface, occurred_at=when
            )

    def test_daily_buckets_are_sparse_ascending_and_split_per_surface(self):
        self._impress(Surface.DIGEST, _at(2026, 6, 2), 2)
        self._impress(Surface.APP_PAGE, _at(2026, 6, 2), 3)
        self._impress(Surface.APP_PAGE, _at(2026, 6, 5), 4)

        trend = selectors.impression_trend(
            self.app.id,
            start=_at(2026, 6, 1, 0),
            end=_at(2026, 6, 28, 0),
            granularity=TrendGranularity.DAY,
        )

        # Only the two days with impressions appear (sparse), ascending by bucket_start.
        self.assertEqual([b.bucket_start for b in trend], [_at(2026, 6, 2, 0), _at(2026, 6, 5, 0)])
        self.assertEqual(trend[0].total, 5)
        self.assertEqual(trend[0].by_surface[Surface.DIGEST], 2)
        self.assertEqual(trend[0].by_surface[Surface.APP_PAGE], 3)
        self.assertEqual(trend[1].total, 4)
        # Each bucket's total equals the sum of its per-surface split.
        for bucket in trend:
            self.assertEqual(bucket.total, sum(bucket.by_surface.values()))

    def test_empty_window_returns_empty_list(self):
        trend = selectors.impression_trend(
            self.app.id,
            start=_at(2026, 6, 1, 0),
            end=_at(2026, 6, 28, 0),
            granularity=TrendGranularity.DAY,
        )
        self.assertEqual(trend, [])

    def test_weekly_buckets_truncate_to_monday_utc(self):
        # 2026-06-02 is a Tuesday → its week starts Monday 2026-06-01.
        self._impress(Surface.DIGEST, _at(2026, 6, 2))
        self._impress(Surface.DIGEST, _at(2026, 6, 4))

        trend = selectors.impression_trend(
            self.app.id,
            start=_at(2026, 6, 1, 0),
            end=_at(2026, 6, 28, 0),
            granularity=TrendGranularity.WEEK,
        )

        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0].bucket_start, _at(2026, 6, 1, 0))
        self.assertEqual(trend[0].total, 2)

    def test_monthly_buckets_truncate_to_first_of_month_utc(self):
        self._impress(Surface.DIGEST, _at(2026, 5, 15))
        self._impress(Surface.DIGEST, _at(2026, 6, 20))

        trend = selectors.impression_trend(
            self.app.id,
            start=_at(2026, 1, 1, 0),
            end=_at(2026, 12, 31, 0),
            granularity=TrendGranularity.MONTH,
        )

        self.assertEqual(
            [b.bucket_start for b in trend], [_at(2026, 5, 1, 0), _at(2026, 6, 1, 0)]
        )

    def test_is_one_query(self):
        self._impress(Surface.DIGEST, _at(2026, 6, 2))
        with self.assertNumQueries(1):
            selectors.impression_trend(
                self.app.id,
                start=_at(2026, 6, 1, 0),
                end=_at(2026, 6, 28, 0),
                granularity=TrendGranularity.DAY,
            )


class BreakdownFunnelInvariantTests(TestCase):
    """The §4.2 invariant: impression_breakdown.total == app_funnel.impressions."""

    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def test_total_matches_funnel_impressions_over_random_fixtures(self):
        rng = random.Random(20260624)
        surfaces = list(Surface.values)
        for _ in range(40):
            capture.record_impression(
                self.user,
                self.app.id,
                surface=rng.choice(surfaces),
                occurred_at=_at(2026, 6, rng.randint(1, 28), rng.randint(0, 23)),
            )

        windows = [
            (_at(2026, 6, 1, 0), _at(2026, 6, 28, 0)),
            (_at(2026, 6, 10, 0), _at(2026, 6, 20, 0)),
            (_at(2026, 6, 5, 0), _at(2026, 6, 6, 0)),
            (_at(2020, 1, 1, 0), _at(2026, 6, 28, 0)),
        ]
        for start, end in windows:
            breakdown = selectors.impression_breakdown(self.app.id, start=start, end=end)
            funnel = selectors.app_funnel(self.app.id, start=start, end=end)
            self.assertEqual(breakdown.total, funnel.impressions)
