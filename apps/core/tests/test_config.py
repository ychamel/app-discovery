"""Tests for apps.core.config — default, override, and fail-loud paths (T-02)."""

import os
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.core import config


class LoginTokenTtlTests(SimpleTestCase):
    def test_default_when_unset(self):
        # No setting and no env var -> documented 15-minute default.
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOGIN_TOKEN_TTL_SECONDS", None)
            self.assertEqual(config.login_token_ttl(), timedelta(minutes=15))

    @override_settings(LOGIN_TOKEN_TTL_SECONDS=120)
    def test_setting_override_wins(self):
        self.assertEqual(config.login_token_ttl(), timedelta(seconds=120))

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"LOGIN_TOKEN_TTL_SECONDS": "300"}):
            self.assertEqual(config.login_token_ttl(), timedelta(seconds=300))

    @override_settings(LOGIN_TOKEN_TTL_SECONDS="not-a-number")
    def test_non_numeric_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.login_token_ttl()

    @override_settings(LOGIN_TOKEN_TTL_SECONDS=0)
    def test_zero_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.login_token_ttl()

    @override_settings(LOGIN_TOKEN_TTL_SECONDS=-5)
    def test_negative_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.login_token_ttl()


class RateLimitTests(SimpleTestCase):
    def test_defaults(self):
        for env_name in ("RATE_LIMIT_PER_EMAIL_PER_HOUR", "RATE_LIMIT_PER_IP_PER_HOUR"):
            os.environ.pop(env_name, None)
        self.assertEqual(config.rate_limit_per_email_per_hour(), 5)
        self.assertEqual(config.rate_limit_per_ip_per_hour(), 20)

    @override_settings(RATE_LIMIT_PER_EMAIL_PER_HOUR=2, RATE_LIMIT_PER_IP_PER_HOUR=9)
    def test_setting_override(self):
        self.assertEqual(config.rate_limit_per_email_per_hour(), 2)
        self.assertEqual(config.rate_limit_per_ip_per_hour(), 9)

    @override_settings(RATE_LIMIT_PER_EMAIL_PER_HOUR=-1)
    def test_invalid_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.rate_limit_per_email_per_hour()


class CatalogMediaLimitTests(SimpleTestCase):
    def test_defaults(self):
        for env_name in ("CATALOG_MEDIA_MAX_COUNT", "CATALOG_MEDIA_MAX_BYTES"):
            os.environ.pop(env_name, None)
        self.assertEqual(config.catalog_media_max_count(), 8)
        self.assertEqual(config.catalog_media_max_bytes(), 5 * 1024 * 1024)

    @override_settings(CATALOG_MEDIA_MAX_COUNT=3, CATALOG_MEDIA_MAX_BYTES=1024)
    def test_setting_override(self):
        self.assertEqual(config.catalog_media_max_count(), 3)
        self.assertEqual(config.catalog_media_max_bytes(), 1024)

    @override_settings(CATALOG_MEDIA_MAX_COUNT=0)
    def test_zero_count_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.catalog_media_max_count()

    @override_settings(CATALOG_MEDIA_MAX_BYTES="huge")
    def test_non_numeric_bytes_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.catalog_media_max_bytes()


class FollowedFeedPageSizeTests(SimpleTestCase):
    def test_default_when_unset(self):
        os.environ.pop("FOLLOWED_FEED_PAGE_SIZE", None)
        self.assertEqual(config.followed_feed_page_size(), 100)

    @override_settings(FOLLOWED_FEED_PAGE_SIZE=25)
    def test_setting_override(self):
        self.assertEqual(config.followed_feed_page_size(), 25)

    @override_settings(FOLLOWED_FEED_PAGE_SIZE=0)
    def test_zero_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.followed_feed_page_size()


