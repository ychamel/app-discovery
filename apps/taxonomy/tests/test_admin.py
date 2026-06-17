"""Tests for the taxonomy Django admin (T-08, DESIGN.md §6/§8).

Confirms the admin enforces the same invariants as the service: an invariant-violating
edit is refused, and retiring routes through ``retire_tag`` (soft, non-destructive).
"""

from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from apps.taxonomy import services
from apps.taxonomy.admin import TagAdmin, TagAdminForm
from apps.taxonomy.models import Tag


def _request_with_messages():
    request = RequestFactory().post("/django-admin/")
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class TagAdminFormTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")

    def test_form_without_a_cluster_is_invalid(self):
        form = TagAdminForm(data={"slug": "todo-app", "label": "To-do app", "clusters": []})
        self.assertFalse(form.is_valid())
        self.assertIn("at least one cluster", str(form.errors))

    def test_form_with_a_cluster_is_valid(self):
        form = TagAdminForm(
            data={"slug": "todo-app", "label": "To-do app", "clusters": [self.cluster.pk]}
        )
        self.assertTrue(form.is_valid())


class TagAdminRetireActionTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")
        self.tag = services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        self.admin = TagAdmin(Tag, AdminSite())

    def test_retire_action_soft_retires_through_service(self):
        self.admin.retire_selected_tags(
            _request_with_messages(), Tag.objects.filter(pk=self.tag.pk)
        )
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.status, Tag.Status.RETIRED)
        self.assertIsNotNone(self.tag.retired_at)
        self.assertTrue(Tag.objects.filter(pk=self.tag.pk).exists())  # kept, not deleted

    def test_delete_is_disabled(self):
        self.assertFalse(self.admin.has_delete_permission(_request_with_messages()))
