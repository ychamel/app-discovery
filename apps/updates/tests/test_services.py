"""T-03 — the single write path (DESIGN §6.2/§5.3/§7).

Covers AC1 (owner gate), AC2/AC3 (kind/length validation + post), AC8 (durable per-author,
per-app rate-limit), and AC7 (scoped, idempotent withdraw) — all at the service layer with the
real ORM and seeded catalog apps (no HTTP). Counters and config-drivenness are asserted on
their paths.
"""

from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core import observability
from apps.updates import services
from apps.updates.errors import (
    AppNotOwnedError,
    InvalidNoticeError,
    RateLimitedError,
)
from apps.updates.models import Notice
from apps.updates.selectors import PublishedNotice
from apps.updates.tests.helpers import make_accepted_app, make_developer, make_tag


class PostNoticeOwnerGateTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.app = make_accepted_app(self.dev, tag_ids=[make_tag("notes").id])

    def test_posting_to_an_unowned_app_raises_and_writes_nothing(self):
        intruder = make_developer("intruder@example.com")
        with self.assertRaises(AppNotOwnedError):
            services.post_notice(
                intruder, self.app.id, kind="update", title="Hi", summary="There"
            )
        self.assertEqual(Notice.objects.count(), 0)

    def test_posting_to_an_unknown_app_raises(self):
        import uuid

        with self.assertRaises(AppNotOwnedError):
            services.post_notice(
                self.dev, uuid.uuid4(), kind="update", title="Hi", summary="There"
            )


class PostNoticeValidationTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.app = make_accepted_app(self.dev, tag_ids=[make_tag("notes").id])

    def _post(self, **overrides):
        fields = {"kind": "update", "title": "A title", "summary": "A summary"}
        fields.update(overrides)
        return services.post_notice(self.dev, self.app.id, **fields)

    def test_valid_update_creates_one_row(self):
        result = self._post(kind="update")
        self.assertIsInstance(result, PublishedNotice)
        self.assertEqual(Notice.objects.count(), 1)
        self.assertEqual(Notice.objects.get().kind, "update")

    def test_valid_early_access_creates_one_row(self):
        self._post(kind="early_access")
        self.assertEqual(Notice.objects.get().kind, "early_access")

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(InvalidNoticeError):
            self._post(kind="announcement")
        self.assertEqual(Notice.objects.count(), 0)

    def test_blank_title_is_rejected(self):
        with self.assertRaises(InvalidNoticeError):
            self._post(title="   ")
        self.assertEqual(Notice.objects.count(), 0)

    def test_blank_summary_is_rejected(self):
        with self.assertRaises(InvalidNoticeError):
            self._post(summary="")
        self.assertEqual(Notice.objects.count(), 0)

    def test_title_and_summary_are_stripped_before_store(self):
        self._post(title="  Trimmed  ", summary="  Body  ")
        notice = Notice.objects.get()
        self.assertEqual(notice.title, "Trimmed")
        self.assertEqual(notice.summary, "Body")

    @override_settings(UPDATES_TITLE_MAX_LENGTH=10)
    def test_over_length_title_is_rejected_at_the_boundary(self):
        with self.assertRaises(InvalidNoticeError):
            self._post(title="x" * 11)
        self.assertEqual(Notice.objects.count(), 0)

    @override_settings(UPDATES_TITLE_MAX_LENGTH=10)
    def test_title_exactly_at_the_cap_is_accepted(self):
        self._post(title="x" * 10)
        self.assertEqual(Notice.objects.count(), 1)

    @override_settings(UPDATES_SUMMARY_MAX_LENGTH=10)
    def test_over_length_summary_is_rejected(self):
        with self.assertRaises(InvalidNoticeError):
            self._post(summary="y" * 11)
        self.assertEqual(Notice.objects.count(), 0)

    def test_reject_counts_post_rejected_invalid(self):
        with mock.patch.object(observability, "increment") as increment:
            with self.assertRaises(InvalidNoticeError):
                self._post(kind="bogus")
        increment.assert_any_call(
            observability.UPDATES_POST_REJECTED, reason="invalid"
        )

    def test_post_counts_notice_posted_with_kind(self):
        with mock.patch.object(observability, "increment") as increment:
            self._post(kind="early_access")
        increment.assert_any_call(
            observability.UPDATES_NOTICE_POSTED, kind="early_access"
        )


