from django.apps import AppConfig


class WidgetConfig(AppConfig):
    """App widget: the embeddable, paste-one-line "what's new" widget (embeddable-update-widget).

    Owns one table (``widget_reach_count`` — a daily rollup of widget impressions and
    click-throughs per app). The widget renders an app's published ``updates`` notices plus a
    labeled "view on platform" link inside a developer's own app, and counts the
    bring-your-own-audience reach that link drives (AC9).

    The firewall (AC6 / M5 = 0) is **structural by absence**: this app imports nothing from
    ``apps.signals`` (AST-enforced, the ``discovery``/``dashboard``/``updates`` precedent), so a
    widget interaction creates no D-7 corpus row and can confer no D-8 curated-rating
    eligibility — anonymous, scrape-prone third-party traffic never enters the integrity corpus.

    The store is structurally PII-free: there is no ``user`` FK and no IP/UA/referrer/geo column
    (the D-7 AC10 posture), so over-collection is unrepresentable, not merely avoided.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.widget"
    label = "widget"
