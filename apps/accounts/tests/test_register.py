"""Registration flow tests (T-08, AC1 + AC2, DESIGN.md §5 #1)."""

from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts import roles
from apps.accounts.models import Account

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
EXPLODING = "apps.core.tests.test_email._ExplodingBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class RegisterTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.url = reverse("accounts:register")

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_valid_registration_creates_unconfirmed_user_and_emails_link(self):
        response = self.client.post(
            self.url, {"email": "new@example.com", "display_name": "New Dev"}
        )
        self.assertEqual(response.status_code, 202)

        account = Account.objects.get(email="new@example.com")
        # Holds the base user role from the creation transaction (AC1)...
        self.assertIn(roles.USER, roles.account_roles(account))
        # ...but is not yet confirmed/digest-eligible until the link is clicked (AC2).
        self.assertIsNone(account.email_confirmed_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("new@example.com", mail.outbox[0].to)

    def test_duplicate_email_is_refused(self):
        Account.objects.create_account("taken@example.com", display_name="First")
        response = self.client.post(
            self.url, {"email": "taken@example.com", "display_name": "Second"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Account.objects.filter(email="taken@example.com").count(), 1)
        self.assertContains(response, "Sign in", status_code=409)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(self.url, {"email": "not-an-email", "display_name": "X"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Account.objects.exists())

    def test_empty_display_name_is_rejected(self):
        response = self.client.post(self.url, {"email": "x@example.com", "display_name": ""})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Account.objects.exists())

    def test_every_account_has_the_user_role(self):
        self.client.post(self.url, {"email": "a@example.com", "display_name": "A"})
        account = Account.objects.get(email="a@example.com")
        user_group = Group.objects.get(name=roles.USER)
        self.assertIn(user_group, account.groups.all())


@override_settings(EMAIL_BACKEND=EXPLODING)
class RegisterSendFailureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_send_failure_returns_503_and_account_stays_unconfirmed(self):
        response = self.client.post(
            reverse("accounts:register"),
            {"email": "fail@example.com", "display_name": "Fail"},
        )
        self.assertEqual(response.status_code, 503)
        # AC2: the failure is surfaced, and the account is NOT digest-eligible.
        account = Account.objects.get(email="fail@example.com")
        self.assertIsNone(account.email_confirmed_at)
        self.assertContains(response, "couldn't send", status_code=503)


@override_settings(
    EMAIL_BACKEND=LOCMEM,
    RATE_LIMIT_PER_EMAIL_PER_HOUR=2,
    RATE_LIMIT_PER_IP_PER_HOUR=100,
)
class RegisterRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_repeated_requests_for_same_email_are_throttled(self):
        url = reverse("accounts:register")
        for _ in range(2):
            self.client.post(url, {"email": "spam@example.com", "display_name": "S"})
        response = self.client.post(url, {"email": "spam@example.com", "display_name": "S"})
        self.assertEqual(response.status_code, 429)
