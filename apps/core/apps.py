from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Cross-cutting shared surface (config, email, rate limiting, observability)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        # Fail loudly at startup if any tunable is misconfigured, rather than
        # surfacing an obscure error the first time a request hits the value.
        from apps.core import config

        config.validate_all()
