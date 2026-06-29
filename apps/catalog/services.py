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

from apps.catalog import facets, gate
from apps.catalog.errors import (
    InvalidFacetError,
    InvalidTagError,
    InvalidTransitionError,
    MediaLimitError,
)
from apps.catalog.facets import FacetCardinality
from apps.catalog.models import App, AppFacet, AppMedia, AppTag, ReviewDecision
from apps.catalog.urlnorm import normalize_url
from apps.core import config, observability
from apps.taxonomy import selectors as taxonomy

# Sentinel for "argument not supplied" so ``edit_app`` can tell "leave unchanged" apart
# from an explicit value (including an empty one, which is itself invalid and refused).
_UNSET = object()

# Allowed upload formats (DESIGN.md §9) → the extension used for the generated filename.
_ALLOWED_IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}

# Allowed demo-clip containers (app-page-redesign DESIGN.md §5.1/§9.4) → generated extension.
# Sniffed from magic bytes (never the client's content-type/extension): MP4 carries an
# ``ftyp`` box at offset 4; WebM/Matroska opens with the EBML magic ``1A 45 DF A3``.
_CLIP_MP4 = "mp4"
_CLIP_WEBM = "webm"
_WEBM_MAGIC = b"\x1a\x45\xdf\xa3"

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
def submit_app(
    owner,
    *,
    name,
    description,
    url,
    tag_ids,
    media,
    tagline="",
    deep_dive="",
    facet_values=None,
    demo_clip=None,
    demo_clip_alt="",
) -> App:
    """Create a ``pending`` app from a complete, valid submission (AC1/AC4).

    Refuses (writing nothing) unless every **required** field is present and valid. The
    marketing fields (``tagline``/``deep_dive``/``facet_values``/``demo_clip`` + its alt) are
    **optional** (app-page-redesign DESIGN.md §8) — the required submission floor is unchanged
    — but each is validated at this boundary when supplied. On success the app enters the
    review queue and ``submission_created`` is emitted.
    """
    clean_name = _require_text(name, "name")
    clean_description = _require_text(description, "description")
    clean_url = _require_url(url)
    unique_tag_ids = _require_valid_tags(tag_ids)
    media_list = _require_media_present(media)
    _check_media_count(0, len(media_list))
    for upload in media_list:
        _validate_image(upload)
    # Validate the optional marketing fields before any write (atomic — nothing persists on a
    # bad facet/clip). The clip is sniffed + size-capped and requires alt text when present.
    clean_tagline = _clean_tagline(tagline)
    clean_deep_dive = _clean_deep_dive(deep_dive)
    facet_pairs = _require_valid_facets(facet_values)
    clip_container = _validate_clip(demo_clip, demo_clip_alt) if demo_clip else None

    app = App.objects.create(
        owner=owner,
        name=clean_name,
        description=clean_description,
        url=clean_url,
        normalized_url=normalize_url(clean_url),
        status=App.Status.PENDING,
        last_submitted_at=timezone.now(),
        tagline=clean_tagline,
        deep_dive=clean_deep_dive,
        demo_clip_alt=(demo_clip_alt or "").strip() if demo_clip else "",
    )
    _set_tags(app, unique_tag_ids)
    for position, upload in enumerate(media_list):
        _store_media(app, upload, position=position)
    if demo_clip:
        _store_clip(app, demo_clip, clip_container)
        app.save(update_fields=["demo_clip"])  # the file was set save=False above
    if facet_pairs:
        _set_facets(app, facet_pairs)

    _maintain_search_vector(app)
    _flag_duplicate_if_any(app)
    observability.increment(observability.SUBMISSION_CREATED, app_id=str(app.id))
    return app


