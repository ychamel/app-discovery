from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """The app catalog: submission, the objective intake gate, and lifecycle (DESIGN.md §2)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    label = "catalog"
