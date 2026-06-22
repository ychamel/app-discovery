"""The single write path for interests (DESIGN.md §5.1/§7) — the only place ``Interest``
rows are created or deleted, and the only caller of ``is_valid_tag`` for this feature's
write boundary.

This module **does not import ``signals.capture``** (IP-5): declaring an interest is
preference state, not behavior, so it emits **no D-7 corpus event**. The cleanest proof of
that invariant is the absent import — asserted by a structural test (DESIGN §17).

The load-bearing seam is the **set-replace with preserve-on-edit** reconcile (DESIGN §7).
A naive set-replace ("the new set is exactly what was submitted") would silently drop a
stored id the active-only picker can't show — a *no-successor* retired tag (``retire_tag``
allows ``replaced_by=None``) — violating AC7/M5. So the reconcile preserves any stored id
that ``resolve_tag`` maps to a non-active tag: the user never saw it, so they did not
deselect it. A renamed/merged id resolves to its *active* successor (shown + pre-checked),
so it normalizes toward the successor on re-save rather than being preserved. ``clear_interests``
deliberately bypasses the preserve rule — an explicit full wipe is the user saying "none".
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from apps.core import config, observability
from apps.interests.errors import InterestValidationError
from apps.interests.models import Interest
from apps.taxonomy import selectors as taxonomy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SetResult:
    """The outcome of a ``set_interests`` save — lets the view message the user and lets the
    metric reflect first-declaration vs. edit vs. cleared (DESIGN §5.1)."""

    added: int
    removed: int
    total: int


def set_interests(user, tag_ids: Iterable[UUID]) -> SetResult:
    """Set ``user``'s declared interests to ``tag_ids`` (the picker save — AC1/AC2/AC4).

    All-or-nothing: every id must be an active taxonomy tag, or nothing is written (AC2).
    Set-replace with preserve-on-edit (§7): the stored set becomes the submitted set, but a
    stored id the active picker can't show (resolves non-active) is preserved so it is never
    silently dropped (AC7). Idempotent: re-saving the current set is a no-op.
    """
    submitted = list(tag_ids)
    _validate_submitted(submitted)

    # Validation guarantees every id is an active tag (hence a well-formed UUID), so the
    # coercion is safe here. We normalize to UUID so the reconcile set-math compares cleanly
    # against the stored ids (which the ORM returns as UUID objects) — strings would never
    # match and would churn every row.
    submitted_set = {UUID(str(tag_id)) for tag_id in submitted}
    current_ids = _current_stored_ids(user)
    preserved = _preserved_unshowable_ids(current_ids)
    new_set = submitted_set | preserved

    to_add = new_set - current_ids
    to_remove = current_ids - new_set
    _apply_delta(user, to_add=to_add, to_remove=to_remove)

    result = SetResult(added=len(to_add), removed=len(to_remove), total=len(new_set))
    _count_write(prior_count=len(current_ids), result=result)
    return result


def clear_interests(user) -> int:
    """Delete **all** ``user``'s interest rows unconditionally — the AC9 self-clear.

    A full wipe deliberately **bypasses** the §7 preserve rule (including any preserved
    non-active ref): an explicit clear is the user saying "none at all", distinct from a
    picker save. Returns the deleted count; idempotent (clearing an empty profile → 0).
    """
    deleted_count, _ = Interest.objects.filter(user=user).delete()
    if deleted_count:
        observability.increment(observability.INTEREST_PROFILE_CLEARED)
        logger.info("interests cleared count=%s", deleted_count)
    return deleted_count


# --- Internals ---------------------------------------------------------------
def _validate_submitted(submitted: list[UUID]) -> None:
    """Reject the whole save loudly if it is over-size or contains any invalid id (AC2).

    Runs **before** any write so a partial set never persists. The over-size cap is a
    defensive resource guard (DESIGN §5.4/§9); ``is_valid_tag`` is the closed-vocabulary
    boundary (active-only, malformed-tolerant).
    """
    if len(submitted) > config.interest_declaration_max():
        observability.increment(observability.INTEREST_DECLARATION_REJECTED, reason="over_size")
        raise InterestValidationError(
            f"Too many interests submitted ({len(submitted)}); "
            f"the limit is {config.interest_declaration_max()}."
        )
    for tag_id in submitted:
        if not taxonomy.is_valid_tag(tag_id):
            observability.increment(
                observability.INTEREST_DECLARATION_REJECTED, reason="invalid_tag"
            )
            raise InterestValidationError(
                f"{tag_id!r} is not a selectable interest tag."
            )


def _current_stored_ids(user) -> set[UUID]:
    """The user's currently stored tag ids (one indexed per-user read)."""
    return set(Interest.objects.filter(user=user).values_list("tag_id", flat=True))


def _preserved_unshowable_ids(stored_ids: set[UUID]) -> set[UUID]:
    """The stored ids the active-only picker can't show, so a save must not drop them (§7/AC7).

    An id whose ``resolve_tag`` is non-active (a no-successor retired tag) — or, defensively,
    unresolvable — is preserved: the user never saw it in the picker, so they did not
    deselect it. An id resolving to an *active* tag (itself, or a successor the picker shows)
    is **not** preserved — it normalizes toward the active id on re-save.
    """
    preserved = set()
    for tag_id in stored_ids:
        resolved = taxonomy.resolve_tag(tag_id)
        if resolved is None or not resolved.is_active:
            preserved.add(tag_id)
    return preserved


def _apply_delta(user, *, to_add: set[UUID], to_remove: set[UUID]) -> None:
    """Apply the reconcile delta in one transaction (DESIGN §7).

    Delta-only writes mean the ``unique(user, tag_id)`` constraint never collides. Saving an
    unchanged set is an empty delta (no row churn). Two concurrent saves by the same user are
    serialized by the transaction; a DB error rolls the whole save back (no partial set).
    """
    if not to_add and not to_remove:
        return
    with transaction.atomic():
        if to_remove:
            Interest.objects.filter(user=user, tag_id__in=to_remove).delete()
        if to_add:
            Interest.objects.bulk_create(
                [Interest(user=user, tag_id=tag_id) for tag_id in to_add]
            )


def _count_write(*, prior_count: int, result: SetResult) -> None:
    """Emit the metric the delta + prior state imply (DESIGN §5.1/§12).

    A no-op save (empty delta) emits nothing. Otherwise: 0 → ≥1 is a first declaration (M1);
    a save that empties a non-empty profile is a clear; any other change to a non-empty
    profile is an edit (M4).
    """
    if result.added == 0 and result.removed == 0:
        return
    if prior_count == 0 and result.total >= 1:
        observability.increment(observability.INTEREST_DECLARED)
    elif result.total == 0:
        observability.increment(observability.INTEREST_PROFILE_CLEARED)
    else:
        observability.increment(observability.INTEREST_PROFILE_UPDATED)
