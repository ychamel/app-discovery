"""Tests for the open-search-browse backfill data migration (T-03, DESIGN §5a/§5b).

The migration's ``backfill``/``clear`` functions are exercised directly against the real
post-0002 schema (identical to the historical state they run in): seed apps whose new
columns are ``NULL`` (created outside the maintained write path), run the backfill, and
assert ``accepted_at`` comes from the latest accept decision and ``search_vector`` matches
the app's text — then assert the reverse clears both columns.
"""

import tempfile
from datetime import timedelta
from importlib import import_module

from django.apps import apps as global_apps
from django.contrib.postgres.search import SearchQuery
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import App, ReviewDecision
from apps.catalog.tests.helpers import make_account

# The migration module name begins with a digit, so import it by string.
_migration = import_module(
    "apps.catalog.migrations.0003_backfill_accepted_at_search_vector"
)
backfill = _migration.backfill
clear = _migration.clear

_MEDIA_ROOT = tempfile.mkdtemp(prefix="catalog-backfill-test-media-")


def _matches(app, term: str) -> bool:
    return App.objects.filter(
        pk=app.pk, search_vector=SearchQuery(term, search_type="websearch")
    ).exists()


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class BackfillMigrationTests(TestCase):
    def setUp(self):
        self.owner = make_account("owner@example.com")
        self.reviewer = make_account("reviewer@example.com")

    def _bare_app(self, *, name, description, status):
        """An App row with NULL accepted_at/search_vector — the pre-migration state."""
        return App.objects.create(
            owner=self.owner,
            name=name,
            description=description,
            url="https://demo.example.com",
            normalized_url="https://demo.example.com",
            status=status,
            last_submitted_at=timezone.now(),
        )

    def _accept_decision(self, app, *, created_at=None):
        decision = ReviewDecision.objects.create(
            app=app,
            reviewer=self.reviewer,
            outcome=ReviewDecision.Outcome.ACCEPTED,
        )
        if created_at is not None:  # created_at is auto_now_add — override for determinism
            ReviewDecision.objects.filter(pk=decision.pk).update(created_at=created_at)
            decision.refresh_from_db()
        return decision

    def test_backfill_populates_accepted_at_and_search_vector(self):
        app = self._bare_app(
            name="Calendar", description="Plan your week.", status=App.Status.ACCEPTED
        )
        decision = self._accept_decision(app)
        self.assertIsNone(app.accepted_at)
        self.assertIsNone(app.search_vector)

        backfill(global_apps, None)

        app.refresh_from_db()
        self.assertEqual(app.accepted_at, decision.created_at)
        self.assertIsNotNone(app.search_vector)
        self.assertTrue(_matches(app, "Calendar"))
        self.assertTrue(_matches(app, "week"))

    def test_never_accepted_app_keeps_null_accepted_at(self):
        # A rejected/withdrawn app with no accept decision stays NULL (never catalogued).
        rejected = self._bare_app(
            name="Bad", description="Nope.", status=App.Status.REJECTED
        )
        ReviewDecision.objects.create(
            app=rejected,
            reviewer=self.reviewer,
            outcome=ReviewDecision.Outcome.REJECTED,
            failed_criteria=["works"],
        )

        backfill(global_apps, None)

        rejected.refresh_from_db()
        self.assertIsNone(rejected.accepted_at)

    def test_reaccepted_app_backfills_from_the_latest_accept_decision(self):
        app = self._bare_app(
            name="Reentry", description="Came back.", status=App.Status.ACCEPTED
        )
        now = timezone.now()
        self._accept_decision(app, created_at=now - timedelta(days=2))
        latest = self._accept_decision(app, created_at=now)

        backfill(global_apps, None)

        app.refresh_from_db()
        self.assertEqual(app.accepted_at, latest.created_at)

    def test_reverse_clears_both_columns(self):
        app = self._bare_app(
            name="Calendar", description="Plan your week.", status=App.Status.ACCEPTED
        )
        self._accept_decision(app)
        backfill(global_apps, None)

        clear(global_apps, None)

        app.refresh_from_db()
        self.assertIsNone(app.accepted_at)
        self.assertIsNone(app.search_vector)