# --- Owner edits -------------------------------------------------------------
@transaction.atomic
def edit_app(
    app,
    *,
    name=_UNSET,
    description=_UNSET,
    url=_UNSET,
    tag_ids=_UNSET,
    tagline=_UNSET,
    deep_dive=_UNSET,
    facet_values=_UNSET,
    demo_clip=_UNSET,
    demo_clip_alt=_UNSET,
) -> App:
    """Edit an app's metadata/tags/marketing fields (AC8). Only supplied fields change.

    If the app is ``accepted`` and any **gate-relevant** field actually changes, it returns
    to ``pending`` (it leaves the catalog until re-reviewed). Which fields are gate-relevant
    is ``gate.gate_relevant_fields()`` — the core floor always, plus the config-toggled
    marketing fields (D-14b). A ``pending``/``rejected`` app updates in place — a rejected app
    re-enters review only via the explicit ``resubmit_app`` (T-06), never as an edit side
    effect.
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
    if tagline is not _UNSET:
        clean_tagline = _clean_tagline(tagline)
        if clean_tagline != app.tagline:
            app.tagline = clean_tagline
            changed_fields.add("tagline")
            update_fields.append("tagline")
    if deep_dive is not _UNSET:
        clean_deep_dive = _clean_deep_dive(deep_dive)
        if clean_deep_dive != app.deep_dive:
            app.deep_dive = clean_deep_dive
            changed_fields.add("deep_dive")
            update_fields.append("deep_dive")
    if facet_values is not _UNSET:
        facet_pairs = _require_valid_facets(facet_values)
        if _facets_changed(app, facet_pairs):
            _set_facets(app, facet_pairs)
            changed_fields.add("facets")
    # The clip (file + its alt) is its own helper — sniff/size/alt validation and the
    # set/replace/remove cases are too involved for an inline block (one function, one job).
    clip_update = _apply_clip_edit(app, demo_clip, demo_clip_alt)
    changed_fields |= clip_update
    update_fields.extend(_CLIP_PERSIST_FIELDS if clip_update else [])

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


# --- Marketing copy (optional; app-page-redesign DESIGN.md §5.1/§8) ----------
def _clean_tagline(value) -> str:
    """Strip the pitch line; refuse one over the 300-char column cap (fail loud at the boundary).

    Empty/blank is allowed (the field is optional → graceful-empty page, M2).
    """
    text = (value or "").strip() if isinstance(value, str) else ""
    if len(text) > 300:
        raise ValidationError({"tagline": "Tagline is too long (max 300 characters)."})
    return text


def _clean_deep_dive(value) -> str:
    """Strip the long-form deep dive; refuse one over the configured cap. Empty allowed (M2)."""
    text = (value or "").strip() if isinstance(value, str) else ""
    max_length = config.app_page_deep_dive_max_length()
    if len(text) > max_length:
        raise ValidationError(
            {"deep_dive": f"Deep dive is too long (max {max_length} characters)."}
        )
    return text


# --- Typed facets (optional; the AppTag pattern, firewalled from ranking) -----
def _require_valid_facets(facet_values) -> list[tuple[str, str]]:
    """Validate ``(facet, value)`` pairs: in-vocabulary + cardinality-respecting; dedupe.

    Each pair is checked against ``facets.is_valid_facet_value`` (off-vocabulary refused,
    nothing written — mirrors ``_require_valid_tags``); a SINGLE-cardinality facet may carry
    at most one value (a 2nd distinct value is refused). Returns the unique pairs to write
    (replace-set semantics applied by ``_set_facets``). ``None``/empty ⇒ ``[]`` (clear/none).
    """
    pairs = list(facet_values or [])
    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    single_choice: dict[str, str] = {}  # facet → its one chosen value (SINGLE cardinality)
    for raw in pairs:
        facet, value = _coerce_facet_pair(raw)
        if not facets.is_valid_facet_value(facet, value):
            raise InvalidFacetError(f"Not a valid facet value: {facet!r}={value!r}.")
        if (facet, value) in seen:
            continue
        if facets.cardinality_of(facet) is FacetCardinality.SINGLE:
            if facet in single_choice and single_choice[facet] != value:
                raise InvalidFacetError(
                    f"Facet {facet!r} allows only one value (got "
                    f"{single_choice[facet]!r} and {value!r})."
                )
            single_choice[facet] = value
        seen.add((facet, value))
        unique.append((facet, value))
    return unique


def _coerce_facet_pair(raw) -> tuple[str, str]:
    """Coerce one item to a ``(facet, value)`` string pair, or raise loudly if malformed."""
    try:
        facet, value = raw
    except (TypeError, ValueError):
        raise InvalidFacetError(
            f"A facet must be a (facet, value) pair, got {raw!r}."
        ) from None
    return str(facet), str(value)


def _facets_changed(app, pairs: list[tuple[str, str]]) -> bool:
    current = {(af.facet, af.value) for af in app.app_facets.all()}
    return current != set(pairs)


def _set_facets(app, pairs: list[tuple[str, str]]) -> None:
    """Replace the app's facet set with exactly ``pairs`` (already validated)."""
    app.app_facets.all().delete()
    AppFacet.objects.bulk_create(
        [AppFacet(app=app, facet=facet, value=value) for facet, value in pairs]
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


# --- Demo clip (optional; app-page-redesign DESIGN.md §5.1/§9.4) -------------
# The App columns persisted whenever the clip or its alt changes (one place, no drift).
_CLIP_PERSIST_FIELDS = ["demo_clip", "demo_clip_alt"]


def _validate_clip(upload, alt) -> str:
    """Validate one demo-clip upload; return its container (``mp4``/``webm``) or raise loudly.

    Same discipline as images: size-capped, container sniffed from **magic bytes** (never the
    client's content-type), and a present clip **requires** alt text (C5/A4). Raises
    ``MediaLimitError`` (nothing stored) on any failure.
    """
    if not (alt or "").strip():
        raise MediaLimitError("A demo clip needs a short text description (alt text).")
    max_bytes = config.catalog_clip_max_bytes()
    size = getattr(upload, "size", None)
    if size is not None and size > max_bytes:
        raise MediaLimitError(f"Demo clip exceeds the {max_bytes}-byte limit.")
    container = _sniff_clip_container(upload)
    if container is None:
        raise MediaLimitError("Demo clip must be an MP4 or WebM video.")
    return container


def _sniff_clip_container(upload) -> str | None:
    """Return ``mp4``/``webm`` from the upload's magic bytes, or None if it is neither."""
    try:
        upload.seek(0)
        head = upload.read(16)
    except (OSError, ValueError):
        return None
    finally:
        try:
            upload.seek(0)
        except (OSError, ValueError):
            pass
    if head[:4] == _WEBM_MAGIC:
        return _CLIP_WEBM
    if head[4:8] == b"ftyp":  # ISO base media (MP4/M4V) carries an ftyp box at offset 4
        return _CLIP_MP4
    return None


def _store_clip(app, upload, container: str) -> None:
    """Persist the demo clip under a framework-generated name (never the client's filename).

    Sets ``app.demo_clip`` in memory (``save=False``); the caller commits it with the rest of
    the row so the write stays in the one ``submit_app``/``edit_app`` transaction.
    """
    generated_name = f"{uuid.uuid4().hex}.{container}"
    upload.seek(0)
    app.demo_clip.save(generated_name, upload, save=False)


def _apply_clip_edit(app, demo_clip, demo_clip_alt) -> set[str]:
    """Apply a demo-clip edit; return the changed gate-field keys (``{"demo_clip"}`` or empty).

    Cases (the ``_UNSET`` sentinel distinguishes "leave alone" from an explicit value):
      * both unset → no change;
      * ``demo_clip`` set to a falsy value (``None``/empty) → **remove** the clip + its alt;
      * ``demo_clip`` set to a file → validate (sniff + size + alt) and **replace**;
      * only ``demo_clip_alt`` supplied → update the alt text of an existing clip.
    A change to the clip or its alt is a ``demo_clip`` gate change (the clip is one public
    claim), so it rides the config-toggled re-review like the other marketing fields.
    """
    if demo_clip is _UNSET:
        return _edit_clip_alt_only(app, demo_clip_alt)
    if not demo_clip:
        return _remove_clip(app)
    return _replace_clip(app, demo_clip, demo_clip_alt)


def _edit_clip_alt_only(app, demo_clip_alt) -> set[str]:
    if demo_clip_alt is _UNSET or not app.demo_clip:
        return set()
    new_alt = (demo_clip_alt or "").strip()
    if not new_alt or new_alt == app.demo_clip_alt:
        return set()
    app.demo_clip_alt = new_alt
    return {"demo_clip"}


def _remove_clip(app) -> set[str]:
    if not app.demo_clip:
        return set()
    app.demo_clip.delete(save=False)
    app.demo_clip = None
    app.demo_clip_alt = ""
    return {"demo_clip"}


def _replace_clip(app, demo_clip, demo_clip_alt) -> set[str]:
    effective_alt = (
        demo_clip_alt if demo_clip_alt is not _UNSET else app.demo_clip_alt
    )
    container = _validate_clip(demo_clip, effective_alt)
    if app.demo_clip:
        app.demo_clip.delete(save=False)
    _store_clip(app, demo_clip, container)
    app.demo_clip_alt = (effective_alt or "").strip()
    return {"demo_clip"}


def _return_to_review_if_accepted(app, changed_fields: set[str]) -> None:
    """Return an accepted app to ``pending`` when a gate-relevant field changed (AC8).

    A gate-relevant edit can break the honest-metadata/works floor, so the app leaves the
    catalog until a reviewer re-clears it; it re-enters the FIFO queue with a fresh
    ``last_submitted_at``. A no-op for a non-accepted app or a non-gate-relevant change.
    """
    if app.status != App.Status.ACCEPTED:
        return
    if not (changed_fields & gate.gate_relevant_fields()):
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
