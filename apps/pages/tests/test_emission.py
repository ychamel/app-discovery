"""T-03 — the surface-side non-blocking capture policy (DESIGN.md §5b/§7; AC6/AC7).

Pure unit tests against a **fake** ``signals.capture`` seam (and a faked impression
lookup): emission's only jobs are the authenticated-only gate (AP-4) and the
fail-soft-but-counted wrapper (AC7). Real capture behavior is signal-capture's own suite.
"""

from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from django.test import SimpleTestCase

from apps.core import observability
from apps.pages import emission
from apps.signals.errors import ImpressionMismatchError
from apps.signals.kinds import Surface


def _request(*, authenticated: bool):
    return SimpleNamespace(user=SimpleNamespace(is_authenticated=authenticated, pk=uuid4()))


class RecordPageViewTests(SimpleTestCase):
    def test_anonymous_captures_nothing_and_returns_none(self):
        with mock.patch.object(emission, "capture") as fake_capture:
            result = emission.record_page_view(_request(authenticated=False), uuid4())
        self.assertIsNone(result)
        fake_capture.record_impression.assert_not_called()

    def test_authenticated_records_app_page_impression_and_returns_id(self):
        app_id = uuid4()
        impression_id = uuid4()
        with mock.patch.object(emission, "capture") as fake_capture:
            fake_capture.record_impression.return_value = SimpleNamespace(id=impression_id)
            result = emission.record_page_view(_request(authenticated=True), app_id)

        self.assertEqual(result, impression_id)
        _, kwargs = fake_capture.record_impression.call_args
        self.assertEqual(kwargs["surface"], Surface.APP_PAGE)

    def test_capture_failure_is_caught_counted_and_returns_none(self):
        with mock.patch.object(emission, "capture") as fake_capture:
            fake_capture.record_impression.side_effect = RuntimeError("signals down")
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                result = emission.record_page_view(_request(authenticated=True), uuid4())

        self.assertIsNone(result)  # no exception propagated
        self.assertTrue(
            any(observability.APP_PAGE_CAPTURE_DEGRADED in line for line in logs.output)
        )


class RecordTryClickTests(SimpleTestCase):
    def test_valid_impression_records_click_through_linked(self):
        app_id = uuid4()
        impression = SimpleNamespace(id=uuid4())
        with mock.patch.object(emission, "capture") as fake_capture, mock.patch.object(
            emission, "_resolve_impression", return_value=impression
        ):
            emission.record_try_click(_request(authenticated=True), app_id, impression.id)

        _, kwargs = fake_capture.record_click_through.call_args
        self.assertIs(kwargs["impression"], impression)

    def test_missing_impression_records_no_event(self):
        with mock.patch.object(emission, "capture") as fake_capture, mock.patch.object(
            emission, "_resolve_impression", return_value=None
        ):
            emission.record_try_click(_request(authenticated=True), uuid4(), None)
        fake_capture.record_click_through.assert_not_called()

    def test_mismatched_impression_is_caught_no_raise(self):
        with mock.patch.object(emission, "capture") as fake_capture, mock.patch.object(
            emission, "_resolve_impression", return_value=SimpleNamespace(id=uuid4())
        ):
            fake_capture.record_click_through.side_effect = ImpressionMismatchError("forged")
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                emission.record_try_click(_request(authenticated=True), uuid4(), uuid4())

        self.assertTrue(
            any(observability.APP_PAGE_CAPTURE_DEGRADED in line for line in logs.output)
        )

    def test_anonymous_records_no_event(self):
        with mock.patch.object(emission, "capture") as fake_capture:
            emission.record_try_click(_request(authenticated=False), uuid4(), uuid4())
        fake_capture.record_click_through.assert_not_called()


class RecordShareTests(SimpleTestCase):
    def test_authenticated_records_share_with_optional_impression(self):
        app_id = uuid4()
        with mock.patch.object(emission, "capture") as fake_capture, mock.patch.object(
            emission, "_resolve_impression", return_value=None
        ):
            emission.record_share(_request(authenticated=True), app_id, None)
        _, kwargs = fake_capture.record_share.call_args
        self.assertIsNone(kwargs["impression"])

    def test_anonymous_records_no_event(self):
        with mock.patch.object(emission, "capture") as fake_capture:
            emission.record_share(_request(authenticated=False), uuid4(), uuid4())
        fake_capture.record_share.assert_not_called()

    def test_capture_failure_is_caught_no_raise(self):
        with mock.patch.object(emission, "capture") as fake_capture, mock.patch.object(
            emission, "_resolve_impression", return_value=None
        ):
            fake_capture.record_share.side_effect = RuntimeError("signals down")
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                emission.record_share(_request(authenticated=True), uuid4(), None)
        self.assertTrue(
            any(observability.APP_PAGE_CAPTURE_DEGRADED in line for line in logs.output)
        )
