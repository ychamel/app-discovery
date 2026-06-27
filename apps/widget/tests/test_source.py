"""T-04 — the widget source-marker codec + credit logic (DESIGN §3/§5.1/§8).

Each behaviour is exercised in isolation (DESIGN §12, "each module in isolation"): the marker
round-trips; a tampered / expired / version-skewed / wrong-app marker is a normal "no source"
no-op with the right ops counter (never an error, never a fabricated credit — AC2); a genuine
credit writes exactly one conversion, dedups per marker (R4), re-issues the cookie with the
*remaining* window (DESIGN §3.4), and lets a writer DB error propagate (the view hook wraps it
fail-soft, not this layer). The signed payload carries no person field (AC4).
"""

import time
from unittest import mock

from django.core import signing
from django.test import RequestFactory, TestCase

from apps.widget import source
from apps.widget.kinds import WidgetConversionKind
from apps.widget.models import WidgetConversionCount


def _request_with_marker(value: str | None) -> "RequestFactory":
    request = RequestFactory().get("/")
    if value is not None:
        request.COOKIES[source.COOKIE_NAME] = value
    return request


def _new_response():
    from django.http import HttpResponse

    return HttpResponse()


def _sign(payload: dict, *, signed_seconds_ago: int = 0) -> str:
    """Sign ``payload`` as the codec would, optionally backdating the signer timestamp."""
    if signed_seconds_ago:
        past = time.time() - signed_seconds_ago
        with mock.patch("time.time", return_value=past):
            return signing.dumps(payload, salt=source._SALT)
    return signing.dumps(payload, salt=source._SALT)


def _valid_payload(src: str, credited=None) -> dict:
    return {"v": source._VERSION, "src": src, "credited": credited or []}


SRC = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"


class SetMarkerTests(TestCase):
    def test_round_trip_sets_a_cookie_that_decodes_to_the_source(self):
        response = _new_response()
        source.set_marker(response, SRC)
        raw = response.cookies[source.COOKIE_NAME].value
        payload = signing.loads(raw, salt=source._SALT, max_age=source._window_seconds())
        self.assertEqual(payload["src"], SRC)
        self.assertEqual(payload["credited"], [])
        self.assertEqual(payload["v"], source._VERSION)

    def test_payload_carries_no_person_field(self):
        response = _new_response()
        source.set_marker(response, SRC)
        raw = response.cookies[source.COOKIE_NAME].value
        payload = signing.loads(raw, salt=source._SALT, max_age=source._window_seconds())
        self.assertEqual(set(payload), {"v", "src", "credited"})  # AC4 — nothing person-linked

    def test_cookie_attributes_match_the_design(self):
        from django.conf import settings

        response = _new_response()
        source.set_marker(response, SRC)
        morsel = response.cookies[source.COOKIE_NAME]
        self.assertEqual(morsel["samesite"], "Lax")
        self.assertTrue(morsel["httponly"])
        self.assertEqual(morsel["path"], "/")
        self.assertEqual(bool(morsel["secure"]), settings.SESSION_COOKIE_SECURE)
        self.assertEqual(int(morsel["max-age"]), source._window_seconds())

    def test_a_second_click_overwrites_the_marker_last_touch(self):
        response = _new_response()
        source.set_marker(response, SRC)
        source.set_marker(response, OTHER)
        raw = response.cookies[source.COOKIE_NAME].value
        payload = signing.loads(raw, salt=source._SALT, max_age=source._window_seconds())
        self.assertEqual(payload["src"], OTHER)


