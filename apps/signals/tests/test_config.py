"""T-01 — the two return-window tunables are typed, defaulted, and fail loud (DESIGN.md §9)."""

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.core import config


class ReturnWindowTunableTests(SimpleTestCase):
    """The return windows are config, never magic constants in logic (CLAUDE.md §5.2)."""

    def test_defaults_match_design(self):
        self.assertEqual(config.return_window_short_days(), 3)
        self.assertEqual(config.return_window_long_days(), 14)

    @override_settings(RETURN_WINDOW_SHORT_DAYS=5, RETURN_WINDOW_LONG_DAYS=30)
    def test_overridable(self):
        self.assertEqual(config.return_window_short_days(), 5)
        self.assertEqual(config.return_window_long_days(), 30)

    @override_settings(RETURN_WINDOW_SHORT_DAYS=0)
    def test_non_positive_short_window_fails_loud(self):
        with self.assertRaises(ImproperlyConfigured):
            config.return_window_short_days()

    @override_settings(RETURN_WINDOW_LONG_DAYS=-1)
    def test_non_positive_long_window_fails_loud(self):
        with self.assertRaises(ImproperlyConfigured):
            config.return_window_long_days()

    @override_settings(RETURN_WINDOW_SHORT_DAYS="not-a-number")
    def test_validate_all_surfaces_misconfiguration(self):
        with self.assertRaises(ImproperlyConfigured):
            config.validate_all()
