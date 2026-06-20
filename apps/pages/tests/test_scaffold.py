"""T-02 — the app-pages scaffold is installed, inert, and owns no schema (DESIGN.md §2/§4).

These pin the structural facts the design depends on: the app is registered, it owns no
model (so it never adds a migration), and its base chrome renders standalone.
"""

from django.apps import apps as django_apps
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class ScaffoldTests(SimpleTestCase):
    def test_app_is_installed(self):
        self.assertTrue(django_apps.is_installed("apps.pages"))

    def test_app_owns_no_model(self):
        """app-pages is a pure consumer — it must never define a model (DESIGN §2/§4)."""
        config = django_apps.get_app_config("pages")
        self.assertEqual(list(config.get_models()), [])

    def test_base_chrome_renders_standalone(self):
        html = render_to_string("pages/base.html")
        self.assertIn("<!DOCTYPE html>", html)
