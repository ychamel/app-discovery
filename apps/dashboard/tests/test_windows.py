"""The reporting-window vocabulary (developer-dashboard §4.3, DD-DESIGN-3).

Pure unit tests (no DB): the fixed 8-window table, per-window granularity, and the fail-safe
``resolve_window`` arithmetic incl. the all-time epoch sentinel.
"""

from datetime import UTC, datetime, timedelta

from django.test import SimpleTestCase

from apps.dashboard import windows
from apps.signals.selectors import TrendGranularity

_NOW = datetime(2026, 6, 24, 12, tzinfo=UTC)


class ReportingWindowsTableTests(SimpleTestCase):
    def test_exactly_the_eight_keys_in_display_order(self):
        keys = [w.key for w in windows.REPORTING_WINDOWS]
        self.assertEqual(keys, ["1w", "2w", "1m", "3m", "6m", "1y", "3y", "all"])

    def test_per_window_granularity_matches_design(self):
        by_key = {w.key: w for w in windows.REPORTING_WINDOWS}
        self.assertEqual(by_key["1w"].granularity, TrendGranularity.DAY)
        self.assertEqual(by_key["1m"].granularity, TrendGranularity.DAY)
        self.assertEqual(by_key["3m"].granularity, TrendGranularity.WEEK)
        self.assertEqual(by_key["6m"].granularity, TrendGranularity.WEEK)
        self.assertEqual(by_key["1y"].granularity, TrendGranularity.MONTH)
        self.assertEqual(by_key["all"].granularity, TrendGranularity.MONTH)

    def test_all_time_window_has_no_duration(self):
        by_key = {w.key: w for w in windows.REPORTING_WINDOWS}
        self.assertIsNone(by_key["all"].duration)

    def test_default_key_is_a_known_window(self):
        self.assertIn(
            windows.DEFAULT_WINDOW_KEY, {w.key for w in windows.REPORTING_WINDOWS}
        )


class ResolveWindowTests(SimpleTestCase):
    def test_bounded_window_resolves_to_now_minus_duration(self):
        resolved = windows.resolve_window("3m", now=_NOW)
        self.assertEqual(resolved.window.key, "3m")
        self.assertEqual(resolved.start, _NOW - timedelta(days=90))
        self.assertEqual(resolved.end, _NOW)
        self.assertEqual(resolved.granularity, TrendGranularity.WEEK)

    def test_all_time_resolves_to_the_epoch_sentinel(self):
        resolved = windows.resolve_window("all", now=_NOW)
        self.assertEqual(resolved.start, windows.ALL_TIME_START)
        self.assertEqual(resolved.end, _NOW)
        self.assertEqual(resolved.granularity, TrendGranularity.MONTH)

    def test_unknown_key_falls_back_to_default_without_raising(self):
        resolved = windows.resolve_window("not-a-window", now=_NOW)
        self.assertEqual(resolved.window.key, windows.DEFAULT_WINDOW_KEY)

    def test_blank_or_none_key_falls_back_to_default(self):
        self.assertEqual(
            windows.resolve_window("", now=_NOW).window.key, windows.DEFAULT_WINDOW_KEY
        )
        self.assertEqual(
            windows.resolve_window(None, now=_NOW).window.key, windows.DEFAULT_WINDOW_KEY
        )
