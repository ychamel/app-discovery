"""T-08 — the corpus admin is read-only: append-only must not be circumventable (DESIGN.md §9)."""

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.signals.models import (
    EngagementEvent,
    Impression,
    ImpressionTag,
    PlatformVisit,
)
from apps.signals.tests.helpers import make_admin

CORPUS_MODELS = (Impression, ImpressionTag, EngagementEvent, PlatformVisit)


class AdminRegistrationTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/admin/")
        self.request.user = make_admin()

    def test_all_four_models_registered(self):
        for model in CORPUS_MODELS:
            self.assertIn(model, admin.site._registry)

    def test_no_model_is_add_change_or_delete_able(self):
        for model in CORPUS_MODELS:
            model_admin = admin.site._registry[model]
            self.assertFalse(
                model_admin.has_add_permission(self.request),
                f"{model.__name__} must not be addable in admin (append-only).",
            )
            self.assertFalse(
                model_admin.has_change_permission(self.request),
                f"{model.__name__} must not be changeable in admin (append-only).",
            )
            self.assertFalse(
                model_admin.has_delete_permission(self.request),
                f"{model.__name__} must not be deletable in admin (append-only).",
            )
