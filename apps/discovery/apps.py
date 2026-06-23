from django.apps import AppConfig


class DiscoveryConfig(AppConfig):
    """The open discovery surface: browse/search/filter the accepted catalogue (DESIGN.md §4c).

    A pure read orchestrator over the D-5 (taxonomy) and D-6 (catalog) read surfaces — it
    owns no model and no migration, and **imports nothing from ``signals``** so a self-driven
    search/browse view can never confer curated-rating eligibility (AC6, structural). Activated
    and rolled back by a single ``config/urls`` include (mirrors ``apps/pages/``).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.discovery"
    label = "discovery"
