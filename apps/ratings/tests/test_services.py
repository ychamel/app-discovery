"""T-04 — the single write path (DESIGN §5a), tested against the real catalog + gate.

Covers AC1 (create), AC2 (boundary validation, nothing stored), AC9 (unknown app), AC5
(determination on 100% of writes), AC7 (non-curated stores not-eligible), AC8 (re-rate
updates the same row + remove), and write atomicity.
"""

from datetime import UTC, datetime
from unittest import mock
from uuid import uuid4

from django.test import TestCase, override_settings

from apps.ratings import services
from apps.ratings.errors import RatingValidationError, UnknownAppError
from apps.ratings.models import EligibilityBasis, Rating
from apps.ratings.tests.helpers import (
    make_accepted_app,
    make_curated,
    make_tag,
    make_user,
)


class SubmitRatingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    # --- AC1 --------------------------------------------------------------
    def test_creates_one_row_keyed_on_user_and_app(self):
        rating = services.submit_rating(
            self.user, self.app.id, score=4, review_text="solid"
        )
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(rating.user, self.user)
        self.assertEqual(rating.app_id, self.app.id)
        self.assertEqual(rating.score, 4)
        self.assertEqual(rating.review_text, "solid")

    def test_review_text_is_optional(self):
        rating = services.submit_rating(self.user, self.app.id, score=3)
        self.assertEqual(rating.review_text, "")

    # --- AC2 --------------------------------------------------------------
    def test_score_below_range_is_rejected_and_nothing_stored(self):
        with self.assertRaises(RatingValidationError):
            services.submit_rating(self.user, self.app.id, score=0)
        self.assertEqual(Rating.objects.count(), 0)

    def test_score_above_range_is_rejected_and_nothing_stored(self):
        with self.assertRaises(RatingValidationError):
            services.submit_rating(self.user, self.app.id, score=6)
        self.assertEqual(Rating.objects.count(), 0)

    @override_settings(REVIEW_TEXT_MAX_LENGTH=10)
    def test_over_length_review_is_rejected_and_nothing_stored(self):
        with self.assertRaises(RatingValidationError):
            services.submit_rating(
                self.user, self.app.id, score=3, review_text="x" * 11
            )
        self.assertEqual(Rating.objects.count(), 0)

    # --- AC9 --------------------------------------------------------------
    def test_unknown_app_is_rejected_and_nothing_stored(self):
        with self.assertRaises(UnknownAppError):
            services.submit_rating(self.user, uuid4(), score=3)
        self.assertEqual(Rating.objects.count(), 0)

    def test_catalog_read_that_raises_propagates_loud(self):
        # DESIGN §8 row 1: a rating has no subject if the catalog read itself fails — propagate.
        with mock.patch(
            "apps.ratings.services.catalog.get_catalogued_app",
            side_effect=RuntimeError("db down"),
        ):
            with self.assertRaises(RuntimeError):
                services.submit_rating(self.user, self.app.id, score=3)

    # --- AC5 / AC7 --------------------------------------------------------
    def test_every_write_stamps_a_determination(self):
        rating = services.submit_rating(self.user, self.app.id, score=3)
        self.assertIsNotNone(rating.weight_eligible)
        self.assertIsNotNone(rating.eligibility_basis)
        self.assertIsNotNone(rating.eligibility_determined_at)

    def test_non_curated_rater_stores_not_eligible(self):
        rating = services.submit_rating(self.user, self.app.id, score=5)
        self.assertFalse(rating.weight_eligible)
        self.assertEqual(rating.eligibility_basis, EligibilityBasis.NO_CURATED_IMPRESSION)

    def test_curated_rater_stores_weight_eligible(self):
        make_curated(self.user, self.app)
        rating = services.submit_rating(self.user, self.app.id, score=5)
        self.assertTrue(rating.weight_eligible)
        self.assertEqual(
            rating.eligibility_basis, EligibilityBasis.CURATED_DIGEST_IMPRESSION
        )

    def test_gate_unverified_still_stores(self):
        # AC5: even when the gate can't verify, a determination is present and the rating stores.
        with mock.patch(
            "apps.ratings.gate.signals.has_impression",
            side_effect=RuntimeError("signals down"),
        ):
            rating = services.submit_rating(self.user, self.app.id, score=2)
        self.assertEqual(Rating.objects.count(), 1)
        self.assertFalse(rating.weight_eligible)
        self.assertEqual(rating.eligibility_basis, EligibilityBasis.CURATION_UNVERIFIED)

    # --- AC8 --------------------------------------------------------------
    def test_resubmit_updates_the_same_row(self):
        first = services.submit_rating(self.user, self.app.id, score=2)
        second = services.submit_rating(
            self.user, self.app.id, score=5, review_text="changed my mind"
        )
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.score, 5)
        self.assertEqual(second.review_text, "changed my mind")

    def test_resubmit_redetermines_eligibility_as_of_the_edit(self):
        first = services.submit_rating(self.user, self.app.id, score=2)
        self.assertFalse(first.weight_eligible)
        # The user becomes curated, then re-rates → eligibility flips on the same row.
        make_curated(self.user, self.app, when=datetime(2026, 6, 2, tzinfo=UTC))
        second = services.submit_rating(self.user, self.app.id, score=4)
        self.assertEqual(first.id, second.id)
        self.assertTrue(second.weight_eligible)

    def test_different_users_each_keep_their_own_row(self):
        other = make_user("other@example.com")
        services.submit_rating(self.user, self.app.id, score=2)
        services.submit_rating(other, self.app.id, score=5)
        self.assertEqual(Rating.objects.count(), 2)

    def test_write_is_atomic_no_partial_row_on_failure(self):
        with mock.patch(
            "apps.ratings.services.Rating.objects.update_or_create",
            side_effect=RuntimeError("write blew up"),
        ):
            with self.assertRaises(RuntimeError):
                services.submit_rating(self.user, self.app.id, score=3)
        self.assertEqual(Rating.objects.count(), 0)


class RemoveRatingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    def test_remove_deletes_the_callers_row_and_reports_existed(self):
        services.submit_rating(self.user, self.app.id, score=3)
        self.assertTrue(services.remove_rating(self.user, self.app.id))
        self.assertEqual(Rating.objects.count(), 0)

    def test_remove_when_none_exists_returns_false(self):
        self.assertFalse(services.remove_rating(self.user, self.app.id))

    def test_remove_only_touches_the_callers_row(self):
        other = make_user("other@example.com")
        services.submit_rating(self.user, self.app.id, score=2)
        services.submit_rating(other, self.app.id, score=5)
        services.remove_rating(self.user, self.app.id)
        self.assertEqual(Rating.objects.count(), 1)
        self.assertTrue(Rating.objects.filter(user=other).exists())
