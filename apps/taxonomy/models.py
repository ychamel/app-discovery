"""Interest-vocabulary data model (DESIGN.md §4).

Three tables, one source of truth each:
  * ``Cluster`` — a named grouping of related tags (the day-one anchor for the future
    adjacency relation, AC8).
  * ``Tag``     — one unit of interest vocabulary; its UUID ``id`` is the stable
    cross-feature reference every downstream feature stores (AC7).
  * ``Tag.clusters`` (M2M) — cluster membership; every *active* tag belongs to ≥1
    cluster (AC5), enforced by the write service, not a single column constraint.

Identity rules (DESIGN.md §7):
  * ``id`` (UUID) is the only durable cross-feature reference. A rename changes
    ``label`` only, so a stored reference always resolves.
  * ``slug`` (citext, unique, immutable) is an *internal* human key for idempotent
    seeding and readable admin/logs — never the downstream reference.

This app enables ``citext`` in its own initial migration and references no other app's
schema, so it stays independently deletable (DESIGN.md §1).
"""

import uuid

from django.db import models


class CITextField(models.CharField):
    """A CharField stored as PostgreSQL ``citext`` for case-insensitive uniqueness.

    Defined locally (not imported from ``accounts``) so ``taxonomy`` depends on no
    other app's code or migration (DESIGN.md §1, independently deletable).
    """

    def db_type(self, connection) -> str:
        return "citext"


class CanonicalLabel(models.Func):
    """SQL for a label's duplicate-detection form: lowercased, trimmed, spaces collapsed.

    Used both by the functional unique index below and by the write service's
    pre-check, so the rule for "these two labels are the same" lives in exactly one
    place (AC1 / R2 non-redundancy) — labels differing only by case or whitespace
    collide.
    """

    function = "regexp_replace"
    template = r"regexp_replace(btrim(lower(%(expressions)s)), '\s+', ' ', 'g')"
    output_field = models.TextField()


class Cluster(models.Model):
    """A named grouping of related tags (AC5); the anchor for future adjacency (AC8)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = CITextField(max_length=80, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "taxonomy_cluster"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    """One unit of interest vocabulary. ``id`` (UUID) is the stable cross-feature reference."""

    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        RETIRED = "retired", "retired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = CITextField(max_length=80, unique=True)
    label = models.CharField(max_length=80)
    definition = models.TextField(blank=True)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.ACTIVE
    )
    # Optional successor when a tag is retired *into* another (merge/de-dupe, AC1/OQ-2).
    # SET_NULL so deleting a successor never blocks; NULL ⇒ retired-but-kept.
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )
    clusters = models.ManyToManyField(Cluster, related_name="tags", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "taxonomy_tag"
        ordering = ["label"]
        constraints = [
            # Duplicate labels (case/whitespace-insensitive) cannot both exist (AC1/R2).
            models.UniqueConstraint(
                CanonicalLabel("label"),
                name="taxonomy_tag_label_canonical_unique",
            ),
        ]
        indexes = [
            # list_active_tags filters on status (DESIGN.md §9 indexed lookups).
            models.Index(fields=["status"], name="taxonomy_tag_status_idx"),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE
