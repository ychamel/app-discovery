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
