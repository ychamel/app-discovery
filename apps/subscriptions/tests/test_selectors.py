"""T-04 — the single read path (DESIGN §5c/§6.2).

Covers AC1 (``is_following`` true/false/anonymous) and AC4 (``followed_apps`` ordering,
accepted-only drop of a withdrawn follow, empty state, the ``limit`` cap, and the 2-query
no-N+1 bound).
"""

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.catalog import services as catalog_services
from apps.subscriptions import selectors
from apps.subscriptions.models import Subscription
from apps.subscriptions.tests.helpers import make_accepted_app, make_tag, make_user


def _follow(user, app, *, when=None):
    """Create one follow row, optionally back-dating ``created_at`` for ordering tests."""
    sub = Subscription.objects.create(user=user, app_id=app.id)
    if when is not None:
        Subscription.objects.filter(pk=sub.pk).update(created_at=when)
    return sub


class IsFollowingTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    def test_true_when_following(self):
        _follow(self.user, self.app)
        self.assertTrue(selectors.is_following(self.user, self.app.id))

    def test_false_when_not_following(self):
        self.assertFalse(selectors.is_following(self.user, self.app.id))

    def test_false_for_anonymous_and_none(self):
        self.assertFalse(selectors.is_following(AnonymousUser(), self.app.id))
        self.assertFalse(selectors.is_following(None, self.app.id))


class FollowedAppsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")

    def _app(self, name):
        return make_accepted_app(self.owner, tag_ids=[self.tag.id], name=name)

    def test_empty_when_no_follows(self):
        self.assertEqual(selectors.followed_apps(self.user, limit=100), [])

    def test_empty_for_anonymous(self):
        self.assertEqual(selectors.followed_apps(AnonymousUser(), limit=100), [])

    def test_returns_current_follows_most_recent_first(self):
        from datetime import UTC, datetime

        first = self._app("First App")
        second = self._app("Second App")
        _follow(self.user, first, when=datetime(2026, 6, 1, tzinfo=UTC))
        _follow(self.user, second, when=datetime(2026, 6, 5, tzinfo=UTC))

        result = selectors.followed_apps(self.user, limit=100)

        self.assertEqual([app.name for app in result], ["Second App", "First App"])

    def test_withdrawn_followed_app_is_silently_absent(self):
        kept = self._app("Kept App")
        withdrawn = self._app("Withdrawn App")
        _follow(self.user, kept)
        _follow(self.user, withdrawn)
        catalog_services.withdraw_app(withdrawn)

        result = selectors.followed_apps(self.user, limit=100)

        self.assertEqual([app.name for app in result], ["Kept App"])

    def test_honours_the_limit(self):
        for i in range(5):
            _follow(self.user, self._app(f"App {i}"))
        self.assertEqual(len(selectors.followed_apps(self.user, limit=2)), 2)

    def test_runs_in_a_bounded_query_count(self):
        # The query count is bounded and independent of the number of follows (no per-app
        # N+1): five follows of same-tag apps cost the same as one (the indexed follow read +
        # the bulk catalog read with its deduped tag resolution).
        for i in range(5):
            _follow(self.user, self._app(f"App {i}"))
        with CaptureQueriesContext(connection) as ctx_many:
            _ = [app.name for app in selectors.followed_apps(self.user, limit=100)]
        many = len(ctx_many.captured_queries)

        Subscription.objects.exclude(
            pk=Subscription.objects.order_by("created_at").first().pk
        ).delete()
        with CaptureQueriesContext(connection) as ctx_one:
            _ = [app.name for app in selectors.followed_apps(self.user, limit=100)]
        one = len(ctx_one.captured_queries)

        self.assertEqual(many, one, "followed-apps query count grows per follow (N+1)")
