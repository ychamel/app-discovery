"""Tests for the URL normalizer (T-03 / DESIGN.md §6c).

Table-driven over equivalence classes: URLs in the same class must normalize to one
string (the duplicate signal fires); URLs in different classes must stay distinct (no
false merge of two different apps).
"""

from django.test import SimpleTestCase

from apps.catalog.urlnorm import normalize_url

# Each row: a set of URLs that must all collapse to the same normalized string.
_EQUIVALENT = [
    # Scheme case.
    ["https://example.com/app", "HTTPS://example.com/app"],
    # Host case.
    ["https://Example.COM/app", "https://example.com/app"],
    # Default port stripped.
    ["https://example.com:443/app", "https://example.com/app"],
    ["http://example.com:80/app", "http://example.com/app"],
    # Trailing slash on a path.
    ["https://example.com/app/", "https://example.com/app"],
    # Root path normalization.
    ["https://example.com", "https://example.com/"],
    # All four cosmetic differences at once.
    ["HTTP://Example.com:80/App/", "http://example.com/App"],
]

# Each row: two URLs that must stay distinct (genuinely different app).
_DISTINCT = [
    ("https://example.com/a", "https://example.com/b"),  # different path
    ("https://example.com", "https://other.com"),  # different host
    ("http://example.com/app", "https://example.com/app"),  # different scheme (not cosmetic)
    ("https://example.com/app", "https://www.example.com/app"),  # www is not collapsed
    ("https://example.com/app?x=1", "https://example.com/app?x=2"),  # different query
    ("https://example.com:8443/app", "https://example.com/app"),  # non-default port kept
    ("https://example.com/App", "https://example.com/app"),  # path case is significant
]


class NormalizeUrlEquivalenceTests(SimpleTestCase):
    def test_cosmetic_variants_collapse(self):
        for group in _EQUIVALENT:
            normalized = {normalize_url(url) for url in group}
            self.assertEqual(
                len(normalized), 1, f"expected {group} to share one normalized form: {normalized}"
            )

    def test_distinct_apps_stay_distinct(self):
        for left, right in _DISTINCT:
            self.assertNotEqual(
                normalize_url(left),
                normalize_url(right),
                f"{left!r} and {right!r} must not collapse",
            )


class NormalizeUrlPropertyTests(SimpleTestCase):
    def test_idempotent(self):
        samples = [
            "https://example.com/app",
            "HTTP://Example.com:80/App/",
            "https://example.com",
            "https://example.com/a/b/c/?q=1#frag",
        ]
        for url in samples:
            once = normalize_url(url)
            self.assertEqual(normalize_url(once), once, f"not idempotent for {url!r}")

    def test_surrounding_whitespace_stripped(self):
        self.assertEqual(
            normalize_url("  https://example.com/app  "),
            normalize_url("https://example.com/app"),
        )
