"""T-04 — the impression anchor + visit substrate, fail-loud (DESIGN.md §5a/§5d).

Covers: app validity (D-6), the frozen capture-time tag snapshot (AC1/AC2), atomicity,
idempotent visits (AC4), and the never-silent capture_error contract (AC11).
"""

import uuid
from datetime import date
from unittest import mock

from django.test import TestCase

from apps.core import observability
from apps.signals import capture
from apps.signals.errors import UnknownAppError
from apps.signals.kinds import Surface
from apps.signals.models import Impression, ImpressionTag, PlatformVisit
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user
from apps.taxonomy import services as taxonomy_services


class RecordImpressionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag_a = make_tag("notes")
        self.tag_b = make_tag("todo")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag_a.id, self.tag_b.id])

    def test_records_impression_with_frozen_tag_snapshot(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            impression = capture.record_impression(
                self.user, self.app.id, surface=Surface.DIGEST
            )

        self.assertEqual(Impression.objects.count(), 1)
        snapshot = set(
            ImpressionTag.objects.filter(impression=impression).values_list(
                "tag_id", flat=True
            )
        )
        self.assertEqual(snapshot, {self.tag_a.id, self.tag_b.id})
        self.assertTrue(any("impression_captured" in line for line in logs.output))

    def test_snapshot_is_frozen_against_later_tag_rename(self):
        impression = capture.record_impression(
            self.user, self.app.id, surface=Surface.DIGEST
        )
        before = set(
            ImpressionTag.objects.filter(impression=impression).values_list(
                "tag_id", flat=True
            )
        )

        taxonomy_services.rename_tag(self.tag_a, label="renamed-notes")

        after = set(
            ImpressionTag.objects.filter(impression=impression).values_list(
                "tag_id", flat=True
            )
        )
        self.assertEqual(before, after)

    def test_unknown_app_raises_and_writes_nothing(self):
        with self.assertRaises(UnknownAppError):
            capture.record_impression(
                self.user, uuid.uuid4(), surface=Surface.DIGEST
            )
        self.assertEqual(Impression.objects.count(), 0)
        self.assertEqual(ImpressionTag.objects.count(), 0)

    def test_non_accepted_app_is_rejected(self):
        """A pending (not yet accepted) app is not catalogued, so capture refuses it (D-6)."""
        from apps.catalog import services as catalog_services
        from apps.signals.tests.helpers import _png_upload

        pending = catalog_services.submit_app(
            self.owner, name="Pending", description="x",
            url="https://example.com/pending", tag_ids=[self.tag_a.id],
            media=[_png_upload()],
        )
        with self.assertRaises(UnknownAppError):
            capture.record_impression(self.user, pending.id, surface=Surface.DIGEST)
        self.assertEqual(Impression.objects.count(), 0)

    def test_partial_write_failure_is_atomic_and_counted(self):
        """A failure while writing the tag rows leaves no impression either (atomic)."""
        with mock.patch.object(
            ImpressionTag.objects, "bulk_create", side_effect=RuntimeError("boom")
        ):
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                with self.assertRaises(RuntimeError):
                    capture.record_impression(
                        self.user, self.app.id, surface=Surface.DIGEST
                    )

        # Nothing persisted, and the loss is loud (capture_error counted + re-raised).
        self.assertEqual(Impression.objects.count(), 0)
        self.assertEqual(ImpressionTag.objects.count(), 0)
        self.assertTrue(
            any("capture_error" in line and "kind=impression" in line for line in logs.output)
        )

    def test_invalid_surface_is_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            capture.record_impression(self.user, self.app.id, surface="banner")
        self.assertEqual(Impression.objects.count(), 0)


class RecordPlatformVisitTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_visit_is_idempotent_per_user_per_day(self):
        first = capture.record_platform_visit(self.user, on_date=date(2026, 6, 18))
        second = capture.record_platform_visit(self.user, on_date=date(2026, 6, 18))

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PlatformVisit.objects.filter(user=self.user).count(), 1)

    def test_only_a_created_visit_emits_the_metric(self):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            capture.record_platform_visit(self.user, on_date=date(2026, 6, 18))
            capture.record_platform_visit(self.user, on_date=date(2026, 6, 18))

        visit_metrics = [line for line in logs.output if "platform_visit_captured" in line]
        self.assertEqual(len(visit_metrics), 1)

    def test_distinct_days_each_record(self):
        capture.record_platform_visit(self.user, on_date=date(2026, 6, 18))
        capture.record_platform_visit(self.user, on_date=date(2026, 6, 19))
        self.assertEqual(PlatformVisit.objects.filter(user=self.user).count(), 2)


class CaptureErrorIsZeroOnHappyPathTests(TestCase):
    """A healthy capture never increments capture_error (CLAUDE.md §6.6)."""

    def test_happy_path_emits_no_capture_error(self):
        user = make_user()
        owner = make_user("owner@example.com")
        tag = make_tag("notes")
        app = make_accepted_app(owner, tag_ids=[tag.id])

        with self.assertLogs("apps.metrics", level="INFO") as logs:
            impression = capture.record_impression(user, app.id, surface=Surface.DIGEST)
            capture.record_platform_visit(user)

        self.assertIsNotNone(impression)
        self.assertFalse(
            any(observability.CAPTURE_ERROR in line for line in logs.output)
        )
