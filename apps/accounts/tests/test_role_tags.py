"""Unit test for the ``is_developer`` template tag (UX-003 patch, PATCH.md §2A / T-01.5).

The tag is the only template-side reader of the role gate. It must agree with
``account_has_role`` exactly: True for a developer account, False for a plain user and
for an anonymous request — so a developer-gated link is never shown to anyone who would
be denied the underlying view.
"""

from django.contrib.auth.models import AnonymousUser
from django.template import Context, Template
from django.test import TestCase

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role

_TEMPLATE = Template("{% load account_roles %}{% is_developer user as flag %}{{ flag }}")


def _render_flag(user) -> str:
    return _TEMPLATE.render(Context({"user": user})).strip()


def _make_account(email: str, *, role: str | None = None) -> Account:
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


class IsDeveloperTagTests(TestCase):
    def test_true_for_developer(self):
        dev = _make_account("dev@example.com", role=roles.DEVELOPER)
        self.assertEqual(_render_flag(dev), "True")

    def test_false_for_plain_user(self):
        user = _make_account("user@example.com")
        self.assertEqual(_render_flag(user), "False")

    def test_false_for_anonymous(self):
        self.assertEqual(_render_flag(AnonymousUser()), "False")
