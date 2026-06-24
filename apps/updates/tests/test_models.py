"""T-01 — the ``updates_notice`` table shape (DESIGN §5.1, DU-DESIGN-3).

Covers the durable contract the producer/feed build on: every column persists, ``kind`` is
constrained to the two ``NoticeKind`` values, ordering is newest-first, the table name and
the backing index match the design, and the author FK **CASCADE**s on account deletion (a
notice is withdrawable content, not retained corpus — AS-5).
"""

import uuid

from django.db import connection
from django.test import TestCase

from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import make_developer


class NoticeModelTests(TestCase):
    def setUp(self):
        self.author = make_developer()
        self.app_id = uuid.uuid4()

    def _make(self, **overrides) -> Notice:
        fields = {
            "app_id": self.app_id,
            "author": self.author,
            "kind": NoticeKind.UPDATE,
            "title": "Shipped dark mode",
            "summary": "You can now switch themes in settings.",
        }
        fields.update(overrides)
        return Notice.objects.create(**fields)

    def test_persists_all_fields(self):
        notice = self._make()
        notice.refresh_from_db()
        self.assertEqual(notice.app_id, self.app_id)
        self.assertEqual(notice.author, self.author)
        self.assertEqual(notice.kind, "update")
        self.assertEqual(notice.title, "Shipped dark mode")
        self.assertEqual(notice.summary, "You can now switch themes in settings.")
        self.assertIsNotNone(notice.published_at)
        self.assertIsInstance(notice.id, uuid.UUID)

    def test_both_kinds_are_accepted(self):
        update = self._make(kind=NoticeKind.UPDATE)
        early = self._make(kind=NoticeKind.EARLY_ACCESS)
        self.assertEqual(update.kind, "update")
        self.assertEqual(early.kind, "early_access")

    def test_kind_choices_are_exactly_the_two_pinned_values(self):
        self.assertEqual(
            [value for value, _label in NoticeKind.choices],
            ["update", "early_access"],
        )

    def test_default_ordering_is_newest_first(self):
        first = self._make(title="First")
        second = self._make(title="Second")
        ordered = list(Notice.objects.all())
        self.assertEqual([n.id for n in ordered], [second.id, first.id])

    def test_db_table_name(self):
        self.assertEqual(Notice._meta.db_table, "updates_notice")

    def test_app_published_index_is_present(self):
        index_names = {index.name for index in Notice._meta.indexes}
        self.assertIn("updates_app_published_idx", index_names)
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_constraints(
                cursor, "updates_notice"
            )
        self.assertIn("updates_app_published_idx", indexes)

    def test_deleting_author_cascades_to_their_notices(self):
        notice = self._make()
        self.author.delete()
        self.assertFalse(Notice.objects.filter(pk=notice.pk).exists())