@override_settings(UPDATES_MAX_POSTS_PER_WINDOW=2, UPDATES_POST_WINDOW_HOURS=24)
class PostNoticeRateLimitTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="App One")

    def _post(self, app=None, dev=None):
        return services.post_notice(
            dev or self.dev,
            (app or self.app).id,
            kind="update",
            title="Title",
            summary="Summary",
        )

    def test_limit_blocks_the_next_post_in_window(self):
        self._post()
        self._post()
        with self.assertRaises(RateLimitedError):
            self._post()
        self.assertEqual(Notice.objects.count(), 2)

    def test_rate_limit_counts_post_rejected_rate_limited(self):
        self._post()
        self._post()
        with mock.patch.object(observability, "increment") as increment:
            with self.assertRaises(RateLimitedError):
                self._post()
        increment.assert_any_call(
            observability.UPDATES_POST_REJECTED, reason="rate_limited"
        )

    def test_a_post_outside_the_window_succeeds(self):
        self._post()
        self._post()
        # Age both notices past the 24h window so the count resets.
        old = timezone.now() - timedelta(hours=25)
        Notice.objects.update(published_at=old)
        self._post()  # does not raise
        self.assertEqual(Notice.objects.count(), 3)

    def test_limit_is_per_app(self):
        self._post()
        self._post()
        second_app = make_accepted_app(self.dev, tag_ids=[self.tag.id], name="App Two")
        self._post(app=second_app)  # a different app is unaffected
        self.assertEqual(Notice.objects.filter(app_id=second_app.id).count(), 1)

    def test_limit_is_per_author(self):
        self._post()
        self._post()
        other = make_developer("other@example.com")
        other_app = make_accepted_app(other, tag_ids=[self.tag.id], name="Other App")
        services.post_notice(
            other, other_app.id, kind="update", title="T", summary="S"
        )  # a different author is unaffected
        self.assertEqual(Notice.objects.filter(author=other).count(), 1)


class WithdrawNoticeTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.dev, tag_ids=[self.tag.id])

    def _post(self):
        return services.post_notice(
            self.dev, self.app.id, kind="update", title="T", summary="S"
        )

    def test_withdraw_deletes_own_notice_and_returns_true(self):
        notice = self._post()
        self.assertTrue(services.withdraw_notice(self.dev, self.app.id, notice.id))
        self.assertFalse(Notice.objects.filter(id=notice.id).exists())

    def test_withdraw_unknown_id_is_a_noop_returning_false(self):
        import uuid

        self.assertFalse(
            services.withdraw_notice(self.dev, self.app.id, uuid.uuid4())
        )

    def test_withdraw_another_authors_notice_does_nothing(self):
        notice = self._post()
        intruder = make_developer("intruder@example.com")
        self.assertFalse(
            services.withdraw_notice(intruder, self.app.id, notice.id)
        )
        self.assertTrue(Notice.objects.filter(id=notice.id).exists())

    def test_withdraw_with_wrong_app_id_does_nothing(self):
        import uuid

        notice = self._post()
        self.assertFalse(
            services.withdraw_notice(self.dev, uuid.uuid4(), notice.id)
        )
        self.assertTrue(Notice.objects.filter(id=notice.id).exists())

    def test_withdraw_counts_notice_withdrawn_only_on_real_delete(self):
        notice = self._post()
        with mock.patch.object(observability, "increment") as increment:
            services.withdraw_notice(self.dev, self.app.id, notice.id)
        increment.assert_any_call(observability.UPDATES_NOTICE_WITHDRAWN)

        import uuid

        with mock.patch.object(observability, "increment") as increment:
            services.withdraw_notice(self.dev, self.app.id, uuid.uuid4())
        increment.assert_not_called()
