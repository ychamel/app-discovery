"""Signal-capture data model (DESIGN.md §4) — the proposed global D-7 event schema.

Four **append-only** tables, one source of truth per fact:

  * ``Impression``     — one shown instance: its own UUID identity (the anchor every
    conversion attributes to, AC1/AC3), who saw it, which accepted app, the surface, when.
  * ``ImpressionTag``  — the **frozen** capture-time category snapshot: which ``Tag.id``s
    the app carried *when shown* (AC1/AC2). Never re-derived.
  * ``EngagementEvent``— one downstream behavioral act in a **single uniform table** with a
    ``kind`` discriminator (no kind-specific columns; even the proxy is just ``is_proxy``).
  * ``PlatformVisit``  — the directly-observed return substrate: one row per user per UTC
    day (the AC4 returns derivation reads it; returns themselves are never stored — SC-9).

Two guarantees are **structural**, not conventions:

  * **Raw, never scored (AC9/R5):** no table has a score/weight/rank/normalized column.
  * **Privacy whitelist (AC10):** no table has an IP/user-agent/device/geo/referrer/
    off-platform-id/free-text column — over-collection is unrepresentable.

Apps and tags are referenced as **soft ``App.id``/``Tag.id`` UUIDs** (D-6/D-5), not DB
FKs, so a later app withdrawal or tag merge does not cascade-erase history. The only
schema edge to another app is the ``Account`` ``user`` FK (see the deletion semantics on
each model — SC-10).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.signals.kinds import EventKind, Surface


class Impression(models.Model):
    """One shown instance of an app — the anchor every conversion attributes to (AC1/AC3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SET_NULL = anonymize-on-deletion (SC-10): the behavioral fact survives as corpus,
    # unlinked from the person, so the H3 backtest keeps its history (no-auto-purge, A3).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="signal_impressions",
    )
    # The accepted catalog.App.id shown — a SOFT ref (no DB FK, D-6), validated at capture
    # via get_catalogued_app. A later app withdrawal must not cascade-erase that it was shown.
    app_id = models.UUIDField()
    surface = models.CharField(max_length=16, choices=Surface.choices)
    # When the app was shown — the funnel/return clock starts here. Always set by the sole
    # writer (capture.record_impression defaults it to now when an emitter passes None), so
    # there is no DB-level default to drift from that contract.
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "signals_impression"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["app_id", "occurred_at"], name="signals_imp_app_time_idx"),
            models.Index(fields=["occurred_at"], name="signals_imp_time_idx"),
            # Backs the per-user-per-app existence read (selectors.has_impression) that the
            # ratings-reviews curated-rating gate runs (ratings DESIGN §4.3/§5d). Additive.
            models.Index(fields=["user", "app_id"], name="signals_imp_user_app_idx"),
        ]

    def __str__(self) -> str:
        return f"impression {self.id} → app {self.app_id}"


class ImpressionTag(models.Model):
    """A ``Tag.id`` the app carried at show time — the frozen capture-time snapshot (AC2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    impression = models.ForeignKey(
        Impression, on_delete=models.CASCADE, related_name="tags"
    )
    # A taxonomy Tag.id copied from get_catalogued_app(app_id).tags AT capture (D-5 soft
    # ref). FROZEN — never re-derived; a tag later renamed/merged still resolves for display
    # via resolve_tag, but which tags were captured does not change (the historical truth).
    tag_id = models.UUIDField()

    class Meta:
        db_table = "signals_impression_tag"
        constraints = [
            models.UniqueConstraint(
                fields=["impression", "tag_id"], name="signals_impression_tag_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["tag_id"], name="signals_imptag_tagid_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.impression_id} → {self.tag_id}"


class EngagementEvent(models.Model):
    """One downstream behavioral act, append-only — a fact table with a ``kind`` type tag (§6)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=24, choices=EventKind.choices)
    # SET_NULL = anonymize-on-deletion (SC-10), as on Impression.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="signal_events",
    )
    # Soft catalog.App.id ref (D-6), validated at capture.
    app_id = models.UUIDField()
    # The originating impression where known (AC3/AC5). REQUIRED for click_through and
    # off_platform_proxy, OPTIONAL for the others — that per-kind rule is enforced in
    # capture (T-04/T-05); the column is nullable so the optional kinds are representable.
    # SET_NULL so anonymizing/removing an impression never erases the conversion fact.
    impression = models.ForeignKey(
        Impression,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events",
    )
    # True ONLY for off_platform_proxy — the flag marking a SECONDARY, proxy-derived signal
    # (AC7). Service-set, never caller-supplied (capture forces it); on-platform acts are False.
    is_proxy = models.BooleanField(default=False)
    # Always set by the sole writer (capture defaults it to now when None is passed).
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "signals_engagement_event"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(
                fields=["app_id", "kind", "occurred_at"], name="signals_evt_app_kind_idx"
            ),
            models.Index(fields=["occurred_at"], name="signals_evt_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} event {self.id} → app {self.app_id}"


class PlatformVisit(models.Model):
    """That a user was active on the platform on a given UTC day — the return substrate (AC4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE (not SET_NULL): a per-day retention tick is only meaningful joined to a live
    # user's impressions. Once the account is gone the anonymized tick is pure noise, so it
    # goes with the account (DESIGN.md §4/§13, SC-10).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signal_visits",
    )
    # The day (UTC) the user was active. Unique per user → idempotent: one row/user/day.
    visit_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "signals_platform_visit"
        ordering = ["-visit_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "visit_date"], name="signals_platform_visit_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["visit_date"], name="signals_visit_date_idx"),
        ]

    def __str__(self) -> str:
        return f"visit {self.user_id} @ {self.visit_date}"
