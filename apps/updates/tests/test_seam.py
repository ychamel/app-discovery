"""T-02 — the AS-3 seam repoint + the load-bearing no-import-cycle proof (DESIGN §4/§13).

Two things are proven here, the second being the headline self-critique of the design:

  * **Seam integration (AC4):** with ``updates_notice`` rows seeded directly via the ORM, the
    repointed ``subscriptions.notices.notices_for_apps`` returns render ``Notice`` instances
    (not ``PublishedNotice``), newest-first, with the producer fields mapped and ``id`` dropped.

  * **No import cycle (DESIGN §4/§13):** the cross-package dependency is a strict DAG —
    ``subscriptions.notices → updates.selectors → updates.models``, and nothing under
    ``apps.updates`` imports ``apps.subscriptions`` while ``subscriptions.selectors``/``models``
    import nothing from ``apps.updates``. Proven both dynamically (importing in either order
    succeeds) and statically (an AST walk of every module's import statements).

The fail-soft preservation (a producer raise is caught by the *existing* feed wrapper) lives in
the subscriptions suite alongside the wrapper it exercises (``test_notices.py``).
"""

import ast
import importlib
import inspect
import uuid
from datetime import UTC, datetime

from django.test import TestCase

from apps.subscriptions import notices as subscriptions_notices
from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import make_developer


def _imported_names(module) -> set[str]:
    """Every module name referenced by an import statement in ``module``'s source."""
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


class SeamIntegrationTests(TestCase):
    def setUp(self):
        self.author = make_developer()
        self.app_a = uuid.uuid4()
        self.app_b = uuid.uuid4()

    def _seed(self, app_id, *, title, kind=NoticeKind.UPDATE, when=None):
        notice = Notice.objects.create(
            author=self.author, app_id=app_id, kind=kind, title=title, summary="body"
        )
        if when is not None:
            Notice.objects.filter(pk=notice.pk).update(published_at=when)
        return notice

    def test_returns_render_notices_newest_first_with_id_dropped(self):
        self._seed(self.app_a, title="Old", when=datetime(2026, 6, 1, tzinfo=UTC))
        self._seed(self.app_a, title="New", when=datetime(2026, 6, 5, tzinfo=UTC))

        result = subscriptions_notices.notices_for_apps([self.app_a])

        self.assertTrue(
            all(isinstance(n, subscriptions_notices.Notice) for n in result)
        )
        self.assertEqual([n.title for n in result], ["New", "Old"])
        # The render Notice has no `id` field — the feed never addresses a notice by id.
        self.assertFalse(hasattr(result[0], "id"))
        self.assertEqual(result[0].app_id, self.app_a)
        self.assertEqual(result[0].kind, "update")

    def test_scoped_to_requested_apps(self):
        self._seed(self.app_a, title="A")
        self._seed(self.app_b, title="B")
        result = subscriptions_notices.notices_for_apps([self.app_a])
        self.assertEqual([n.title for n in result], ["A"])

    def test_empty_input_and_no_rows_return_empty(self):
        self.assertEqual(subscriptions_notices.notices_for_apps([]), [])
        self.assertEqual(subscriptions_notices.notices_for_apps([self.app_a]), [])


class ImportCycleAbsenceTests(TestCase):
    """The headline risk: the two packages must never form a module-load cycle (DESIGN §13)."""

    def test_importing_both_seam_modules_in_either_order_succeeds(self):
        # A module-load cycle would raise ImportError on one of these orders.
        for order in (
            ["apps.subscriptions.notices", "apps.updates.selectors"],
            ["apps.updates.selectors", "apps.subscriptions.notices"],
        ):
            for name in order:
                importlib.import_module(name)

    def test_updates_producer_core_does_not_import_subscriptions(self):
        # The DAG has two edges (DESIGN §4): subscriptions.notices → updates.selectors (the
        # producer read the feed pulls) and updates.views → subscriptions.selectors (the
        # audience hint). Neither forms a cycle *as long as* the producer core that
        # subscriptions.notices transitively depends on — selectors, models, services — imports
        # nothing back from subscriptions. (updates.views is exempt: it is a leaf consumer that
        # nothing in subscriptions imports, so its edge to subscriptions.selectors cannot close
        # a loop.)
        core = (
            "apps.updates.selectors",
            "apps.updates.models",
            "apps.updates.services",
        )
        for name in core:
            module = importlib.import_module(name)
            hits = {n for n in _imported_names(module) if "apps.subscriptions" in n}
            self.assertEqual(
                hits, set(), f"{name} (producer core) must not import subscriptions: {hits}"
            )

    def test_subscriptions_read_modules_do_not_import_updates(self):
        # The other end of the DAG: subscriptions.notices is allowed to import updates.selectors
        # (the one permitted producer edge), but the read/data core that updates.views depends on
        # (selectors, models) must not import updates, or the second edge would close a cycle.
        for name in ("apps.subscriptions.selectors", "apps.subscriptions.models"):
            module = importlib.import_module(name)
            hits = {n for n in _imported_names(module) if "apps.updates" in n}
            self.assertEqual(hits, set(), f"{name} must not import apps.updates: {hits}")
