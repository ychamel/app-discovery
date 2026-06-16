"""Sign-in, verify, and session tests (T-09, AC3 + AC4, DESIGN.md §5 #2/#3)."""

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role
from apps.accounts.tests.helpers import latest_magic_link_token

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM)
class SignInFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.account = Account.objects.create_account("user@example.com", display_name="U")
        grant_role(self.account, roles.USER)

    def _request_link(self, email):
        return self.client.post(reverse("accounts:login"), {"email": email})

    def test_valid_auth_establishes_session(self):
        response = self._request_link("user@example.com")
        self.assertEqual(response.status_code, 202)

        token = latest_magic_link_token()
        verify = self.client.get(reverse("accounts:verify"), {"token": token})
        self.assertRedirects(verify, reverse("accounts:profile"), fetch_redirect_response=False)

        # Session is live: an authenticated-only endpoint now succeeds (AC3).
        me = self.client.get(reverse("accounts:me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "user@example.com")

    def test_first_verify_confirms_email(self):
        self._request_link("user@example.com")
        token = latest_magic_link_token()
        self.client.get(reverse("accounts:verify"), {"token": token})
        self.account.refresh_from_db()
        self.assertIsNotNone(self.account.email_confirmed_at)

    def test_invalid_token_denies_and_creates_no_session(self):
        response = self.client.get(reverse("accounts:verify"), {"token": "bogus"})
        self.assertEqual(response.status_code, 410)
        me = self.client.get(reverse("accounts:me"))
        self.assertEqual(me.status_code, 403)  # no session → DRF denies

    def test_expired_or_reused_token_denied(self):
        self._request_link("user@example.com")
        token = latest_magic_link_token()
        self.client.get(reverse("accounts:verify"), {"token": token})  # first use
        self.client.logout()
        second = self.client.get(reverse("accounts:verify"), {"token": token})  # reuse
        self.assertEqual(second.status_code, 410)

    def test_login_is_generic_for_unknown_email(self):
        # No account exists for this email: still 202, and no email is sent (no enumeration).
        response = self._request_link("ghost@example.com")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(EMAIL_BACKEND=LOCMEM)
class RecoverySameAccountTests(TestCase):
    """AC4: re-authenticating via email returns the same account with the same roles."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.account = Account.objects.create_account("dev@example.com", display_name="Dev")
        grant_role(self.account, roles.USER)
        grant_role(self.account, roles.DEVELOPER)

    def test_reauth_returns_same_account_and_roles(self):
        self.client.post(reverse("accounts:login"), {"email": "dev@example.com"})
        token = latest_magic_link_token()
        self.client.get(reverse("accounts:verify"), {"token": token})

        me = self.client.get(reverse("accounts:me")).json()
        self.assertEqual(me["id"], str(self.account.id))
        self.assertEqual(set(me["roles"]), {roles.USER, roles.DEVELOPER})
