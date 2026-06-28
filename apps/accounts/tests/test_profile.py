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


class ProfileFormActionTests(TestCase):
    """BUG-002 — the profile Edit-display-name + Delete-account forms must post to
    dedicated server-rendered §9 handlers (PRG + messages), not the JSON ``/me`` API.

    Red-first: these assert the fixed behaviour, so they fail against today's code
    (the ``profile-display-name`` / ``profile-delete`` routes and views do not exist
    yet, and the forms still post to ``accounts:me``).
    """

    def setUp(self):
        self.account = Account.objects.create_account("u@example.com", display_name="Old Name")
        grant_role(self.account, roles.USER)
        self.display_name_url = reverse("accounts:profile-display-name")
        self.delete_url = reverse("accounts:profile-delete")

    # --- Edit display name ------------------------------------------------
    def test_valid_display_name_update_redirects_and_persists(self):
        self.client.force_login(self.account)
        response = self.client.post(self.display_name_url, {"display_name": "New Name"})
        self.assertRedirects(
            response, reverse("accounts:profile"), fetch_redirect_response=False
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.display_name, "New Name")
        follow = self.client.get(response["Location"])
        self.assertTrue([m.message for m in follow.context["messages"]])  # success surfaced

    def test_blank_display_name_is_rejected_without_changing_the_name(self):
        self.client.force_login(self.account)
        response = self.client.post(self.display_name_url, {"display_name": "   "}, follow=True)
        self.assertEqual(response.status_code, 200)  # no 500
        self.account.refresh_from_db()
        self.assertEqual(self.account.display_name, "Old Name")  # unchanged
        self.assertTrue([m.message for m in response.context["messages"]])  # error surfaced

    def test_display_name_route_is_post_only(self):
        self.client.force_login(self.account)
        self.assertEqual(self.client.get(self.display_name_url).status_code, 405)

    def test_display_name_route_requires_login(self):
        response = self.client.post(self.display_name_url, {"display_name": "New Name"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:signin"), response["Location"])

    # --- Delete account ---------------------------------------------------
    def test_confirmed_delete_removes_account_and_logs_out(self):
        self.client.force_login(self.account)
        response = self.client.post(self.delete_url, {"confirm": "true"})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
        # Session was flushed: the now-anonymous client is bounced off the profile page.
        follow = self.client.get(reverse("accounts:profile"))
        self.assertEqual(follow.status_code, 302)
        self.assertIn(reverse("accounts:signin"), follow["Location"])

    def test_unconfirmed_delete_keeps_the_account(self):
        self.client.force_login(self.account)
        response = self.client.post(self.delete_url, {}, follow=True)
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())  # untouched
        self.assertTrue([m.message for m in response.context["messages"]])  # error surfaced

    def test_delete_route_is_post_only(self):
        self.client.force_login(self.account)
        self.assertEqual(self.client.get(self.delete_url).status_code, 405)

    def test_delete_route_requires_login(self):
        response = self.client.post(self.delete_url, {"confirm": "true"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:signin"), response["Location"])
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())

    # --- The page wires the forms to the new routes -----------------------
    def test_profile_page_posts_forms_to_the_new_routes_not_the_api(self):
        self.client.force_login(self.account)
        html = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn(f'action="{self.display_name_url}"', html)
        self.assertIn(f'action="{self.delete_url}"', html)
        self.assertNotIn(f'action="{reverse("accounts:me")}"', html)
