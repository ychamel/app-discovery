"""T-08 — the redesigned launch page template (app-page-redesign DESIGN.md §7).

Rendered directly against hand-built ``AppPageContent`` DTOs (the template's only input) so we
can exercise the empty/populated states the submission floor would otherwise prevent. The
cross-app inclusion tags (reviews/follow/devlog) render their fail-soft degraded state under a
``SimpleTestCase`` (no DB) — that is their contract; their behavioural wiring lives in
test_views and each feature's own tests.

The load-bearing assertions: tagline as copy + meta description (AC-1); demo clip as a muted
aria-labelled video peer (AC-2); facets as a fact strip (AC-3); the deep dive as a no-JS
``<details>`` (AC-4); the developer hub with display_name + ACCEPTED-only other apps (AC-5);
and **structural uniformity** — two wildly different apps render the identical always-present
slot set/order (AC-7).
"""

import re
from uuid import uuid4

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from apps.catalog.facets import FacetValue
from apps.catalog.selectors import (
    AppPageContent,
    CatalogApp,
    CatalogDeveloper,
    CatalogFacet,
    CatalogMedia,
    CatalogTag,
)

# The always-present slot landmarks (the structural fingerprint). The deep-dive <details> is
# content-conditional (shown only when the developer wrote one) — fair, not identity-gated —
# so it is excluded from the always-present fingerprint.
_ALWAYS_SLOTS = [
    "hero", "media", "about", "developer", "devlog", "try", "follow", "share", "reviews",
]


def _media(position, *, alt="A screenshot"):
    return CatalogMedia(
        id=uuid4(), url=f"/media/shot{position}.png", alt_text=alt, position=position
    )


def _catalog_app(name="Other"):
    return CatalogApp(
        id=uuid4(), name=name, description="d", url="https://example.com/other",
        tags=[CatalogTag(id=uuid4(), label="Notes")], media=[],
    )


def _content(*, name="Demo", tagline="", deep_dive="", demo_clip_url=None, demo_clip_alt="",
             tags=None, media=None, facets=None, other_apps=None, developer_name="Acme Studio"):
    return AppPageContent(
        id=uuid4(),
        name=name,
        description=f"{name} is a small vibecoded web app.",
        url="https://example.com/demo",
        tags=tags if tags is not None else [CatalogTag(id=uuid4(), label="Notes")],
        media=media if media is not None else [_media(0), _media(1)],
        tagline=tagline,
        deep_dive=deep_dive,
        demo_clip_url=demo_clip_url,
        demo_clip_alt=demo_clip_alt,
        facets=facets if facets is not None else [],
        developer=CatalogDeveloper(id=uuid4(), display_name=developer_name),
        other_apps=other_apps if other_apps is not None else [],
    )


def _render(app, *, imp=None):
    request = RequestFactory().get(f"/apps/{app.id}/")
    return render_to_string("pages/app_page.html", {"app": app, "imp": imp}, request=request)


def _slots(html):
    """The ordered always-present slot landmarks (excludes the conditional deep-dive)."""
    return [s for s in re.findall(r'data-slot="([^"]+)"', html) if s != "deep-dive"]


