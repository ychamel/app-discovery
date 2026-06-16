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


class ValidateAllTests(SimpleTestCase):
    def test_passes_with_defaults(self):
        config.validate_all()  # should not raise

    @override_settings(RATE_LIMIT_PER_IP_PER_HOUR="bad")
    def test_surfaces_first_bad_value(self):
        with self.assertRaises(ImproperlyConfigured):
            config.validate_all()
