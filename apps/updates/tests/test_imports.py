"""AC6 structural proof: the updates app imports nothing from ``signals`` (DESIGN §8).

The transparency line: a developer controls *content* (a notice reaching an audience they
already earned) but never *signal*. The cleanest proof that posting can never confer
corpus value is that the producer app cannot emit a D-7 signal at all — it never imports the
corpus emitter. We parse each module's import statements (not its prose), so docstrings may
name ``signals`` freely. Mirrors ``apps/discovery/tests/test_imports.py``.
"""

import ast
import importlib
import inspect
import pkgutil

from django.test import TestCase

import apps.updates


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


class UpdatesImportsTests(TestCase):
    def test_no_module_in_the_app_imports_signals(self):
        offenders: dict[str, set[str]] = {}
        for info in pkgutil.walk_packages(
            apps.updates.__path__, prefix="apps.updates."
        ):
            if info.name.endswith(".tests") or ".tests." in info.name:
                continue  # tests may reference signals to patch them
            module = importlib.import_module(info.name)
            signals_imports = {n for n in _imported_names(module) if "signals" in n}
            if signals_imports:
                offenders[info.name] = signals_imports
        self.assertEqual(offenders, {}, f"updates must not import signals: {offenders}")
