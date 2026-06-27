"""The widget's closed event vocabulary (embeddable-update-widget DESIGN §6).

Exactly two kinds of widget interaction are counted, and no other can exist: an
**impression** (the widget rendered inside a host page) and a **click_through** (an end user
followed the "view on platform" link). This enum is the single source of truth for both the
model ``kind`` column and the ``attribution`` writer; a new kind is a deliberate, additive
``TextChoices`` change, never an ad-hoc string.
"""

from django.db import models


class WidgetEventKind(models.TextChoices):
    """The two counted widget interactions — the closed vocabulary of ``widget_reach_count``."""

    IMPRESSION = "impression", "widget render"
    CLICK_THROUGH = "click_through", "view-on-platform click"


class WidgetConversionKind(models.TextChoices):
    """The two counted downstream conversions — the closed vocabulary of ``widget_conversion_count``
    (widget-conversion-attribution DESIGN §2/§6.1).

    A conversion is an action a visitor takes *after* a widget click-through that the source app
    is credited for: a genuinely new **follow** of the clicked-through app, or a new platform
    **account**. This enum is the single source of truth for the model ``kind`` column, the
    ``record_widget_conversion`` writer, and the conversion selectors. It is deliberately a
    **separate** vocabulary from :class:`WidgetEventKind` — reach and conversion are distinct
    facts in distinct tables (DESIGN §6.1), so their kinds must not share members.
    """

    FOLLOW = "follow", "new follow of the clicked-through app"
    ACCOUNT = "account", "new platform account"
