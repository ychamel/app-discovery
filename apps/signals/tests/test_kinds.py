"""T-02 — the event vocabularies are closed and exactly as specified (DESIGN.md §3/§4).

These tests pin the *exact* member set so a new kind/surface cannot be slipped in
unreviewed: adding one is a deliberate edit that must also update this test.
"""

from django.test import SimpleTestCase

from apps.signals.kinds import EventKind, Surface


class EventKindTests(SimpleTestCase):
    def test_exactly_the_five_kinds(self):
        self.assertEqual(
            set(EventKind.values),
            {
                "click_through",
                "subscribe",
                "page_reengagement",
                "share",
                "off_platform_proxy",
            },
        )


class SurfaceTests(SimpleTestCase):
    def test_exactly_the_known_surfaces(self):
        # digest (signal-capture MVP) + app_page (app-pages additive extension, DESIGN §11).
        self.assertEqual(set(Surface.values), {"digest", "app_page"})
