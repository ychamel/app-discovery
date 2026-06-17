"""The single write path for the interest vocabulary (DESIGN.md §3/§5b/§7).

Every mutation of a ``Tag`` or ``Cluster`` goes through one of these functions —
nothing else writes taxonomy rows. That keeps the vocabulary's invariants in exactly
one place:

  * every *active* tag belongs to ≥1 cluster (AC5),
  * no two tags share a slug or a normalized label (AC1 / R2 non-redundancy),
  * a tag is retired (kept), never deleted, optionally pointing at a successor (AC6/OQ-2).

Each function runs in a single ``transaction.atomic()`` so a failed invariant writes
nothing, and the tag-lifecycle writes emit the observability counters from
``apps.core.observability`` (reusing ``increment`` as-is). Invariant failures are
raised loudly via ``apps.taxonomy.errors`` — never swallowed.
"""

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count, Value
from django.utils import timezone

from apps.core import observability
from apps.taxonomy.errors import (
    DuplicateTagError,
    OrphanTagError,
    RetireSuccessorError,
)
from apps.taxonomy.models import CanonicalLabel, Cluster, Tag

# --- Duplicate detection -----------------------------------------------------
# The DB carries the ultimate guards (unique slug; functional unique index on the
# canonical label). These pre-checks exist to raise a clear, specific error before
# the constraint fires; the constraint remains the race-proof backstop.


def _slug_taken(slug: str, *, exclude_pk=None) -> bool:
    queryset = Tag.objects.filter(slug=slug)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def _label_taken(label: str, *, exclude_pk=None) -> bool:
    """True if another tag's label matches ``label`` in canonical form (case/space-insensitive).

    Both sides are reduced by the same SQL ``CanonicalLabel`` expression, so the
    "same label" rule has a single source of truth shared with the unique index.
    """
    candidate = CanonicalLabel(Value(label))
    queryset = Tag.objects.annotate(_canonical=CanonicalLabel("label")).filter(
        _canonical=candidate
    )
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


# --- Tag lifecycle -----------------------------------------------------------
@transaction.atomic
def add_tag(slug: str, label: str, *, clusters: list[Cluster], definition: str = "") -> Tag:
    """Create an active tag in ≥1 cluster (AC5), rejecting slug/label duplicates (AC1)."""
    if not clusters:
        raise OrphanTagError(f"Tag {slug!r} must be created in at least one cluster.")
    if _slug_taken(slug):
        raise DuplicateTagError(f"A tag with slug {slug!r} already exists.")
    if _label_taken(label):
        raise DuplicateTagError(f"A tag with label {label!r} already exists.")

    tag = Tag.objects.create(slug=slug, label=label, definition=definition)
    tag.clusters.set(clusters)
    observability.increment(observability.TAXONOMY_TAG_ADDED, slug=slug)
    return tag


@transaction.atomic
def rename_tag(tag: Tag, *, label: str) -> Tag:
    """Change a tag's display label only — never its id or slug (AC6/AC7)."""
    if _label_taken(label, exclude_pk=tag.pk):
        raise DuplicateTagError(f"A tag with label {label!r} already exists.")
    tag.label = label
    tag.save(update_fields=["label", "updated_at"])
    observability.increment(observability.TAXONOMY_TAG_RENAMED, slug=tag.slug)
    return tag


@transaction.atomic
def update_tag(tag: Tag, *, label: str, clusters: list[Cluster], definition: str = "") -> Tag:
    """Idempotently sync an existing tag's editable fields (label, definition, membership).

    The sync path used by ``seed_taxonomy`` (DESIGN.md §6): it applies the same dedupe
    and ≥1-cluster guards as ``add_tag``, but **does nothing when nothing changed**, so
    re-running the seed on an unchanged file is a true no-op. Never touches id, slug, or
    lifecycle (status/retire is a separate explicit action).
    """
    if tag.is_active and not clusters:
        raise OrphanTagError(f"Tag {tag.slug!r} is active and must stay in ≥1 cluster.")
    if _label_taken(label, exclude_pk=tag.pk):
        raise DuplicateTagError(f"A tag with label {label!r} already exists.")

    label_changed = tag.label != label
    definition_changed = tag.definition != definition
    if label_changed or definition_changed:
        tag.label = label
        tag.definition = definition
        tag.save(update_fields=["label", "definition", "updated_at"])
        if label_changed:
            observability.increment(observability.TAXONOMY_TAG_RENAMED, slug=tag.slug)

    if set(tag.clusters.values_list("pk", flat=True)) != {c.pk for c in clusters}:
        tag.clusters.set(clusters)
    return tag


