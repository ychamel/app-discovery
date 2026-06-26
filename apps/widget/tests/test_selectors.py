"""T-02 — the single reader (DESIGN §5.2): windowed SUM, zero-fill, no N+1.

``widget_reach`` / ``widget_reach_for_apps`` sum the daily rollup over a window, zero-fill kinds
and apps with no rows, exclude rows outside the day range, and answer the dashboard's K-app
summary in **one** grouped query regardless of K.
"""

import uuid
from datetime import UTC, date, datetime

from django.test import TestCase

from apps.widget import selectors
from apps.widget.kinds import WidgetEventKind
from apps.widget.models import WidgetReachCount


def _seed(app_id, kind, count_date: date, count: int) -> None:
    WidgetReachCount.objects.create(
        app_id=app_id, kind=kind, count_date=count_date, count=count
    )


class WidgetReachTests(TestCase):
    def setUp(self):
        self.app_id = uuid.uuid4()
        self.day1 = date(2026, 6, 10)
        self.day2 = date(2026, 6, 11)
        self.start = datetime(2026, 6, 1, tzinfo=UTC)
        self.end = datetime(2026, 6, 30, tzinfo=UTC)

    def test_sums_across_days_per_kind(self):
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.day1, 3)
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.day2, 4)
        _seed(self.app_id, WidgetEventKind.CLICK_THROUGH, self.day1, 2)
        reach = selectors.widget_reach(self.app_id, start=self.start, end=self.end)
        self.assertEqual(reach.impressions, 7)
        self.assertEqual(reach.click_throughs, 2)

    def test_zero_filled_when_no_rows(self):
        reach = selectors.widget_reach(self.app_id, start=self.start, end=self.end)
        self.assertEqual(reach.impressions, 0)
        self.assertEqual(reach.click_throughs, 0)

    def test_zero_filled_when_a_kind_is_absent(self):
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.day1, 5)
        reach = selectors.widget_reach(self.app_id, start=self.start, end=self.end)
        self.assertEqual(reach.impressions, 5)
        self.assertEqual(reach.click_throughs, 0)

    def test_rows_outside_the_window_are_excluded(self):
        _seed(self.app_id, WidgetEventKind.IMPRESSION, date(2026, 5, 31), 9)  # before
        _seed(self.app_id, WidgetEventKind.IMPRESSION, date(2026, 7, 1), 9)  # after
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.day1, 2)  # inside
        reach = selectors.widget_reach(self.app_id, start=self.start, end=self.end)
        self.assertEqual(reach.impressions, 2)

    def test_window_bounds_are_inclusive_of_their_days(self):
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.start.date(), 1)
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.end.date(), 1)
        reach = selectors.widget_reach(self.app_id, start=self.start, end=self.end)
        self.assertEqual(reach.impressions, 2)

    def test_is_one_query(self):
        _seed(self.app_id, WidgetEventKind.IMPRESSION, self.day1, 1)
        with self.assertNumQueries(1):
            selectors.widget_reach(self.app_id, start=self.start, end=self.end)


class WidgetReachForAppsTests(TestCase):
    def setUp(self):
        self.start = datetime(2026, 6, 1, tzinfo=UTC)
        self.end = datetime(2026, 6, 30, tzinfo=UTC)
        self.day = date(2026, 6, 10)

    def test_empty_input_returns_empty_dict(self):
        self.assertEqual(
            selectors.widget_reach_for_apps([], start=self.start, end=self.end), {}
        )

    def test_one_entry_per_requested_app_zero_filled(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        _seed(a, WidgetEventKind.IMPRESSION, self.day, 3)
        _seed(a, WidgetEventKind.CLICK_THROUGH, self.day, 1)
        result = selectors.widget_reach_for_apps([a, b], start=self.start, end=self.end)
        self.assertEqual(set(result), {a, b})
        self.assertEqual(result[a].impressions, 3)
        self.assertEqual(result[a].click_throughs, 1)
        self.assertEqual(result[b].impressions, 0)  # requested but no rows ⇒ zero-filled
        self.assertEqual(result[b].click_throughs, 0)

    def test_is_one_query_regardless_of_app_count(self):
        app_ids = [uuid.uuid4() for _ in range(50)]
        for app_id in app_ids:
            _seed(app_id, WidgetEventKind.IMPRESSION, self.day, 1)
        with self.assertNumQueries(1):
            selectors.widget_reach_for_apps(app_ids, start=self.start, end=self.end)
