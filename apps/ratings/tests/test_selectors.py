"""T-05 — the display read path (DESIGN §5c).

Covers AC4 (count + distribution + ordered list + empty state), AC6 (no average/score is
computed — the summary is raw counts), and AC7 (a not-weight-eligible rating is still shown).
"""

import dataclasses
import inspect
from datetime import UTC, datetime

from django.test import TestCase, override_settings

from apps.ratings import selectors
from apps.ratings.models import EligibilityBasis, Rating
from apps.ratings.tests.helpers import make_accepted_app, make_tag, make_user


def _rate(user, app, *, score, weight_eligible=False, when=None, text=""):
    """Create one rating row directly, with a controllable ``created_at`` for ordering tests."""
    rating = Rating.objects.create(
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
        eligibility_determined_at=when or datetime(2026, 6, 1, tzinfo=UTC),
    )
    if when is not None:
        # auto_now_add already stamped created_at; override it for deterministic ordering.
        Rating.objects.filter(pk=rating.pk).update(created_at=when)
    return rating


class ReviewsForAppTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def test_empty_state_when_no_ratings(self):
        result = selectors.reviews_for_app(self.app.id, limit=20)
        self.assertEqual(result.total_count, 0)
        self.assertEqual(result.distribution, {})
        self.assertEqual(result.reviews, [])

    def test_count_and_distribution_match_fixtures(self):
        _rate(make_user("a@example.com"), self.app, score=5)
        _rate(make_user("b@example.com"), self.app, score=5)
        _rate(make_user("c@example.com"), self.app, score=2)

        result = selectors.reviews_for_app(self.app.id, limit=20)

        self.assertEqual(result.total_count, 3)
        self.assertEqual(result.distribution, {5: 2, 2: 1})

    def test_list_is_most_recent_first(self):
        _rate(
            make_user("old@example.com"),
            self.app,
            score=3,
            when=datetime(2026, 6, 1, tzinfo=UTC),
        )
        _rate(
            make_user("new@example.com"),
            self.app,
            score=4,
            when=datetime(2026, 6, 5, tzinfo=UTC),
        )
        result = selectors.reviews_for_app(self.app.id, limit=20)
        self.assertEqual([row.score for row in result.reviews], [4, 3])

    def test_honours_the_limit(self):
        for i in range(5):
            _rate(make_user(f"u{i}@example.com"), self.app, score=3)
        result = selectors.reviews_for_app(self.app.id, limit=2)
        self.assertEqual(len(result.reviews), 2)
        # the count + distribution still reflect ALL ratings, not just the shown page
        self.assertEqual(result.total_count, 5)

    def test_runs_in_a_bounded_query_count(self):
        for i in range(5):
            _rate(make_user(f"u{i}@example.com"), self.app, score=3, text="nice")
        # Two queries regardless of the number of ratings (no N+1 on author lookup).
        with self.assertNumQueries(2):
            result = selectors.reviews_for_app(self.app.id, limit=20)
            _ = [row.author_display for row in result.reviews]

    # --- AC7 --------------------------------------------------------------
    def test_not_weight_eligible_rating_is_included(self):
        _rate(make_user("outside@example.com"), self.app, score=1, weight_eligible=False)
        result = selectors.reviews_for_app(self.app.id, limit=20)
        self.assertEqual(result.total_count, 1)
        self.assertEqual(len(result.reviews), 1)
        # The public row carries no eligibility field at all (AC7/DESIGN §5c).
        self.assertFalse(hasattr(result.reviews[0], "weight_eligible"))

    def test_anonymized_author_renders_a_placeholder(self):
        rating = _rate(make_user("gone@example.com"), self.app, score=4)
        Rating.objects.filter(pk=rating.pk).update(user=None)
        result = selectors.reviews_for_app(self.app.id, limit=20)
        self.assertEqual(
            result.reviews[0].author_display, selectors.ANONYMIZED_AUTHOR_DISPLAY
        )

    # --- AC6 (structural) -------------------------------------------------
    def test_summary_shape_is_count_plus_distribution_only(self):
        # No average/score/rank field on the public summary — only the raw count + distribution.
        fields = {field.name for field in dataclasses.fields(selectors.AppReviews)}
        self.assertEqual(
            fields, {"app_id", "total_count", "distribution", "reviews"}
        )

    def test_no_averaging_machinery_is_used(self):
        # The summary must never compute an average/mean. Assert the code (function bodies,
        # not docstrings) imports/uses no averaging aggregate or division.
        for func in (
            selectors.reviews_for_app,
            selectors._score_distribution,
            selectors._to_row,
        ):
            body = "".join(
                line for line in inspect.getsource(func).splitlines(keepends=True)
            )
            code_only = "\n".join(
                line for line in body.splitlines() if not line.strip().startswith("#")
            )
            for forbidden in ("Avg(", "statistics", "mean(", "/ "):
                self.assertNotIn(forbidden, code_only)


class UserRatingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    def test_returns_the_callers_row(self):
        _rate(self.user, self.app, score=4)
        self.assertIsNotNone(selectors.user_rating(self.user, self.app.id))

    def test_returns_none_when_caller_has_no_row(self):
        self.assertIsNone(selectors.user_rating(self.user, self.app.id))

    @override_settings()
    def test_returns_none_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertIsNone(selectors.user_rating(AnonymousUser(), self.app.id))