@transaction.atomic
def retire_tag(tag: Tag, *, replaced_by: Tag | None = None) -> Tag:
    """Soft-retire a tag (kept, never deleted), optionally pointing at a successor (AC6/OQ-2).

    Idempotent: re-retiring an already-retired tag keeps its original ``retired_at``
    and emits no new counter, so re-running the seed is a no-op.
    """
    if replaced_by is not None:
        _validate_successor(tag, replaced_by)

    was_active = tag.is_active
    tag.status = Tag.Status.RETIRED
    tag.replaced_by = replaced_by
    if was_active:
        tag.retired_at = timezone.now()
    tag.save(update_fields=["status", "replaced_by", "retired_at", "updated_at"])
    if was_active:
        observability.increment(observability.TAXONOMY_TAG_RETIRED, slug=tag.slug)
    return tag


def _validate_successor(tag: Tag, successor: Tag) -> None:
    """Reject a retire successor that is the tag itself, retired, or would form a cycle (OQ-2)."""
    if successor.pk == tag.pk:
        raise RetireSuccessorError(f"Tag {tag.slug!r} cannot be its own successor.")
    if not successor.is_active:
        raise RetireSuccessorError(
            f"Successor {successor.slug!r} is retired; pick an active successor."
        )
    # Walk the successor's own chain; reaching `tag` would form a cycle once we link them.
    seen = {tag.pk}
    cursor = successor
    while cursor is not None:
        if cursor.pk in seen:
            raise RetireSuccessorError(
                f"Retiring {tag.slug!r} into {successor.slug!r} would form a replaced_by cycle."
            )
        seen.add(cursor.pk)
        cursor = cursor.replaced_by


# --- Cluster lifecycle -------------------------------------------------------
# Cluster create/rename and membership changes are structural; the design names no
# dedicated metric for them (§9 lists only the tag-lifecycle + diagnostic counters),
# so they emit none. Their safety is asserted by check_integrity / check_taxonomy.
@transaction.atomic
def add_cluster(slug: str, name: str, *, description: str = "") -> Cluster:
    return Cluster.objects.create(slug=slug, name=name, description=description)


@transaction.atomic
def rename_cluster(cluster: Cluster, *, name: str) -> Cluster:
    cluster.name = name
    cluster.save(update_fields=["name", "updated_at"])
    return cluster


@transaction.atomic
def update_cluster(cluster: Cluster, *, name: str, description: str = "") -> Cluster:
    """Idempotently sync a cluster's name + description (seed sync path, DESIGN.md §6).

    A no-op when both already match, so re-seeding an unchanged file writes nothing.
    """
    if cluster.name == name and cluster.description == description:
        return cluster
    cluster.name = name
    cluster.description = description
    cluster.save(update_fields=["name", "description", "updated_at"])
    return cluster


@transaction.atomic
def assign_to_cluster(tag: Tag, cluster: Cluster) -> None:
    tag.clusters.add(cluster)


@transaction.atomic
def remove_from_cluster(tag: Tag, cluster: Cluster) -> None:
    """Remove a tag from a cluster, refusing to orphan an active tag (AC5)."""
    if tag.is_active and tag.clusters.exclude(pk=cluster.pk).count() == 0:
        raise OrphanTagError(
            f"Removing {tag.slug!r} from its last cluster would orphan an active tag."
        )
    tag.clusters.remove(cluster)


# --- Integrity ---------------------------------------------------------------
@dataclass
class IntegrityReport:
    """The result of a vocabulary integrity scan (AC5; backs check_taxonomy, T-07)."""

    orphan_active_tags: list[Tag] = field(default_factory=list)
    empty_clusters: list[Cluster] = field(default_factory=list)
    duplicate_labels: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True only when nothing that breaks the ≥1-cluster / non-redundancy invariants exists.

        Empty clusters are a *warning*, not a violation (a cluster may legitimately
        empty as its tags retire; it is never auto-deleted — AC8), so they do not
        make a report unclean.
        """
        return not self.orphan_active_tags and not self.duplicate_labels


def check_integrity() -> IntegrityReport:
    """Scan for orphan active tags, empty clusters, and duplicate labels (AC5)."""
    orphan_active_tags = list(
        Tag.objects.filter(status=Tag.Status.ACTIVE)
        .annotate(cluster_count=Count("clusters"))
        .filter(cluster_count=0)
    )
    empty_clusters = list(Cluster.objects.annotate(tag_count=Count("tags")).filter(tag_count=0))
    # .order_by() clears the model's Meta ordering so the GROUP BY is on the canonical
    # label alone (otherwise Django adds `label` to GROUP BY and the grouping breaks).
    duplicate_rows = (
        Tag.objects.annotate(_canonical=CanonicalLabel("label"))
        .values("_canonical")
        .order_by()
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    duplicate_labels = [row["_canonical"] for row in duplicate_rows]
    return IntegrityReport(
        orphan_active_tags=orphan_active_tags,
        empty_clusters=empty_clusters,
        duplicate_labels=duplicate_labels,
    )
