from django.apps import AppConfig


class PagesConfig(AppConfig):
    """Public app pages: the uniform, openly-accessible page per accepted app (DESIGN.md §2).

    A pure D-6/D-7 consumer — it owns no model and no migration. Its only persistence is
    the D-7 rows written *through* ``apps.signals.capture`` (app-pages DESIGN §4/§12).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pages"
    label = "pages"
