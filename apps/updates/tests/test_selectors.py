"""T-02 — the read path (DESIGN §6.1).

Covers the AS-3 producer read (``published_notices_for_apps``: newest-first, ``limit``-capped,
app-scoped, ``[]`` for empty, one query, follower-count-independent) and the owner manage list
(``notices_for_channel``: own + app-scoped, newest-first, one query).
"""

import uuid
from datetime import UTC, datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.updates import selectors
from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import make_developer


def _seed(author, app_id, *, title="Notice", kind=NoticeKind.UPDATE, when=None) -> Notice:
    """Create one notice row directly via the ORM (no write path needed at T-02)."""
    notice = Notice.objects.create(
        author=author, app_id=app_id, kind=kind, title=title, summary="body"
    )
    if when is not None:
        Notice.objects.filter(pk=notice.pk).update(published_at=when)
    return notice


class PublishedNoticesForAppsTests(TestCase):
    def setUp(self):
        self.author = make_developer()
        self.app_a = uuid.uuid4()
        self.app_b = uuid.uuid4()

    def test_empty_input_returns_empty(self):
        self.assertEqual(selectors.published_notices_for_apps([], limit=50), [])

    def test_newest_first(self):
        old = _seed(self.author, self.app_a, title="Old", when=datetime(2026, 6, 1, tzinfo=UTC))
        new = _seed(self.author, self.app_a, title="New", when=datetime(2026, 6, 5, tzinfo=UTC))
        result = selectors.published_notices_for_apps([self.app_a], limit=50)
        self.assertEqual([n.id for n in result], [new.id, old.id])

    def test_returns_published_notice_dtos_not_rows(self):
        _seed(self.author, self.app_a)
        [notice] = selectors.published_notices_for_apps([self.app_a], limit=50)
        self.assertIsInstance(notice, selectors.PublishedNotice)
        self.assertEqual(notice.app_id, self.app_a)
        self.assertEqual(notice.kind, "update")

    def test_scoped_to_requested_apps_only(self):
        _seed(self.author, self.app_a, title="A")
        _seed(self.author, self.app_b, title="B")
        result = selectors.published_notices_for_apps([self.app_a], limit=50)
        self.assertEqual([n.title for n in result], ["A"])

    def test_capped_at_limit(self):
        for i in range(6):
            _seed(self.author, self.app_a, title=f"N{i}", when=datetime(2026, 6, i + 1, tzinfo=UTC))
        result = selectors.published_notices_for_apps([self.app_a], limit=3)
        self.assertEqual(len(result), 3)
        self.assertEqual([n.title for n in result], ["N5", "N4", "N3"])

    def test_one_query_independent_of_notice_count(self):
        for i in range(50):
            _seed(self.author, self.app_a, title=f"N{i}")
        with CaptureQueriesContext(connection) as ctx:
            selectors.published_notices_for_apps([self.app_a], limit=5)
        self.assertEqual(len(ctx), 1)


class NoticesForChannelTests(TestCase):
    def setUp(self):
        self.owner = make_developer()
        self.other = make_developer("other@example.com")
        self.app_id = uuid.uuid4()

    def test_owner_own_notices_newest_first(self):
        old = _seed(self.owner, self.app_id, title="Old", when=datetime(2026, 6, 1, tzinfo=UTC))
        new = _seed(self.owner, self.app_id, title="New", when=datetime(2026, 6, 5, tzinfo=UTC))
        result = selectors.notices_for_channel(self.owner, self.app_id)
        self.assertEqual([n.id for n in result], [new.id, old.id])

    def test_excludes_other_authors(self):
        _seed(self.owner, self.app_id, title="Mine")
        _seed(self.other, self.app_id, title="Theirs")
        result = selectors.notices_for_channel(self.owner, self.app_id)
        self.assertEqual([n.title for n in result], ["Mine"])

    def test_scoped_to_app(self):
        _seed(self.owner, self.app_id, title="This app")
        _seed(self.owner, uuid.uuid4(), title="Other app")
        result = selectors.notices_for_channel(self.owner, self.app_id)
        self.assertEqual([n.title for n in result], ["This app"])

    def test_empty_when_no_notices(self):
        self.assertEqual(selectors.notices_for_channel(self.owner, self.app_id), [])

    def test_one_query(self):
        for i in range(5):
            _seed(self.owner, self.app_id, title=f"N{i}")
        with CaptureQueriesContext(connection) as ctx:
            selectors.notices_for_channel(self.owner, self.app_id)
        self.assertEqual(len(ctx), 1)
