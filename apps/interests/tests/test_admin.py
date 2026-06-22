"""T-06 — the Interest admin is read-only (DESIGN §3 invariant: services is the only writer)."""

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.interests.admin import InterestAdmin
from apps.interests.models import Interest


class ReadOnlyAdminTests(TestCase):
    def setUp(self):
        self.model_admin = InterestAdmin(Interest, admin.site)
        self.request = RequestFactory().get("/django-admin/")

    def test_admin_grants_no_write_permissions(self):
        self.assertFalse(self.model_admin.has_add_permission(self.request))
        self.assertFalse(self.model_admin.has_change_permission(self.request))
        self.assertFalse(self.model_admin.has_delete_permission(self.request))
