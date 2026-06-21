"""T-01 (ratings-reviews) — the factual ``has_impression`` existence read (DESIGN §5d).

This selector is the D-7-compliant evidence read the ratings-reviews curated-rating gate
runs. The tests pin its three load-bearing properties: it is keyed on *this* user and app,
it filters by *surface* (so an open APP_PAGE view never matches a DIGEST query), and its
``as_of`` bound is inclusive (``<=``).
"""

from datetime import UTC, datetime, timedelta

from django.test import TestCase

from apps.signals import capture, selectors
from apps.signals.kinds import Surface
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user


def _at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 6, day, hour, tzinfo=UTC)


class HasImpressionTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other_user = make_user("other@example.com")
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.other_app = make_accepted_app(
            self.owner, tag_ids=[self.tag.id], name="Other App"
        )
        capture.record_impression(
            self.user, self.app.id, surface=Surface.DIGEST, occurred_at=_at(10)
        )

    def test_true_when_a_matching_impression_exists(self):
        self.assertTrue(
            selectors.has_impression(
                self.user.id, self.app.id, surfaces={Surface.DIGEST}
            )
        )

    def test_false_for_a_different_user(self):
        self.assertFalse(
            selectors.has_impression(
                self.other_user.id, self.app.id, surfaces={Surface.DIGEST}
            )
        )

    def test_false_for_a_different_app(self):
        self.assertFalse(
            selectors.has_impression(
                self.user.id, self.other_app.id, surfaces={Surface.DIGEST}
            )
        )

    def test_surface_filter_excludes_non_listed_surfaces(self):
        # The user's only impression is on DIGEST; an APP_PAGE-only query must not match it.
        self.assertFalse(
            selectors.has_impression(
                self.user.id, self.app.id, surfaces={Surface.APP_PAGE}
            )
        )
        # …and an APP_PAGE impression must not satisfy a DIGEST query.
        capture.record_impression(
            self.other_user, self.app.id, surface=Surface.APP_PAGE, occurred_at=_at(10)
        )
        self.assertFalse(
            selectors.has_impression(
                self.other_user.id, self.app.id, surfaces={Surface.DIGEST}
            )
        )

    def test_matches_any_of_several_surfaces(self):
        self.assertTrue(
            selectors.has_impression(
                self.user.id,
                self.app.id,
                surfaces={Surface.DIGEST, Surface.APP_PAGE},
            )
        )

    def test_as_of_boundary_is_inclusive(self):
        # An impression exactly at as_of counts; one strictly after does not.
        self.assertTrue(
            selectors.has_impression(
                self.user.id, self.app.id, surfaces={Surface.DIGEST}, as_of=_at(10)
            )
        )
        self.assertFalse(
            selectors.has_impression(
                self.user.id,
                self.app.id,
                surfaces={Surface.DIGEST},
                as_of=_at(10) - timedelta(seconds=1),
            )
        )

    def test_as_of_omitted_considers_any_time(self):
        self.assertTrue(
            selectors.has_impression(
                self.user.id, self.app.id, surfaces={Surface.DIGEST}, as_of=None
            )
        )
