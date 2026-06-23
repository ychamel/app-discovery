"""The single read/validate/resolve path for the interest vocabulary (DESIGN.md §5a/§7).

Every consumer — the matcher, interest-profile, submission-intake, and the JSON read
API in this app — reads the vocabulary through these functions, so "what a tag means
now" has one source of truth. The two functions downstream features lean on are:

  * ``is_valid_tag(id)`` — the closed-set validator consumers enforce at *their* write
    boundary (AC2), mirroring how ``HasRole`` supplies a check the view enforces; and
  * ``resolve_tag(id)`` — follows ``replaced_by`` to a tag's current meaning, keeping
    retired references valid and never rewriting the caller's stored value
    (reference-break-rate = 0, AC6/AC7).
"""

import logging
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Prefetch

from apps.core import config, observability
from apps.taxonomy.models import Cluster, Tag

logger = logging.getLogger("apps.taxonomy.selectors")


def list_active_tags() -> list[Tag]:
    """All active tags with their cluster membership prefetched (no N+1) — feeds the picker."""
    return list(
        Tag.objects.filter(status=Tag.Status.ACTIVE).prefetch_related("clusters")
    )


def list_clusters() -> list[Cluster]:
    """All clusters, each carrying only its *active* tags (prefetched, no N+1)."""
    active_tags = Tag.objects.filter(status=Tag.Status.ACTIVE)
    return list(
        Cluster.objects.prefetch_related(Prefetch("tags", queryset=active_tags))
    )


def get_tag(tag_id: UUID) -> Tag | None:
    """Return the tag of any status, or None if no tag has that id."""
    return (
        Tag.objects.filter(pk=tag_id).prefetch_related("clusters").first()
    )


def is_valid_tag(tag_id: UUID) -> bool:
    """True only for an existing ACTIVE tag (AC2).

    Tolerant of a malformed id: an off-vocabulary or non-UUID value is simply invalid
    (False), never an exception — this is the validator consumers run on input they do
    not control.
    """
    try:
        return Tag.objects.filter(pk=tag_id, status=Tag.Status.ACTIVE).exists()
    except (ValidationError, ValueError, TypeError):
        return False


def tag_ids_resolving_to(active_id: UUID) -> frozenset[UUID]:
    """All stored tag ids that resolve to ``active_id`` now (open-search-browse DESIGN.md §6.2).

    Returns ``{active_id}`` plus its **transitive merge predecessors** — every tag whose
    ``replaced_by`` chain leads to ``active_id``. This is the reverse of ``resolve_tag``: a
    catalogue tag filter on ``active_id`` must also match a retired predecessor that now
    *means* ``active_id``, so the filter stays consistent with the resolved labels the
    catalogue displays (AC3).

    Tolerant of bad input like ``is_valid_tag`` — an unknown / non-UUID / malformed id yields
    ``frozenset()`` and never raises (the caller validates with ``is_valid_tag`` first). The
    walk is bounded by **vocabulary size** (small, slow-growing reference data), not catalogue
    size — a deliberate, documented bound (DESIGN §5.2/§14). If the vocabulary ever grows huge,
    a recursive CTE replaces the walk behind this same signature.
    """
    try:
        if not Tag.objects.filter(pk=active_id).exists():
            return frozenset()
    except (ValidationError, ValueError, TypeError):
        return frozenset()

    resolved: set[UUID] = {active_id}
    frontier: set[UUID] = {active_id}
    while frontier:
        # The inverse of the replaced_by FK (related_name="replaces"): the tags merged
        # directly into anything in the current frontier, minus those already collected.
        predecessors = set(
            Tag.objects.filter(replaced_by_id__in=frontier)
            .exclude(pk__in=resolved)
            .values_list("id", flat=True)
        )
        if not predecessors:
            break
        resolved |= predecessors
        frontier = predecessors
    return frozenset(resolved)


def resolve_tag(tag_id: UUID) -> Tag | None:
    """Resolve a stored tag id to its current meaning (AC6/AC7).

    Follows ``replaced_by`` to the active successor; a retired tag with no successor
    resolves to *itself* (kept, never dropped). Returns None only if the id never
    existed. The walk is bounded by ``config.taxonomy_resolve_max_steps`` — on a cycle
    or over-long chain it logs loudly, counts ``TAXONOMY_REFERENCE_BREAK``, and returns
    the last good tag rather than looping. It never rewrites the caller's stored value.
    """
    tag = get_tag(tag_id)
    if tag is None:
        return None

    max_steps = config.taxonomy_resolve_max_steps()
    current = tag
    for _ in range(max_steps):
        if current.replaced_by_id is None:
            return current
        current = current.replaced_by

    # Still chaining after max_steps ⇒ a cycle or pathological chain. Fail loud, alert,
    # and return the last tag we reached (never loop, never drop the reference).
    logger.error(
        "resolve_tag stopped after %s steps for tag id %s (cycle or over-long replaced_by chain)",
        max_steps,
        tag_id,
    )
    observability.increment(observability.TAXONOMY_REFERENCE_BREAK, tag_id=str(tag_id))
    return current
