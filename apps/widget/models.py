"""embeddable-update-widget data model (DESIGN §6) — the per-(app, kind, day) reach counter.

One feature-owned table, ``widget_reach_count``: a **daily rollup** of how many times an app's
widget rendered (``impression``) and how many times an end user clicked through to the platform
(``click_through``), one row per ``(app_id, kind, count_date)``. The dashboard reads it as a
clearly-labeled off-platform reach figure (AC9); the count of widget reach for an (app, day)
lives **only** here (one source of truth per fact). The notices the widget shows are *not*
stored — they are read live from ``apps.updates`` (F3), so a publish/withdraw needs no
widget-side duplication.

Three facts are **structural**, not conventions (DESIGN §3/§6/§9 — illegal states made
unrepresentable):

  * **No ``user`` FK and no IP/UA/referrer/geo/device column.** The widget serves anonymous
    end users and must collect no PII (the D-7 AC10 posture). There is nowhere here to store an
    actor or a fingerprint — anonymity and the PII-free posture are guaranteed by absence, not
    by a runtime rule.
  * **No score / weight / rank column (AC6).** Widget reach is a private off-platform figure,
    never a corpus signal the Quality Score could trust. The firewall is reinforced here: there
    is nothing to feed a ranking even if one tried.
  * **A daily rollup, not append-per-event (EUW-9).** The widget is *designed* to live in
    third-party apps that may dwarf platform traffic; an append row per anonymous load would
    grow unboundedly on a scrape-prone surface. The rollup bounds growth to ``apps × 2 × days``
    and stores exactly the daily shape the dashboard reads.

The model declares the shape only. The atomic increment (the single writer) lives in
``apps.widget.attribution``; the windowed read in ``apps.widget.selectors``. The model holds no
business logic.
"""

import uuid

from django.db import models

from apps.widget.kinds import WidgetConversionKind, WidgetEventKind


class WidgetReachCount(models.Model):
    """One ``(app_id, kind, count_date)`` reach counter — incremented, never hand-edited."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The accepted catalog.App.id this reach is for — a SOFT D-6 ref (no DB FK), validated at
    # the write boundary by the calling view (mirrors updates/subscriptions). A later app
    # withdrawal must not cascade-erase the historical reach rollup.
    app_id = models.UUIDField()
    kind = models.CharField(max_length=16, choices=WidgetEventKind.choices)
    count_date = models.DateField()  # the UTC day this rollup row aggregates
    count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "widget_reach_count"
        constraints = [
            # One row per app×kind×day. This is what turns a concurrent create into a caught
            # IntegrityError the writer retries as an atomic increment (attribution, DESIGN §6).
            models.UniqueConstraint(
                fields=["app_id", "kind", "count_date"],
                name="widget_reach_count_unique",
            ),
        ]
        indexes = [
            # Backs both the atomic per-day increment (filter app_id= + kind= + count_date=)
            # and the windowed dashboard read (app_id[ IN] + kind + count_date range, grouped).
            models.Index(
                fields=["app_id", "kind", "count_date"],
                name="widget_reach_app_kind_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"widget {self.kind} × app {self.app_id} on {self.count_date}: {self.count}"


class WidgetConversionCount(models.Model):
    """One ``(app_id, kind, count_date)`` conversion counter — incremented, never hand-edited.

    The sibling of :class:`WidgetReachCount` for the **downstream** half of the funnel
    (widget-conversion-attribution DESIGN §6.1): a daily rollup of conversions credited to the
    widget **source** app — a new ``follow`` of the clicked-through app, or a new platform
    ``account`` — one row per ``(app_id, kind, count_date)``. A separate table, not more kinds on
    ``widget_reach_count``: reach and conversion are *distinct facts, distinct counts* (brief §3),
    and keeping them apart keeps each selector's zero-fill vocabulary clean and makes the feature
    deletable by dropping one table (design-for-deletion). The concurrency-hard increment is **not**
    duplicated — it is the shared ``apps.widget.rollup`` helper both writers call.

    The same three facts are **structural** here as on the reach table (illegal states made
    unrepresentable by absence, not by a runtime rule):

      * **No ``user`` FK and no IP/UA/referrer/geo/device column.** The marker that drives a
        conversion carries only a public source app-id and bookkeeping flags — never a person — so
        there is nowhere here to store an actor. The no-PII posture (AC4 / M5 = 0) is guaranteed by
        absence.
      * **No score / weight / rank column (AC6).** An attributed conversion is a private
        off-platform vanity figure, never a corpus signal the Quality Score could read. The
        firewall is reinforced here: there is nothing to feed a ranking even if one tried.
      * **A daily rollup, not append-per-event.** Bounds growth to ``apps × 2 × days`` rather than
        a row per anonymous conversion, exactly the daily shape the dashboard funnel reads.

    The model declares the shape only. The atomic increment (the single writer) lives in
    ``apps.widget.attribution.record_widget_conversion``; the windowed read in
    ``apps.widget.selectors``. The model holds no business logic.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The accepted catalog.App.id credited as the conversion's widget SOURCE — a SOFT D-6 ref (no
    # DB FK), mirroring WidgetReachCount. A later app withdrawal must not cascade-erase history.
    app_id = models.UUIDField()
    kind = models.CharField(max_length=16, choices=WidgetConversionKind.choices)
    count_date = models.DateField()  # the UTC day this rollup row aggregates
    count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "widget_conversion_count"
        constraints = [
            # One row per app×kind×day — the same hinge as the reach table: a concurrent create
            # becomes a caught IntegrityError the shared rollup helper retries as an increment.
            models.UniqueConstraint(
                fields=["app_id", "kind", "count_date"],
                name="widget_conversion_count_unique",
            ),
        ]
        indexes = [
            # Backs both the atomic per-day increment (filter app_id= + kind= + count_date=) and
            # the windowed dashboard funnel read (app_id[ IN] + kind + count_date range, grouped).
            models.Index(
                fields=["app_id", "kind", "count_date"],
                name="widget_conv_app_kind_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"conversion {self.kind} × app {self.app_id} on {self.count_date}: {self.count}"
