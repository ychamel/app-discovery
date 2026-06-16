from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """The identity feature: Account, magic-link auth, roles, profile, admin grants."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
