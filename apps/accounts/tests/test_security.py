"""Security posture tests (T-16, DESIGN.md §10)."""

import logging

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Account

EXPLODING = "apps.core.tests.test_email._ExplodingBackend"


class CookieAndTransportSettingsTests(TestCase):
    def test_session_cookie_hardening(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")

    def test_secure_transport_flags_are_consistent(self):
        # The HTTPS-dependent protections move together (all on in prod, all off in
        # local http dev). The runner mutates DEBUG, so we assert internal
        # consistency rather than tie to the live DEBUG value.
        flags = {
            settings.SESSION_COOKIE_SECURE,
            settings.CSRF_COOKIE_SECURE,
            settings.SECURE_SSL_REDIRECT,
        }
        self.assertEqual(len(flags), 1, f"secure flags disagree: {flags}")

    def test_content_type_nosniff_enabled(self):
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)


class CsrfEnforcementTests(TestCase):
    def test_form_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("accounts:register"),
            {"email": "x@example.com", "display_name": "X"},
        )
        self.assertEqual(response.status_code, 403)


@override_settings(EMAIL_BACKEND=EXPLODING)
class LogPiiTests(TestCase):
    def test_logs_carry_uuid_not_raw_email(self):
        # The send-failure path logs; assert it records the account UUID, never the email.
        with self.assertLogs("apps.accounts.views", level=logging.ERROR) as captured:
            self.client.post(
                reverse("accounts:register"),
                {"email": "secret@example.com", "display_name": "S"},
            )
        log_text = "\n".join(captured.output)
        account = Account.objects.get(email="secret@example.com")
        self.assertIn(str(account.id), log_text)
        self.assertNotIn("secret@example.com", log_text)
