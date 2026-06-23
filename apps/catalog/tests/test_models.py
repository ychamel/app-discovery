"""Tests for the catalog data model and initial migration (T-04, DESIGN.md §4).

Covers the structural guarantees the schema must make: UUID identity, the soft-tag and
position uniqueness constraints, the pending default, the indexed-but-not-unique
normalized URL (SI-2 — duplicates may coexist), ownership cascade, reviewer SET_NULL, and
the **absence** of any payment/priority field (AC3 fairness is unrepresentable).
"""

import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.catalog.gate import Criterion
from apps.catalog.models import App, AppMedia, AppTag, ReviewDecision
from apps.catalog.tests.helpers import make_account


class AppModelTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")

    def _make_app(self, **overrides) -> App:
        fields = {
            "owner": self.owner,
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "normalized_url": "https://demo.example.com",
            "last_submitted_at": timezone.now(),
        }
        fields.update(overrides)
        return App.objects.create(**fields)

    def test_uuid_primary_key_is_the_cross_feature_reference(self):
        app = self._make_app()
        self.assertIsInstance(app.id, uuid.UUID)

    def test_status_defaults_to_pending(self):
        self.assertEqual(self._make_app().status, App.Status.PENDING)

    def test_normalized_url_is_not_unique(self):
        # Two apps may share a normalized URL — duplicate detection is a manual signal
        # (SI-2 / §6c), never a DB constraint.
        self._make_app()
        try:
            with transaction.atomic():
                self._make_app()
        except IntegrityError:
            self.fail("normalized_url must not be unique (duplicates may coexist)")

    def test_owner_deletion_cascades_apps(self):
        app = self._make_app()
        self.owner.delete()
        self.assertFalse(App.objects.filter(pk=app.pk).exists())

    def test_no_monetary_or_priority_field_exists(self):
        # AC3: an unfair intake is unrepresentable — assert no such column exists.
        field_names = {f.name for f in App._meta.get_fields()}
        forbidden = {"price", "payment", "tier", "budget", "brand", "priority", "fast_lane"}
        self.assertEqual(field_names & forbidden, set())

    def test_accepted_at_and_search_vector_are_nullable_additive_columns(self):
        # open-search-browse T-01/DESIGN §5: both browse-order/search columns are additive
        # and nullable — an app that has never been accepted/maintained carries NULL.
        accepted_at = App._meta.get_field("accepted_at")
        search_vector = App._meta.get_field("search_vector")
        self.assertTrue(accepted_at.null)
        self.assertTrue(search_vector.null)
        app = self._make_app()
        self.assertIsNone(app.accepted_at)
        self.assertIsNone(app.search_vector)

    def test_browse_order_and_search_indexes_present(self):
        # AC9: the accepted-only ordered browse is one index range scan, search is GIN-backed.
        index_names = {index.name for index in App._meta.indexes}
        self.assertIn("catalog_app_status_acc_idx", index_names)
        self.assertIn("catalog_app_search_gin", index_names)
        # The pre-existing indexes are untouched (additive change).
        self.assertIn("catalog_app_status_idx", index_names)
        self.assertIn("catalog_app_normurl_idx", index_names)


class AppTagModelTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.app = App.objects.create(
            owner=self.owner,
            name="Demo",
            description="d",
            url="https://demo.example.com",
            normalized_url="https://demo.example.com",
            last_submitted_at=timezone.now(),
        )

    def test_tag_id_is_a_plain_uuid_not_a_db_fk(self):
        # A tag_id need not reference any existing taxonomy row at the DB level (D-5 soft
        # reference); validity is a write-boundary check, not a foreign key.
        tag = AppTag.objects.create(app=self.app, tag_id=uuid.uuid4())
        self.assertIsInstance(tag.tag_id, uuid.UUID)

    def test_unique_app_tag(self):
        tag_id = uuid.uuid4()
        AppTag.objects.create(app=self.app, tag_id=tag_id)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AppTag.objects.create(app=self.app, tag_id=tag_id)


class AppMediaModelTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.app = App.objects.create(
            owner=self.owner,
            name="Demo",
            description="d",
            url="https://demo.example.com",
            normalized_url="https://demo.example.com",
            last_submitted_at=timezone.now(),
        )

    def test_unique_app_position(self):
        AppMedia.objects.create(app=self.app, image="app_media/a.png", position=0)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AppMedia.objects.create(app=self.app, image="app_media/b.png", position=0)


class ReviewDecisionModelTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.app = App.objects.create(
            owner=self.owner,
            name="Demo",
            description="d",
            url="https://demo.example.com",
            normalized_url="https://demo.example.com",
            last_submitted_at=timezone.now(),
        )

    def test_accepted_decision_has_empty_failed_criteria(self):
        decision = ReviewDecision.objects.create(
            app=self.app, reviewer=self.reviewer, outcome=ReviewDecision.Outcome.ACCEPTED
        )
        self.assertEqual(decision.failed_criteria, [])

    def test_rejected_decision_stores_only_criterion_values(self):
        decision = ReviewDecision.objects.create(
            app=self.app,
            reviewer=self.reviewer,
            outcome=ReviewDecision.Outcome.REJECTED,
            failed_criteria=[Criterion.WORKS, Criterion.HONEST],
        )
        decision.refresh_from_db()
        self.assertEqual(decision.failed_criteria, ["works", "honest_metadata"])

    def test_reviewer_deletion_sets_null_and_keeps_decision(self):
        decision = ReviewDecision.objects.create(
            app=self.app, reviewer=self.reviewer, outcome=ReviewDecision.Outcome.ACCEPTED
        )
        self.reviewer.delete()
        decision.refresh_from_db()
        self.assertIsNone(decision.reviewer)
