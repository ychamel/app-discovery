"""The single read path for interests (DESIGN.md §5.2) — the **only** read surface and the
**only** place ``resolve_tag`` is applied to stored ids.

No consumer (including this app's own views) reads ``Interest`` rows directly (AC8): the
picker reads through here, the onboarding nudge reads through here, and the future matcher
reads through ``declared_tag_ids``. No write, no scoring.

  * ``declared_tag_ids`` — the **matcher contract** (AC7/AC8): the deduplicated set of
    *resolved current* ``Tag.id``s. A no-successor retired ref resolves to itself and stays
    (never dropped); two stored ids resolving to one successor collapse to one.
  * ``declared_tags`` — the same, as resolved ``Tag`` objects ordered by label, for display
    and the picker pre-check.
  * ``has_declared_interests`` — one indexed ``EXISTS``; drives the onboarding prompt and the
    empty-state branch (AC6).
  * ``count_unresolvable`` — the M5 ops invariant: stored ids whose ``resolve_tag`` is
    ``None`` (**0 by construction**; D-5 soft-retires, never hard-deletes).
"""

from uuid import UUID

from apps.interests.models import Interest
from apps.taxonomy import selectors as taxonomy
from apps.taxonomy.models import Tag


def _authenticated(user) -> bool:
    return user is not None and getattr(user, "is_authenticated", False)


def _resolved_tags(user) -> list[Tag]:
    """Resolve each stored id to its current meaning, deduped by resolved id (DESIGN §5.2/§7).

    A no-successor retired tag resolves to itself and is kept (AC7); ids resolving to the same
    successor collapse to one. Bounded by the per-user set size (small) — one read of the
    stored ids plus a ``resolve_tag`` per id.
    """
    stored_ids = Interest.objects.filter(user=user).values_list("tag_id", flat=True)
    resolved_by_id: dict[UUID, Tag] = {}
    for tag_id in stored_ids:
        tag = taxonomy.resolve_tag(tag_id)
        if tag is not None:
            resolved_by_id.setdefault(tag.id, tag)
    return list(resolved_by_id.values())


def declared_tag_ids(user) -> frozenset[UUID]:
    """The user's declared interests as resolved current ``Tag.id``s — the matcher contract.

    Returns a ``frozenset`` of ``Tag.id``s (never a label/slug). Anonymous/``None`` → empty
    (AC6). A renamed/merged stored id appears as its successor; a no-successor retired id
    appears as itself (never silently dropped — AC7); duplicates collapse (dedupe).
    """
    if not _authenticated(user):
        return frozenset()
    return frozenset(tag.id for tag in _resolved_tags(user))


def declared_tags(user) -> list[Tag]:
    """The user's declared interests as resolved ``Tag`` objects, ordered by label (display)."""
    if not _authenticated(user):
        return []
    return sorted(_resolved_tags(user), key=lambda tag: tag.label)


def has_declared_interests(user) -> bool:
    """Whether ``user`` has declared any interest — ``False`` for anonymous/``None`` (AC6)."""
    if not _authenticated(user):
        return False
    return Interest.objects.filter(user=user).exists()


def count_unresolvable() -> int:
    """The M5 ops invariant: stored ids whose ``resolve_tag`` is ``None`` (DESIGN §12).

    **0 by construction** — every id is validated active at write and D-5 soft-retires rather
    than hard-deletes, so a stored id always still exists. This is a cheap invariant check
    (the live reference-break counter is the taxonomy ``TAXONOMY_REFERENCE_BREAK``, reused —
    not re-added here). Detects a corrupted/hand-inserted id; it does not produce one.
    """
    stored_ids = Interest.objects.values_list("tag_id", flat=True).distinct()
    return sum(1 for tag_id in stored_ids if taxonomy.resolve_tag(tag_id) is None)
