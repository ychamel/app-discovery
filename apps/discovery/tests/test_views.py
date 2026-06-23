"""End-to-end tests for the discovery view through the project URLconf (T-06, DESIGN §6.3/§9).

Covers AC8 (anonymous access), AC1 (browse, accepted-only), AC2 (keyword search), AC3 (tag
filter incl. merged predecessors + invalid-tag-ignored), AC4 (card → app-page link), AC7
(empty/zero-result states), and the failure split (core read loud, facet sidebar soft). The
search_catalogue/tag_ids_resolving_to internals are unit-tested at the ORM level (T-04/T-05);
here we assert the HTTP surface and its degradation behaviour.
"""

import tempfile
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.catalog import services as catalog_services
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="discovery-view-test-media-")
_BROWSE = reverse("discovery:browse")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AnonymousAccessTests(TestCase):
    """AC8 — the open surface has no login wall; signing in changes nothing about it."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Notes")

    def test_anonymous_browse_search_and_filter_all_return_200(self):
        client = Client()
        for url in (_BROWSE, f"{_BROWSE}?q=Notes", f"{_BROWSE}?tag={self.tag.id}"):
            response = client.get(url)
            self.assertEqual(response.status_code, 200, msg=url)
            self.assertNotIn("location", {k.lower() for k in response.headers})

    def test_signed_in_sees_the_same_surface(self):
        client = Client()
        client.force_login(make_user("viewer@example.com"))
        response = client.get(_BROWSE)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notes")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class BrowseTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def test_accepted_apps_listed_non_catalogued_excluded(self):
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="LiveApp")
        withdrawn = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="GoneApp")
        catalog_services.withdraw_app(withdrawn)

        response = Client().get(_BROWSE)
        self.assertContains(response, "LiveApp")
        self.assertNotContains(response, "GoneApp")

    @override_settings(DISCOVERY_PAGE_SIZE=2)
    def test_pagination_controls_render(self):
        for i in range(3):
            make_accepted_app(self.owner, tag_ids=[self.tag.id], name=f"App{i}")
        response = Client().get(_BROWSE)
        self.assertContains(response, "Page 1")
        self.assertContains(response, "Next")

    def test_result_card_links_to_the_stable_app_page_url(self):
        app = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Linked")
        response = Client().get(_BROWSE)
        self.assertContains(response, reverse("pages:app-page", args=[app.id]))


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class KeywordSearchTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def test_query_returns_matches_and_excludes_non_matching(self):
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Calendar")
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Spreadsheet")
        response = Client().get(f"{_BROWSE}?q=Calendar")
        self.assertContains(response, "Calendar")
        self.assertNotContains(response, "Spreadsheet")

    def test_query_excludes_non_accepted(self):
        catalog_services.submit_app(
            self.owner,
            name="PendingCalendar",
            description="x",
            url="https://demo.example.com",
            tag_ids=[self.tag.id],
            media=[_png()],
        )
        response = Client().get(f"{_BROWSE}?q=PendingCalendar")
        self.assertContains(response, "No apps match")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class TagFilterTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")

    def test_filter_shows_only_carriers(self):
        games = make_tag("games")
        other = make_tag("other")
        make_accepted_app(self.owner, tag_ids=[games.id], name="GameApp")
        make_accepted_app(self.owner, tag_ids=[other.id], name="OtherApp")

        response = Client().get(f"{_BROWSE}?tag={games.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GameApp")
        self.assertNotContains(response, "OtherApp")

    def test_filter_includes_merged_predecessor_carriers(self):
        # AC3: an app tagged with a tag later merged into another still matches the successor.
        old = make_tag("old-games")
        new = make_tag("new-games")
        make_accepted_app(self.owner, tag_ids=[old.id], name="Merged")
        taxonomy_services.retire_tag(old, replaced_by=new)

        response = Client().get(f"{_BROWSE}?tag={new.id}")
        self.assertContains(response, "Merged")
        # the facet sidebar lists only the active successor, not the retired predecessor
        self.assertContains(response, "new-games")
        self.assertNotContains(response, "old-games")

    def test_retired_no_successor_tag_is_ignored_no_500(self):
        retired = make_tag("retiree")
        make_accepted_app(self.owner, tag_ids=[make_tag("live").id], name="LiveApp")
        taxonomy_services.retire_tag(retired)  # no successor → not an active tag

        response = Client().get(f"{_BROWSE}?tag={retired.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LiveApp")  # unfiltered listing

    def test_unknown_and_malformed_tag_are_ignored_no_500(self):
        make_accepted_app(self.owner, tag_ids=[make_tag("live").id], name="LiveApp")
        for value in ("00000000-0000-0000-0000-000000000000", "not-a-uuid"):
            response = Client().get(f"{_BROWSE}?tag={value}")
            self.assertEqual(response.status_code, 200, msg=value)
            self.assertContains(response, "LiveApp")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class EmptyStateTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def test_empty_catalogue_renders_its_message_200(self):
        response = Client().get(_BROWSE)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No apps in the catalogue yet")

    def test_zero_result_query_renders_its_message_200(self):
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Calendar")
        response = Client().get(f"{_BROWSE}?q=nonexistentterm")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No apps match")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class FailureSplitTests(TestCase):
    """DESIGN §7/§9 — the core read fails loud (500); the facet sidebar fails soft."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Live")

    def test_core_read_failure_is_a_loud_500_not_a_fake_empty_state(self):
        client = Client(raise_request_exception=False)
        with mock.patch(
            "apps.discovery.views.catalog.search_catalogue",
            side_effect=RuntimeError("db down"),
        ):
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                response = client.get(_BROWSE)
        self.assertEqual(response.status_code, 500)
        self.assertTrue(any("discovery_listing_degraded" in line for line in logs.output))

    def test_facet_read_failure_degrades_soft_results_still_render(self):
        with mock.patch(
            "apps.discovery.views.taxonomy.list_active_tags",
            side_effect=RuntimeError("taxonomy down"),
        ):
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                response = Client().get(_BROWSE)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live")  # results render
        self.assertContains(response, "Filters are unavailable")
        self.assertTrue(any("discovery_facets_degraded" in line for line in logs.output))


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class CounterTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        make_accepted_app(self.owner, tag_ids=[self.tag.id], name="Calendar")

    def _metrics_for(self, url):
        with self.assertLogs("apps.metrics", level="INFO") as logs:
            Client().get(url)
        return "\n".join(logs.output)

    def test_browse_search_and_zero_result_counters_fire(self):
        self.assertIn("discovery_browse_rendered", self._metrics_for(_BROWSE))
        self.assertIn("discovery_search_performed", self._metrics_for(f"{_BROWSE}?q=Calendar"))
        self.assertIn("discovery_tag_filtered", self._metrics_for(f"{_BROWSE}?tag={self.tag.id}"))
        self.assertIn("discovery_zero_results", self._metrics_for(f"{_BROWSE}?q=nomatch"))


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(120, 120, 120)).save(buffer, format="PNG")
    return SimpleUploadedFile("shot.png", buffer.getvalue(), content_type="image/png")
