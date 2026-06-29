"""T-09 — the two hard structural invariants of app-page-redesign (DESIGN.md §12).

These are not behaviour tests — they are *structural* guards that the load-bearing fairness
and firewall properties are unrepresentable to break, not merely unbroken today:

  (i)  **Uniformity** (AC-7/R2): the page read-model carries no tier/payment/identity field,
       so a richer page can never be unlocked by *who* an app is — only by its *content*. (The
       template-side "same slots regardless of content" proof lives in pages/test_template.)
  (ii) **Firewall** (AC-3/AC-6/D-14a, M5=0): typed facets are read by **no** ranking/discovery
       path, and the on-page devlog slot adds **no** ``signals`` emission — so neither can ever
       affect a score.
"""

import ast
import importlib
import inspect
import pkgutil
from dataclasses import fields

from django.test import SimpleTestCase

from apps.catalog import selectors


def _imported_names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)
    return names


class UniformityInvariantTests(SimpleTestCase):
    def test_page_read_model_has_no_identity_or_tier_field(self):
        # The only identity surfaced is the developer block (display_name only). No field that
        # could gate richness by identity/tier/payment exists on the page read-model.
        names = {f.name for f in fields(selectors.AppPageContent)}
        forbidden = {
            "tier", "plan", "paid", "price", "payment", "priority", "featured", "rank", "boost",
        }
        self.assertEqual(names & forbidden, set())

    def test_developer_block_exposes_display_name_only(self):
        # No email/PII can leak from the identity block — the DTO simply has no such field.
        names = {f.name for f in fields(selectors.CatalogDeveloper)}
        self.assertEqual(names, {"id", "display_name"})


class RankingFirewallInvariantTests(SimpleTestCase):
    def test_search_and_match_paths_never_read_facets(self):
        # AppFacet is NOT AppTag: it must not enter the open-discovery query or the tag filter.
        for func in (selectors.search_catalogue, selectors._accepted_matching):
            source = inspect.getsource(func)
            self.assertNotIn("app_facets", source)
            self.assertNotIn("AppFacet", source)

    def test_discovery_and_interests_apps_never_reference_facets(self):
        # Scan the whole discovery + interests packages: no facet storage is read by ranking.
        offenders: dict[str, list[str]] = {}
        for package in ("apps.discovery", "apps.interests"):
            root = importlib.import_module(package)
            for info in pkgutil.walk_packages(root.__path__, prefix=f"{package}."):
                if info.name.endswith(".tests") or ".tests." in info.name:
                    continue
                module = importlib.import_module(info.name)
                source = inspect.getsource(module)
                hits = [token for token in ("AppFacet", "app_facets") if token in source]
                if hits:
                    offenders[info.name] = hits
        self.assertEqual(offenders, {}, f"ranking/discovery must not read facets: {offenders}")


class DevlogFirewallInvariantTests(SimpleTestCase):
    def test_devlog_tag_imports_nothing_from_signals(self):
        # M5=0 structural: surfacing the devlog adds no score-affecting event (no signals import).
        from apps.updates.templatetags import updates_tags

        signals_imports = {n for n in _imported_names(updates_tags) if "signals" in n}
        self.assertEqual(signals_imports, set())
