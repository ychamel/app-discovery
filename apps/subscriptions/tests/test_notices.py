"""The followed-apps notice seam (DESIGN §5d/§6.3), repointed to its producer at
developer-updates T-02.

The render ``Notice`` *shape* and the *call site* are still the stable contract (asserted
here); the *body* now delegates to ``apps.updates`` and maps ``PublishedNotice`` → ``Notice``.
The cross-package no-import-cycle proof lives with the producer
(``apps/updates/tests/test_seam.py``); here we assert the adapter's mapping behaviour.
"""

import dataclasses
import uuid
from uuid import uuid4

from django.test import SimpleTestCase, TestCase

from apps.subscriptions import notices
from apps.updates.models import Notice as NoticeModel
from apps.updates.models import NoticeKind


class NoticesForAppsTests(TestCase):
    def setUp(self):
        from apps.updates.tests.helpers import make_developer

        self.author = make_developer()
        self.app_id = uuid.uuid4()

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(notices.notices_for_apps([]), [])

    def test_returns_empty_when_no_notices_exist(self):
        self.assertEqual(notices.notices_for_apps([uuid4(), uuid4()]), [])

    def test_maps_producer_rows_to_render_notices(self):
        NoticeModel.objects.create(
            author=self.author,
            app_id=self.app_id,
            kind=NoticeKind.EARLY_ACCESS,
            title="Beta open",
            summary="Try it now.",
        )

        [notice] = notices.notices_for_apps([self.app_id])

        self.assertIsInstance(notice, notices.Notice)
        self.assertEqual(notice.app_id, self.app_id)
        self.assertEqual(notice.kind, "early_access")
        self.assertEqual(notice.title, "Beta open")
        self.assertEqual(notice.summary, "Try it now.")
        # The render Notice drops the producer's notice id (the feed has no use for it).
        self.assertFalse(hasattr(notice, "id"))


class NoticeShapeTests(SimpleTestCase):
    def test_notice_is_frozen(self):
        self.assertTrue(dataclasses.fields(notices.Notice))  # is a dataclass
        params = notices.Notice.__dataclass_params__
        self.assertTrue(params.frozen)

    def test_notice_exposes_exactly_the_five_contract_fields(self):
        fields = {f.name for f in dataclasses.fields(notices.Notice)}
        self.assertEqual(
            fields, {"app_id", "kind", "title", "summary", "published_at"}
        )
