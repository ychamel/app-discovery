"""Tests for the catalog lifecycle/decision service (T-06, DESIGN.md §5a/§7).

The sharp guarantees: accept/reject write the decision AND flip status in one transaction
(neither survives a mid-call failure), a reject names ≥1 valid floor (no taste rejection —
AC6), a concurrent second decision is refused (no double decision), and withdraw/resubmit
honor the §7 state machine.
"""

import tempfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.catalog import services
from apps.catalog.errors import InvalidTransitionError
from apps.catalog.gate import Criterion
from apps.catalog.models import App, ReviewDecision
from apps.catalog.tests.helpers import make_account, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag(slug="todo-app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, "To-do app", clusters=[cluster])


def _make_pending_app(owner, tag):
    return services.submit_app(
        owner,
        name="Demo",
        description="A demo app.",
        url="https://demo.example.com",
        tag_ids=[tag.id],
        media=[make_image_upload()],
    )


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AcceptRejectTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()
        self.app = _make_pending_app(self.owner, self.tag)

    def test_accept_flips_status_and_writes_decision(self):
        decision = services.accept_app(self.app, self.reviewer)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.ACCEPTED)
        self.assertEqual(decision.outcome, ReviewDecision.Outcome.ACCEPTED)
        self.assertEqual(decision.failed_criteria, [])

    def test_reject_flips_status_and_records_criteria(self):
        decision = services.reject_app(
            self.app, self.reviewer, failed_criteria=[Criterion.WORKS], note="Broken."
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.REJECTED)
        self.assertEqual(decision.failed_criteria, ["works"])
        self.assertEqual(decision.note, "Broken.")

    def test_reject_with_zero_criteria_refused(self):
        with self.assertRaises(ValidationError):
            services.reject_app(self.app, self.reviewer, failed_criteria=[])
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)
        self.assertEqual(ReviewDecision.objects.count(), 0)

    def test_reject_with_unknown_criterion_refused(self):
        with self.assertRaises(ValidationError):
            services.reject_app(self.app, self.reviewer, failed_criteria=["quality"])
        self.assertEqual(ReviewDecision.objects.count(), 0)

    def test_accept_non_pending_raises_transition(self):
        services.accept_app(self.app, self.reviewer)
        with self.assertRaises(InvalidTransitionError):
            services.accept_app(self.app, self.reviewer)

    def test_decision_atomic_failure_leaves_neither(self):
        # Force the status-save to fail after the decision is written; the transaction must
        # roll back so neither the decision nor the status change persists (AC5 atomicity).
        with mock.patch.object(
            App, "save", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                services.accept_app(self.app, self.reviewer)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)
        self.assertEqual(ReviewDecision.objects.count(), 0)

    def test_reject_emits_per_criterion_metric(self):
        with mock.patch.object(services.observability, "increment") as inc:
            services.reject_app(
                self.app,
                self.reviewer,
                failed_criteria=[Criterion.WORKS, Criterion.HONEST],
            )
        criteria_tags = [
            call.kwargs.get("criterion")
            for call in inc.call_args_list
            if call.args and call.args[0] == services.observability.REVIEW_DECISION
        ]
        self.assertIn("works", criteria_tags)
        self.assertIn("honest_metadata", criteria_tags)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class WithdrawResubmitTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()
        self.app = _make_pending_app(self.owner, self.tag)

    def test_withdraw_from_pending(self):
        services.withdraw_app(self.app)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.WITHDRAWN)

    def test_withdraw_from_accepted(self):
        services.accept_app(self.app, self.reviewer)
        services.withdraw_app(self.app)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.WITHDRAWN)

    def test_double_withdraw_refused(self):
        services.withdraw_app(self.app)
        with self.assertRaises(InvalidTransitionError):
            services.withdraw_app(self.app)

    def test_resubmit_from_rejected(self):
        services.reject_app(self.app, self.reviewer, failed_criteria=[Criterion.WORKS])
        before = self.app.last_submitted_at
        services.resubmit_app(self.app)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)
        self.assertGreaterEqual(self.app.last_submitted_at, before)

    def test_resubmit_from_withdrawn(self):
        services.withdraw_app(self.app)
        services.resubmit_app(self.app)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)

    def test_resubmit_pending_refused(self):
        with self.assertRaises(InvalidTransitionError):
            services.resubmit_app(self.app)

    def test_review_decisions_are_append_only(self):
        services.reject_app(self.app, self.reviewer, failed_criteria=[Criterion.WORKS])
        services.resubmit_app(self.app)
        services.accept_app(self.app, self.reviewer)
        # Both decisions are retained — the log is never mutated or pruned.
        self.assertEqual(ReviewDecision.objects.filter(app=self.app).count(), 2)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DoubleDecisionTests(TestCase):
    """The row lock + status re-check let exactly one decision win (no double decision)."""

    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()
        self.app = _make_pending_app(self.owner, self.tag)

    def test_second_decision_is_refused(self):
        # The first decision moves the app off `pending`; a second decision re-fetches under
        # select_for_update, sees the non-pending status, and raises — so exactly one
        # decision survives (the guarantee the row lock provides under real concurrency).
        services.accept_app(self.app, self.reviewer)
        with self.assertRaises(InvalidTransitionError):
            services.reject_app(self.app, self.reviewer, failed_criteria=[Criterion.WORKS])
        self.assertEqual(ReviewDecision.objects.filter(app=self.app).count(), 1)
