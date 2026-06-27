"""AC6 structural proof: the widget app imports nothing from ``signals`` (DESIGN §3/§9).

The headline integrity property of this feature is that a widget interaction can never confer
curated-rating eligibility (D-8). The cleanest proof is that the widget app **cannot emit a D-7
signal at all** — no module in it imports the corpus emitter. We parse each module's import
statements (not its prose), so docstrings may name ``signals`` freely. Mirrors
``apps/discovery/tests/test_imports.py`` (the established precedent).
"""

import ast
import importlib
import inspect
import pkgutil

from django.test import TestCase

import apps.widget


def _imported_names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported.add(base)
            imported.update(f"{base}.{alias.name}" for alias in node.names)
    return imported


class WidgetImportsTests(TestCase):
    def _non_test_modules(self) -> dict[str, object]:
        modules: dict[str, object] = {}
        for info in pkgutil.walk_packages(
            apps.widget.__path__, prefix="apps.widget."
        ):
            if info.name.endswith(".tests") or ".tests." in info.name:
                continue  # tests may reference signals to assert the corpus stays empty
            modules[info.name] = importlib.import_module(info.name)
        return modules

    def test_no_module_in_the_app_imports_signals(self):
        offenders: dict[str, set[str]] = {}
        for name, module in self._non_test_modules().items():
            signals_imports = {n for n in _imported_names(module) if "signals" in n}
            if signals_imports:
                offenders[name] = signals_imports
        self.assertEqual(offenders, {}, f"widget must not import signals: {offenders}")

    def test_the_new_attribution_modules_are_actually_walked(self):
        """Guard the firewall proof: the new conversion-side modules must be in the swept set, so a
        future `from apps.signals` in any is caught — not silently skipped (DESIGN §12)."""
        walked = set(self._non_test_modules())
        for required in (
            "apps.widget.rollup",
            "apps.widget.attribution",
            "apps.widget.source",
        ):
            self.assertIn(required, walked)
