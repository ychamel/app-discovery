# PATCH.md — patch-block-self-interaction

**Source issues (bundled):**
- [`Q-002`](../../issues/Q-002.md) — Should a user be able to submit a review for their own app? → **Answered: Option A — block self-review** (DN-Q002). Severity: **Medium**.
- [`Q-003`](../../issues/Q-003.md) — Should a user be able to follow their own app? → **Answered: Option A — block self-follow** (DN-Q003). Severity: **Low**.

These two are bundled because they are the **same shape**: a single ownership guard
(`viewer owns the app`) that suppresses an interaction control on the public app page and
rejects the corresponding mutation server-side. They touch the same surface (the app page
slots) and the same owner-identity source, so one patch resolves both coherently.

---

## 1. Coordinator triage (2026-06-29) — Source & scope gate

> Written by the Coordinator at routing. The **root-cause design and task list below are
> the Maintenance Planner's to fill** (Stage `P-plan`). This section is the verified
> starting context.

### Owner identity is available without a schema change

The public app page renders `app = catalog.get_catalogued_app(app_id)`, a
[`CatalogApp`](../../apps/catalog/selectors.py#L54) read-model that **already carries
`owner`** ([selectors.py:70](../../apps/catalog/selectors.py#L70), populated from the
existing `App.owner` FK at [selectors.py:108](../../apps/catalog/selectors.py#L108)). So
"is the viewer the app's owner?" is answerable today — **no migration, no new field.**

> Note for the Planner: [`app_page.html`](../../apps/pages/templates/pages/app_page.html)
> carries a comment claiming `CatalogApp` "carries no owner/team/paid field". That comment
> is about page *uniformity* (no app renders a *richer* page than another); it predates /
> is inconsistent with the DTO actually exposing `owner`. Confirm the field is reliably
> populated on the public path before relying on it, and reconcile the comment.

### Self-review (Q-002, Option A)

- Control: the rating form in
  [`_reviews_slot.html`](../../apps/ratings/templates/ratings/_reviews_slot.html#L48-L80),
  rendered via the `{% app_reviews app %}` inclusion tag
  ([`ratings_tags.py`](../../apps/ratings/templatetags/ratings_tags.py)).
- Mutation endpoint: `POST /ratings/apps/<id>/rating` →
  [`ratings.views.submit`](../../apps/ratings/views.py) →
  [`ratings.services.submit_rating`](../../apps/ratings/services.py).

### Self-follow (Q-003, Option A)

- Control: the Follow button in
  [`_follow_slot.html`](../../apps/subscriptions/templates/subscriptions/_follow_slot.html#L12-L17),
  rendered via the `{% app_follow app %}` inclusion tag
  ([`subscriptions_tags.py`](../../apps/subscriptions/templatetags/subscriptions_tags.py)).
- Mutation endpoint: `POST /subscriptions/apps/<id>/follow` →
  [`subscriptions.views.follow`](../../apps/subscriptions/views.py) →
  [`subscriptions.services.follow_app`](../../apps/subscriptions/services.py).

### Scope gate → Patch Track (confirmed)

No migration, **no new or changed public endpoint/route** (the guard is added *behaviour*
on existing endpoints, not a new contract), no global ADR. Hiding the control is
presentation; the robust block is a **server-side owner guard** at the write boundary —
per CLAUDE.md §5.4 the template hide alone is not sufficient (it is bypassable), so both
layers are in scope. **No-Schema Assertion to be confirmed by `makemigrations --check` at
build.**

### Framing for the Planner (not yet designed)

- Decide where the owner guard lives so it is the **single source of truth** for "owner
  cannot self-interact" — service layer is the robust trust boundary; the template hide is
  the cooperating UX layer. Avoid duplicating the ownership rule in two places without one
  canonical helper.
- Decide the rejected-mutation behaviour (e.g. 403 vs. fail-soft message + PRG) consistent
  with each app's existing house pattern (ratings uses PRG + `messages`; subscriptions
  surfaces faults as a message + PRG).
- Decide the suppressed-control UX (hide entirely vs. show a disabled control with a
  notice — Q-002 suggests *"You can't review your own app."*).
- Consider an owner who already has a pre-existing rating/follow from before this patch
  (edge case: should `remove`/`unfollow` still be allowed? likely yes, to let them clean
  up). Record the call in `DECISIONS.md`.

---

## 2. Problem Statement

### Planner investigation (2026-06-29)

**Key correction to Coordinator triage:** `CatalogApp` (the frozen dataclass at
[`selectors.py:54–63`](../../apps/catalog/selectors.py#L54)) exposes only `id`, `name`,
`description`, `url`, `tags`, `media`. **There is no `owner` field** on `CatalogApp`. The
`owner` references at selectors.py:70 and :108 belong to `ReviewRow` and
`list_review_queue` respectively — the admin queue path, not the public page path. The
`_to_catalog_app` factory at selectors.py:310 does not populate an `owner` field. The
comment in [`app_page.html:4–9`](../../apps/pages/templates/pages/app_page.html#L4) ("the
only input is `CatalogApp`, which carries no owner/team/paid field") is **accurate** — not
stale. No reconciliation needed there.

The issue files (Q-002/Q-003) both state "owner identity is already on the `CatalogApp`
read-model" — this is incorrect. The fix design must NOT rely on `app.owner` in templates
or inclusion tags (the field does not exist there).

### Reproduction

**Q-002 — Self-review:**
1. Register as a developer. Submit and get an app accepted via the admin queue.
2. While authenticated as that developer, navigate to `/apps/<id>/`.
3. The ratings slot renders a full score-select + review form addressed to `ratings:submit`.
4. Submit a rating: `POST /ratings/apps/<id>/rating` with `score=5`. Returns 302 to the
   app page — **rating is stored with no rejection** (`Rating.objects.filter(user=developer,
   app_id=<id>).exists()` → `True`).

**Q-003 — Self-follow:**
1. Same developer + accepted app.
2. The Follow slot renders a "Follow" button addressed to `subscriptions:follow`.
3. Click Follow: `POST /subscriptions/apps/<id>/follow`. Returns 302 to the app page —
   **follow row is stored** (`Subscription.objects.filter(user=developer,
   app_id=<id>).exists()` → `True`).

### Root Cause

Both write paths lack any ownership check:

- `ratings.services.submit_rating` ([services.py:33](../../apps/ratings/services.py#L33))
  calls `_require_catalogued_app` and `_validate` but has **no check** that the user is
  not the app's owner.
- `subscriptions.services.follow_app` ([services.py:30](../../apps/subscriptions/services.py#L30))
  calls `_require_catalogued_app` but has **no check** that the user is not the app's owner.
- Both inclusion tags (`app_reviews`, `app_follow`) build their slot context with no
  ownership check, so the form and Follow button are always shown to authenticated users.

The root cause is the **complete absence** of an owner guard — not a misconfigured one.

---

## 3. Proposed Fix / Root-Cause Design

### Single canonical ownership helper

Add `is_app_owner(user, app_id) -> bool` to [`catalog/selectors.py`](../../apps/catalog/selectors.py).

```python
def is_app_owner(user, app_id: UUID) -> bool:
    """Return True iff ``user`` is the owner of the app identified by ``app_id``."""
    if not getattr(user, "is_authenticated", False):
        return False
    return App.objects.filter(owner=user, pk=app_id).exists()
```

This is a single-column PK lookup (EXISTS, O(1)); no prefetch. It is the **one source of
truth** for "this user owns this app" used by both services and both inclusion tags.

### Service-layer guard (the trust boundary)

Add `SelfRatingError` to [`ratings/errors.py`](../../apps/ratings/errors.py) and
`SelfFollowError` to [`subscriptions/errors.py`](../../apps/subscriptions/errors.py) —
per the existing per-feature error pattern (`UnknownAppError` already lives separately in
each).

In `ratings.services.submit_rating`, after `_require_catalogued_app`:

```python
_require_non_owner(user, app_id)
```

where:

```python
def _require_non_owner(user, app_id: UUID) -> None:
    if catalog.is_app_owner(user, app_id):
        raise SelfRatingError("You can't review your own app.")
```

In `subscriptions.services.follow_app`, after `_require_catalogued_app`:

```python
_require_non_owner(user, app_id)
```

where:

```python
def _require_non_owner(user, app_id: UUID) -> None:
    if catalog.is_app_owner(user, app_id):
        raise SelfFollowError("You can't follow your own app.")
```

`remove_rating` and `unfollow_app` receive **no guard** — owners may clean up pre-existing
rows (see edge-case decision below).

### View-layer mapping (house PRG + messages pattern)

**Ratings view** (`ratings/views.submit`): add `except SelfRatingError as exc:` before the
existing `except RatingValidationError as exc:` clause; surface as `messages.error`. The
existing PRG redirect already follows.

**Subscriptions view** (`subscriptions/views.follow`): add `except SelfFollowError as exc:`
*before* the broad `except Exception:` clause (order matters: SelfFollowError must be
caught specifically so it is not logged as a generic failure). Surface as `messages.error`.

### Template-layer hide (UX cooperation layer)

**`ratings_tags.py`**: import `catalog.selectors`; inside `app_reviews`, compute
`is_owner = catalog.is_app_owner(user, app.id)` (within the existing `try` block so a
failure degrades gracefully); include `is_owner` in both the normal and degraded context
dicts (default `False` in the degraded path).

**`_reviews_slot.html`**: gate the submit/update form on `{% if not is_owner %}`. For an
owner, show a notice instead:

```
<p style="…">You can't review your own app.</p>
```

If the owner has a pre-existing rating (`own_rating` is truthy), still render the
"Remove your rating" form below the notice (cleanup allowed).

**`subscriptions_tags.py`**: same pattern — compute `is_owner = catalog.is_app_owner(user,
app.id)` inside the try block; include in both context dicts.

**`_follow_slot.html`**: for an authenticated owner:
- If `is_following` (pre-existing follow): show the Unfollow button (cleanup allowed).
- Otherwise: render nothing (no button, no sign-in link — the slot is simply empty for
  the owner).

### Edge-case decision: pre-existing owner rating / follow

**Decision:** Allow `remove_rating` and `unfollow_app` to proceed for owners. Pre-existing
rows created before this patch are **not retroactively deleted** — the owner may clean them
up via the Remove/Unfollow controls, which remain visible in the slot. This is the
minimally-invasive choice (no data migration, no retroactive action). Record in
`DECISIONS.md`.

### No-Schema Assertion

This patch contains **no schema changes, no new public API endpoints, and no global ADR
updates.** All changes are: a new catalog selector function, two new exception classes, two
new service-layer guard calls, two view except-clauses, two inclusion-tag additions, and
two template adjustments. `makemigrations --check` must confirm no drift at build time.

---

## 4. Task List

**T-01 — Red-first regression tests** *(S — tests only; code unchanged)*

Write tests that **fail** on the unpatched codebase:

- `tests/catalog/test_selectors.py` (or `test_is_app_owner.py`):
  - `test_is_app_owner_returns_true_for_owner` — assert `True` for the app owner.
  - `test_is_app_owner_returns_false_for_non_owner` — assert `False` for another user.
  - `test_is_app_owner_returns_false_for_anonymous` — assert `False` for `AnonymousUser`.
- `tests/ratings/test_services.py`:
  - `test_submit_rating_raises_self_rating_error_for_owner` — assert `SelfRatingError`
    when the submitting user is the app's owner (succeeds once service guard is added).
- `tests/subscriptions/test_services.py`:
  - `test_follow_app_raises_self_follow_error_for_owner` — assert `SelfFollowError`
    when the following user is the app's owner.
- `tests/ratings/test_views.py`:
  - `test_submit_view_blocks_owner_with_message` — POST as owner → 302 + error message +
    no `Rating` row created.
- `tests/subscriptions/test_views.py`:
  - `test_follow_view_blocks_owner_with_message` — POST as owner → 302 + error message +
    no `Subscription` row created.
- `tests/ratings/test_tags.py` (or inclusion-tag test):
  - `test_reviews_slot_shows_notice_for_owner` — assert slot contains "You can't review
    your own app." for an owner and no `<form>` for rating submission.
- `tests/subscriptions/test_tags.py`:
  - `test_follow_slot_hides_button_for_owner` — assert no Follow `<button>` for owner
    (and no `<form>` pointing to `subscriptions:follow`).

**DoD:** All new tests exist and fail with `AttributeError`, `AssertionError`, or
`ImportError` on the unpatched tree (demonstrating they are red). Existing suite unchanged.

**Files touched:** `apps/catalog/tests/` · `apps/ratings/tests/` · `apps/subscriptions/tests/`

---

**T-02 — Add `is_app_owner` catalog selector** *(S)*

Add `is_app_owner(user, app_id: UUID) -> bool` to
[`apps/catalog/selectors.py`](../../apps/catalog/selectors.py) in the "Owner reads"
section (after `list_owned_apps`). Guard against anonymous/unauthenticated users.

**DoD:** `test_is_app_owner_*` tests from T-01 pass; no other test regresses.

**Files touched:** `apps/catalog/selectors.py`

---

**T-03 — Ratings service + view guard** *(S)*

1. Add `SelfRatingError` to [`apps/ratings/errors.py`](../../apps/ratings/errors.py).
2. In [`apps/ratings/services.py`](../../apps/ratings/services.py):
   - Import `SelfRatingError` from `apps.ratings.errors`.
   - Add `_require_non_owner(user, app_id)` private function using `catalog.is_app_owner`.
   - Call `_require_non_owner(user, app_id)` in `submit_rating` after
     `_require_catalogued_app(app_id)`.
3. In [`apps/ratings/views.py`](../../apps/ratings/views.py):
   - Import `SelfRatingError`.
   - Add `except SelfRatingError as exc: messages.error(request, str(exc))` before the
     existing `except RatingValidationError` clause in `submit`.

**DoD:** `test_submit_rating_raises_self_rating_error_for_owner` + `test_submit_view_blocks_owner_with_message` pass; `remove_rating` tests unchanged.

**Files touched:** `apps/ratings/errors.py` · `apps/ratings/services.py` · `apps/ratings/views.py`

---

**T-04 — Subscriptions service + view guard** *(S)*

1. Add `SelfFollowError` to [`apps/subscriptions/errors.py`](../../apps/subscriptions/errors.py).
2. In [`apps/subscriptions/services.py`](../../apps/subscriptions/services.py):
   - Import `SelfFollowError` from `apps.subscriptions.errors`.
   - Add `_require_non_owner(user, app_id)` private function using `catalog.is_app_owner`.
   - Call `_require_non_owner(user, app_id)` in `follow_app` after
     `_require_catalogued_app(app_id)`.
3. In [`apps/subscriptions/views.py`](../../apps/subscriptions/views.py):
   - Import `SelfFollowError`.
   - Add `except SelfFollowError as exc: messages.error(request, "You can't follow your own app.")` before the broad `except Exception:` clause in `follow`.

**DoD:** `test_follow_app_raises_self_follow_error_for_owner` + `test_follow_view_blocks_owner_with_message` pass; `unfollow_app` tests unchanged.

**Files touched:** `apps/subscriptions/errors.py` · `apps/subscriptions/services.py` · `apps/subscriptions/views.py`

---

**T-05 — Ratings slot UX** *(S)*

1. In [`apps/ratings/templatetags/ratings_tags.py`](../../apps/ratings/templatetags/ratings_tags.py):
   - Add `from apps.catalog import selectors as catalog`.
   - In `app_reviews`: compute `user = getattr(request, "user", None)` then
     `is_owner = catalog.is_app_owner(user, app.id)` inside the try block.
   - Include `"is_owner": is_owner` in the normal context dict.
   - Include `"is_owner": False` in the degraded context dict.
2. In [`apps/ratings/templates/ratings/_reviews_slot.html`](../../apps/ratings/templates/ratings/_reviews_slot.html):
   - In the authenticated branch (`{% if request.user.is_authenticated %}`), gate the
     rating `<form>` on `{% if not is_owner %}`. In the owner case, show:
     `<p style="color: var(--color-muted); font-size: var(--font-size-sm); margin: 0;">You can't review your own app.</p>`
   - If the owner has a pre-existing rating (`{% if own_rating %}`), still render the
     Remove form below the notice.

**DoD:** `test_reviews_slot_shows_notice_for_owner` passes; all existing reviews-slot tests pass.

**Files touched:** `apps/ratings/templatetags/ratings_tags.py` · `apps/ratings/templates/ratings/_reviews_slot.html`

---

**T-06 — Follow slot UX** *(S)*

1. In [`apps/subscriptions/templatetags/subscriptions_tags.py`](../../apps/subscriptions/templatetags/subscriptions_tags.py):
   - Add `from apps.catalog import selectors as catalog`.
   - In `app_follow`: compute `is_owner = catalog.is_app_owner(user, app.id)` inside the
     try block (after `following = selectors.is_following(...)`).
   - Include `"is_owner": is_owner` in the normal context dict.
   - Include `"is_owner": False` in the degraded context dict.
2. In [`apps/subscriptions/templates/subscriptions/_follow_slot.html`](../../apps/subscriptions/templates/subscriptions/_follow_slot.html):
   - In the authenticated branch (`{% elif request.user.is_authenticated %}`), gate on
     `{% if is_owner %}`:
     - If owner AND `is_following` → show the Unfollow form only (cleanup path).
     - If owner AND NOT `is_following` → render nothing (empty slot).
   - Else (non-owner) → existing Follow/Unfollow logic unchanged.

**DoD:** `test_follow_slot_hides_button_for_owner` passes; all existing follow-slot tests pass.

**Files touched:** `apps/subscriptions/templatetags/subscriptions_tags.py` · `apps/subscriptions/templates/subscriptions/_follow_slot.html`

---

**T-07 — Verify + close-out artifacts** *(S)*

1. Run full test suite → must be green (+≥8 new tests passing, zero failures).
2. `ruff check` → clean.
3. `manage.py check` → clean.
4. `makemigrations --check` → **no drift** (confirms No-Schema Assertion).
5. Rehearse rollback (DU-REL-1): stash the patch, run `makemigrations --check` + targeted
   tests on the reverted tree, restore intact.
6. Write [`DECISIONS.md`](DECISIONS.md): record the pre-existing owner rating/follow edge
   case decision.
7. Write [`TEST_PLAN.md`](TEST_PLAN.md) and [`RELEASE_NOTES.md`](RELEASE_NOTES.md).

**DoD:** Suite green, ruff clean, check clean, no migration drift, rollback verified,
three artifact files written.

**Files touched:** `patches/patch-block-self-interaction/DECISIONS.md` ·
`patches/patch-block-self-interaction/TEST_PLAN.md` ·
`patches/patch-block-self-interaction/RELEASE_NOTES.md`

---

## 5. No-Schema Assertion

This patch contains **no schema changes, no new public API endpoints, and no global ADR
updates.** To be confirmed at build via `makemigrations --check` (no drift).
