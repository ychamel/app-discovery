"""T-06 — the page-scoped read ``get_app_page_content`` (DESIGN.md §3/§6).

Coverage: full content for an accepted app; None for non-accepted/unknown (D-6); a legacy/
sparse app degrades to empty strings / None clip / [] facets / [] other_apps (M2); facets in
registry order with a registry-absent value dropped at read (the D-5 pattern); other_apps is
ACCEPTED-only and excludes this app (no leak); bounded query count (no N+1); and the shared
``CatalogApp`` contract stays byte-stable.
"""

import tempfile
from uuid import uuid4

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.catalog import selectors, services
from apps.catalog.models import AppFacet
from apps.catalog.tests.helpers import make_account, make_clip_upload, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-page-content-test-media-")


def _valid_tag(slug="todo-app", label="To-do app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class GetAppPageContentTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com", )
        self.owner.display_name = "Acme Studio"
        self.owner.save(update_fields=["display_name"])
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()

    def _submit(self, owner=None, *, url="https://demo.example.com", media=None, **marketing):
        return services.submit_app(
            owner or self.owner,
            name="Demo",
            description="A demo app.",
            url=url,
            tag_ids=[self.tag.id],
            media=media or [make_image_upload()],
            **marketing,
        )

    def _accept(self, app):
        services.accept_app(app, self.reviewer)
        app.refresh_from_db()
        return app

    def test_full_content_for_accepted_app(self):
        app = self._submit(
            tagline="Ship faster.",
            deep_dive="The long story.",
            facet_values=[("pricing", "free"), ("platform", "web"), ("platform", "mobile")],
            demo_clip=make_clip_upload(),
            demo_clip_alt="A short tour.",
        )
        self._accept(app)

        content = selectors.get_app_page_content(app.id)
        self.assertEqual(content.name, "Demo")
        self.assertEqual(content.tagline, "Ship faster.")
        self.assertEqual(content.deep_dive, "The long story.")
        self.assertIsNotNone(content.demo_clip_url)
        self.assertEqual(content.demo_clip_alt, "A short tour.")
        self.assertEqual(content.developer.display_name, "Acme Studio")
        # Facets resolved in registry order: pricing before platform; web before mobile.
        self.assertEqual([f.facet for f in content.facets], ["pricing", "platform"])
        self.assertEqual([v.key for v in content.facets[1].values], ["web", "mobile"])
        self.assertEqual(content.facets[0].label, "Pricing")

    def test_none_for_non_accepted_or_unknown(self):
        pending = self._submit()  # never accepted
        self.assertIsNone(selectors.get_app_page_content(pending.id))
        self.assertIsNone(selectors.get_app_page_content(uuid4()))

    def test_legacy_app_degrades_to_empty(self):
        app = self._accept(self._submit())  # no marketing fields at all
        content = selectors.get_app_page_content(app.id)
        self.assertEqual(content.tagline, "")
        self.assertEqual(content.deep_dive, "")
        self.assertIsNone(content.demo_clip_url)
        self.assertEqual(content.demo_clip_alt, "")
        self.assertEqual(content.facets, [])
        self.assertEqual(content.other_apps, [])

    def test_registry_absent_facet_value_dropped_at_read(self):
        app = self._accept(self._submit(facet_values=[("pricing", "free")]))
        # Simulate a value that left the registry after it was stored (the D-5 graceful case).
        AppFacet.objects.create(app=app, facet="pricing", value="barter_now_removed")
        content = selectors.get_app_page_content(app.id)
        self.assertEqual([v.key for v in content.facets[0].values], ["free"])

    def test_other_apps_accepted_only_excludes_self_and_leaks_nothing(self):
        first = self._accept(self._submit(url="https://one.example.com"))
        second = self._accept(self._submit(url="https://two.example.com"))
        self._submit(url="https://pending.example.com")  # pending — must not leak

        content = selectors.get_app_page_content(first.id)
        ids = {a.id for a in content.other_apps}
        self.assertIn(second.id, ids)
        self.assertNotIn(first.id, ids)  # never includes the viewed app
        self.assertEqual(len(content.other_apps), 1)  # only the other accepted one

    def test_other_apps_respects_configured_limit(self):
        viewed = self._accept(self._submit(url="https://viewed.example.com"))
        for i in range(4):
            self._accept(self._submit(url=f"https://extra-{i}.example.com"))
        with override_settings(APP_PAGE_OTHER_APPS_LIMIT=2):
            content = selectors.get_app_page_content(viewed.id)
        self.assertEqual(len(content.other_apps), 2)

    def test_no_n_plus_one_on_facets_and_media(self):
        # Query count must not grow with the number of facets/media on the app (no N+1). Use
        # two SOLO owners so other_apps is [] for both — isolating facet/media scaling.
        owner_small = make_account("solo-small@example.com")
        owner_big = make_account("solo-big@example.com")
        small = self._accept(
            self._submit(
                owner=owner_small,
                url="https://small.example.com",
                facet_values=[("pricing", "free")],
            )
        )
        with CaptureQueriesContext(connection) as small_ctx:
            selectors.get_app_page_content(small.id)

        big = self._accept(
            self._submit(
                owner=owner_big,
                url="https://big.example.com",
                facet_values=[("pricing", "free"), ("platform", "web"), ("platform", "mobile")],
                media=[make_image_upload("a.png"), make_image_upload("b.png")],
            )
        )
        with CaptureQueriesContext(connection) as big_ctx:
            selectors.get_app_page_content(big.id)

        self.assertEqual(len(small_ctx.captured_queries), len(big_ctx.captured_queries))

    def test_catalog_app_contract_unchanged(self):
        # AC-9: the byte-stable shared contract must keep exactly its original fields.
        from dataclasses import fields

        self.assertEqual(
            [f.name for f in fields(selectors.CatalogApp)],
            ["id", "name", "description", "url", "tags", "media"],
        )
