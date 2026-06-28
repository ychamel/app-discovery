"""Env-gated Sentry initialization (platform-staging T-09, DESIGN §4.6).

SENTRY_DSN unset ⇒ no init (and sentry_sdk untouched); set ⇒ initialized once.
"""

from unittest import mock

from django.test import SimpleTestCase

from config.settings import _init_sentry


class SentryGatingTests(SimpleTestCase):
    def test_disabled_when_dsn_unset(self):
        import sentry_sdk

        with mock.patch.object(sentry_sdk, "init") as init:
            self.assertFalse(_init_sentry(None))
        init.assert_not_called()

    def test_disabled_when_dsn_blank(self):
        import sentry_sdk

        with mock.patch.object(sentry_sdk, "init") as init:
            self.assertFalse(_init_sentry(""))
        init.assert_not_called()

    def test_initialized_once_when_dsn_set(self):
        import sentry_sdk

        with mock.patch.object(sentry_sdk, "init") as init:
            self.assertTrue(_init_sentry("https://key@example.ingest.sentry.io/1"))
        init.assert_called_once()
        self.assertEqual(init.call_args.kwargs["dsn"], "https://key@example.ingest.sentry.io/1")
        self.assertFalse(init.call_args.kwargs["send_default_pii"])
