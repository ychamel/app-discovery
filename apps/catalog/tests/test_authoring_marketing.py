"""T-05 — both authoring surfaces round-trip the marketing fields (DESIGN.md §8).

Server-rendered form and the DRF API both call the **same** ``catalog.services`` from T-04
(no second source of truth). Coverage: a server submit/edit sets and re-displays each new
field; facet choices are fed from ``facets.FACETS`` (registry drives the UI — G6); the DRF
create/patch sets each new field and the serializer returns it; invalid input surfaces loudly.
"""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog import facets
from apps.catalog.forms import SubmissionForm
from apps.catalog.models import App
from apps.catalog.tests.helpers import (
    make_clip_upload,
    make_developer,
    make_image_upload,
)
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-authoring-test-media-")


def _valid_tag(slug="todo-app", label="To-do app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, label, clusters=[cluster])


class FacetChoiceSourceTests(TestCase):
    def test_form_facet_choices_come_from_the_registry(self):
        # Changing the registry must change the choices — no duplicate hardcoded vocabulary (G6).
        form = SubmissionForm()
        flat = {value for _group, pairs in form.fields["facets"].choices for value, _ in pairs}
        expected = {
            f"{fdef.key}:{v.key}"
            for fdef in facets.FACETS.values()
            for v in fdef.values
        }
        self.assertEqual(flat, expected)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ServerRenderedAuthoringTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = _valid_tag()
        self.client.force_login(self.dev)

    def _submit_payload(self, **overrides):
        payload = {
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "tags": [str(self.tag.id)],
            "media": [make_image_upload()],
            "tagline": "Ship faster.",
            "deep_dive": "The longer story.",
            "facets": ["pricing:free", "platform:web"],
            "demo_clip_alt": "",
        }
        payload.update(overrides)
        return payload

    def test_server_submit_sets_marketing_fields(self):
        resp = self.client.post(reverse("catalog:submit"), data=self._submit_payload())
        self.assertEqual(resp.status_code, 302)
        app = App.objects.get()
        self.assertEqual(app.tagline, "Ship faster.")
        self.assertEqual(app.deep_dive, "The longer story.")
        self.assertEqual(
            {(f.facet, f.value) for f in app.app_facets.all()},
            {("pricing", "free"), ("platform", "web")},
        )

    def test_server_edit_redisplays_fields_with_checked_facets(self):
        self.client.post(reverse("catalog:submit"), data=self._submit_payload())
        app = App.objects.get()

        resp = self.client.get(reverse("catalog:app-detail", args=[app.id]))
        self.assertContains(resp, "Ship faster.")  # tagline value re-displayed
        self.assertContains(resp, 'value="pricing:free"')
        # The set facet checkbox is pre-checked; an unset one is not (round-trip for editing).
        html = resp.content.decode()
        self.assertRegex(html, r'value="pricing:free"[^>]*\bchecked\b')
        self.assertNotRegex(html, r'value="pricing:paid"[^>]*\bchecked\b')

    def test_server_edit_updates_facets(self):
        self.client.post(reverse("catalog:submit"), data=self._submit_payload())
        app = App.objects.get()
        edit = self._submit_payload(facets=["pricing:paid"])
        edit["action"] = "edit"
        edit.pop("media")  # edit form has no media field
        self.client.post(reverse("catalog:app-detail", args=[app.id]), data=edit)
        self.assertEqual(
            {(f.facet, f.value) for f in app.app_facets.all()}, {("pricing", "paid")}
        )

    def test_server_submit_invalid_facet_resubmits_with_error(self):
        # MultipleChoiceField rejects an off-registry value at the form layer (loud boundary).
        resp = self.client.post(
            reverse("catalog:submit"), data=self._submit_payload(facets=["genre:puzzle"])
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(App.objects.count(), 0)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DrfAuthoringTests(TestCase):
    def setUp(self):
        self.dev = make_developer()
        self.tag = _valid_tag()
        self.client.force_login(self.dev)

    def _create(self, **overrides):
        payload = {
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "tag_ids": [str(self.tag.id)],
            "media": [make_image_upload()],
            "tagline": "API pitch.",
            "deep_dive": "API long-form.",
            "facet_values": ["pricing:freemium", "platform:mobile"],
        }
        payload.update(overrides)
        return self.client.post(reverse("catalog:api-app-create"), data=payload)

    def test_drf_create_sets_and_returns_marketing_fields(self):
        resp = self._create()
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["tagline"], "API pitch.")
        self.assertEqual(body["deep_dive"], "API long-form.")
        self.assertEqual(
            {(f["facet"], f["value"]) for f in body["facets"]},
            {("pricing", "freemium"), ("platform", "mobile")},
        )
        self.assertIsNone(body["demo_clip_url"])

    def test_drf_create_off_vocabulary_facet_is_400(self):
        resp = self._create(facet_values=["genre:puzzle"])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(App.objects.count(), 0)

    def test_drf_patch_updates_marketing_fields(self):
        app_id = self._create().json()["id"]
        resp = self.client.patch(
            reverse("catalog:api-app-detail", args=[app_id]),
            data={"tagline": "Edited pitch.", "facet_values": ["pricing:paid"]},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["tagline"], "Edited pitch.")
        self.assertEqual(
            {(f["facet"], f["value"]) for f in body["facets"]}, {("pricing", "paid")}
        )

    def test_drf_patch_can_clear_facets(self):
        app_id = self._create().json()["id"]
        resp = self.client.patch(
            reverse("catalog:api-app-detail", args=[app_id]),
            data={"facet_values": []},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["facets"], [])

    def test_drf_patch_can_set_the_clip_via_multipart(self):
        from django.test.client import encode_multipart

        app_id = self._create().json()["id"]
        payload = encode_multipart(
            "BoUnDaRy",
            {"demo_clip": make_clip_upload(), "demo_clip_alt": "a quick tour"},
        )
        resp = self.client.patch(
            reverse("catalog:api-app-detail", args=[app_id]),
            data=payload,
            content_type="multipart/form-data; boundary=BoUnDaRy",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIsNotNone(resp.json()["demo_clip_url"])
