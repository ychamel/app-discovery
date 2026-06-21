"""T-05 — the empty-until-producer notice seam (DESIGN §5d/§6.3).

The data is empty today; the *shape* and the *call site* are the contract developer-updates
builds against, so both are asserted stable here.
"""

import dataclasses
from uuid import uuid4

from django.test import SimpleTestCase

from apps.subscriptions import notices


class NoticesForAppsTests(SimpleTestCase):
    def test_returns_empty_for_any_input(self):
        self.assertEqual(notices.notices_for_apps([uuid4(), uuid4()]), [])

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(notices.notices_for_apps([]), [])


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