class CoreContentTests(SimpleTestCase):
    def test_all_core_content_present(self):
        app = _content(name="Notable", tags=[CatalogTag(id=uuid4(), label="Notes")])
        html = _render(app, imp=uuid4())
        self.assertIn("Notable", html)
        self.assertIn("small vibecoded web app", html)
        self.assertIn("Notes", html)
        for media in app.media:
            self.assertIn(media.url, html)
        self.assertIn(f"/apps/{app.id}/try", html)

    def test_try_anchor_bypasses_htmx_and_opens_new_tab(self):
        # BUG-004 carried forward: the Try anchor follows the redirect natively (not via AJAX).
        html = _render(_content())
        self.assertIn('hx-boost="false"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)

    def test_try_link_carries_impression(self):
        imp = uuid4()
        self.assertIn(f"?imp={imp}", _render(_content(), imp=imp))


class PitchTests(SimpleTestCase):
    """AC-1 — the pitch line shows above the fold and as the meta description."""

    def test_tagline_renders_and_is_meta_description(self):
        html = _render(_content(tagline="The fastest way to ship."))
        self.assertIn("The fastest way to ship.", html)
        self.assertRegex(html, r'<meta name="description" content="The fastest way to ship\.">')

    def test_empty_tagline_breaks_nothing(self):
        html = _render(_content(tagline=""))
        self.assertNotIn('<meta name="description"', html)
        self.assertEqual(_slots(html), _ALWAYS_SLOTS)  # all slots still present


class DemoClipTests(SimpleTestCase):
    """AC-2 — the demo clip is a muted, alt-described video peer; no hosted-video dependency."""

    def test_clip_renders_as_muted_aria_labelled_video(self):
        html = _render(_content(demo_clip_url="/media/app_clips/x.mp4", demo_clip_alt="A 10s tour"))
        self.assertRegex(html, r"<video[^>]*\bmuted\b")
        self.assertRegex(html, r"<video[^>]*\bloop\b")
        self.assertIn('aria-label="A 10s tour"', html)
        self.assertIn("/media/app_clips/x.mp4", html)
        # No third-party embed (youtube/vimeo/iframe) — self-hosted only.
        self.assertNotIn("<iframe", html)

    def test_no_clip_keeps_screenshots(self):
        html = _render(_content(demo_clip_url=None))
        self.assertNotIn("<video", html)
        self.assertIn("<img", html)


class FacetTests(SimpleTestCase):
    """AC-3 — facets render as an at-a-glance fact strip."""

    def test_facets_render_in_fact_strip(self):
        facets = [
            CatalogFacet(facet="pricing", label="Pricing", values=[FacetValue("free", "Free")]),
            CatalogFacet(facet="platform", label="Platform",
                         values=[FacetValue("web", "Web"), FacetValue("mobile", "Mobile")]),
        ]
        html = _render(_content(facets=facets))
        self.assertIn("fact-strip", html)
        self.assertIn(">Free<", html)
        self.assertIn(">Web<", html)
        self.assertIn(">Mobile<", html)


class DeepDiveTests(SimpleTestCase):
    """AC-4 — the deep dive is a native <details> 'show more', reachable with JS disabled."""

    def test_deep_dive_is_native_details_no_js(self):
        html = _render(_content(deep_dive="A much longer story about the app."))
        self.assertRegex(html, r"<details[^>]*data-slot=\"deep-dive\"")
        self.assertIn("<summary", html)
        self.assertIn("A much longer story about the app.", html)
        # The deep dive must not depend on JS/HTMX to be reachable.
        deep_dive_block = re.search(r"<details.*?</details>", html, re.DOTALL).group(0)
        self.assertNotIn("hx-", deep_dive_block)

    def test_no_deep_dive_omits_the_details(self):
        html = _render(_content(deep_dive=""))
        self.assertNotIn('data-slot="deep-dive"', html)
        self.assertEqual(_slots(html), _ALWAYS_SLOTS)  # always-present slots unaffected


class DeveloperHubTests(SimpleTestCase):
    """AC-5 — identity is display_name + ACCEPTED-only other apps; no email/PII."""

    def test_developer_name_and_other_apps_render(self):
        others = [_catalog_app("Sibling One"), _catalog_app("Sibling Two")]
        html = _render(_content(developer_name="Acme Studio", other_apps=others))
        self.assertIn("An app by Acme Studio", html)
        self.assertIn("Sibling One", html)
        for other in others:
            self.assertIn(f"/apps/{other.id}/", html)

    def test_no_other_apps_when_solo(self):
        html = _render(_content(other_apps=[]))
        self.assertNotIn("More from this developer", html)
        self.assertIn('data-slot="developer"', html)  # the slot landmark is still present

    def test_no_email_or_pii_in_identity_block(self):
        html = _render(_content(developer_name="Acme Studio"))
        self.assertNotIn("@", html.split('data-slot="developer"')[1].split("</section>")[0])


class StructuralUniformityTests(SimpleTestCase):
    """AC-7 — uniformity is structural: same slots, same order, regardless of content."""

    def test_two_wildly_different_apps_render_identical_slots(self):
        rich = _content(
            name="Rich",
            tagline="A bold pitch.",
            deep_dive="A long story.",
            demo_clip_url="/media/app_clips/x.mp4",
            demo_clip_alt="tour",
            tags=[CatalogTag(id=uuid4(), label="A"), CatalogTag(id=uuid4(), label="B")],
            media=[_media(0), _media(1)],
            facets=[CatalogFacet("pricing", "Pricing", [FacetValue("free", "Free")])],
            other_apps=[_catalog_app("Sib")],
        )
        sparse = _content(name="Sparse", tags=[], media=[], facets=[], other_apps=[])
        self.assertEqual(_slots(_render(rich)), _ALWAYS_SLOTS)
        self.assertEqual(_slots(_render(rich)), _slots(_render(sparse)))

    def test_read_model_has_no_tier_payment_or_identity_field(self):
        app = _content()
        for forbidden in ("owner", "team", "paid", "price", "tier", "priority", "featured"):
            self.assertFalse(hasattr(app, forbidden))


class PressKitAndAccessibilityTests(SimpleTestCase):
    def test_canonical_url_present_and_copyable(self):
        app = _content()
        html = _render(app)
        self.assertIn('rel="canonical"', html)
        self.assertIn(f"/apps/{app.id}/", html)
        self.assertIn("readonly", html)

    def test_every_screenshot_has_non_empty_alt(self):
        html = _render(_content(media=[_media(0, alt="Home screen"), _media(1, alt="Editor view")]))
        alts = re.findall(r'<img[^>]*\salt="([^"]*)"', html)
        self.assertEqual(len(alts), 2)
        self.assertTrue(all(alt.strip() for alt in alts))

    def test_try_and_share_are_focusable_controls(self):
        html = _render(_content())
        self.assertRegex(html, r"<a\s[^>]*href=")
        self.assertIn('<button type="submit">Share</button>', html)
