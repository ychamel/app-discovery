"""Tests for the open-search-browse column maintenance in the catalog write path (T-02).

The two additive columns (open-search-browse DESIGN.md §5a/§5b) are written **only** here:

  * ``accept_app`` stamps ``accepted_at`` (and re-stamps it on re-acceptance) — the one
    source of truth for newest-accepted-first browse order;
  * ``submit_app``/``edit_app`` maintain ``search_vector`` from the row's own
    name/description via the single ``_search_vector_expr`` formula.

These prove the column-level freshness the eventual read (T-05) depends on, with no change
to acceptance/submission/edit semantics.
"""

import inspect
import tempfile
from datetime import timedelta
from unittest import mock

from django.contrib.postgres.search import SearchQuery
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog import services
from apps.catalog.models import App
from apps.catalog.tests.helpers import make_account, make_image_upload
from apps.taxonomy import services as taxonomy_services

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-search-test-media-")


def _valid_tag(slug="todo-app"):
    cluster = taxonomy_services.add_cluster(f"c-{slug}", f"Cluster {slug}")
    return taxonomy_services.add_tag(slug, f"Tag {slug}", clusters=[cluster])


def _matches(app, term: str) -> bool:
    """True iff the app's stored FTS vector matches ``term`` (the same @@ the read uses)."""
    return App.objects.filter(
        pk=app.pk, search_vector=SearchQuery(term, search_type="websearch")
    ).exists()


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AcceptedAtStampingTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")
        self.tag = _valid_tag()

    def _submit(self, **overrides):
        fields = {
            "name": "Demo",
            "description": "A demo app.",
            "url": "https://demo.example.com",
            "tag_ids": [self.tag.id],
            "media": [make_image_upload()],
        }
        fields.update(overrides)
        return services.submit_app(self.owner, **fields)

    def test_pending_app_has_no_accepted_at(self):
        app = self._submit()
        self.assertIsNone(app.accepted_at)

    def test_accept_stamps_accepted_at_to_now(self):
        app = self._submit()
        before = timezone.now()
        services.accept_app(app, self.reviewer)
        after = timezone.now()
        app.refresh_from_db()
        self.assertIsNotNone(app.accepted_at)
        self.assertGreaterEqual(app.accepted_at, before)
        self.assertLessEqual(app.accepted_at, after)

    def test_reacceptance_restamps_accepted_at_strictly_later(self):
        # withdraw → resubmit → accept again yields a strictly later accepted_at, so a
        # re-entering app sorts as newest (AC5/M6 — DESIGN §5a honest re-entry semantics).
        app = self._submit()
        services.accept_app(app, self.reviewer)
        app.refresh_from_db()
        first_accepted_at = app.accepted_at

        services.withdraw_app(app)
        services.resubmit_app(app)
        later = first_accepted_at + timedelta(seconds=10)
        with mock.patch.object(services.timezone, "now", return_value=later):
            services.accept_app(app, self.reviewer)
        app.refresh_from_db()
        self.assertGreater(app.accepted_at, first_accepted_at)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class SearchVectorMaintenanceTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.tag = _valid_tag()

    def _submit(self, **overrides):
        fields = {
            "name": "Calendar",
            "description": "Plan your week.",
            "url": "https://demo.example.com",
            "tag_ids": [self.tag.id],
            "media": [make_image_upload()],
        }
        fields.update(overrides)
        return services.submit_app(self.owner, **fields)

    def test_submit_populates_search_vector_from_name_and_description(self):
        app = self._submit()
        app.refresh_from_db()
        self.assertIsNotNone(app.search_vector)
        self.assertTrue(_matches(app, "Calendar"))  # name (weight A)
        self.assertTrue(_matches(app, "week"))  # description (weight B)
        self.assertFalse(_matches(app, "Spreadsheet"))

    def test_edit_recomputes_vector_when_name_changes(self):
        app = self._submit()
        services.edit_app(app, name="Spreadsheet")
        app.refresh_from_db()
        self.assertTrue(_matches(app, "Spreadsheet"))  # the new term matches
        self.assertFalse(_matches(app, "Calendar"))  # the old term no longer matches (AC2)

    def test_edit_recomputes_vector_when_description_changes(self):
        app = self._submit()
        services.edit_app(app, description="Track your budget.")
        app.refresh_from_db()
        self.assertTrue(_matches(app, "budget"))
        self.assertFalse(_matches(app, "week"))

    def test_tags_only_edit_does_not_rewrite_the_vector(self):
        # A non-text edit must not needlessly recompute the vector (DESIGN §5b).
        app = self._submit()
        other_tag = _valid_tag(slug="notes-app")
        with mock.patch.object(services, "_maintain_search_vector") as maintain:
            services.edit_app(app, tag_ids=[self.tag.id, other_tag.id])
        maintain.assert_not_called()


class SearchFormulaSingleSourceTests(TestCase):
    def test_search_vector_formula_is_defined_in_exactly_one_place(self):
        # The field list + weights live only in _search_vector_expr (DESIGN §5b/§8) — so a
        # change to what is searchable is a one-function edit. No other SearchVector(...)
        # construction exists in the write path.
        source = inspect.getsource(services)
        self.assertEqual(source.count("SearchVector("), 2)  # name(A) + description(B), once
        expr_source = inspect.getsource(services._search_vector_expr)
        self.assertEqual(expr_source.count("SearchVector("), 2)
