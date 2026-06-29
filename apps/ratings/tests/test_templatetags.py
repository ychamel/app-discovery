"""T-07 — the AP-1 reviews-slot inclusion tag + the app_page.html slot fill (DESIGN §5f/§5g).

Covers AC4 (summary + list + empty state), AC3 (anonymous read-only + sign-in link; signed-in
form), AC7 (a not-eligible rating shows with no badge), fail-soft (a selector error degrades
the slot without 500ing the page), and the structural guarantee that the slot edit is
content-only (the six app_page slots + the Reviews aria-label/heading are intact).
"""

from datetime import UTC, datetime
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.ratings.models import EligibilityBasis, Rating
from apps.ratings.tests.helpers import make_accepted_app, make_tag, make_user


def _rate(user, app, *, score, weight_eligible=False, text=""):
    return Rating.objects.create(
        user=user,
        app_id=app.id,
        score=score,
        review_text=text,
        weight_eligible=weight_eligible,
        eligibility_basis=(
            EligibilityBasis.CURATED_DIGEST_IMPRESSION
            if weight_eligible
            else EligibilityBasis.NO_CURATED_IMPRESSION
        ),
        eligibility_determined_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


class ReviewsSlotRenderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])
        self.page_url = reverse("pages:app-page", args=[self.app.id])

    # --- AC4 --------------------------------------------------------------
    def test_app_with_reviews_renders_summary_and_list(self):
        _rate(make_user("a@example.com"), self.app, score=5, text="great tool")
        _rate(make_user("b@example.com"), self.app, score=2)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("2 ratings", html)
        self.assertIn("Score distribution", html)
        self.assertIn("great tool", html)

    def test_empty_state_when_no_reviews(self):
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("No reviews yet", html)
        self.assertIn('aria-label="Reviews"', html)  # the slot still renders, uniform

    # --- AC3 --------------------------------------------------------------
    def test_anonymous_sees_read_only_reviews_and_a_signin_link_no_form(self):
        _rate(make_user("a@example.com"), self.app, score=4)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("Sign in to rate", html)
        self.assertNotIn('name="score"', html)  # no form for anonymous

    def test_signed_in_sees_the_form(self):
        self.client.force_login(self.user)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn('name="score"', html)
        self.assertIn(reverse("ratings:submit", args=[self.app.id]), html)

    def test_signed_in_with_own_rating_sees_prefilled_form_and_remove(self):
        _rate(self.user, self.app, score=3, text="mine")
        self.client.force_login(self.user)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("mine", html)
        self.assertIn(reverse("ratings:remove", args=[self.app.id]), html)

    # --- AC7 --------------------------------------------------------------
    def test_not_eligible_rating_shows_without_a_badge(self):
        _rate(make_user("outside@example.com"), self.app, score=1, weight_eligible=False)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("1 rating", html)
        # No eligibility wording leaks into the public render.
        for leak in ("weight_eligible", "not curated", "eligible"):
            self.assertNotIn(leak, html)

    # --- fail-soft --------------------------------------------------------
    def test_selector_error_degrades_the_slot_without_500ing_the_page(self):
        with (
            mock.patch(
                "apps.ratings.templatetags.ratings_tags.selectors.reviews_for_app",
                side_effect=RuntimeError("reviews down"),
            ),
            mock.patch(
                "apps.ratings.templatetags.ratings_tags.observability.increment"
            ) as increment,
        ):
            response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)  # the rest of the page still renders
        self.assertIn("temporarily unavailable", response.content.decode())
        # increment is a shared module attribute, so the page-render metric is also seen here;
        # assert specifically that the slot recorded its degradation.
        from apps.core import observability

        increment.assert_any_call(
            observability.RATING_DISPLAY_DEGRADED, app_id=str(self.app.id)
        )

    # --- structural: slot edit is content-only ----------------------------
    def test_app_page_keeps_its_slots_and_reviews_section_intact(self):
        # The reviews-slot edit is content-only: the app page's other uniform slots are intact
        # (landmarks per app-page-redesign §7) and the Reviews section still renders.
        html = self.client.get(self.page_url).content.decode()
        for aria in (
            'aria-label="App summary"',
            'aria-label="Media"',
            'aria-label="About"',
            'aria-label="Try it"',
            'aria-label="Share"',
            'aria-label="Reviews"',
        ):
            self.assertIn(aria, html)
        self.assertIn("<h2>Reviews</h2>", html)

    # --- owner notice (patch-block-self-interaction) ----------------------
    def test_reviews_slot_shows_notice_for_owner(self):
        self.client.force_login(self.owner)
        html = self.client.get(self.page_url).content.decode()
        self.assertIn("can't review your own app", html)
        submit_url = reverse("ratings:submit", args=[self.app.id])
        self.assertNotIn(f'action="{submit_url}"', html)
