from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """The developer-dashboard: a read-only view of an owned app's reception (DESIGN.md §3).

    A pure read orchestrator over the D-3 (accounts), D-6 (catalog), D-7 (signals) and D-8
    (ratings) read surfaces — it owns no model and no migration, and **imports nothing from
    ``signals.capture``** so viewing a dashboard can never emit a D-7 impression of the
    developer's own app (AC8, structural). Activated and rolled back by a single
    ``config/urls`` include plus the ``INSTALLED_APPS`` line (mirrors ``apps/discovery/``).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    label = "dashboard"
