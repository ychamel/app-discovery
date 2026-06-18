from django.apps import AppConfig


class SignalsConfig(AppConfig):
    """Behavioral signal capture: the append-only event corpus + funnel read path (DESIGN.md §2)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.signals"
    label = "signals"
