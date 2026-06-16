"""Sign-out tests (T-10, AC5, DESIGN.md §5 #4)."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Account


class LogoutTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="U")

    def test_logout_flushes_session_and_protected_action_requires_reauth(self):
        self.client.force_login(self.account)
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 200)

        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 204)

        # Session is gone — a protected endpoint now denies (AC5).
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, 403)

    def test_logout_requires_post(self):
        self.client.force_login(self.account)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
