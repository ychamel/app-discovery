"""T-05 — the uniform template's slots, empty states, accessibility (DESIGN.md §5c).

Rendered directly against hand-built ``CatalogApp`` DTOs (the template's only input) so we
can exercise the empty-tag / single-image / multi-image states the catalog's ≥1-tag/≥1-image
submission floor would otherwise prevent. The behavioral wiring is covered in test_views.
"""

import re
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from apps.catalog.selectors import CatalogApp, CatalogMedia, CatalogTag


def _media(position, *, alt="A screenshot"):
    return CatalogMedia(
        id=uuid4(), url=f"/media/shot{position}.png", alt_text=alt, position=position
    )


def _app(*, name="Demo", tags=None, media=None):
    return CatalogApp(
        id=uuid4(),
        name=name,
        description=f"{name} is a small vibecoded web app.",
        url="https://example.com/demo",
        tags=tags if tags is not None else [CatalogTag(id=uuid4(), label="Notes")],
        media=media if media is not None else [_media(0), _media(1)],
    )


def _render(app, *, imp=None):
    request = RequestFactory().get(f"/apps/{app.id}/")
    return render_to_string("pages/app_page.html", {"app": app, "imp": imp}, request=request)


# Landmarks contributed by the shared responsive shell (core/base.html), not by the page
# itself — excluded so this fingerprint stays about the page's own slots (platform-staging T-06).
_SHELL_CHROME_LABELS = {"Primary", "Messages"}


def _slot_labels(html):
    """The ordered sequence of the page's OWN slot landmarks (excluding the shared-shell
    chrome) — the structural fingerprint of the page."""
    labels = re.findall(r'aria-label="([^"]+)"', html)
    return [label for label in labels if label not in _SHELL_CHROME_LABELS]


class FullyPopulatedTests(SimpleTestCase):
    """AC1 — a complete app renders name, description, ordered media, categories, try-it."""

    def test_all_core_content_present(self):
        app = _app(name="Notable", tags=[CatalogTag(id=uuid4(), label="Notes")])
        html = _render(app, imp=uuid4())

        self.assertIn("Notable", html)
        self.assertIn("small vibecoded web app", html)
        self.assertIn("Notes", html)
        for media in app.media:
            self.assertIn(media.url, html)
            self.assertIn(media.alt_text, html)
        self.assertIn(f"/apps/{app.id}/try", html)

    def test_try_link_carries_impression_when_present(self):
        imp = uuid4()
        html = _render(_app(), imp=imp)
        self.assertIn(f"?imp={imp}", html)


class EmptyAndPartialStateTests(SimpleTestCase):
    """AC2 — empty/single states keep every slot present with no layout-collapsing variance.

    Slot count is 7: the six original app-page slots + the Follow slot the app-subscriptions
    feature inserts after the header (a sanctioned, viewer-state-driven section — DESIGN §5f).
    """

    def test_no_tags_shows_uncategorized(self):
        html = _render(_app(tags=[]))
        self.assertIn("Uncategorized", html)
        self.assertEqual(len(_slot_labels(html)), 7)

    def test_no_media_shows_placeholder_and_all_slots(self):
        html = _render(_app(media=[]))
        self.assertIn("No screenshots yet", html)
        self.assertEqual(len(_slot_labels(html)), 7)

    def test_single_image_renders_and_keeps_all_slots(self):
        html = _render(_app(media=[_media(0)]))
        self.assertEqual(html.count("<img"), 1)
        self.assertEqual(len(_slot_labels(html)), 7)


class StructuralUniformityTests(SimpleTestCase):
    """AC3 — uniformity is structural: same slots, same order, no identity/paid input."""

    def test_two_different_apps_render_identical_slot_order(self):
        rich = _app(
            name="Rich",
            tags=[CatalogTag(id=uuid4(), label="A")],
            media=[_media(0), _media(1)],
        )
        sparse = _app(name="Sparse", tags=[], media=[])
        self.assertEqual(_slot_labels(_render(rich)), _slot_labels(_render(sparse)))

    def test_dto_has_no_owner_team_or_paid_field(self):
        app = _app()
        for forbidden in ("owner", "team", "paid", "price", "developer"):
            self.assertFalse(hasattr(app, forbidden))


class ReviewsSlotTests(SimpleTestCase):
    """AC9 — the reviews slot is a defined empty state; no rating data is rendered."""

    def test_reviews_empty_state_present_no_rating_data(self):
        html = _render(_app())
        self.assertIn("Reviews coming soon", html)
        self.assertNotIn("★", html)
        self.assertNotRegex(html, r"\b\d(\.\d)?\s*/\s*5\b")


class PressKitAndAccessibilityTests(SimpleTestCase):
    def test_canonical_url_is_present_and_copyable(self):
        """AC4 — the canonical page URL is in a <link> and a readonly copyable field."""
        app = _app()
        html = _render(app)
        self.assertIn('rel="canonical"', html)
        self.assertIn(f"/apps/{app.id}/", html)
        self.assertIn('readonly', html)

    def test_every_image_has_non_empty_alt(self):
        html = _render(_app(media=[_media(0, alt="Home screen"), _media(1, alt="Editor view")]))
        alts = re.findall(r'<img[^>]*\salt="([^"]*)"', html)
        self.assertEqual(len(alts), 2)
        self.assertTrue(all(alt.strip() for alt in alts))

    def test_try_and_share_are_focusable_controls(self):
        html = _render(_app())
        self.assertRegex(html, r"<a\s[^>]*href=")  # try-it is a real link
        self.assertIn('<button type="submit">Share</button>', html)
