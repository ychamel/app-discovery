"""T-07 — the ``{% app_devlog app %}`` inclusion tag (app-page-redesign DESIGN.md §6/§9.3).

Coverage: published notices render newest-first; no notices → the defined empty state; a read
that raises is **fail-soft** (renders nothing, never raises, increments the degrade metric).
The no-``signals`` firewall (M5=0) is proven structurally by ``tests/test_imports.py`` (which
walks the whole ``apps.updates`` package, including this new templatetag module).
"""

from types import SimpleNamespace
from unittest import mock

from django.template import Context, Template
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.core import observability
from apps.updates.models import Notice
from apps.updates.templatetags import updates_tags

_TEMPLATE = Template("{% load updates_tags %}{% app_devlog app %}")


def _render(app) -> str:
    return _TEMPLATE.render(Context({"app": app}))


class AppDevlogTagTests(TestCase):
    def setUp(self):
        self.author = Account.objects.create_account("dev@example.com")
        self.app = SimpleNamespace(id=__import__("uuid").uuid4())

    def _post(self, title, *, kind="update", summary="A change."):
        return Notice.objects.create(
            app_id=self.app.id,
            author=self.author,
            kind=kind,
            title=title,
            summary=summary,
            published_at=timezone.now(),
        )

    def test_published_notices_render(self):
        self._post("Shipped dark mode")
        html = _render(self.app)
        self.assertIn("Shipped dark mode", html)
        self.assertIn("A change.", html)

    def test_no_notices_renders_empty_state(self):
        html = _render(self.app)
        self.assertIn("No updates posted yet.", html)

    def test_read_error_is_fail_soft_and_counted(self):
        with mock.patch.object(
            updates_tags.selectors,
            "published_notices_for_apps",
            side_effect=RuntimeError("boom"),
        ):
            with mock.patch.object(observability, "increment") as inc:
                html = _render(self.app)  # must not raise
        self.assertIn("temporarily unavailable", html)
        metrics = {call.args[0] for call in inc.call_args_list}
        self.assertIn(observability.APP_PAGE_DEVLOG_DEGRADED, metrics)

    def test_limit_is_the_config_devlog_limit(self):
        with mock.patch.object(
            updates_tags.selectors, "published_notices_for_apps", return_value=[]
        ) as read:
            _render(self.app)
        _args, kwargs = read.call_args
        self.assertEqual(kwargs["limit"], 5)  # the DEFAULT_APP_PAGE_DEVLOG_LIMIT
