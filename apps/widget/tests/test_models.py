"""T-01 — the ``widget_reach_count`` table shape (DESIGN §6, EUW-8/EUW-9).

Covers the durable contract the attribution writer and dashboard reader build on: every column
persists, ``kind`` is constrained to the two ``WidgetEventKind`` values, the table name and the
backing index/constraint match the design, the unique constraint enforces one row per
``(app_id, kind, count_date)`` (the create-race retry hinge), and — locking the AC6/AC10
posture — the model has **no** ``user``/IP/referrer/score field (over-collection is structurally
unrepresentable).
"""

import datetime
import uuid

from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from apps.widget.kinds import WidgetConversionKind, WidgetEventKind
from apps.widget.models import WidgetConversionCount, WidgetReachCount


class WidgetReachCountModelTests(TestCase):
    def setUp(self):
        self.app_id = uuid.uuid4()
        self.today = datetime.date(2026, 6, 26)

    def _make(self, **overrides) -> WidgetReachCount:
        fields = {
            "app_id": self.app_id,
            "kind": WidgetEventKind.IMPRESSION,
            "count_date": self.today,
            "count": 1,
        }
        fields.update(overrides)
        return WidgetReachCount.objects.create(**fields)

    def test_persists_all_fields(self):
        row = self._make(count=7)
        row.refresh_from_db()
        self.assertEqual(row.app_id, self.app_id)
        self.assertEqual(row.kind, "impression")
        self.assertEqual(row.count_date, self.today)
        self.assertEqual(row.count, 7)
        self.assertIsNotNone(row.created_at)
        self.assertIsNotNone(row.updated_at)
        self.assertIsInstance(row.id, uuid.UUID)

    def test_both_kinds_are_accepted(self):
        impression = self._make(kind=WidgetEventKind.IMPRESSION)
        click = self._make(kind=WidgetEventKind.CLICK_THROUGH)
        self.assertEqual(impression.kind, "impression")
        self.assertEqual(click.kind, "click_through")

    def test_kind_choices_are_exactly_the_two_pinned_values(self):
        self.assertEqual(
            [value for value, _label in WidgetEventKind.choices],
            ["impression", "click_through"],
        )

    def test_db_table_name(self):
        self.assertEqual(WidgetReachCount._meta.db_table, "widget_reach_count")

    def test_unique_constraint_rejects_a_second_row_for_the_same_app_kind_day(self):
        self._make()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make()

    def test_different_kind_or_day_or_app_is_a_separate_row(self):
        self._make()
        # Same app+day, other kind — allowed.
        self._make(kind=WidgetEventKind.CLICK_THROUGH)
        # Same app+kind, other day — allowed.
        self._make(count_date=datetime.date(2026, 6, 27))
        # Other app, same kind+day — allowed.
        self._make(app_id=uuid.uuid4())
        self.assertEqual(WidgetReachCount.objects.count(), 4)

    def test_reach_index_is_present(self):
        index_names = {index.name for index in WidgetReachCount._meta.indexes}
        self.assertIn("widget_reach_app_kind_date_idx", index_names)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, "widget_reach_count"
            )
        self.assertIn("widget_reach_app_kind_date_idx", constraints)

    def test_no_actor_or_pii_or_score_field_exists(self):
        """The AC6/AC10 posture is structural — these columns must never exist (DESIGN §6)."""
        field_names = {field.name for field in WidgetReachCount._meta.get_fields()}
        forbidden = {
            "user",
            "actor",
            "ip",
            "ip_address",
            "user_agent",
            "ua",
            "referrer",
            "geo",
            "device",
            "score",
            "weight",
            "rank",
        }
        self.assertEqual(field_names & forbidden, set())

    def test_fields_are_exactly_the_designed_set(self):
        field_names = {field.name for field in WidgetReachCount._meta.get_fields()}
        self.assertEqual(
            field_names,
            {"id", "app_id", "kind", "count_date", "count", "created_at", "updated_at"},
        )


class WidgetConversionCountModelTests(TestCase):
    """T-02 — the ``widget_conversion_count`` table shape (DESIGN §6.1).

    The conversion-side sibling of the reach table: same durable contract, separate table. Locks
    the AC4 no-PII + AC6 firewall posture **structurally** — there is no person column and no
    score column for a conversion row to carry (M5 = 0 by absence)."""

    def setUp(self):
        self.app_id = uuid.uuid4()
        self.today = datetime.date(2026, 6, 26)

    def _make(self, **overrides) -> WidgetConversionCount:
        fields = {
            "app_id": self.app_id,
            "kind": WidgetConversionKind.FOLLOW,
            "count_date": self.today,
            "count": 1,
        }
        fields.update(overrides)
        return WidgetConversionCount.objects.create(**fields)

    def test_persists_all_fields(self):
        row = self._make(count=4)
        row.refresh_from_db()
        self.assertEqual(row.app_id, self.app_id)
        self.assertEqual(row.kind, "follow")
        self.assertEqual(row.count_date, self.today)
        self.assertEqual(row.count, 4)
        self.assertIsNotNone(row.created_at)
        self.assertIsNotNone(row.updated_at)
        self.assertIsInstance(row.id, uuid.UUID)

    def test_both_kinds_are_accepted(self):
        follow = self._make(kind=WidgetConversionKind.FOLLOW)
        account = self._make(kind=WidgetConversionKind.ACCOUNT)
        self.assertEqual(follow.kind, "follow")
        self.assertEqual(account.kind, "account")

    def test_kind_choices_are_exactly_the_two_pinned_values(self):
        self.assertEqual(
            [value for value, _label in WidgetConversionKind.choices],
            ["follow", "account"],
        )

    def test_db_table_name(self):
        self.assertEqual(
            WidgetConversionCount._meta.db_table, "widget_conversion_count"
        )

    def test_unique_constraint_rejects_a_second_row_for_the_same_app_kind_day(self):
        self._make()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make()

    def test_different_kind_or_day_or_app_is_a_separate_row(self):
        self._make()
        self._make(kind=WidgetConversionKind.ACCOUNT)  # same app+day, other kind
        self._make(count_date=datetime.date(2026, 6, 27))  # same app+kind, other day
        self._make(app_id=uuid.uuid4())  # other app, same kind+day
        self.assertEqual(WidgetConversionCount.objects.count(), 4)

    def test_conversion_index_is_present(self):
        index_names = {index.name for index in WidgetConversionCount._meta.indexes}
        self.assertIn("widget_conv_app_kind_date_idx", index_names)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, "widget_conversion_count"
            )
        self.assertIn("widget_conv_app_kind_date_idx", constraints)

    def test_no_actor_or_pii_or_score_field_exists(self):
        """The AC4 (no-PII) + AC6 (firewall) posture is structural — these columns must never
        exist, so M5 = 0 and the score can read nothing (DESIGN §6.1)."""
        field_names = {field.name for field in WidgetConversionCount._meta.get_fields()}
        forbidden = {
            "user",
            "actor",
            "ip",
            "ip_address",
            "user_agent",
            "ua",
            "referrer",
            "geo",
            "device",
            "score",
            "weight",
            "rank",
        }
        self.assertEqual(field_names & forbidden, set())

    def test_fields_are_exactly_the_designed_set(self):
        field_names = {field.name for field in WidgetConversionCount._meta.get_fields()}
        self.assertEqual(
            field_names,
            {"id", "app_id", "kind", "count_date", "count", "created_at", "updated_at"},
        )
