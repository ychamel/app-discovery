"""T-01 — the code-fixed facet registry (DESIGN.md §4/§5.3).

Pure-declaration tests: no DB is touched, so these run as ``SimpleTestCase``. They pin the
vocabulary, the closed-set validation, cardinality, and the graceful registry-ordered
resolve that silently drops a value no longer in the registry (the D-5 pattern).
"""

from dataclasses import dataclass

from django.test import SimpleTestCase

from apps.catalog import facets


@dataclass
class _Row:
    """A stand-in for an ``AppFacet`` row — resolve_facets only needs .facet / .value."""

    facet: str
    value: str


class FacetRegistryTests(SimpleTestCase):
    def test_facet_keys_in_registry_order(self):
        self.assertEqual(
            facets.facet_keys(), ["pricing", "maturity", "modality", "platform"]
        )

    def test_valid_facet_value_accepted(self):
        self.assertTrue(facets.is_valid_facet_value("pricing", "free"))
        self.assertTrue(facets.is_valid_facet_value("platform", "mobile"))

    def test_off_vocabulary_facet_rejected(self):
        self.assertFalse(facets.is_valid_facet_value("genre", "free"))

    def test_off_vocabulary_value_rejected(self):
        # A value that belongs to *no* facet, and a value valid for a *different* facet.
        self.assertFalse(facets.is_valid_facet_value("pricing", "gratis"))
        self.assertFalse(facets.is_valid_facet_value("pricing", "mobile"))

    def test_cardinality_per_facet(self):
        self.assertEqual(facets.cardinality_of("pricing"), facets.FacetCardinality.SINGLE)
        self.assertEqual(facets.cardinality_of("maturity"), facets.FacetCardinality.SINGLE)
        self.assertEqual(facets.cardinality_of("modality"), facets.FacetCardinality.MULTI)
        self.assertEqual(facets.cardinality_of("platform"), facets.FacetCardinality.MULTI)

    def test_cardinality_of_unknown_facet_raises(self):
        with self.assertRaises(KeyError):
            facets.cardinality_of("genre")


class ResolveFacetsTests(SimpleTestCase):
    def test_resolves_in_registry_order_not_storage_order(self):
        # Stored out of order (platform before pricing, mobile before web) → registry order.
        rows = [
            _Row("platform", "mobile"),
            _Row("pricing", "free"),
            _Row("platform", "web"),
        ]
        resolved = facets.resolve_facets(rows)

        self.assertEqual([r.facet for r in resolved], ["pricing", "platform"])
        platform = resolved[1]
        self.assertEqual([v.key for v in platform.values], ["web", "mobile"])
        self.assertEqual(platform.label, "Platform")
        self.assertEqual([v.label for v in resolved[0].values], ["Free"])

    def test_registry_absent_value_silently_dropped(self):
        # A value removed from the registry must never raise — it just disappears (D-5).
        rows = [_Row("pricing", "free"), _Row("pricing", "gratis"), _Row("ghost", "x")]
        resolved = facets.resolve_facets(rows)

        self.assertEqual(len(resolved), 1)
        self.assertEqual([v.key for v in resolved[0].values], ["free"])

    def test_empty_rows_returns_empty(self):
        self.assertEqual(facets.resolve_facets([]), [])

    def test_facet_with_only_invalid_values_omitted(self):
        resolved = facets.resolve_facets([_Row("pricing", "gratis")])
        self.assertEqual(resolved, [])


class FacetModulePurityTests(SimpleTestCase):
    """The registry is pure declaration: no Django model, no DB (the gate.py precedent)."""

    def test_module_imports_no_models_and_no_db(self):
        import ast
        import inspect

        source = inspect.getsource(facets)
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")

        self.assertNotIn("django.db", imported)
        self.assertFalse(
            any(name.startswith("apps.") and name.endswith("models") for name in imported),
            f"facets.py must not import any models: {imported}",
        )
