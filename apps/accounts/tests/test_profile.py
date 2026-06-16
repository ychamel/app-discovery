"""Profile view/edit tests (T-11, AC7, DESIGN.md §5 #5/#6, §9)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role


class MeApiTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="Old Name")
        grant_role(self.account, roles.USER)
        self.api = APIClient()
        self.api.force_authenticate(self.account)

    def test_get_me_returns_account_shape(self):
        data = self.api.get(reverse("accounts:me")).json()
        self.assertEqual(data["id"], str(self.account.id))
        self.assertEqual(data["email"], "u@example.com")
        self.assertEqual(data["display_name"], "Old Name")
        self.assertEqual(data["roles"], [roles.USER])
        self.assertIn("email_confirmed", data)

    def test_patch_updates_display_name(self):
        response = self.api.patch(
            reverse("accounts:me"), {"display_name": "New Name"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.display_name, "New Name")
        # Reflected by a subsequent read (AC7).
        self.assertEqual(self.api.get(reverse("accounts:me")).json()["display_name"], "New Name")

    def test_patch_rejects_empty_display_name(self):
        response = self.api.patch(reverse("accounts:me"), {"display_name": ""}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_me_denied(self):
        self.assertEqual(APIClient().get(reverse("accounts:me")).status_code, 403)


class ProfilePageTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="U")
        grant_role(self.account, roles.USER)

    def test_authenticated_profile_renders(self):
        self.client.force_login(self.account)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your profile")
        self.assertContains(response, "Become a developer")

    def test_anonymous_profile_redirects_to_signin(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:signin"), response["Location"])
