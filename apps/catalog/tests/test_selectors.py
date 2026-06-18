"""Tests for the catalog read selectors (T-07, DESIGN.md §5b/§9/§11).

The load-bearing guarantees: owner isolation (AC8), the accepted-only downstream catalogue
(AC9 — one test per non-accepted state), read-time tag resolution (D-5), ordered media,
no N+1 on list reads, strict FIFO review queue with the duplicate hint and no priority
field (AC3), and the time-to-decision reporting value.
"""

import tempfile

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.catalog import selectors, services
from apps.catalog.gate import Criterion
from apps.catalog.models import App
from apps.catalog.tests.helpers import make_account, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag(slug="todo-app", label="To-do app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SelectorTestBase(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.other = make_account("other@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()

    def _submit(self, owner=None, *, url="https://demo.example.com", tag_ids=None, media=None):
        return services.submit_app(
            owner or self.owner,
            name="Demo",
            description="A demo app.",
            url=url,
            tag_ids=tag_ids or [self.tag.id],
            media=media or [make_image_upload()],
        )

    def _accept(self, app):
        services.accept_app(app, self.reviewer)
        app.refresh_from_db()
        return app


class OwnerScopeTests(SelectorTestBase):
    def test_get_owned_app_returns_only_callers_app(self):
        app = self._submit()
        self.assertIsNotNone(selectors.get_owned_app(self.owner, app.id))
        self.assertIsNone(selectors.get_owned_app(self.other, app.id))

    def test_list_owned_apps_is_owner_scoped(self):
        self._submit(self.owner)
        self._submit(self.other, url="https://other.example.com")
        self.assertEqual(len(selectors.list_owned_apps(self.owner)), 1)


class CataloguedAppTests(SelectorTestBase):
    def test_accepted_app_is_catalogued(self):
        app = self._accept(self._submit())
        self.assertEqual(len(selectors.list_catalogued_apps()), 1)
        self.assertIsNotNone(selectors.get_catalogued_app(app.id))

    def test_pending_app_is_not_catalogued(self):
        app = self._submit()
        self.assertEqual(selectors.list_catalogued_apps(), [])
        self.assertIsNone(selectors.get_catalogued_app(app.id))

    def test_rejected_app_is_not_catalogued(self):
        app = self._submit()
        services.reject_app(app, self.reviewer, failed_criteria=[Criterion.WORKS])
        self.assertEqual(selectors.list_catalogued_apps(), [])
        self.assertIsNone(selectors.get_catalogued_app(app.id))

    def test_withdrawn_app_is_not_catalogued(self):
        app = self._accept(self._submit())
        services.withdraw_app(app)
        self.assertEqual(selectors.list_catalogued_apps(), [])
        self.assertIsNone(selectors.get_catalogued_app(app.id))

    def test_tags_are_resolved_to_current_label(self):
        app = self._accept(self._submit())
        taxonomy_services.rename_tag(self.tag, label="Renamed Tag")
        catalogued = selectors.get_catalogued_app(app.id)
        self.assertEqual([t.label for t in catalogued.tags], ["Renamed Tag"])

    def test_retired_tag_resolves_to_successor(self):
        successor = _valid_tag("notes", "Notes")
        app = self._accept(self._submit(tag_ids=[self.tag.id]))
        taxonomy_services.retire_tag(self.tag, replaced_by=successor)
        catalogued = selectors.get_catalogued_app(app.id)
        # The stored ref is kept, resolved to the successor — nothing dropped (D-5).
        self.assertEqual([t.label for t in catalogued.tags], ["Notes"])

    def test_media_returned_in_position_order(self):
        app = self._submit(media=[make_image_upload("a.png")])
        services.add_media(app, make_image_upload("b.png"))
        services.add_media(app, make_image_upload("c.png"))
        self._accept(app)
        catalogued = selectors.get_catalogued_app(app.id)
        positions = [m.position for m in catalogued.media]
        self.assertEqual(positions, sorted(positions))

    def test_list_does_not_n_plus_one(self):
        # Three accepted apps sharing one tag must cost the same query count as one — the
        # prefetch + deduped tag resolution means no per-app growth (AC9 read at scale).
        for i in range(3):
            self._accept(self._submit(url=f"https://app{i}.example.com"))

        with CaptureQueriesContext(connection) as ctx_many:
            selectors.list_catalogued_apps()
        many = len(ctx_many.captured_queries)

        App.objects.exclude(pk=App.objects.first().pk).delete()
        with CaptureQueriesContext(connection) as ctx_one:
            selectors.list_catalogued_apps()
        one = len(ctx_one.captured_queries)

        self.assertEqual(many, one, "catalogue list query count grows per app (N+1)")


class ReviewQueueTests(SelectorTestBase):
    def test_queue_is_fifo_by_submission_time(self):
        first = self._submit(url="https://a.example.com")
        second = self._submit(url="https://b.example.com")
        third = self._submit(url="https://c.example.com")
        queue = selectors.list_review_queue()
        self.assertEqual(
            [row.app.id for row in queue], [first.id, second.id, third.id]
        )

    def test_duplicate_hint_counts_other_apps_with_same_url(self):
        self._submit(url="https://dup.example.com")
        self._submit(self.other, url="https://dup.example.com")
        queue = selectors.list_review_queue()
        self.assertTrue(all(row.duplicate_hint == 1 for row in queue))

    def test_no_duplicate_hint_for_unique_url(self):
        self._submit(url="https://unique.example.com")
        [row] = selectors.list_review_queue()
        self.assertEqual(row.duplicate_hint, 0)

    def test_queue_row_has_no_priority_field(self):
        self._submit()
        [row] = selectors.list_review_queue()
        self.assertFalse(hasattr(row, "priority"))
        self.assertFalse(hasattr(row, "tier"))

    def test_apps_sharing_url_excludes_self(self):
        app = self._submit(url="https://dup.example.com")
        self._submit(self.other, url="https://dup.example.com")
        shared = selectors.apps_sharing_url(app.normalized_url, exclude=app.pk)
        self.assertEqual(len(shared), 1)


class TimeToDecisionTests(SelectorTestBase):
    def test_undecided_app_has_no_latency(self):
        app = self._submit()
        self.assertIsNone(selectors.time_to_decision(app))

    def test_decided_app_reports_stored_timestamp_delta(self):
        app = self._submit()
        self._accept(app)
        latency = selectors.time_to_decision(app)
        self.assertIsNotNone(latency)
        self.assertGreaterEqual(latency.total_seconds(), 0)

    def test_decision_latencies_lists_decided_apps(self):
        app = self._submit()
        self._accept(app)
        self.assertEqual(len(selectors.decision_latencies()), 1)
