"""Catalog data model (DESIGN.md §4) — four tables, one source of truth each.

  * ``App``            — one submitted web app: stable identity (UUID ``id`` — the
    cross-feature reference, AC9/D-6), ownership, metadata, and its lifecycle ``status``
    (one source of truth for "where it is", §7).
  * ``AppTag``         — the app↔tag link, stored as a **soft** ``tag_id`` UUID (the D-5
    reference): no DB FK to taxonomy, validated at the write boundary, resolved at read.
  * ``AppMedia``       — one ordered screenshot belonging to an app.
  * ``ReviewDecision`` — an **append-only** record of one gate decision (the audit +
    metrics source); never updated or deleted.

Fairness is **structural** here (AC3): no payment, tier, budget, brand, priority, or
fast-lane field exists on any table — an unfair intake is unrepresentable.

This app enables ``citext`` in its own initial migration and references no other app's
schema except the ``accounts.Account`` ownership/reviewer FKs, so it stays independently
deletable apart from that intended edge (DESIGN.md §1/§4).
"""

import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.catalog.gate import Criterion


class CITextField(models.CharField):
    """A CharField stored as PostgreSQL ``citext`` for case-insensitive comparison.

    Defined locally (not imported from ``accounts``/``taxonomy``) so ``catalog`` depends
    on no other app's code or migration (DESIGN.md §1, independently deletable).
    """

    def db_type(self, connection) -> str:
        return "citext"


class App(models.Model):
    """One submitted web app: identity, ownership, metadata, and lifecycle state."""

    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        ACCEPTED = "accepted", "accepted"
        REJECTED = "rejected", "rejected"
        WITHDRAWN = "withdrawn", "withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Individual ownership (SI-4). CASCADE = a developer's apps are their content, removed
    # on account deletion (DESIGN.md §13, flagged to revisit when signal-capture exists).
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="catalog_apps",
    )
    name = models.CharField(max_length=120)
    description = models.TextField()
    # The URL as entered (displayed back); validated http(s) + well-formed at the boundary.
    url = models.CharField(max_length=2000)
    # Canonical form from urlnorm.normalize_url for the duplicate SIGNAL (§6c). Indexed,
    # NOT unique — review is manual (SI-2) and rejected/withdrawn dupes may coexist.
    normalized_url = CITextField(max_length=2000)
    status = models.CharField(
        max_length=9, choices=Status.choices, default=Status.PENDING
    )
    # Set on each entry into pending: FIFO queue order AND the time-to-decision start point.
    last_submitted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_app"
        ordering = ["-last_submitted_at"]
        indexes = [
            models.Index(fields=["status"], name="catalog_app_status_idx"),
            models.Index(fields=["normalized_url"], name="catalog_app_normurl_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class AppTag(models.Model):
    """The app↔tag link, stored as a soft ``tag_id`` UUID reference (D-5)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="app_tags")
    # A taxonomy Tag.id stored as a plain UUID, NOT a DB FK — the D-5 soft reference:
    # validated with is_valid_tag at write (AC4), dereferenced with resolve_tag at read
    # (AC9). Keeps catalog decoupled from taxonomy's schema; a tag may retire/merge with
    # no cascade here.
    tag_id = models.UUIDField()

    class Meta:
        db_table = "catalog_app_tag"
        constraints = [
            models.UniqueConstraint(
                fields=["app", "tag_id"], name="catalog_app_tag_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["tag_id"], name="catalog_app_tag_tagid_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.app_id} → {self.tag_id}"


class AppMedia(models.Model):
    """One ordered screenshot belonging to an app (validated by Pillow at write, §9)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to="app_media/%Y/%m/")
    position = models.SmallIntegerField()
    alt_text = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_app_media"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["app", "position"], name="catalog_app_media_position_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.app_id} #{self.position}"


class ReviewDecision(models.Model):
    """An append-only record of one gate decision — never updated or deleted (§4/§6)."""

    class Outcome(models.TextChoices):
        ACCEPTED = "accepted", "accepted"
        REJECTED = "rejected", "rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="decisions")
    # SET_NULL so the decision survives reviewer deletion (mirrors accounts.RoleGrant).
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="catalog_decisions",
    )
    outcome = models.CharField(max_length=8, choices=Outcome.choices)
    # Empty for accepted, ≥1 of the five fixed floors for rejected (enforced in services,
    # T-06). choices=Criterion ⇒ no "other" value can be stored (AC6/R1, §6b).
    failed_criteria = ArrayField(
        models.CharField(max_length=20, choices=Criterion.choices),
        default=list,
        blank=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_review_decision"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.app_id}: {self.outcome}"
