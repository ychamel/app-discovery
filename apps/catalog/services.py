"""The single write path for the catalog (DESIGN.md §3/§5a/§7/§10).

Every mutation of an ``App``, its tags, its media, or a ``ReviewDecision`` goes through
one of these functions — **nothing else writes catalog rows**. That keeps the invariants
in exactly one place (illegal states unrepresentable):

  * a submission has a name, description, well-formed http(s) URL, ≥1 valid tag, ≥1 image
    (AC1) — else nothing is written (atomic);
  * every tag is an *active* taxonomy tag (AC4) — off-vocabulary ids are refused, never
    coined here;
  * media is a real, decodable image of an allowed format within the size/count caps (§9),
    stored under framework-generated names (never the client filename);
  * only the lawful lifecycle transitions occur, and an edit to a gate-relevant field of an
    *accepted* app returns it to ``pending`` for re-review (AC8).

This module is split across two task-sized halves that share this file: the **content
writes** here (T-05) and the **lifecycle/decision writes** (T-06). Each function runs in a
single ``transaction.atomic()`` so a failed invariant writes nothing, and emits its
observability counter on success. Failures are raised loudly via ``apps.catalog.errors``
or Django ``ValidationError`` — never swallowed.
"""

import uuid

from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.utils import timezone

from apps.catalog import gate
from apps.catalog.errors import (
    InvalidTagError,
    InvalidTransitionError,
    MediaLimitError,
)
from apps.catalog.models import App, AppMedia, AppTag, ReviewDecision
from apps.catalog.urlnorm import normalize_url
from apps.core import config, observability
from apps.taxonomy import selectors as taxonomy

# Sentinel for "argument not supplied" so ``edit_app`` can tell "leave unchanged" apart
# from an explicit value (including an empty one, which is itself invalid and refused).
_UNSET = object()

# Allowed upload formats (DESIGN.md §9) → the extension used for the generated filename.
_ALLOWED_IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}

_validate_http_url = URLValidator(schemes=["http", "https"])


# --- Full-text search index (the single source of the search formula) --------
def _search_vector_expr() -> SearchVector:
    """The one definition of the catalogue's full-text index: name(A) + description(B).

    The search field list and their weights live here and nowhere else (open-search-browse
    DESIGN.md §5b/§8) — changing what is searchable is a one-function edit (then a
    re-backfill). Used by ``submit_app``/``edit_app`` to maintain ``App.search_vector`` and
    by the T-03 backfill data migration (imported, not re-stated), so the formula cannot
    drift between the write path and the backfill.
    """
    return SearchVector("name", weight="A") + SearchVector("description", weight="B")


def _maintain_search_vector(app: App) -> None:
    """Recompute and store ``app.search_vector`` from its own name/description columns.

    Runs one ``UPDATE ... SET search_vector = <expr>`` so the vector is computed in the
    database from the row's current text — called only where name/description change
    (``submit_app`` on create, ``edit_app`` on a text edit), inside the same transaction.
    """
    App.objects.filter(pk=app.pk).update(search_vector=_search_vector_expr())


# --- Submission --------------------------------------------------------------
@transaction.atomic
def submit_app(owner, *, name, description, url, tag_ids, media) -> App:
    """Create a ``pending`` app from a complete, valid submission (AC1/AC4).

    Refuses (writing nothing) unless every required field is present and valid. On success
    the app enters the review queue and ``submission_created`` is emitted.
    """
    clean_name = _require_text(name, "name")
    clean_description = _require_text(description, "description")
    clean_url = _require_url(url)
    unique_tag_ids = _require_valid_tags(tag_ids)
    media_list = _require_media_present(media)
    _check_media_count(0, len(media_list))
    for upload in media_list:
        _validate_image(upload)

    app = App.objects.create(
        owner=owner,
        name=clean_name,
        description=clean_description,
        url=clean_url,
        normalized_url=normalize_url(clean_url),
        status=App.Status.PENDING,
        last_submitted_at=timezone.now(),
    )
    _set_tags(app, unique_tag_ids)
    for position, upload in enumerate(media_list):
        _store_media(app, upload, position=position)

    _maintain_search_vector(app)
    _flag_duplicate_if_any(app)
    observability.increment(observability.SUBMISSION_CREATED, app_id=str(app.id))
    return app


