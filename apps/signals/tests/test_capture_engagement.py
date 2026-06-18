"""T-05 — the engagement recorders, with their linkage + proxy invariants (DESIGN.md §5a).

Covers: impression-required vs optional kinds (AC3/AC5/AC6), the cross-app/user mismatch
guard (AC3/§10), the service-set `is_proxy` (AC7), and fail-loud counting (AC11).
"""

import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core import observability
from apps.signals import capture
from apps.signals.errors import ImpressionMismatchError, UnknownAppError
from apps.signals.kinds import EventKind, Surface
from apps.signals.models import EngagementEvent
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user


class EngagementCaptureTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.other_app = make_accepted_app(
            self.owner, tag_ids=[self.tag.id], name="Other App"
        )
        self.impression = capture.record_impression(
            self.user, self.app.id, surface=Surface.DIGEST
        )

    # --- click-through: impression REQUIRED (AC3) ----------------------------
    def test_click_through_links_impression(self):
        event = capture.record_click_through(
            self.user, self.app.id, impression=self.impression
        )
        self.assertEqual(event.kind, EventKind.CLICK_THROUGH)
        self.assertEqual(event.impression_id, self.impression.id)
        self.assertFalse(event.is_proxy)

    def test_click_through_requires_an_impression(self):
        with self.assertRaises(ValidationError):
            capture.record_click_through(self.user, self.app.id, impression=None)
        self.assertEqual(EngagementEvent.objects.count(), 0)

    def test_click_through_rejects_mismatched_app(self):
        with self.assertRaises(ImpressionMismatchError):
            capture.record_click_through(
                self.user, self.other_app.id, impression=self.impression
            )
        self.assertEqual(EngagementEvent.objects.count(), 0)

    def test_click_through_rejects_another_users_impression(self):
        stranger = make_user("stranger@example.com")
        with self.assertRaises(ImpressionMismatchError):
            capture.record_click_through(
                stranger, self.app.id, impression=self.impression
            )
        self.assertEqual(EngagementEvent.objects.count(), 0)

    # --- optional-impression kinds (AC5/AC6) ---------------------------------
    def test_subscribe_without_impression(self):
        event = capture.record_subscribe(self.user, self.app.id)
        self.assertEqual(event.kind, EventKind.SUBSCRIBE)
        self.assertIsNone(event.impression_id)

    def test_page_reengagement_with_impression(self):
        event = capture.record_page_reengagement(
            self.user, self.app.id, impression=self.impression
        )
        self.assertEqual(event.kind, EventKind.PAGE_REENGAGEMENT)
        self.assertEqual(event.impression_id, self.impression.id)

    def test_share_without_impression(self):
        event = capture.record_share(self.user, self.app.id)
        self.assertEqual(event.kind, EventKind.SHARE)
        self.assertIsNone(event.impression_id)

    def test_optional_kind_still_validates_a_supplied_impression(self):
        with self.assertRaises(ImpressionMismatchError):
            capture.record_subscribe(
                self.user, self.other_app.id, impression=self.impression
            )
        self.assertEqual(EngagementEvent.objects.count(), 0)

    # --- off-platform proxy: secondary, is_proxy service-set (AC7) -----------
    def test_off_platform_proxy_is_flagged_secondary(self):
        event = capture.record_off_platform_proxy(
            self.user, self.app.id, impression=self.impression
        )
        self.assertEqual(event.kind, EventKind.OFF_PLATFORM_PROXY)
        self.assertTrue(event.is_proxy)

    def test_on_platform_recorders_never_set_is_proxy(self):
        """The caller cannot flip is_proxy — every on-platform act is False (AC7)."""
        events = [
            capture.record_click_through(self.user, self.app.id, impression=self.impression),
            capture.record_subscribe(self.user, self.app.id),
            capture.record_page_reengagement(self.user, self.app.id),
            capture.record_share(self.user, self.app.id),
        ]
        self.assertTrue(all(not e.is_proxy for e in events))

    def test_off_platform_proxy_requires_an_impression(self):
        with self.assertRaises(ValidationError):
            capture.record_off_platform_proxy(self.user, self.app.id, impression=None)
        self.assertEqual(EngagementEvent.objects.count(), 0)

    # --- app validity + fail-loud (AC11) -------------------------------------
    def test_unknown_app_is_rejected(self):
        with self.assertRaises(UnknownAppError):
            capture.record_subscribe(self.user, uuid.uuid4())
        self.assertEqual(EngagementEvent.objects.count(), 0)

    def test_failure_counts_capture_error_tagged_with_kind(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            with self.assertRaises(ImpressionMismatchError):
                capture.record_click_through(
                    self.user, self.other_app.id, impression=self.impression
                )
        self.assertTrue(
            any("capture_error" in line and "kind=click_through" in line for line in logs.output)
        )

    def test_happy_path_emits_no_capture_error(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            capture.record_click_through(self.user, self.app.id, impression=self.impression)
            capture.record_subscribe(self.user, self.app.id)
        self.assertFalse(
            any(observability.CAPTURE_ERROR in line for line in logs.output)
        )
