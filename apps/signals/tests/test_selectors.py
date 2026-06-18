"""T-07 — the raw funnel read path, incl. derived returns (DESIGN.md §5b/§9; SC-9).

Builds a known corpus through the capture recorders and asserts every funnel field is
reconstructed from stored rows with no backfill — counts (AC8/AC9), the window-boundary
returns derivation (AC4), proxy segregation (AC7), no-N+1 (AC9), and the per-category
baseline (AC2).
"""

from datetime import UTC, datetime

from django.test import TestCase, override_settings

from apps.signals import capture, selectors
from apps.signals.kinds import Surface
from apps.signals.tests.helpers import make_accepted_app, make_tag, make_user


def _at(day: int, hour: int = 12) -> datetime:
    """A fixed UTC instant on 2026-06-<day> for deterministic window math."""
    return datetime(2026, 6, day, hour, tzinfo=UTC)


WINDOW = {"start": _at(1, 0), "end": _at(28, 0)}


class AppFunnelCountTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])
        self.impression = capture.record_impression(
            self.user, self.app.id, surface=Surface.DIGEST, occurred_at=_at(2)
        )

    def test_counts_each_funnel_field_from_stored_rows(self):
        capture.record_click_through(
            self.user, self.app.id, impression=self.impression, occurred_at=_at(2)
        )
        capture.record_subscribe(self.user, self.app.id, occurred_at=_at(3))
        capture.record_page_reengagement(self.user, self.app.id, occurred_at=_at(3))
        capture.record_share(self.user, self.app.id, occurred_at=_at(4))
        capture.record_off_platform_proxy(
            self.user, self.app.id, impression=self.impression, occurred_at=_at(4)
        )

        funnel = selectors.app_funnel(self.app.id, **WINDOW)

        self.assertEqual(funnel.impressions, 1)
        self.assertEqual(funnel.click_throughs, 1)
        self.assertEqual(funnel.subscribes, 1)
        self.assertEqual(funnel.page_reengagements, 1)
        self.assertEqual(funnel.shares, 1)
        self.assertEqual(funnel.off_platform_proxy, 1)

    def test_proxy_is_never_folded_into_click_throughs(self):
        capture.record_off_platform_proxy(
            self.user, self.app.id, impression=self.impression, occurred_at=_at(2)
        )
        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        self.assertEqual(funnel.click_throughs, 0)
        self.assertEqual(funnel.off_platform_proxy, 1)

    def test_out_of_window_events_excluded(self):
        capture.record_subscribe(self.user, self.app.id, occurred_at=_at(2))
        narrow = selectors.app_funnel(self.app.id, start=_at(10), end=_at(20))
        self.assertEqual(narrow.impressions, 0)
        self.assertEqual(narrow.subscribes, 0)


class ReturnsDerivationTests(TestCase):
    """AC4/SC-9 — returns are derived from impression × PlatformVisit at the window boundary."""

    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app = make_accepted_app(self.owner, tag_ids=[self.tag.id])

    def _impress(self, user, day: int):
        return capture.record_impression(
            user, self.app.id, surface=Surface.DIGEST, occurred_at=_at(day)
        )

    def test_visit_on_day_plus_3_counts_in_both_windows(self):
        user = make_user("u3@example.com")
        self._impress(user, 2)  # shown on the 2nd
        capture.record_platform_visit(user, on_date=_at(5).date())  # +3 days

        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        self.assertEqual(funnel.returns_3d, 1)
        self.assertEqual(funnel.returns_14d, 1)

    def test_visit_on_day_plus_10_counts_only_in_long_window(self):
        user = make_user("u10@example.com")
        self._impress(user, 2)
        capture.record_platform_visit(user, on_date=_at(12).date())  # +10 days

        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        self.assertEqual(funnel.returns_3d, 0)
        self.assertEqual(funnel.returns_14d, 1)

    def test_no_in_window_visit_counts_in_neither(self):
        user = make_user("u0@example.com")
        self._impress(user, 2)
        # No return visit at all → the not-returned outcome is representable as absence.

        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        self.assertEqual(funnel.returns_3d, 0)
        self.assertEqual(funnel.returns_14d, 0)

    def test_same_day_visit_is_not_a_return(self):
        user = make_user("usd@example.com")
        self._impress(user, 2)
        capture.record_platform_visit(user, on_date=_at(2).date())  # same day

        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        self.assertEqual(funnel.returns_3d, 0)
        self.assertEqual(funnel.returns_14d, 0)

    @override_settings(RETURN_WINDOW_SHORT_DAYS=7)
    def test_window_length_comes_from_config(self):
        user = make_user("ucfg@example.com")
        self._impress(user, 2)
        capture.record_platform_visit(user, on_date=_at(8).date())  # +6 days

        funnel = selectors.app_funnel(self.app.id, **WINDOW)
        # +6 is outside the default 3-day window but inside the overridden 7-day one.
        self.assertEqual(funnel.returns_3d, 1)


class FunnelForAppsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.tag = make_tag("notes")
        self.app_a = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="App A")
        self.app_b = make_accepted_app(self.owner, tag_ids=[self.tag.id], name="App B")

    def test_bulk_funnel_does_not_n_plus_one(self):
        for app in (self.app_a, self.app_b):
            imp = capture.record_impression(
                self.user, app.id, surface=Surface.DIGEST, occurred_at=_at(2)
            )
            capture.record_click_through(
                self.user, app.id, impression=imp, occurred_at=_at(2)
            )

        # Two grouped queries total, independent of the number of apps (no N+1).
        with self.assertNumQueries(2):
            funnels = selectors.funnel_for_apps(
                [self.app_a.id, self.app_b.id], **WINDOW
            )

        self.assertEqual(len(funnels), 2)
        self.assertEqual([f.app_id for f in funnels], [self.app_a.id, self.app_b.id])
        self.assertTrue(all(f.click_throughs == 1 for f in funnels))

    def test_app_with_no_signal_returns_zero_filled_funnel(self):
        funnels = selectors.funnel_for_apps([self.app_a.id], **WINDOW)
        self.assertEqual(funnels[0].impressions, 0)
        self.assertEqual(funnels[0].click_throughs, 0)

    def test_funnel_dto_has_no_score_field(self):
        funnels = selectors.funnel_for_apps([self.app_a.id], **WINDOW)
        for forbidden in ("score", "weight", "rank", "normalized"):
            self.assertFalse(hasattr(funnels[0], forbidden))


class CategoryImpressionsTests(TestCase):
    def test_counts_impressions_whose_snapshot_includes_tag(self):
        user = make_user()
        owner = make_user("owner@example.com")
        tag_a = make_tag("notes")
        tag_b = make_tag("todo")
        app_a = make_accepted_app(owner, tag_ids=[tag_a.id], name="App A")
        app_b = make_accepted_app(owner, tag_ids=[tag_b.id], name="App B")

        capture.record_impression(user, app_a.id, surface=Surface.DIGEST, occurred_at=_at(2))
        capture.record_impression(user, app_a.id, surface=Surface.DIGEST, occurred_at=_at(3))
        capture.record_impression(user, app_b.id, surface=Surface.DIGEST, occurred_at=_at(3))

        self.assertEqual(selectors.category_impressions(tag_a.id, **WINDOW), 2)
        self.assertEqual(selectors.category_impressions(tag_b.id, **WINDOW), 1)
