from django.apps import AppConfig


class UpdatesConfig(AppConfig):
    """App updates: the single producer of developer→follower update/early-access notices.

    Owns one table (``updates_notice``) — the authored content a developer posts about an app
    they own, which the followed-apps feed pulls as the AS-3 producer (developer-updates
    DESIGN §4/§5.1). Unlike the model-less consumers (``apps/pages``/``apps/discovery``/
    ``apps/dashboard``), this app owns durable authored content, so it needs a table.

    Posting is **inert to the corpus**: this app imports nothing from ``signals.capture``
    (DESIGN §8, AST-enforced), so a notice is *content*, never a score-bearing D-7 signal —
    the developer controls reach to an audience they already earned, never the signal.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.updates"
    label = "updates"
