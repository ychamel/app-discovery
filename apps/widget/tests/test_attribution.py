"""T-02 — the single writer (DESIGN §5.2/§6) + the AC6 firewall integration proof (the risk).

Two concerns, both load-bearing:

  * **Write correctness under concurrency.** The atomic ``F("count") + 1`` increment lands on
    today's ``(app_id, kind)`` rollup row, and the unique-constraint create-race is resolved by
    a caught retry (not a lost update or a duplicate row).
  * **The firewall (AC6 / M5 = 0), structurally.** A widget impression + click-through writes
    **zero** ``signals`` corpus rows and leaves ``has_impression(surfaces=CURATED_SURFACES)``
    False — a widget interaction is not, and cannot become, curated-rating evidence (the AST
    proof in ``test_imports.py`` is complemented here by a behavioural one).
"""

import uuid
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.ratings.gate import CURATED_SURFACES
from apps.signals.models import EngagementEvent, Impression
from apps.signals.selectors import has_impression
from apps.widget import attribution, rollup
from apps.widget.kinds import WidgetConversionKind, WidgetEventKind
from apps.widget.models import WidgetConversionCount, WidgetReachCount


class RecordImpressionTests(TestCase):
    def setUp(self):
        self.app_id = uuid.uuid4()
        self.today = timezone.now().date()

    def _row(self, kind=WidgetEventKind.IMPRESSION) -> WidgetReachCount:
        return WidgetReachCount.objects.get(
            app_id=self.app_id, kind=kind, count_date=self.today
        )

    def test_first_impression_creates_todays_row_with_count_one(self):
        attribution.record_widget_impression(self.app_id)
        row = self._row()
        self.assertEqual(row.count, 1)
        self.assertEqual(row.count_date, self.today)

    def test_subsequent_impressions_increment_the_same_row(self):
        for _ in range(4):
            attribution.record_widget_impression(self.app_id)
        self.assertEqual(
            WidgetReachCount.objects.filter(
                app_id=self.app_id, kind=WidgetEventKind.IMPRESSION
            ).count(),
            1,
        )
        self.assertEqual(self._row().count, 4)

    def test_impression_and_click_through_are_separate_rows(self):
        attribution.record_widget_impression(self.app_id)
        attribution.record_widget_click_through(self.app_id)
        self.assertEqual(self._row(WidgetEventKind.IMPRESSION).count, 1)
        self.assertEqual(self._row(WidgetEventKind.CLICK_THROUGH).count, 1)

    def test_a_different_app_is_a_separate_row(self):
        other = uuid.uuid4()
        attribution.record_widget_impression(self.app_id)
        attribution.record_widget_impression(other)
        self.assertEqual(self._row().count, 1)
        self.assertEqual(
            WidgetReachCount.objects.get(
                app_id=other, kind=WidgetEventKind.IMPRESSION, count_date=self.today
            ).count,
            1,
        )

    def test_create_race_falls_back_to_an_atomic_increment(self):
        """The IntegrityError branch (DESIGN §6): a row that appears between filter and create.

        We force the writer to *think* no row exists (the first existence-increment misses),
        let ``create`` hit the real unique constraint on the pre-seeded row, and assert the
        caught retry increments the existing row rather than raising or duplicating.
        """
        WidgetReachCount.objects.create(
            app_id=self.app_id,
            kind=WidgetEventKind.IMPRESSION,
            count_date=self.today,
            count=5,
        )
        real_increment = rollup._increment_existing_row
        calls = {"n": 0}

        def miss_then_real(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return False  # pretend the row was not there at filter time (the race)
            return real_increment(*args, **kwargs)

        with mock.patch.object(
            rollup, "_increment_existing_row", side_effect=miss_then_real
        ):
            attribution.record_widget_impression(self.app_id)

        self.assertEqual(
            WidgetReachCount.objects.filter(
                app_id=self.app_id, kind=WidgetEventKind.IMPRESSION
            ).count(),
            1,
        )
        self.assertEqual(self._row().count, 6)  # 5 seeded + 1 from the retried increment


class RecordConversionTests(TestCase):
    """T-03 — the single conversion writer ``record_widget_conversion`` (DESIGN §5.4)."""

    def setUp(self):
        self.app_id = uuid.uuid4()
        self.today = timezone.now().date()

    def _row(self, kind=WidgetConversionKind.FOLLOW) -> WidgetConversionCount:
        return WidgetConversionCount.objects.get(
            app_id=self.app_id, kind=kind, count_date=self.today
        )

    def test_first_conversion_creates_todays_row_with_count_one(self):
        attribution.record_widget_conversion(self.app_id, WidgetConversionKind.FOLLOW)
        row = self._row()
        self.assertEqual(row.count, 1)
        self.assertEqual(row.count_date, self.today)

    def test_subsequent_conversions_increment_the_same_row(self):
        for _ in range(3):
            attribution.record_widget_conversion(
                self.app_id, WidgetConversionKind.ACCOUNT
            )
        self.assertEqual(
            WidgetConversionCount.objects.filter(
                app_id=self.app_id, kind=WidgetConversionKind.ACCOUNT
            ).count(),
            1,
        )
        self.assertEqual(self._row(WidgetConversionKind.ACCOUNT).count, 3)

    def test_follow_and_account_are_separate_rows(self):
        attribution.record_widget_conversion(self.app_id, WidgetConversionKind.FOLLOW)
        attribution.record_widget_conversion(self.app_id, WidgetConversionKind.ACCOUNT)
        self.assertEqual(self._row(WidgetConversionKind.FOLLOW).count, 1)
        self.assertEqual(self._row(WidgetConversionKind.ACCOUNT).count, 1)

    def test_db_error_propagates_not_swallowed(self):
        """A DB write failure must raise to the caller (the fail-soft hook wraps it, not here)."""
        # Patch where the name is bound: attribution imports `_increment_daily` by name.
        with mock.patch.object(
            attribution, "_increment_daily", side_effect=RuntimeError("db down")
        ):
            with self.assertRaises(RuntimeError):
                attribution.record_widget_conversion(
                    self.app_id, WidgetConversionKind.FOLLOW
                )


class FirewallTests(TestCase):
    """AC6 / M5 = 0 — a widget interaction/conversion never enters the D-7 corpus (DESIGN §3/§9)."""

    def setUp(self):
        self.app_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_recording_widget_reach_writes_no_signals_rows(self):
        attribution.record_widget_impression(self.app_id)
        attribution.record_widget_click_through(self.app_id)
        self.assertEqual(Impression.objects.count(), 0)
        self.assertEqual(EngagementEvent.objects.count(), 0)

    def test_recording_a_conversion_writes_no_signals_rows(self):
        attribution.record_widget_conversion(self.app_id, WidgetConversionKind.FOLLOW)
        attribution.record_widget_conversion(self.app_id, WidgetConversionKind.ACCOUNT)
        self.assertEqual(Impression.objects.count(), 0)
        self.assertEqual(EngagementEvent.objects.count(), 0)

    def test_widget_reach_is_not_curated_surface_evidence(self):
        attribution.record_widget_impression(self.app_id)
        attribution.record_widget_click_through(self.app_id)
        self.assertFalse(
            has_impression(self.user_id, self.app_id, surfaces=CURATED_SURFACES)
        )
