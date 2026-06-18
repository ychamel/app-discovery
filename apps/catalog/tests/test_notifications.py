"""Tests for decision notifications (T-08, DESIGN.md §5d).

The accepted/rejected templates render the right content (the rejected body lists each
failing floor's label + the note, AC7), and a send failure is counted without rolling back
the decision — the email is a notification, not part of the gate (§5d).
"""

import tempfile
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings

from apps.catalog import notifications, services
from apps.catalog.gate import Criterion
from apps.catalog.models import App
from apps.catalog.tests.helpers import make_account, make_image_upload
from apps.core.email import EmailSendError
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag():
    cluster = taxonomy_services.add_cluster("c-todo", "Cluster")
    return taxonomy_services.add_tag("todo-app", "To-do app", clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class NotifyDecisionTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()
        self.app = services.submit_app(
            self.owner,
            name="Demo",
            description="A demo app.",
            url="https://demo.example.com",
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )

    def test_accepted_decision_sends_accepted_template(self):
        decision = services.accept_app(self.app, self.reviewer)
        sent = notifications.notify_decision(decision)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("catalogue", mail.outbox[0].subject.lower())

    def test_rejected_body_lists_each_failing_criterion_and_note(self):
        decision = services.reject_app(
            self.app,
            self.reviewer,
            failed_criteria=[Criterion.WORKS, Criterion.HONEST],
            note="The landing page 404s.",
        )
        notifications.notify_decision(decision)
        body = mail.outbox[0].body
        self.assertIn(Criterion.WORKS.label, body)
        self.assertIn(Criterion.HONEST.label, body)
        self.assertIn("The landing page 404s.", body)

    def test_send_failure_is_counted_and_decision_stands(self):
        decision = services.reject_app(
            self.app, self.reviewer, failed_criteria=[Criterion.WORKS]
        )
        failing_sender = mock.Mock()
        failing_sender.send.side_effect = EmailSendError("transport down")
        with mock.patch.object(notifications, "get_email_sender", return_value=failing_sender):
            with mock.patch.object(notifications.observability, "increment") as inc:
                sent = notifications.notify_decision(decision)

        self.assertFalse(sent)
        metrics = {call.args[0] for call in inc.call_args_list}
        self.assertIn(notifications.observability.EMAIL_SEND_FAILURE, metrics)
        # The decision is untouched — status and the decision row both stand (§5d).
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.REJECTED)
        self.assertEqual(self.app.decisions.count(), 1)