class InterestTunableTests(SimpleTestCase):
    def test_suggested_minimum_default(self):
        os.environ.pop("INTEREST_SUGGESTED_MINIMUM", None)
        self.assertEqual(config.interest_suggested_minimum(), 3)

    def test_declaration_max_default(self):
        os.environ.pop("INTEREST_DECLARATION_MAX", None)
        self.assertEqual(config.interest_declaration_max(), 500)

    @override_settings(INTEREST_SUGGESTED_MINIMUM=5)
    def test_suggested_minimum_override(self):
        self.assertEqual(config.interest_suggested_minimum(), 5)

    @override_settings(INTEREST_DECLARATION_MAX=0)
    def test_declaration_max_zero_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.interest_declaration_max()


class UpdatesTunableTests(SimpleTestCase):
    def test_defaults(self):
        for name in (
            "UPDATES_FEED_NOTICE_LIMIT",
            "UPDATES_MAX_POSTS_PER_WINDOW",
            "UPDATES_POST_WINDOW_HOURS",
            "UPDATES_TITLE_MAX_LENGTH",
            "UPDATES_SUMMARY_MAX_LENGTH",
        ):
            os.environ.pop(name, None)
        self.assertEqual(config.updates_feed_notice_limit(), 50)
        self.assertEqual(config.updates_max_posts_per_window(), 5)
        self.assertEqual(config.updates_post_window_hours(), 24)
        self.assertEqual(config.updates_title_max_length(), 120)
        self.assertEqual(config.updates_summary_max_length(), 4000)

    @override_settings(
        UPDATES_FEED_NOTICE_LIMIT=10,
        UPDATES_MAX_POSTS_PER_WINDOW=3,
        UPDATES_POST_WINDOW_HOURS=6,
        UPDATES_TITLE_MAX_LENGTH=80,
        UPDATES_SUMMARY_MAX_LENGTH=500,
    )
    def test_overrides(self):
        self.assertEqual(config.updates_feed_notice_limit(), 10)
        self.assertEqual(config.updates_max_posts_per_window(), 3)
        self.assertEqual(config.updates_post_window_hours(), 6)
        self.assertEqual(config.updates_title_max_length(), 80)
        self.assertEqual(config.updates_summary_max_length(), 500)

    @override_settings(UPDATES_MAX_POSTS_PER_WINDOW=0)
    def test_non_positive_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.updates_max_posts_per_window()


class WidgetTunableTests(SimpleTestCase):
    def test_defaults(self):
        for name in (
            "WIDGET_NOTICE_LIMIT",
            "WIDGET_RENDER_RATE_LIMIT_PER_IP_PER_MINUTE",
            "WIDGET_CACHE_MAX_AGE_SECONDS",
        ):
            os.environ.pop(name, None)
        self.assertEqual(config.widget_notice_limit(), 5)
        self.assertEqual(config.widget_render_rate_limit_per_ip_per_minute(), 60)
        self.assertEqual(config.widget_cache_max_age_seconds(), 60)

    @override_settings(
        WIDGET_NOTICE_LIMIT=3,
        WIDGET_RENDER_RATE_LIMIT_PER_IP_PER_MINUTE=10,
        WIDGET_CACHE_MAX_AGE_SECONDS=30,
    )
    def test_overrides(self):
        self.assertEqual(config.widget_notice_limit(), 3)
        self.assertEqual(config.widget_render_rate_limit_per_ip_per_minute(), 10)
        self.assertEqual(config.widget_cache_max_age_seconds(), 30)

    @override_settings(WIDGET_NOTICE_LIMIT=0)
    def test_non_positive_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.widget_notice_limit()


