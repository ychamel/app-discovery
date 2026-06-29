"""T-04 — write path for the marketing fields, facets, and demo clip (DESIGN.md §8/§8.1).

The boundary guarantees under test: the new fields are **optional** (the submission floor is
unchanged); a valid facet/marketing/clip persists atomically; an off-vocabulary facet, a 2nd
value on a SINGLE facet, an oversized/non-AV clip, and a clip without alt each raise loudly
with **nothing written**; ``edit_app`` is replace-set; and editing each new field on an
ACCEPTED app returns it to ``pending`` exactly when its re-review toggle is on (D-14b).
"""

import tempfile

from django.test import TestCase, override_settings

from apps.catalog import services
from apps.catalog.errors import InvalidFacetError, MediaLimitError
from apps.catalog.models import App, AppFacet
from apps.catalog.tests.helpers import (
    make_account,
    make_clip_upload,
    make_image_upload,
)
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-marketing-test-media-")


def _valid_tag(slug="todo-app", label="To-do app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SubmitMarketingFieldsTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.tag = _valid_tag()

    def _submit(self, **overrides):
        kwargs = {
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "tag_ids": [self.tag.id],
            "media": [make_image_upload()],
        }
        kwargs.update(overrides)
        return services.submit_app(self.owner, **kwargs)

    def test_submission_floor_unchanged_marketing_fields_optional(self):
        app = self._submit()  # no marketing args at all
        app.refresh_from_db()
        self.assertEqual(app.tagline, "")
        self.assertEqual(app.deep_dive, "")
        self.assertEqual(app.app_facets.count(), 0)
        self.assertFalse(app.demo_clip)

    def test_valid_marketing_and_facets_persist(self):
        app = self._submit(
            tagline="The fastest way to ship.",
            deep_dive="A much longer story about the app.",
            facet_values=[("pricing", "free"), ("platform", "web"), ("platform", "mobile")],
        )
        app.refresh_from_db()
        self.assertEqual(app.tagline, "The fastest way to ship.")
        self.assertEqual(app.deep_dive, "A much longer story about the app.")
        self.assertEqual(
            {(f.facet, f.value) for f in app.app_facets.all()},
            {("pricing", "free"), ("platform", "web"), ("platform", "mobile")},
        )

    def test_off_vocabulary_facet_refused_nothing_written(self):
        with self.assertRaises(InvalidFacetError):
            self._submit(facet_values=[("genre", "puzzle")])
        self.assertEqual(App.objects.count(), 0)
        self.assertEqual(AppFacet.objects.count(), 0)

    def test_single_facet_second_value_refused(self):
        with self.assertRaises(InvalidFacetError):
            self._submit(facet_values=[("pricing", "free"), ("pricing", "paid")])
        self.assertEqual(App.objects.count(), 0)
        self.assertEqual(AppFacet.objects.count(), 0)

    def test_single_facet_same_value_twice_collapses(self):
        app = self._submit(facet_values=[("pricing", "free"), ("pricing", "free")])
        self.assertEqual(app.app_facets.count(), 1)

    def test_oversize_tagline_refused(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self._submit(tagline="x" * 301)
        self.assertEqual(App.objects.count(), 0)

    @override_settings(APP_PAGE_DEEP_DIVE_MAX_LENGTH=10)
    def test_oversize_deep_dive_refused(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self._submit(deep_dive="x" * 11)
        self.assertEqual(App.objects.count(), 0)

    def test_valid_clip_with_alt_persists(self):
        app = self._submit(demo_clip=make_clip_upload(), demo_clip_alt="A 10s product tour.")
        app.refresh_from_db()
        self.assertTrue(app.demo_clip)
        self.assertTrue(app.demo_clip.name.endswith(".mp4"))
        self.assertEqual(app.demo_clip_alt, "A 10s product tour.")

    def test_webm_clip_accepted(self):
        app = self._submit(
            demo_clip=make_clip_upload("d.webm", container="webm", content_type="video/webm"),
            demo_clip_alt="tour",
        )
        app.refresh_from_db()
        self.assertTrue(app.demo_clip.name.endswith(".webm"))

    def test_clip_without_alt_refused(self):
        with self.assertRaises(MediaLimitError):
            self._submit(demo_clip=make_clip_upload(), demo_clip_alt="")
        self.assertEqual(App.objects.count(), 0)

    def test_non_av_clip_refused(self):
        not_video = make_image_upload("a.png")  # a real PNG is not an MP4/WebM container
        with self.assertRaises(MediaLimitError):
            self._submit(demo_clip=not_video, demo_clip_alt="x")
        self.assertEqual(App.objects.count(), 0)

    @override_settings(CATALOG_CLIP_MAX_BYTES=8)
    def test_oversize_clip_refused(self):
        with self.assertRaises(MediaLimitError):
            self._submit(demo_clip=make_clip_upload(extra_bytes=1000), demo_clip_alt="x")
        self.assertEqual(App.objects.count(), 0)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class EditMarketingFieldsTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.tag = _valid_tag()
        self.app = services.submit_app(
            self.owner,
            name="Demo",
            description="A demo app.",
            url="https://demo.example.com",
            tag_ids=[self.tag.id],
            media=[make_image_upload()],
            tagline="Original pitch.",
            facet_values=[("pricing", "free"), ("platform", "web")],
        )

    def _accept(self):
        self.app.status = App.Status.ACCEPTED
        self.app.save(update_fields=["status"])

    def test_facets_replace_set_semantics(self):
        services.edit_app(self.app, facet_values=[("pricing", "paid")])
        self.assertEqual(
            {(f.facet, f.value) for f in self.app.app_facets.all()},
            {("pricing", "paid")},
        )

    def test_facets_cleared_with_empty_list(self):
        services.edit_app(self.app, facet_values=[])
        self.assertEqual(self.app.app_facets.count(), 0)

    def test_unsupplied_fields_untouched(self):
        services.edit_app(self.app, tagline="New pitch.")  # facets not supplied
        self.app.refresh_from_db()
        self.assertEqual(self.app.tagline, "New pitch.")
        self.assertEqual(self.app.app_facets.count(), 2)  # unchanged

    # --- Re-review toggle (D-14b): config decides whether a marketing edit re-reviews ----
    def test_marketing_edit_returns_accepted_app_to_pending_by_default(self):
        for field, kwargs in [
            ("tagline", {"tagline": "Brand new pitch."}),
            ("deep_dive", {"deep_dive": "A new long story."}),
            ("facets", {"facet_values": [("pricing", "paid")]}),
        ]:
            with self.subTest(field=field):
                self._accept()
                services.edit_app(self.app, **kwargs)
                self.app.refresh_from_db()
                self.assertEqual(self.app.status, App.Status.PENDING)

    @override_settings(APP_PAGE_GATED_FIELDS=[])  # relax all new fields
    def test_marketing_edit_stays_accepted_when_toggled_off(self):
        self._accept()
        services.edit_app(self.app, tagline="Brand new pitch.", deep_dive="new story")
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.ACCEPTED)

    @override_settings(APP_PAGE_GATED_FIELDS=["tagline"])  # only tagline gates
    def test_partial_toggle_gates_only_configured_field(self):
        self._accept()
        services.edit_app(self.app, deep_dive="a fresh long story")  # not gated now
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.ACCEPTED)

    def test_clip_set_then_replaced_then_removed(self):
        services.edit_app(self.app, demo_clip=make_clip_upload(), demo_clip_alt="tour")
        self.app.refresh_from_db()
        self.assertTrue(self.app.demo_clip)

        services.edit_app(
            self.app,
            demo_clip=make_clip_upload("d2.webm", container="webm"),
            demo_clip_alt="new tour",
        )
        self.app.refresh_from_db()
        self.assertTrue(self.app.demo_clip.name.endswith(".webm"))
        self.assertEqual(self.app.demo_clip_alt, "new tour")

        services.edit_app(self.app, demo_clip=None)
        self.app.refresh_from_db()
        self.assertFalse(self.app.demo_clip)
        self.assertEqual(self.app.demo_clip_alt, "")

    def test_clip_edit_returns_accepted_app_to_pending(self):
        self._accept()
        services.edit_app(self.app, demo_clip=make_clip_upload(), demo_clip_alt="tour")
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)
