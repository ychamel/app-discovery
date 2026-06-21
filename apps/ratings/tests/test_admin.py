"""T-08 — the Rating admin is read-only (DESIGN §4 / §5a invariant).

Writes go only through ``services``; the admin must never offer an add/change/delete path.
"""

from django.contrib import admin
from django.test import TestCase

from apps.ratings.models import Rating


class RatingAdminTests(TestCase):
    def setUp(self):
        self.model_admin = admin.site._registry[Rating]

    def test_is_registered(self):
        self.assertIn(Rating, admin.site._registry)

    def test_no_add_change_or_delete_permission(self):
        self.assertFalse(self.model_admin.has_add_permission(request=None))
        self.assertFalse(self.model_admin.has_change_permission(request=None))
        self.assertFalse(self.model_admin.has_delete_permission(request=None))
