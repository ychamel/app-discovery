"""Tests for the catalog Django-admin registration (T-13, DESIGN.md §3/§9).

App and ReviewDecision are registered for inspection, and ReviewDecision is append-only in
admin (no add/change/delete) so the gate audit cannot be edited away.
"""

from django.contrib import admin
from django.test import TestCase

from apps.catalog.models import App, ReviewDecision


class AdminRegistrationTests(TestCase):
    def test_models_are_registered(self):
        self.assertIn(App, admin.site._registry)
        self.assertIn(ReviewDecision, admin.site._registry)

    def test_review_decision_is_append_only(self):
        decision_admin = admin.site._registry[ReviewDecision]
        self.assertFalse(decision_admin.has_add_permission(None))
        self.assertFalse(decision_admin.has_change_permission(None))
        self.assertFalse(decision_admin.has_delete_permission(None))

    def test_app_status_is_read_only_in_admin(self):
        app_admin = admin.site._registry[App]
        self.assertIn("status", app_admin.readonly_fields)
