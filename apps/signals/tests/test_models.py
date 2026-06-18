"""T-03 — the four append-only tables and their structural guarantees (DESIGN.md §4).

These tests pin the schema D-7 depends on: UUID identities, the two unique constraints,
the ``is_proxy`` default, the indexes, the SET_NULL/CASCADE deletion semantics (SC-10),
and the two *structural* guarantees — no score/weight/rank column (AC9) and no IP/UA/
device/geo/referrer/free-text column (AC10 whitelist).
"""

import uuid
from datetime import date

from django.db import IntegrityError, connection
from django.test import TestCase
from django.utils import timezone

from apps.signals.kinds import EventKind, Surface
from apps.signals.models import (
    EngagementEvent,
    Impression,
    ImpressionTag,
    PlatformVisit,
)
from apps.signals.tests.helpers import make_user


class IdentityTests(TestCase):
    def test_all_four_models_have_uuid_primary_keys(self):
        user = make_user()
        impression = Impression.objects.create(
            user=user, app_id=uuid.uuid4(), surface=Surface.DIGEST,
            occurred_at=timezone.now(),
        )
        tag = ImpressionTag.objects.create(impression=impression, tag_id=uuid.uuid4())
        event = EngagementEvent.objects.create(
            kind=EventKind.CLICK_THROUGH, user=user, app_id=impression.app_id,
            impression=impression, occurred_at=timezone.now(),
        )
        visit = PlatformVisit.objects.create(user=user, visit_date=date.today())
        for obj in (impression, tag, event, visit):
            self.assertIsInstance(obj.pk, uuid.UUID)


class ConstraintTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.impression = Impression.objects.create(
            user=self.user, app_id=uuid.uuid4(), surface=Surface.DIGEST,
            occurred_at=timezone.now(),
        )

    def test_impression_tag_unique_per_impression(self):
        tag_id = uuid.uuid4()
        ImpressionTag.objects.create(impression=self.impression, tag_id=tag_id)
        with self.assertRaises(IntegrityError):
            ImpressionTag.objects.create(impression=self.impression, tag_id=tag_id)

    def test_platform_visit_unique_per_user_per_day(self):
        today = date.today()
        PlatformVisit.objects.create(user=self.user, visit_date=today)
        with self.assertRaises(IntegrityError):
            PlatformVisit.objects.create(user=self.user, visit_date=today)

    def test_is_proxy_defaults_false(self):
        event = EngagementEvent.objects.create(
            kind=EventKind.SHARE, user=self.user, app_id=uuid.uuid4(),
            occurred_at=timezone.now(),
        )
        self.assertFalse(event.is_proxy)


class IndexTests(TestCase):
    """The funnel-read indexes from DESIGN.md §4 exist (named exactly)."""

    def test_expected_indexes_present(self):
        index_names = set()
        for model in (Impression, EngagementEvent, ImpressionTag, PlatformVisit):
            with connection.cursor() as cursor:
                index_names.update(
                    connection.introspection.get_constraints(
                        cursor, model._meta.db_table
                    ).keys()
                )
        for expected in (
            "signals_imp_app_time_idx",
            "signals_evt_app_kind_idx",
            "signals_imptag_tagid_idx",
            "signals_visit_date_idx",
        ):
            self.assertIn(expected, index_names)


class DeletionSemanticsTests(TestCase):
    """SC-10: anonymize the event corpus (SET_NULL), purge the visit ticks (CASCADE)."""

    def test_account_deletion_set_nulls_impression_and_event_user(self):
        user = make_user()
        impression = Impression.objects.create(
            user=user, app_id=uuid.uuid4(), surface=Surface.DIGEST,
            occurred_at=timezone.now(),
        )
        event = EngagementEvent.objects.create(
            kind=EventKind.CLICK_THROUGH, user=user, app_id=impression.app_id,
            impression=impression, occurred_at=timezone.now(),
        )

        user.delete()

        impression.refresh_from_db()
        event.refresh_from_db()
        # The behavioral facts survive as anonymized corpus rows, unlinked from the person.
        self.assertIsNone(impression.user_id)
        self.assertIsNone(event.user_id)

    def test_account_deletion_cascades_platform_visits(self):
        user = make_user()
        PlatformVisit.objects.create(user=user, visit_date=date.today())

        user.delete()

        # An unlinked daily tick is pure noise → it goes with the account.
        self.assertEqual(PlatformVisit.objects.count(), 0)


class StructuralGuaranteeTests(TestCase):
    """The raw-only (AC9) and privacy-whitelist (AC10) guarantees are enforced by schema."""

    FORBIDDEN_SCORING = {"score", "weight", "rank", "normalized"}
    FORBIDDEN_PII = {
        "ip", "ip_address", "user_agent", "useragent", "device",
        "geo", "geolocation", "location", "referrer", "off_platform_id", "metadata",
    }

    def _field_names(self, model) -> set[str]:
        return {f.name for f in model._meta.get_fields()}

    def test_no_scoring_column_on_any_table(self):
        for model in (Impression, ImpressionTag, EngagementEvent, PlatformVisit):
            self.assertEqual(
                self._field_names(model) & self.FORBIDDEN_SCORING, set(),
                f"{model.__name__} must carry no score/weight/rank column (AC9).",
            )

    def test_no_pii_column_on_any_table(self):
        for model in (Impression, ImpressionTag, EngagementEvent, PlatformVisit):
            self.assertEqual(
                self._field_names(model) & self.FORBIDDEN_PII, set(),
                f"{model.__name__} must carry no IP/UA/geo/referrer/free-text column (AC10).",
            )


class SoftReferenceTests(TestCase):
    """app_id / tag_id are plain UUIDs, not DB FKs (decoupled soft refs — §13)."""

    def test_app_id_and_tag_id_are_not_foreign_keys(self):
        self.assertFalse(Impression._meta.get_field("app_id").is_relation)
        self.assertFalse(EngagementEvent._meta.get_field("app_id").is_relation)
        self.assertFalse(ImpressionTag._meta.get_field("tag_id").is_relation)