class AttributeFollowTests(TestCase):
    def _rows(self, kind=WidgetConversionKind.FOLLOW) -> int:
        return WidgetConversionCount.objects.filter(app_id=SRC, kind=kind).count()

    def test_no_marker_is_a_no_source_no_op(self):
        request = _request_with_marker(None)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        inc.assert_called_once_with(source.WIDGET_CONVERSION_NO_SOURCE)
        self.assertEqual(self._rows(), 0)

    def test_tampered_marker_is_a_no_source_no_op(self):
        raw = _sign(_valid_payload(SRC))
        tampered = raw[:-2] + ("aa" if not raw.endswith("aa") else "bb")
        request = _request_with_marker(tampered)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        inc.assert_called_once_with(source.WIDGET_CONVERSION_NO_SOURCE)
        self.assertEqual(self._rows(), 0)

    def test_expired_marker_is_not_credited(self):
        # Signed older than the window -> signing rejects it as expired (AC2: no fabrication).
        raw = _sign(_valid_payload(SRC), signed_seconds_ago=source._window_seconds() + 60)
        request = _request_with_marker(raw)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        inc.assert_called_once_with(source.WIDGET_CONVERSION_EXPIRED)
        self.assertEqual(self._rows(), 0)

    def test_version_skew_is_a_no_source_no_op(self):
        raw = _sign({"v": 2, "src": SRC, "credited": []})  # unknown future version
        request = _request_with_marker(raw)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        inc.assert_called_once_with(source.WIDGET_CONVERSION_NO_SOURCE)
        self.assertEqual(self._rows(), 0)

    def test_app_mismatch_is_not_credited(self):
        # Marker is for OTHER; the visitor follows SRC -> no applicable widget source for SRC.
        raw = _sign(_valid_payload(OTHER))
        request = _request_with_marker(raw)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        inc.assert_called_once_with(source.WIDGET_CONVERSION_NO_SOURCE)
        self.assertEqual(self._rows(), 0)

    def test_matching_marker_credits_one_follow(self):
        raw = _sign(_valid_payload(SRC))
        request = _request_with_marker(raw)
        response = _new_response()
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(request, response, followed_app_id=SRC)
        self.assertEqual(self._rows(), 1)
        self.assertEqual(
            WidgetConversionCount.objects.get(
                app_id=SRC, kind=WidgetConversionKind.FOLLOW
            ).count,
            1,
        )
        inc.assert_called_once_with(
            source.WIDGET_CONVERSION_ATTRIBUTED, kind=WidgetConversionKind.FOLLOW
        )

    def test_re_follow_in_the_same_browser_is_deduped(self):
        # First credit re-issues the cookie with FOLLOW in `credited`; feeding that back in is a
        # silent per-marker dedup no-op (R4) — the count stays 1 and nothing new is recorded.
        raw = _sign(_valid_payload(SRC))
        response = _new_response()
        source.attribute_follow(
            _request_with_marker(raw), response, followed_app_id=SRC
        )
        reissued = response.cookies[source.COOKIE_NAME].value
        with mock.patch.object(source, "increment") as inc:
            source.attribute_follow(
                _request_with_marker(reissued), _new_response(), followed_app_id=SRC
            )
        inc.assert_not_called()  # dedup is silent — not a coverage miss
        self.assertEqual(self._rows(), 1)

    def test_credit_re_issues_cookie_with_the_remaining_window(self):
        age = 10 * 86400  # signed 10 days ago
        raw = _sign(_valid_payload(SRC), signed_seconds_ago=age)
        response = _new_response()
        source.attribute_follow(
            _request_with_marker(raw), response, followed_app_id=SRC
        )
        reissued_max_age = int(response.cookies[source.COOKIE_NAME]["max-age"])
        expected_remaining = source._window_seconds() - age
        # Anchored to the original click, not reset to a full window.
        self.assertAlmostEqual(reissued_max_age, expected_remaining, delta=5)
        self.assertLess(reissued_max_age, source._window_seconds())

    def test_writer_db_error_propagates(self):
        raw = _sign(_valid_payload(SRC))
        request = _request_with_marker(raw)
        with mock.patch.object(
            source, "record_widget_conversion", side_effect=RuntimeError("db down")
        ):
            with self.assertRaises(RuntimeError):
                source.attribute_follow(request, _new_response(), followed_app_id=SRC)


class AttributeAccountTests(TestCase):
    def _account_rows(self) -> int:
        return WidgetConversionCount.objects.filter(
            app_id=SRC, kind=WidgetConversionKind.ACCOUNT
        ).count()

    def test_live_marker_credits_one_account_to_its_source(self):
        raw = _sign(_valid_payload(SRC))
        request = _request_with_marker(raw)
        source.attribute_account(request, _new_response())
        self.assertEqual(self._account_rows(), 1)

    def test_account_is_creditable_even_when_follow_already_credited(self):
        # `credited=[follow]` must not block the independent ACCOUNT credit (distinct counts).
        raw = _sign(_valid_payload(SRC, credited=[WidgetConversionKind.FOLLOW]))
        request = _request_with_marker(raw)
        source.attribute_account(request, _new_response())
        self.assertEqual(self._account_rows(), 1)

    def test_no_marker_is_a_no_source_no_op(self):
        with mock.patch.object(source, "increment") as inc:
            source.attribute_account(_request_with_marker(None), _new_response())
        inc.assert_called_once_with(source.WIDGET_CONVERSION_NO_SOURCE)
        self.assertEqual(self._account_rows(), 0)

    def test_already_credited_account_is_a_silent_no_op(self):
        raw = _sign(_valid_payload(SRC, credited=[WidgetConversionKind.ACCOUNT]))
        with mock.patch.object(source, "increment") as inc:
            source.attribute_account(_request_with_marker(raw), _new_response())
        inc.assert_not_called()
        self.assertEqual(self._account_rows(), 0)