class WidgetAttributionWindowTests(SimpleTestCase):
    def test_default_is_thirty_days(self):
        os.environ.pop("WIDGET_ATTRIBUTION_WINDOW_DAYS", None)
        self.assertEqual(config.widget_attribution_window_days(), 30)

    @override_settings(WIDGET_ATTRIBUTION_WINDOW_DAYS=7)
    def test_setting_override_wins(self):
        self.assertEqual(config.widget_attribution_window_days(), 7)

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"WIDGET_ATTRIBUTION_WINDOW_DAYS": "14"}):
            self.assertEqual(config.widget_attribution_window_days(), 14)

    @override_settings(WIDGET_ATTRIBUTION_WINDOW_DAYS=0)
    def test_non_positive_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.widget_attribution_window_days()

    @override_settings(WIDGET_ATTRIBUTION_WINDOW_DAYS="not-a-number")
    def test_non_numeric_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.widget_attribution_window_days()


class AppPageTunableTests(SimpleTestCase):
    def test_defaults(self):
        for name in (
            "APP_PAGE_DEEP_DIVE_MAX_LENGTH",
            "CATALOG_CLIP_MAX_BYTES",
            "APP_PAGE_DEVLOG_LIMIT",
        ):
            os.environ.pop(name, None)
        self.assertEqual(config.app_page_deep_dive_max_length(), 8000)
        self.assertEqual(config.catalog_clip_max_bytes(), 10 * 1024 * 1024)
        self.assertEqual(config.app_page_devlog_limit(), 5)

    @override_settings(APP_PAGE_DEEP_DIVE_MAX_LENGTH=2000, APP_PAGE_DEVLOG_LIMIT=3)
    def test_setting_overrides(self):
        self.assertEqual(config.app_page_deep_dive_max_length(), 2000)
        self.assertEqual(config.app_page_devlog_limit(), 3)

    @override_settings(CATALOG_CLIP_MAX_BYTES=0)
    def test_non_positive_clip_cap_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            config.catalog_clip_max_bytes()


class AppPageGatedFieldsTests(SimpleTestCase):
    _CANDIDATES = frozenset({"tagline", "deep_dive", "facets", "demo_clip"})

    def test_default_is_all_candidates(self):
        os.environ.pop("APP_PAGE_GATED_FIELDS", None)
        self.assertEqual(config.app_page_gated_fields(), self._CANDIDATES)

    @override_settings(APP_PAGE_GATED_FIELDS=["tagline", "facets"])
    def test_setting_relaxes_to_subset(self):
        self.assertEqual(config.app_page_gated_fields(), frozenset({"tagline", "facets"}))

    @override_settings(APP_PAGE_GATED_FIELDS=[])
    def test_empty_setting_gates_no_new_field(self):
        self.assertEqual(config.app_page_gated_fields(), frozenset())

    @override_settings(APP_PAGE_GATED_FIELDS=["tagline", "unknown_field"])
    def test_unknown_name_is_intersected_out(self):
        self.assertEqual(config.app_page_gated_fields(), frozenset({"tagline"}))

    def test_env_comma_string_override(self):
        with mock.patch.dict(os.environ, {"APP_PAGE_GATED_FIELDS": "deep_dive, demo_clip"}):
            self.assertEqual(
                config.app_page_gated_fields(), frozenset({"deep_dive", "demo_clip"})
            )


class ValidateAllTests(SimpleTestCase):
    def test_passes_with_defaults(self):
        config.validate_all()  # should not raise

    @override_settings(RATE_LIMIT_PER_IP_PER_HOUR="bad")
    def test_surfaces_first_bad_value(self):
        with self.assertRaises(ImproperlyConfigured):
            config.validate_all()

    @override_settings(WIDGET_RENDER_RATE_LIMIT_PER_IP_PER_MINUTE="bad")
    def test_evaluates_widget_tunables(self):
        # validate_all must cover the widget tunables, so a bad value surfaces at startup.
        with self.assertRaises(ImproperlyConfigured):
            config.validate_all()

    @override_settings(WIDGET_ATTRIBUTION_WINDOW_DAYS="bad")
    def test_evaluates_widget_attribution_window(self):
        # validate_all must cover the attribution window, so a bad value surfaces at startup.
        with self.assertRaises(ImproperlyConfigured):
            config.validate_all()