# --- Owner edits -------------------------------------------------------------
@transaction.atomic
def edit_app(app, *, name=_UNSET, description=_UNSET, url=_UNSET, tag_ids=_UNSET) -> App:
    """Edit an app's metadata/tags (AC8). Only supplied fields change.

    If the app is ``accepted`` and any gate-relevant field actually changes, it returns to
    ``pending`` (it leaves the catalog until re-reviewed). A ``pending``/``rejected`` app
    updates in place — a rejected app re-enters review only via the explicit
    ``resubmit_app`` (T-06), never as a side effect of an edit.
    """
    changed_fields: set[str] = set()
    update_fields: list[str] = []

    if name is not _UNSET:
        clean_name = _require_text(name, "name")
        if clean_name != app.name:
            app.name = clean_name
            changed_fields.add("name")
            update_fields.append("name")
    if description is not _UNSET:
        clean_description = _require_text(description, "description")
        if clean_description != app.description:
            app.description = clean_description
            changed_fields.add("description")
            update_fields.append("description")
    if url is not _UNSET:
        clean_url = _require_url(url)
        if clean_url != app.url:
            app.url = clean_url
            app.normalized_url = normalize_url(clean_url)
            changed_fields.add("url")
            update_fields.extend(["url", "normalized_url"])
    if tag_ids is not _UNSET:
        unique_tag_ids = _require_valid_tags(tag_ids)
        if _tags_changed(app, unique_tag_ids):
            _set_tags(app, unique_tag_ids)
            changed_fields.add("tags")

    if update_fields:
        update_fields.append("updated_at")
        app.save(update_fields=update_fields)
    # Recompute the FTS vector only when a searched field (name/description) actually changed
    # — a tags-only or url-only edit leaves it untouched (DESIGN.md §5b, no needless rewrite).
    if changed_fields & {"name", "description"}:
        _maintain_search_vector(app)
    _return_to_review_if_accepted(app, changed_fields)
    return app


# --- Media -------------------------------------------------------------------
@transaction.atomic
def add_media(app, image, *, alt_text="") -> AppMedia:
    """Add one screenshot to an app, bounded by the per-app count cap (AC8/§9).

    Media is a gate-relevant field, so adding one to an *accepted* app returns it to
    ``pending`` for re-review (AC8).
    """
    existing = app.media.count()
    _check_media_count(existing, 1)
    _validate_image(image)
    media = _store_media(app, image, position=_next_position(app), alt_text=alt_text)
    _return_to_review_if_accepted(app, {"media"})
    return media


@transaction.atomic
def remove_media(media) -> None:
    """Remove a screenshot, refusing to drop an app below its 1-image minimum (AC1/AC8)."""
    app = media.app
    if app.media.count() <= 1:
        raise MediaLimitError("An app must keep at least one screenshot.")
    media.delete()
    _return_to_review_if_accepted(app, {"media"})


# --- Invariant helpers (the single boundary) ---------------------------------
def _require_text(value, field: str) -> str:
    """Return a non-blank, stripped string for ``field`` or raise a per-field error."""
    text = (value or "").strip() if isinstance(value, str) else ""
    if not text:
        raise ValidationError({field: "This field is required."})
    return text


def _require_url(value) -> str:
    """Return a well-formed, length-bounded http(s) URL or raise a per-field error."""
    url = _require_text(value, "url")
    if len(url) > 2000:
        raise ValidationError({"url": "URL is too long (max 2000 characters)."})
    try:
        _validate_http_url(url)
    except ValidationError:
        raise ValidationError({"url": "Enter a valid http(s) URL."}) from None
    return url


def _require_valid_tags(tag_ids) -> list[uuid.UUID]:
    """Validate ≥1 tag, all active taxonomy tags (AC4); return deduped ids in order.

    Off-vocabulary ids are counted (``tag_off_vocabulary_rejected`` must read 0 in normal
    use) and refused — nothing is written. No tag is ever coined here.
    """
    ids = list(tag_ids or [])
    if not ids:
        raise ValidationError({"tags": "Select at least one tag."})

    unique_ids: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    invalid: list = []
    for raw in ids:
        coerced = _coerce_uuid(raw)
        if coerced is None or not taxonomy.is_valid_tag(coerced):
            invalid.append(raw)
            continue
        if coerced not in seen:
            seen.add(coerced)
            unique_ids.append(coerced)

    if invalid:
        for bad in invalid:
            observability.increment(
                observability.TAG_OFF_VOCABULARY_REJECTED, tag_id=str(bad)
            )
        raise InvalidTagError(f"Not active taxonomy tags: {invalid!r}.")
    return unique_ids


def _coerce_uuid(raw):
    """Coerce a value to a UUID, or None if it is not a valid UUID (never raises)."""
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        return None


def _tags_changed(app, unique_tag_ids: list[uuid.UUID]) -> bool:
    current = set(app.app_tags.values_list("tag_id", flat=True))
    return current != set(unique_tag_ids)


def _set_tags(app, unique_tag_ids: list[uuid.UUID]) -> None:
    """Replace the app's tag set with exactly ``unique_tag_ids`` (already validated)."""
    app.app_tags.all().delete()
    AppTag.objects.bulk_create(
        [AppTag(app=app, tag_id=tag_id) for tag_id in unique_tag_ids]
    )


