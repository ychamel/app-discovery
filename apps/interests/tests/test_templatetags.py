"""T-05 — the onboarding nudge inclusion tag ``{% interest_prompt %}`` (DESIGN §5.4, AC3).

Tested both in isolation (the tag's fail-soft contract) and through the live
``accounts:profile`` page (the one sanctioned content line), with the ``interests/`` URLconf
included.
"""

from unittest import mock

from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core import observability
from apps.interests.models import Interest
from apps.interests.tests.helpers import make_tag, make_user


def _render_tag(user):
    request = RequestFactory().get("/profile")
    request.user = user
    template = Template("{% load interests_tags %}{% interest_prompt %}")
    return template.render(Context({"request": request}))


class InterestPromptTagTests(TestCase):
    def test_renders_nudge_for_an_empty_profile(self):
        # AC3: an empty-profile user sees the nudge linking to the picker.
        html = _render_tag(make_user())
        self.assertIn(reverse("interests:picker"), html)
        self.assertIn("interested in", html)

    def test_renders_nothing_when_the_user_has_declared_interests(self):
        # AC3/AC6: the nudge self-resolves once any interest exists.
        user = make_user()
        Interest.objects.create(user=user, tag_id=make_tag("calm").id)
        html = _render_tag(user)
        self.assertNotIn("interested in", html)

    def test_fail_soft_renders_nothing_and_counts_degraded(self):
        # A selector error renders nothing + INTEREST_PROMPT_DEGRADED, never raises.
        user = make_user()
        with mock.patch(
            "apps.interests.templatetags.interests_tags.selectors.has_declared_interests",
            side_effect=RuntimeError("read down"),
        ):
            with mock.patch.object(observability, "increment") as inc:
                html = _render_tag(user)
        self.assertEqual(html.strip(), "")
        inc.assert_called_once_with(observability.INTEREST_PROMPT_DEGRADED)


class ProfilePageNudgeTests(TestCase):
    def test_empty_profile_user_sees_the_nudge_on_the_profile_page(self):
        # AC3: a signed-in, empty-profile user landing on profile sees the (non-gating) nudge.
        user = make_user()
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("interests:picker"))

    def test_user_with_interests_sees_no_nudge_but_page_renders(self):
        user = make_user()
        Interest.objects.create(user=user, tag_id=make_tag("calm").id)
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("interests:picker"))

    def test_profile_page_still_renders_when_the_nudge_fails(self):
        # Fail-soft: a read error must not 500 the profile page.
        user = make_user()
        self.client.force_login(user)
        with mock.patch(
            "apps.interests.templatetags.interests_tags.selectors.has_declared_interests",
            side_effect=RuntimeError("read down"),
        ):
            response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your profile")
