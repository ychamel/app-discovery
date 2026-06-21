"""T-08 — the Subscription admin is read-only (DESIGN §5 / §5a invariant).

Writes go only through ``services`` (the follow row + its atomic ``subscribe`` emit); the
admin must never offer an add/change/delete path that would create a follow without its event.
"""

from django.contrib import admin
from django.test import TestCase

from apps.subscriptions.models import Subscription


class SubscriptionAdminTests(TestCase):
    def setUp(self):
        self.model_admin = admin.site._registry[Subscription]

    def test_is_registered(self):
        self.assertIn(Subscription, admin.site._registry)

    def test_no_add_change_or_delete_permission(self):
        self.assertFalse(self.model_admin.has_add_permission(request=None))
        self.assertFalse(self.model_admin.has_change_permission(request=None))
        self.assertFalse(self.model_admin.has_delete_permission(request=None))