def _check_media_count(existing: int, adding: int) -> None:
    """Raise if ``existing + adding`` would exceed the per-app media cap (§9)."""
    max_count = config.catalog_media_max_count()
    if existing + adding > max_count:
        raise MediaLimitError(
            f"An app may have at most {max_count} screenshots."
        )


def _require_media_present(media) -> list:
    media_list = list(media or [])
    if not media_list:
        raise ValidationError({"media": "Add at least one screenshot."})
    return media_list


def _validate_image(upload) -> None:
    """Validate one upload as a real, decodable image of an allowed format within size (§9).

    Pillow decodes the bytes (a non-image fails ``verify``); the format must be one of the
    allowed types and the byte size within the configured cap. Raises ``MediaLimitError``
    on any failure — no file is stored.
    """
    max_bytes = config.catalog_media_max_bytes()
    size = getattr(upload, "size", None)
    if size is not None and size > max_bytes:
        raise MediaLimitError(f"Image exceeds the {max_bytes}-byte limit.")
    if _decode_image_format(upload) not in _ALLOWED_IMAGE_FORMATS:
        raise MediaLimitError("Upload must be a PNG, JPEG, or WebP image.")


def _decode_image_format(upload) -> str | None:
    """Return the Pillow-detected format of ``upload`` (e.g. ``PNG``), or None if undecodable."""
    from PIL import Image, UnidentifiedImageError

    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()  # integrity check — raises on a truncated/forged image
        upload.seek(0)
        with Image.open(upload) as image:
            return image.format
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    finally:
        upload.seek(0)


def _next_position(app) -> int:
    """The next free display position for an app's media (max + 1, gap-tolerant)."""
    last = app.media.order_by("-position").values_list("position", flat=True).first()
    return 0 if last is None else last + 1


def _store_media(app, upload, *, position: int, alt_text: str = "") -> AppMedia:
    """Persist one validated image under a framework-generated name (never the client's)."""
    fmt = _decode_image_format(upload)
    extension = _ALLOWED_IMAGE_FORMATS[fmt]
    generated_name = f"{uuid.uuid4().hex}.{extension}"
    media = AppMedia(app=app, position=position, alt_text=alt_text)
    upload.seek(0)
    media.image.save(generated_name, upload, save=False)
    media.save()
    return media


def _return_to_review_if_accepted(app, changed_fields: set[str]) -> None:
    """Return an accepted app to ``pending`` when a gate-relevant field changed (AC8).

    A gate-relevant edit can break the honest-metadata/works floor, so the app leaves the
    catalog until a reviewer re-clears it; it re-enters the FIFO queue with a fresh
    ``last_submitted_at``. A no-op for a non-accepted app or a non-gate-relevant change.
    """
    if app.status != App.Status.ACCEPTED:
        return
    if not (changed_fields & gate.GATE_RELEVANT_FIELDS):
        return
    app.status = App.Status.PENDING
    app.last_submitted_at = timezone.now()
    app.save(update_fields=["status", "last_submitted_at", "updated_at"])


def _flag_duplicate_if_any(app) -> None:
    """Emit ``duplicate_flagged`` if another app already shares this normalized URL (§6c).

    A signal for the reviewer (and a metric), never a rejection — duplicates may legitimately
    coexist (SI-2). The read-side hint that surfaces this in the queue lives in selectors (T-07).
    """
    shares = (
        App.objects.filter(normalized_url=app.normalized_url)
        .exclude(pk=app.pk)
        .exists()
    )
    if shares:
        observability.increment(observability.DUPLICATE_FLAGGED, app_id=str(app.id))


# --- Lifecycle & decisions (T-06; the only code that flips App.status via review) --------
# The lawful transitions from the §7 state machine. Any change from a state not listed for
# an action raises InvalidTransitionError (loud → 409). The accepted→pending re-review on
# an owner edit (T-05) is handled in _return_to_review_if_accepted, not here.
_WITHDRAWABLE_FROM = {App.Status.PENDING, App.Status.ACCEPTED, App.Status.REJECTED}
_RESUBMITTABLE_FROM = {App.Status.REJECTED, App.Status.WITHDRAWN}


