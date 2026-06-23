"""AC8 structural proof: the dashboard imports nothing from ``signals.capture`` (DESIGN §5.3/§8).

The cleanest proof that *viewing* a dashboard records no D-7 impression of the developer's own
app (so a developer can't inflate their own reach by looking at it) is that the app cannot
reach the corpus **emitter** at all — it never imports ``signals.capture``. The dashboard *does*
read ``signals.selectors`` (that is its whole job), so — unlike ``apps/discovery`` which forbids
*any* signals import — this test forbids the ``capture`` emitter specifically. We parse each
module's import statements (not its prose), so docstrings may name ``signals.capture`` freely.
"""

import ast
import importlib
import inspect
import pkgutil

from django.test import SimpleTestCase

import apps.dashboard


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


class DashboardImportsTests(SimpleTestCase):
    def test_no_module_in_the_app_imports_signals_capture(self):
        offenders: dict[str, set[str]] = {}
        for info in pkgutil.walk_packages(
            apps.dashboard.__path__, prefix="apps.dashboard."
        ):
            if info.name.endswith(".tests") or ".tests." in info.name:
                continue  # tests may reference capture to patch/seed
            module = importlib.import_module(info.name)
            capture_imports = {
                name for name in _imported_names(module) if "signals.capture" in name
            }
            if capture_imports:
                offenders[info.name] = capture_imports
        self.assertEqual(
            offenders, {}, f"dashboard must not import signals.capture: {offenders}"
        )
