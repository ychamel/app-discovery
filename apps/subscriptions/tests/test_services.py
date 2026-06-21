"""T-03 — the single write path (DESIGN §5a/§6.1), tested against the real catalog + the
real ``signals.capture`` (capture is patched only to force the failure case).

Covers AC1 (follow creates a row + exactly one subscribe event; idempotent re-follow),
AC3 (unfollow hard-delete, idempotent, no event), AC5/AC7 (the atomic follow+emit; capture
failure rolls the follow back), and AC9 (the corpus SC-10 half — events anonymized while
follow rows CASCADE away).
"""

from unittest import mock
from uuid import uuid4

from django.test import TestCase

from apps.accounts.services import delete_account
from apps.signals.kinds import EventKind
from apps.signals.models import EngagementEvent
from apps.subscriptions import services
from apps.subscriptions.errors import UnknownAppError
from apps.subscriptions.models import Subscription
from apps.subscriptions.tests.helpers import make_accepted_app, make_tag, make_user


def _subscribe_events(user=None, app_id=None):
    qs = EngagementEvent.objects.filter(kind=EventKind.SUBSCRIBE)
    if user is not None:
        qs = qs.filter(user=user)
    if app_id is not None:
        qs = qs.filter(app_id=app_id)
    return qs


class FollowAppTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    # --- AC1 --------------------------------------------------------------
    def test_follow_creates_one_row_and_exactly_one_subscribe_event(self):
        self.assertTrue(services.follow_app(self.user, self.app.id))

        rows = Subscription.objects.filter(user=self.user, app_id=self.app.id)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(_subscribe_events(self.user, self.app.id).count(), 1)

    def test_re_follow_of_a_current_follow_is_a_noop(self):
        self.assertTrue(services.follow_app(self.user, self.app.id))
        self.assertFalse(services.follow_app(self.user, self.app.id))

        self.assertEqual(Subscription.objects.count(), 1)
        # No second corpus event for an idempotent re-follow.
        self.assertEqual(_subscribe_events(self.user, self.app.id).count(), 1)

    def test_re_follow_after_unfollow_is_a_genuine_new_event(self):
        services.follow_app(self.user, self.app.id)
        services.unfollow_app(self.user, self.app.id)
        self.assertTrue(services.follow_app(self.user, self.app.id))

        # Each act of following is its own append-only corpus fact (D-7) — two events,
        # one current row.
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(_subscribe_events(self.user, self.app.id).count(), 2)

    def test_unknown_app_raises_and_stores_nothing(self):
        with self.assertRaises(UnknownAppError):
            services.follow_app(self.user, uuid4())
        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(_subscribe_events().count(), 0)

    def test_non_accepted_app_raises(self):
        from apps.catalog import services as catalog_services

        pending = catalog_services.submit_app(
            self.owner,
            name="Pending App",
            description="not yet accepted",
            url="https://example.com/pending",
            tag_ids=[make_tag("draft").id],
            media=[_png()],
        )
        with self.assertRaises(UnknownAppError):
            services.follow_app(self.user, pending.id)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_catalog_read_that_raises_propagates_loud(self):
        # DESIGN §8: a follow has no subject if the catalog read itself fails — propagate.
        with mock.patch(
            "apps.subscriptions.services.catalog.get_catalogued_app",
            side_effect=RuntimeError("db down"),
        ):
            with self.assertRaises(RuntimeError):
                services.follow_app(self.user, self.app.id)
        self.assertEqual(Subscription.objects.count(), 0)

    # --- AC5 / AC7 — the atomic coupling ---------------------------------
    def test_capture_failure_rolls_back_the_follow(self):
        # With record_subscribe forced to raise, the follow row must NOT persist (the
        # get_or_create rolled back inside the same transaction) — durable state is
        # not-followed (AC7), and signals' _guard counted CAPTURE_ERROR.
        with mock.patch(
            "apps.subscriptions.services.signals_capture.record_subscribe",
            side_effect=RuntimeError("capture blew up"),
        ):
            with self.assertRaises(RuntimeError):
                services.follow_app(self.user, self.app.id)

        self.assertEqual(Subscription.objects.count(), 0)
        self.assertEqual(_subscribe_events().count(), 0)

    def test_capture_failure_increments_capture_error(self):
        # Drive the *real* recorder into its fail-loud _guard by failing the event write — the
        # guard counts CAPTURE_ERROR{kind=subscribe} before re-raising, and follow_app's outer
        # transaction rolls the follow row back (AC5/AC7).
        from apps.core import observability

        with (
            mock.patch("apps.signals.capture.observability.increment") as increment,
            mock.patch(
                "apps.signals.capture.EngagementEvent.objects.create",
                side_effect=RuntimeError("write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                services.follow_app(self.user, self.app.id)

        increment.assert_any_call(
            observability.CAPTURE_ERROR, kind="subscribe", error="RuntimeError"
        )
        self.assertEqual(Subscription.objects.count(), 0)


class UnfollowAppTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    # --- AC3 --------------------------------------------------------------
    def test_unfollow_deletes_the_row_emits_no_event_and_reports_existed(self):
        services.follow_app(self.user, self.app.id)
        before = _subscribe_events().count()

        self.assertTrue(services.unfollow_app(self.user, self.app.id))

        self.assertEqual(Subscription.objects.count(), 0)
        # No corpus event on unfollow (OQ-3 = no D-7 unfollow kind).
        self.assertEqual(_subscribe_events().count(), before)

    def test_unfollow_when_absent_is_a_noop(self):
        self.assertFalse(services.unfollow_app(self.user, self.app.id))

    def test_unfollow_only_touches_the_callers_row(self):
        other = make_user("other@example.com")
        services.follow_app(self.user, self.app.id)
        services.follow_app(other, self.app.id)

        services.unfollow_app(self.user, self.app.id)

        self.assertEqual(Subscription.objects.count(), 1)
        self.assertTrue(Subscription.objects.filter(user=other).exists())


class AccountDeletionCorpusTests(TestCase):
    """AC9 (the two-owner split) — follow rows CASCADE away; subscribe events anonymize (SC-10)."""

    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    def test_deletion_removes_follows_but_anonymizes_the_subscribe_events(self):
        services.follow_app(self.user, self.app.id)
        user_id = self.user.pk
        self.assertEqual(_subscribe_events(app_id=self.app.id).count(), 1)

        delete_account(self.user)

        # Follow state is gone (CASCADE)…
        self.assertFalse(Subscription.objects.filter(user_id=user_id).exists())
        # …while the already-emitted subscribe event is retained but unlinked (SET_NULL/SC-10).
        event = _subscribe_events(app_id=self.app.id).get()
        self.assertIsNone(event.user_id)


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(10, 10, 10)).save(buffer, format="PNG")
    return SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
