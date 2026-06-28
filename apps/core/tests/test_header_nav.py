"""Header navigation reachability tests (UX-003 patch, PATCH.md §2B / T-01 cases 1-3).

Regression guard for UX-003: a ``developer``-role account must have a header link to
their submissions list (``catalog:my-apps``), and that link must NOT appear for a plain
authenticated user or for an anonymous visitor. The header lives in the shared
``core/base.html``, so any authenticated surface (here: ``discovery:browse``) exercises it.
"""

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role


def _make_account(email: str, *, role: str | None = None) -> Account:
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


class HeaderSubmissionsLinkTests(TestCase):
    def setUp(self):
        self.browse_url = reverse("discovery:browse")
        self.submissions_url = reverse("catalog:my-apps")

    def test_present_for_developer(self):
        client = Client()
        client.force_login(_make_account("dev@example.com", role=roles.DEVELOPER))
        response = client.get(self.browse_url)
        self.assertContains(response, f'href="{self.submissions_url}"')

    def test_absent_for_plain_user(self):
        client = Client()
        client.force_login(_make_account("user@example.com"))
        response = client.get(self.browse_url)
        self.assertNotContains(response, f'href="{self.submissions_url}"')

    def test_absent_for_anonymous(self):
        response = Client().get(self.browse_url)
        self.assertNotContains(response, f'href="{self.submissions_url}"')
