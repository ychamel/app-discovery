"""Tests for apps.core.email — successful send and fail-loud behavior (T-03)."""

from django.core import mail
from django.test import SimpleTestCase, override_settings

from apps.core.email import DefaultEmailSender, EmailSendError, get_email_sender


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@test.local",
)
class SuccessfulSendTests(SimpleTestCase):
    def test_send_delivers_via_configured_backend(self):
        DefaultEmailSender().send(
            to="user@example.com",
            template="magic_link",
            context={"link": "https://app/verify?token=abc", "purpose": "login", "ttl_minutes": 15},
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["user@example.com"])
        self.assertEqual(message.from_email, "no-reply@test.local")
        self.assertIn("https://app/verify?token=abc", message.body)
        self.assertIn("sign-in link", message.subject)

    def test_register_template_renders_register_copy(self):
        DefaultEmailSender().send(
            to="new@example.com",
            template="magic_link",
            context={
                "link": "https://app/verify?token=xyz",
                "purpose": "register",
                "ttl_minutes": 15,
            },
        )
        self.assertIn("Confirm your email", mail.outbox[0].subject)


class _ExplodingBackend:
    """An email backend whose send raises — used to prove failures propagate."""

    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise OSError("simulated transport outage")


class FailLoudTests(SimpleTestCase):
    @override_settings(
        EMAIL_BACKEND="apps.core.tests.test_email._ExplodingBackend",
        DEFAULT_FROM_EMAIL="no-reply@test.local",
    )
    def test_backend_failure_raises(self):
        with self.assertRaises(EmailSendError):
            DefaultEmailSender().send(
                to="user@example.com",
                template="magic_link",
                context={"link": "x", "purpose": "login", "ttl_minutes": 15},
            )


class FactoryTests(SimpleTestCase):
    def test_get_email_sender_returns_default(self):
        self.assertIsInstance(get_email_sender(), DefaultEmailSender)


class SmtpSettingsWiringTests(SimpleTestCase):
    """Django's SMTP backend reads EMAIL_HOST/PORT/... from settings; settings.py now
    exposes those five from env (platform-staging T-04). Prove the SMTP backend picks
    them up — i.e. the names we wire are exactly the ones the transport consumes."""

    @override_settings(
        EMAIL_HOST="smtp.resend.com",
        EMAIL_PORT=587,
        EMAIL_HOST_USER="resend",
        EMAIL_HOST_PASSWORD="rk_secret",
        EMAIL_USE_TLS=True,
    )
    def test_smtp_backend_consumes_wired_settings(self):
        from django.core.mail.backends.smtp import EmailBackend as SmtpBackend

        backend = SmtpBackend()
        self.assertEqual(backend.host, "smtp.resend.com")
        self.assertEqual(backend.port, 587)
        self.assertEqual(backend.username, "resend")
        self.assertEqual(backend.password, "rk_secret")
        self.assertTrue(backend.use_tls)
