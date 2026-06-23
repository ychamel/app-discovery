"""Tests for the paginated open-discovery read primitive (T-05, open-search-browse §6.1).

``search_catalogue`` is the risk centerpiece: a constant-query-count, no-N+1, FTS-ranked,
neutrally-ordered, clamped paginated read over the accepted catalogue. These tests exercise
it at the ORM level (seeded through the real write path so accepted_at/search_vector are
real), including the two load-bearing assertions — **constant query count across catalogue
size** (AC9) and **ORDER-BY neutrality** (AC5/M5) — before any view exists.
"""

import tempfile
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog import selectors, services
from apps.catalog.models import App, AppTag
from apps.catalog.selectors import CatalogPage, search_catalogue
from apps.catalog.tests.helpers import make_account, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-discovery-test-media-")


def _tag(slug, label):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SearchCatalogueTestBase(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _tag("todo-app", "To-do app")

    def _accepted(self, *, name="App", description="A useful app.", tag_ids=None, accepted_at=None):
        app = services.submit_app(
            self.owner,
            name=name,
            description=description,
            url="https://demo.example.com",
            tag_ids=tag_ids or [self.tag.id],
            media=[make_image_upload()],
        )
        services.accept_app(app, self.reviewer)
        if accepted_at is not None:
            App.objects.filter(pk=app.pk).update(accepted_at=accepted_at)
        app.refresh_from_db()
        return app

    def _pending(self, *, name="Pending", description="Not yet."):
        return services.submit_app(
            self.owner,
            name=name,
            description=description,
            url="https://demo.example.com",
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
        )


class BrowseTests(SearchCatalogueTestBase):
    def test_returns_only_accepted_apps_newest_first(self):
        now = timezone.now()
        old = self._accepted(name="Old", accepted_at=now - timedelta(days=2))
        mid = self._accepted(name="Mid", accepted_at=now - timedelta(days=1))
        new = self._accepted(name="New", accepted_at=now)
        self._pending(name="PendingApp")  # never catalogued

        result = search_catalogue()

        self.assertEqual([app.id for app in result.apps], [new.id, mid.id, old.id])
        self.assertEqual(result.total, 3)

    def test_pending_rejected_withdrawn_never_returned(self):
        accepted = self._accepted(name="Live")
        pending = self._pending()
        rejected = self._accepted(name="WillReject")
        services.withdraw_app(rejected)  # leaves the catalogue

        returned_ids = {app.id for app in search_catalogue().apps}
        self.assertIn(accepted.id, returned_ids)
        self.assertNotIn(pending.id, returned_ids)
        self.assertNotIn(rejected.id, returned_ids)

    def test_returns_catalogpage_shape(self):
        self._accepted()
        result = search_catalogue()
        self.assertIsInstance(result, CatalogPage)
        self.assertEqual(result.page, 1)
        self.assertFalse(result.has_next)


class KeywordSearchTests(SearchCatalogueTestBase):
    def test_matches_name_and_description_excludes_non_matching(self):
        calendar = self._accepted(name="Calendar", description="Plan your week.")
        budget = self._accepted(name="Budget", description="Track spending.")

        result = search_catalogue(query="calendar")
        self.assertEqual([app.id for app in result.apps], [calendar.id])

        result = search_catalogue(query="spending")
        self.assertEqual([app.id for app in result.apps], [budget.id])

    def test_non_accepted_match_is_excluded(self):
        self._pending(name="Calendar", description="Plan your week.")
        result = search_catalogue(query="calendar")
        self.assertEqual(result.apps, [])
        self.assertEqual(result.total, 0)

    def test_blank_query_is_browse_mode(self):
        self._accepted(name="Anything")
        self.assertEqual(search_catalogue(query="   ").total, 1)

    def test_malformed_query_does_not_raise(self):
        self._accepted(name="Calendar")
        # websearch_to_tsquery tolerates arbitrary punctuation — never an error.
        result = search_catalogue(query='!! "(unbalanced')
        self.assertIsInstance(result, CatalogPage)


class TagFilterTests(SearchCatalogueTestBase):
    def test_returns_only_carriers(self):
        wanted = _tag("games", "Games")
        match = self._accepted(name="Game", tag_ids=[wanted.id])
        self._accepted(name="Other", tag_ids=[self.tag.id])

        result = search_catalogue(tag_ids=[wanted.id])
        self.assertEqual([app.id for app in result.apps], [match.id])

    def test_app_with_multiple_matching_tags_is_not_duplicated(self):
        a = _tag("a", "A")
        b = _tag("b", "B")
        app = self._accepted(name="Multi", tag_ids=[a.id, b.id])

        result = search_catalogue(tag_ids=[a.id, b.id])
        self.assertEqual([app_.id for app_ in result.apps], [app.id])
        self.assertEqual(result.total, 1)

    def test_keyword_and_tag_compose_as_and(self):
        wanted = _tag("games", "Games")
        both = self._accepted(name="Calendar Game", tag_ids=[wanted.id])
        self._accepted(name="Calendar", tag_ids=[self.tag.id])  # keyword only
        self._accepted(name="Game", tag_ids=[wanted.id])  # tag only

        result = search_catalogue(query="calendar", tag_ids=[wanted.id])
        self.assertEqual([app.id for app in result.apps], [both.id])


class OrderNeutralityTests(SearchCatalogueTestBase):
    def test_browse_order_is_accepted_at_then_id_only(self):
        order = selectors._apply_neutral_order(
            App.objects.filter(status=App.Status.ACCEPTED), ""
        ).query.order_by
        self.assertEqual(order, ("-accepted_at", "id"))

    def test_keyword_order_is_rank_then_accepted_at_then_id_only(self):
        order = selectors._apply_neutral_order(
            App.objects.filter(status=App.Status.ACCEPTED), "calendar"
        ).query.order_by
        self.assertEqual(order, ("-rank", "-accepted_at", "id"))

    def test_no_purchasable_key_participates_in_ordering(self):
        # M5 position-neutrality = 0 by construction: no paid/tier/score/impression term.
        forbidden = {"price", "payment", "tier", "budget", "priority", "score", "impression"}
        for keyword in ("", "calendar"):
            order = selectors._apply_neutral_order(
                App.objects.filter(status=App.Status.ACCEPTED), keyword
            ).query.order_by
            for key in order:
                self.assertFalse(
                    any(bad in key for bad in forbidden),
                    msg=f"ordering key {key!r} references a purchasable input",
                )


class PaginationTests(SearchCatalogueTestBase):
    def _seed(self, n):
        now = timezone.now()
        for i in range(n):
            self._accepted(name=f"App {i}", accepted_at=now - timedelta(minutes=i))

    def test_pages_partition_the_catalogue_with_correct_flags(self):
        self._seed(5)
        first = search_catalogue(page=1, page_size=2)
        self.assertEqual(len(first.apps), 2)
        self.assertEqual(first.total, 5)
        self.assertTrue(first.has_next)

        last = search_catalogue(page=3, page_size=2)
        self.assertEqual(len(last.apps), 1)
        self.assertFalse(last.has_next)

    def test_over_large_page_clamps_to_last_page(self):
        self._seed(3)
        result = search_catalogue(page=99, page_size=2)
        self.assertEqual(result.page, 2)  # clamped to the last page
        self.assertEqual(len(result.apps), 1)
        self.assertFalse(result.has_next)

    def test_page_below_one_clamps_to_first(self):
        self._seed(3)
        self.assertEqual(search_catalogue(page=0, page_size=2).page, 1)

    def test_page_size_is_clamped_to_the_configured_ceiling(self):
        self._seed(2)
        # An absurd page_size is clamped to discovery_page_size_max() (default 100).
        result = search_catalogue(page_size=10_000)
        self.assertEqual(result.page_size, 100)

    def test_every_accepted_app_is_reachable_across_pages(self):
        # M1 open-access coverage = 100% by construction.
        self._seed(7)
        all_ids = set(App.objects.filter(status=App.Status.ACCEPTED).values_list("id", flat=True))
        seen = set()
        page = 1
        while True:
            result = search_catalogue(page=page, page_size=2)
            seen.update(app.id for app in result.apps)
            if not result.has_next:
                break
            page += 1
        self.assertEqual(seen, all_ids)


class ScaleTests(SearchCatalogueTestBase):
    """The load-bearing AC9 assertion: per-page query count is independent of catalogue size."""

    def _bare_accepted(self, n):
        now = timezone.now()
        for i in range(n):
            app = App.objects.create(
                owner=self.owner,
                name=f"App {i}",
                description="A useful app.",
                url="https://demo.example.com",
                normalized_url="https://demo.example.com",
                status=App.Status.ACCEPTED,
                last_submitted_at=now,
                accepted_at=now - timedelta(seconds=i),
            )
            AppTag.objects.create(app=app, tag_id=self.tag.id)  # all share one tag

    def test_query_count_constant_across_catalogue_size(self):
        # Same page_size, same single shared tag → the page always holds 5 apps resolving one
        # tag, so the query count must not grow with the catalogue (no N+1 on app count).
        # COUNT + page SELECT + media prefetch + app_tags prefetch + resolve the one shared
        # tag (get_tag + its clusters prefetch = 2) → 6, and crucially the SAME at any size.
        self._bare_accepted(5)
        with self.assertNumQueries(6):
            search_catalogue(page=1, page_size=5)

        self._bare_accepted(45)  # 50 total now
        with self.assertNumQueries(6):
            search_catalogue(page=1, page_size=5)


class EmptyStateTests(SearchCatalogueTestBase):
    def test_filter_matching_nothing_is_a_valid_empty_page(self):
        self._accepted(name="Calendar")
        result = search_catalogue(query="nonexistentterm")
        self.assertEqual(result.apps, [])
        self.assertEqual(result.total, 0)
        self.assertFalse(result.has_next)
        self.assertEqual(result.page, 1)

    def test_empty_catalogue_is_a_valid_empty_page(self):
        result = search_catalogue()
        self.assertEqual(result.apps, [])
        self.assertEqual(result.total, 0)
        self.assertFalse(result.has_next)


class ConfigTests(TestCase):
    def test_discovery_page_size_defaults(self):
        from apps.core import config

        self.assertEqual(config.discovery_page_size(), 24)
        self.assertEqual(config.discovery_page_size_max(), 100)

    def test_validate_all_covers_the_new_tunables(self):
        from apps.core import config

        config.validate_all()  # must not raise