@transaction.atomic
def accept_app(app, reviewer) -> ReviewDecision:
    """Accept a pending app (AC5): write the decision and flip status in one transaction.

    Takes a row lock and re-checks ``status == pending`` so two concurrent reviewers cannot
    double-decide (DESIGN.md §4). The developer notification is sent by the caller **after**
    commit (T-08) — kept out of this transaction.
    """
    locked = _lock_pending(app, "accept")
    decision = ReviewDecision.objects.create(
        app=locked,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.ACCEPTED,
        failed_criteria=[],
    )
    locked.status = App.Status.ACCEPTED
    # The single place accepted_at is stamped (re-stamped on re-acceptance) — the one source
    # of truth for newest-accepted-first browse order (DESIGN.md §5a). Set nowhere else.
    locked.accepted_at = timezone.now()
    locked.save(update_fields=["status", "accepted_at", "updated_at"])
    observability.increment(observability.APP_ACCEPTED, app_id=str(locked.id))
    observability.increment(observability.REVIEW_DECISION, outcome="accepted")
    _sync(app, locked)
    return decision


@transaction.atomic
def reject_app(app, reviewer, *, failed_criteria, note: str = "") -> ReviewDecision:
    """Reject a pending app naming ≥1 failed objective floor (AC5/AC6/AC7).

    A rejection **must** name ≥1 valid ``Criterion`` — zero or an unknown value raises
    ``ValidationError`` (→ 400). There is no "other" floor, so a taste rejection cannot be
    expressed (AC6). Writes the decision and flips status atomically; notifies after commit.
    """
    criteria = _clean_failed_criteria(failed_criteria)
    locked = _lock_pending(app, "reject")
    decision = ReviewDecision.objects.create(
        app=locked,
        reviewer=reviewer,
        outcome=ReviewDecision.Outcome.REJECTED,
        failed_criteria=criteria,
        note=(note or "").strip(),
    )
    locked.status = App.Status.REJECTED
    locked.save(update_fields=["status", "updated_at"])
    observability.increment(observability.APP_REJECTED, app_id=str(locked.id))
    observability.increment(observability.REVIEW_DECISION, outcome="rejected")
    for criterion in criteria:
        observability.increment(observability.REVIEW_DECISION, criterion=criterion)
    _sync(app, locked)
    return decision


@transaction.atomic
def withdraw_app(app) -> App:
    """Owner withdraws an app from the catalog/queue (AC8): * → withdrawn."""
    locked = _lock(app)
    if locked.status not in _WITHDRAWABLE_FROM:
        raise InvalidTransitionError(
            f"Cannot withdraw an app in status {locked.status!r}."
        )
    locked.status = App.Status.WITHDRAWN
    locked.save(update_fields=["status", "updated_at"])
    observability.increment(observability.APP_WITHDRAWN, app_id=str(locked.id))
    _sync(app, locked)
    return app


@transaction.atomic
def resubmit_app(app) -> App:
    """Re-offer a rejected/withdrawn app (AC7 — rejection is non-terminal): → pending.

    Sets a fresh ``last_submitted_at`` so the app re-enters the FIFO queue at the back.
    """
    locked = _lock(app)
    if locked.status not in _RESUBMITTABLE_FROM:
        raise InvalidTransitionError(
            f"Cannot resubmit an app in status {locked.status!r}."
        )
    locked.status = App.Status.PENDING
    locked.last_submitted_at = timezone.now()
    locked.save(update_fields=["status", "last_submitted_at", "updated_at"])
    observability.increment(observability.APP_RESUBMITTED, app_id=str(locked.id))
    _sync(app, locked)
    return app


def _lock(app) -> App:
    """Re-fetch the app row under ``select_for_update`` so its status cannot race."""
    return App.objects.select_for_update().get(pk=app.pk)


def _lock_pending(app, action: str) -> App:
    """Lock the row and assert it is still ``pending`` (no double decision, §4)."""
    locked = _lock(app)
    if locked.status != App.Status.PENDING:
        raise InvalidTransitionError(
            f"Cannot {action} an app in status {locked.status!r} (must be pending)."
        )
    return locked


def _clean_failed_criteria(failed_criteria) -> list[str]:
    """Coerce/validate the failed-floor list: ≥1 value, each a known ``Criterion`` (AC6)."""
    values = [str(c) for c in (failed_criteria or [])]
    if not values:
        raise ValidationError(
            {"failed_criteria": "A rejection must name at least one failed criterion."}
        )
    valid = set(gate.Criterion.values)
    unknown = [v for v in values if v not in valid]
    if unknown:
        raise ValidationError(
            {"failed_criteria": f"Unknown criterion value(s): {unknown!r}."}
        )
    # De-duplicate while preserving order (one row per floor in the metric).
    seen: set[str] = set()
    return [v for v in values if not (v in seen or seen.add(v))]


def _sync(app, locked) -> None:
    """Reflect the locked row's committed state back onto the caller's in-memory app."""
    app.status = locked.status
    app.last_submitted_at = locked.last_submitted_at
    app.accepted_at = locked.accepted_at
    app.updated_at = locked.updated_at
