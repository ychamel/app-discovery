"""T-03 — the shared daily-rollup increment ``rollup._increment_daily`` (DESIGN §6.2).

The concurrency-correct write extracted from the reach writer and now shared by both the reach
and conversion writers. These tests exercise it **directly against the conversion model** (the new
caller) so the extraction is proven behavior-preserving on a second model, including the
create-race retry that the unique constraint turns into a caught ``IntegrityError``.
"""

import uuid
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.widget import rollup
from apps.widget.kinds import WidgetConversionKind
from apps.widget.models import WidgetConversionCount


class IncrementDailyTests(TestCase):
    def setUp(self):
        self.app_id = uuid.uuid4()
        self.today = timezone.now().date()

    def _count(self, kind=WidgetConversionKind.FOLLOW) -> int:
        return WidgetConversionCount.objects.get(
            app_id=self.app_id, kind=kind, count_date=self.today
        ).count

    def test_first_increment_creates_todays_row_with_count_one(self):
        rollup._increment_daily(
            WidgetConversionCount, self.app_id, WidgetConversionKind.FOLLOW
        )
        self.assertEqual(self._count(), 1)

    def test_two_increments_land_on_one_row(self):
        rollup._increment_daily(
            WidgetConversionCount, self.app_id, WidgetConversionKind.FOLLOW
        )
        rollup._increment_daily(
            WidgetConversionCount, self.app_id, WidgetConversionKind.FOLLOW
        )
        self.assertEqual(
            WidgetConversionCount.objects.filter(
                app_id=self.app_id, kind=WidgetConversionKind.FOLLOW
            ).count(),
            1,
        )
        self.assertEqual(self._count(), 2)

    def test_create_race_falls_back_to_an_atomic_increment(self):
        """Two concurrent first-of-day conversions for the same (app, kind) end at count == 2.

        We pre-seed the row, force the first existence-increment to *miss* (simulating the race
        where the row appears between filter and create), let ``create`` hit the real unique
        constraint, and assert the caught retry increments rather than raising or duplicating.
        """
        WidgetConversionCount.objects.create(
            app_id=self.app_id,
            kind=WidgetConversionKind.FOLLOW,
            count_date=self.today,
            count=1,
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
            rollup._increment_daily(
                WidgetConversionCount, self.app_id, WidgetConversionKind.FOLLOW
            )

        self.assertEqual(
            WidgetConversionCount.objects.filter(
                app_id=self.app_id, kind=WidgetConversionKind.FOLLOW
            ).count(),
            1,
        )
        self.assertEqual(self._count(), 2)  # 1 seeded + 1 from the retried increment
