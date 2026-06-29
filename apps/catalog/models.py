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
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
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
    # --- Marketing/launch-page content (app-page-redesign DESIGN.md §5.1) ---------------
    # All optional and additive: a legacy/sparse app stores the empty default and renders the
    # graceful-empty page state (M2). Written only through catalog.services, validated there.
    # Text columns use blank + default="" (never NULL) so there is one empty representation.
    # NONE of these is a tier/payment/identity field — page uniformity stays structural (R2).
    tagline = models.CharField(max_length=300, blank=True, default="")
    deep_dive = models.TextField(blank=True, default="")
    # The one optional self-hosted demo clip (MP4/WebM), stored under a generated name on the
    # same media storage as screenshots; null=True because a FileField stores "" poorly.
    demo_clip = models.FileField(upload_to="app_clips/%Y/%m/", blank=True, null=True)
    demo_clip_alt = models.CharField(max_length=200, blank=True, default="")
    # Canonical form from urlnorm.normalize_url for the duplicate SIGNAL (§6c). Indexed,
    # NOT unique — review is manual (SI-2) and rejected/withdrawn dupes may coexist.
    normalized_url = CITextField(max_length=2000)
    status = models.CharField(
        max_length=9, choices=Status.choices, default=Status.PENDING
    )
    # Set on each entry into pending: FIFO queue order AND the time-to-decision start point.
    last_submitted_at = models.DateTimeField()
    # The one source of truth for "when this app (last) entered the accepted catalogue" —
    # the newest-accepted-first browse-order key (open-search-browse DESIGN.md §5a). Stamped
    # only inside accept_app's transaction (re-stamped on re-acceptance); NULL until accepted,
    # so a never-accepted app — which is never catalogued — never appears in a result set.
    accepted_at = models.DateTimeField(null=True)
    # The stored, GIN-indexed full-text index of name(weight A) + description(weight B), the
    # keyword-relevance search substrate (open-search-browse DESIGN.md §5b). Maintained only in
    # the catalog write path (submit_app/edit_app) via catalog.services._search_vector_expr —
    # no other code writes it, so the stored vector cannot drift. NULL until first maintained.
    search_vector = SearchVectorField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_app"
        ordering = ["-last_submitted_at"]
        indexes = [
            models.Index(fields=["status"], name="catalog_app_status_idx"),
            models.Index(fields=["normalized_url"], name="catalog_app_normurl_idx"),
            # The accepted-only, newest-first browse page = one index range scan (AC9).
            models.Index(
                fields=["status", "-accepted_at"], name="catalog_app_status_acc_idx"
            ),
            # GIN over the FTS column backs keyword search at 100× catalogue size (AC9).
            GinIndex(fields=["search_vector"], name="catalog_app_search_gin"),
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


class AppFacet(models.Model):
    """One typed facet value on an app — a soft, code-validated reference (mirrors AppTag).

    ``facet``/``value`` are keys from the code-fixed ``catalog.facets`` registry, **not** DB
    FKs: validated with ``is_valid_facet_value`` at the write boundary (app-page-redesign
    DESIGN.md §5.2) and resolved through the registry at read — a value later removed from
    the registry is silently dropped at display, never an error (the D-5 pattern).

    Firewalled from ranking/discovery (D-14a): this is **not** ``AppTag``, so it never enters
    ``search_catalogue``'s tag filter or the interest matcher — facets are display-only in v1.
    Cardinality (one pricing value, many platforms) is enforced in the write service; the
    unique constraint here stops duplicate values, making illegal multiplicity unrepresentable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="app_facets")
    facet = models.CharField(max_length=32)
    value = models.CharField(max_length=48)

    class Meta:
        db_table = "catalog_app_facet"
        constraints = [
            models.UniqueConstraint(
                fields=["app", "facet", "value"], name="catalog_app_facet_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["app"], name="catalog_app_facet_app_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.app_id}: {self.facet}={self.value}"


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
