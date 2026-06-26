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
    def test_no_module_in_the_app_imports_signals(self):
        offenders: dict[str, set[str]] = {}
        for info in pkgutil.walk_packages(
            apps.widget.__path__, prefix="apps.widget."
        ):
            if info.name.endswith(".tests") or ".tests." in info.name:
                continue  # tests may reference signals to assert the corpus stays empty
            module = importlib.import_module(info.name)
            signals_imports = {n for n in _imported_names(module) if "signals" in n}
            if signals_imports:
                offenders[info.name] = signals_imports
        self.assertEqual(offenders, {}, f"widget must not import signals: {offenders}")
