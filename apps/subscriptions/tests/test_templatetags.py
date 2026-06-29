"""T-07 — the Follow-slot inclusion tag + the app_page.html slot insertion (DESIGN §5f).

Covers AC2 (anonymous → "Sign in to follow", no form, page renders), AC1 (signed-in,
not-following → Follow form), AC1/AC3 (signed-in, following → Unfollow form), fail-soft (a
selector error degrades the slot without 500ing the page; the ratings slot is unaffected),
and the structural guarantee that the slot edit is content-only (the existing slots + the
Reviews section are intact; the Follow section sits after the header).
"""

from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.subscriptions.models import Subscription
from apps.subscriptions.tests.helpers import make_accepted_app, make_tag, make_user


class FollowSlotRenderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    # --- AC2 --------------------------------------------------------------
    def test_anonymous_sees_a_signin_link_and_no_form(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("Sign in to follow", html)
        self.assertNotIn(
            reverse("subscriptions:follow", args=[self.app.id]), html
        )  # no follow form for anonymous

    # --- AC1 --------------------------------------------------------------
    def test_signed_in_not_following_sees_a_follow_form(self):
        self.client.force_login(self.user)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn(reverse("subscriptions:follow", args=[self.app.id]), html)
        self.assertIn("Follow", html)

    # --- AC1 / AC3 --------------------------------------------------------
    def test_signed_in_following_sees_an_unfollow_form(self):
        Subscription.objects.create(user=self.user, app_id=self.app.id)
        self.client.force_login(self.user)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn(reverse("subscriptions:unfollow", args=[self.app.id]), html)
        self.assertIn("Unfollow", html)

    # --- fail-soft --------------------------------------------------------
    def test_selector_error_degrades_the_slot_without_500ing_the_page(self):
        from apps.core import observability

        with (
            mock.patch(
                "apps.subscriptions.templatetags.subscriptions_tags.selectors.is_following",
                side_effect=RuntimeError("subscriptions down"),
            ),
            mock.patch(
                "apps.subscriptions.templatetags.subscriptions_tags.observability.increment"
            ) as increment,
        ):
            response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)  # the rest of the page still renders
        self.assertIn("Follow is temporarily unavailable", response.content.decode())
        increment.assert_any_call(
            observability.SUBSCRIPTION_CONTROL_DEGRADED, app_id=str(self.app.id)
        )

    def test_follow_slot_failure_does_not_affect_the_reviews_slot(self):
        # Independent inclusion tags — a subscriptions selector error must not degrade ratings.
        with mock.patch(
            "apps.subscriptions.templatetags.subscriptions_tags.selectors.is_following",
            side_effect=RuntimeError("subscriptions down"),
        ):
            html = self.client.get(self.page_url).content.decode()
        self.assertIn('aria-label="Reviews"', html)
        self.assertIn("No reviews yet", html)  # ratings slot rendered normally

    # --- owner (patch-block-self-interaction) ----------------------------
    def test_follow_slot_hides_button_for_owner(self):
        self.client.force_login(self.owner)
        html = self.client.get(self.page_url).content.decode()
        follow_url = reverse("subscriptions:follow", args=[self.app.id])
        self.assertNotIn(follow_url, html)

    # --- structural: slot edit is content-only ----------------------------
    def test_app_page_renders_follow_with_all_slots_intact(self):
        # The Follow-slot edit is content-only: every uniform app-page slot is intact
        # (landmarks per app-page-redesign §7) and the Follow + Reviews sections render.
        html = self.client.get(self.page_url).content.decode()
        for aria in (
            'aria-label="App summary"',
            'aria-label="Follow"',
            'aria-label="Media"',
            'aria-label="About"',
            'aria-label="Try it"',
            'aria-label="Share"',
            'aria-label="Reviews"',
        ):
            self.assertIn(aria, html)
        # The Follow section (sidebar) comes after the hero, and the Reviews heading is
        # untouched (the ratings slot fill is independent).
        self.assertGreater(
            html.index('aria-label="Follow"'), html.index('aria-label="App summary"')
        )
        self.assertIn("<h2>Reviews</h2>", html)
