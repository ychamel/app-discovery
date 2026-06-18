"""Tests for the catalog write service — submit/edit/media invariants (T-05, DESIGN.md §5a).

The boundary guarantees under test: a submission writes nothing unless every field is
present and valid (AC1, atomic), off-vocabulary tags are refused and counted (AC4), media
must be a real allowed-format image within the caps and is stored under a generated name
(§9), and a gate-relevant edit of an accepted app returns it to pending (AC8).
"""

import tempfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.catalog import services
from apps.catalog.errors import InvalidTagError, MediaLimitError
from apps.catalog.models import App, AppMedia, AppTag
from apps.catalog.tests.helpers import (
    make_account,
    make_image_upload,
    make_non_image_upload,
)
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-test-media-")


def _valid_tag(slug="todo-app", label="To-do app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SubmitAppTests(TestCase):
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

    def test_valid_submission_creates_pending_app(self):
        app = self._submit()
        self.assertEqual(app.status, App.Status.PENDING)
        self.assertEqual(app.normalized_url, "https://demo.example.com/")
        self.assertEqual(app.app_tags.count(), 1)
        self.assertEqual(app.media.count(), 1)
        self.assertIsNotNone(app.last_submitted_at)

    def test_submission_emits_created_counter(self):
        with mock.patch.object(services.observability, "increment") as inc:
            self._submit()
        metrics = {call.args[0] for call in inc.call_args_list}
        self.assertIn(services.observability.SUBMISSION_CREATED, metrics)

    def test_missing_name_writes_nothing(self):
        with self.assertRaises(ValidationError):
            self._submit(name="   ")
        self.assertEqual(App.objects.count(), 0)
        self.assertEqual(AppMedia.objects.count(), 0)

    def test_missing_description_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit(description="")
        self.assertEqual(App.objects.count(), 0)

    def test_malformed_url_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit(url="not-a-url")
        self.assertEqual(App.objects.count(), 0)

    def test_non_http_scheme_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit(url="ftp://example.com/app")
        self.assertEqual(App.objects.count(), 0)

    def test_zero_tags_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit(tag_ids=[])
        self.assertEqual(App.objects.count(), 0)

    def test_zero_media_rejected(self):
        with self.assertRaises(ValidationError):
            self._submit(media=[])
        self.assertEqual(App.objects.count(), 0)

    def test_off_vocabulary_tag_refused_and_counted(self):
        import uuid

        with mock.patch.object(services.observability, "increment") as inc:
            with self.assertRaises(InvalidTagError):
                self._submit(tag_ids=[uuid.uuid4()])
        self.assertEqual(App.objects.count(), 0)
        self.assertEqual(AppTag.objects.count(), 0)
        metrics = {call.args[0] for call in inc.call_args_list}
        self.assertIn(services.observability.TAG_OFF_VOCABULARY_REJECTED, metrics)

    def test_duplicate_tag_ids_collapse(self):
        app = self._submit(tag_ids=[self.tag.id, self.tag.id])
        self.assertEqual(app.app_tags.count(), 1)

    def test_non_image_upload_rejected_no_file(self):
        with self.assertRaises(MediaLimitError):
            self._submit(media=[make_non_image_upload()])
        self.assertEqual(App.objects.count(), 0)
        self.assertEqual(AppMedia.objects.count(), 0)

    def test_disallowed_format_rejected(self):
        gif = make_image_upload("a.gif", fmt="GIF", content_type="image/gif")
        with self.assertRaises(MediaLimitError):
            self._submit(media=[gif])
        self.assertEqual(App.objects.count(), 0)

    @override_settings(CATALOG_MEDIA_MAX_BYTES=10)
    def test_oversize_upload_rejected(self):
        with self.assertRaises(MediaLimitError):
            self._submit(media=[make_image_upload()])
        self.assertEqual(App.objects.count(), 0)

    @override_settings(CATALOG_MEDIA_MAX_COUNT=2)
    def test_over_count_rejected(self):
        media = [make_image_upload(f"s{i}.png") for i in range(3)]
        with self.assertRaises(MediaLimitError):
            self._submit(media=media)
        self.assertEqual(App.objects.count(), 0)

    def test_stored_file_uses_generated_name_not_client_name(self):
        app = self._submit(media=[make_image_upload("my-secret-name.png")])
        stored = app.media.first().image.name
        self.assertNotIn("my-secret-name", stored)
        self.assertTrue(stored.endswith(".png"))

    def test_webp_and_jpeg_accepted(self):
        for fmt, name, ct in [("JPEG", "a.jpg", "image/jpeg"), ("WEBP", "a.webp", "image/webp")]:
            app = self._submit(media=[make_image_upload(name, fmt=fmt, content_type=ct)])
            self.assertEqual(app.media.count(), 1)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class EditAppTests(TestCase):
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
        )

    def _accept(self):
        self.app.status = App.Status.ACCEPTED
        self.app.save(update_fields=["status"])

    def test_edit_pending_updates_in_place(self):
        services.edit_app(self.app, name="Renamed")
        self.app.refresh_from_db()
        self.assertEqual(self.app.name, "Renamed")
        self.assertEqual(self.app.status, App.Status.PENDING)

    def test_gate_relevant_edit_of_accepted_returns_to_pending(self):
        self._accept()
        services.edit_app(self.app, name="Renamed")
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)

    def test_unchanged_edit_of_accepted_stays_accepted(self):
        self._accept()
        services.edit_app(self.app, name="Demo")  # same value
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.ACCEPTED)

    def test_edit_rejected_app_stays_rejected(self):
        self.app.status = App.Status.REJECTED
        self.app.save(update_fields=["status"])
        services.edit_app(self.app, name="Renamed")
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.REJECTED)

    def test_invalid_edit_value_rejected(self):
        with self.assertRaises(ValidationError):
            services.edit_app(self.app, name="  ")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class MediaServiceTests(TestCase):
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
        )

    def test_add_media_appends_with_next_position(self):
        media = services.add_media(self.app, make_image_upload("b.png"))
        self.assertEqual(media.position, 1)
        self.assertEqual(self.app.media.count(), 2)

    def test_remove_media_below_one_refused(self):
        only = self.app.media.first()
        with self.assertRaises(MediaLimitError):
            services.remove_media(only)
        self.assertEqual(self.app.media.count(), 1)

    def test_remove_media_above_minimum_allowed(self):
        services.add_media(self.app, make_image_upload("b.png"))
        services.remove_media(self.app.media.first())
        self.assertEqual(self.app.media.count(), 1)

    def test_add_media_to_accepted_returns_to_pending(self):
        self.app.status = App.Status.ACCEPTED
        self.app.save(update_fields=["status"])
        services.add_media(self.app, make_image_upload("b.png"))
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, App.Status.PENDING)

    @override_settings(CATALOG_MEDIA_MAX_COUNT=1)
    def test_add_media_over_cap_refused(self):
        with self.assertRaises(MediaLimitError):
            services.add_media(self.app, make_image_upload("b.png"))
        self.assertEqual(self.app.media.count(), 1)
