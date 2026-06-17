from django.apps import AppConfig


class TaxonomyConfig(AppConfig):
    """The shared interest vocabulary: tags, clusters, and their lifecycle (DESIGN.md §2)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.taxonomy"
    label = "taxonomy"
