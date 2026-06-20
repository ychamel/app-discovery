# TASKS — ratings-reviews

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-11 → approved) and the approved [DESIGN.md](DESIGN.md) (DN-12 → approved; global
[D-8](../../DECISIONS.md) APPROVED). Produces an ordered, independently-verifiable task list;
full per-AC verification is written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a
> contract or decision the design does not already make. The only schema touch outside
> `apps/ratings/` is one **additive, reversible** index on `signals.Impression` (DESIGN §4.3)
> and one **additive** `signals.selectors` read function (DESIGN §5d); the only template touch
> is the sanctioned one-line AP-1 slot fill (DESIGN §5g). The gate semantic is global
> [D-8](../../DECISIONS.md), already APPROVED.

---

## Ordering rationale (sequencing rules → this order)

1. **Adopt before you read (the one hard cross-app ordering constraint).** The additive index
   on `signals.Impression` and the new factual `signals.selectors.has_impression` land **first**
   (T-01): the gate (T-03) reads through that selector, and D-7 forbids reading `signals_*`
   directly past the selector surface. Nothing that consults the gate may precede it.
2. **Schema/data → core logic → interfaces → UI → telemetry → docs.** Spine: the signals read
   surface + its index (T-01) → the feature's own `Rating` store (T-02) → the integrity core,
   the gate (T-03) → the single write path (T-04) → the single display read path (T-05) → the
   thin HTTP views + the activation include (T-06) → the AP-1 slot fill that surfaces it all
   (T-07) → read-only admin + docs/finalize (T-08).
3. **Risk first.** The genuinely uncertain pieces — the **signals coupling** (the new
   `has_impression` selector + its index) and the **gate determination + fail-closed policy**
   (DESIGN §14 self-critique attacks both) — are concentrated in **T-01 + T-03** and verified
   there with a fake `has_impression` seam, before any write/UI work. The **slot edit** to the
   closed-out `app-pages` template (the third self-critique target) is isolated to **T-07**, a
   content-only one-line change with a one-line rollback.
4. **Each task leaves the system working and releasable.** T-01/T-02 are inert additions (an
   additive index; a new model + migration, no routes). T-03/T-04/T-05 add unreached
   code paths. The feature only becomes reachable when T-06 adds the `config/urls.py` include
   **and** T-07 fills the slot — the two-line activation/rollback of DESIGN §12.

**File-collision note (no two tasks edit the same file in parallel — tasks are sequential):**
- `apps/core/observability.py` is touched by **T-03** (`RATING_GATE_UNVERIFIED`), **T-04**
  (`RATING_SUBMITTED`/`_UPDATED`/`_REMOVED`/`_REJECTED`) and **T-07** (`RATING_DISPLAY_DEGRADED`);
  they run in order, never concurrently.
- `apps/core/config.py` is touched by **T-04** (`rating_scale_max`, `review_text_max_length`)
  and **T-05** (`reviews_display_limit`) — sequential.
- `config/settings*.py` (`INSTALLED_APPS`) is touched once (**T-02**); `config/urls.py` once
  (**T-06**); `apps/pages/templates/pages/app_page.html` once (**T-07**); `apps/signals/*` once
  (**T-01**).

---

## T-01 — `signals` read surface for the gate: the `has_impression` selector + its additive index

- **Description.** Add the new **factual** read function `has_impression(user_id, app_id, *,
  surfaces, as_of=None) -> bool` to `apps/signals/selectors.py` exactly per the DESIGN §5d
  contract — a pure `EXISTS` over `Impression` (`user_id`, `app_id`, `surface__in=surfaces`, and
  `occurred_at__lte=as_of` when given). **No scoring, no judgement** (D-7 raw-only); the curation
  *judgement* stays in `ratings.gate` (T-03), not here — signals stays neutral. This is an
  **additive** extension of the D-7 read surface (DESIGN §5d), **not** a new global ADR. Then add
  the **additive, reversible** index backing the new per-user-per-app existence query (DESIGN §4.3):
  `Index(fields=["user", "app_id"], name="signals_imp_user_app_idx")` on `signals.Impression`, with
  its migration `signals/0003_impression_user_app_idx`. No data migration, no backfill.
- **Dependencies.** none (this is the foundational adopt-before-read step).
- **Definition of done.**
  - `signals.selectors.has_impression` exists and is unit-tested: returns `True` only when a
    matching impression exists; the **`surface` filter** excludes non-listed surfaces (a `DIGEST`
    impression is not matched when `surfaces={APP_PAGE}` and vice-versa); the **`as_of` boundary**
    is `<=` (an impression exactly at `as_of` counts; one strictly after does not); a different
    user or app yields `False`.
  - `python manage.py makemigrations signals` produces exactly one migration adding
    `signals_imp_user_app_idx` (an `AddIndex` only — no column/data change); `makemigrations
    --check` reports no further drift after it is committed.
  - The migration is **reversible**: `migrate signals 0003` → `migrate signals 0002` → `migrate
    signals 0003` all succeed with no error (rehearsed; DESIGN §4.3/§12).
  - Existing `apps/signals` suite green; `ruff` clean; full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/selectors.py`, `apps/signals/migrations/0003_*.py`,
  `apps/signals/tests/` (a new `has_impression` test).

## T-02 — Scaffold `apps/ratings` + the `Rating` store + `EligibilityBasis` + migration

- **Description.** Create the new Django app per DESIGN §2/§4.1: `__init__.py`, `apps.py`
  (`AppConfig`, `name="apps.ratings"`), `tests/`. Register `"apps.ratings"` in `INSTALLED_APPS`.
  Implement `apps/ratings/models.py` exactly to the DESIGN §4.1 contract:
  - `EligibilityBasis(TextChoices)` — `CURATED_DIGEST_IMPRESSION` / `NO_CURATED_IMPRESSION` /
    `CURATION_UNVERIFIED` (the recorded reason; the §8.4 metric tag).
  - `Rating` — `id` (UUID pk), `user` FK **`SET_NULL, null=True`** (anonymize-on-deletion, SC-10
    posture — DESIGN §4.2), `app_id` (UUID soft D-6 ref), `score` (`PositiveSmallIntegerField`),
    `review_text` (`TextField, blank, default=""`), and the recorded-gate columns
    **`weight_eligible` (`BooleanField`, never null)**, `eligibility_basis` (`CharField`,
    `choices`), `eligibility_determined_at` (`DateTimeField`), `created_at`/`updated_at`.
  - `Meta`: `db_table="ratings_rating"`; the **unique constraint** `ratings_one_active_per_user_app`
    on `(user, app_id)` (AC8); the display index `ratings_app_created_idx` on `(app_id, created_at)`.
  - **Structural no-score (AC6):** the table has **no** score/weight/rank/average/quality column —
    `weight_eligible` is an *eligibility boolean*, not a quality value. This is a structural fact to
    be asserted by a test, not a convention.
  - **No business logic** in the model — all invariants (range, the `weight_eligible ==
    (basis == CURATED_DIGEST_IMPRESSION)` coupling, the determination) are enforced by the write
    path (T-04). The model just declares the shape.
  - Generate `ratings/0001_initial`.
- **Dependencies.** none (independent of T-01; both precede T-03).
- **Definition of done.**
  - `apps.ratings` imports and appears in `INSTALLED_APPS`; `python manage.py check` clean.
  - `makemigrations ratings` produces `0001_initial` creating `ratings_rating` with the unique
    constraint + index; `makemigrations --check` clean after commit.
  - A structural test asserts the model has the gate columns (`weight_eligible`,
    `eligibility_basis`, `eligibility_determined_at`) and has **no** score/weight/rank/average
    column (AC6); the unique constraint on `(user, app_id)` is present (AC8); `user` FK is
    `SET_NULL` (DESIGN §4.2).
  - The migration is reversible: `migrate ratings 0001` → `migrate ratings zero` → `migrate
    ratings 0001` all succeed (DESIGN §12).
  - `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/ratings/` (new package: `__init__.py`, `apps.py`, `models.py`,
  `migrations/0001_initial.py`, `tests/__init__.py`, `tests/test_models.py`),
  `config/settings*.py` (`INSTALLED_APPS`).

## T-03 — The gate: `gate.py` — the eligibility determination + the `CURATED_SURFACES` definition (D-8)

- **Description.** Implement `apps/ratings/gate.py` exactly to the DESIGN §5b contract — the
  **integrity core and the second riskiest piece** (the freeze/derive critique, DESIGN §14):
  - `CURATED_SURFACES: frozenset[str] = frozenset({Surface.DIGEST})` — **the one place the §4.1 /
    D-8 gate definition lives** (`APP_PAGE`/open views excluded). Changing what counts as curation
    is one line here (DESIGN §10).
  - `EligibilityDetermination` (frozen dataclass: `weight_eligible`, `basis`, `determined_at`).
  - `determine_eligibility(user, app_id, *, as_of) -> EligibilityDetermination`: weight-eligible
    **iff** `signals.selectors.has_impression(user.id, app_id, surfaces=CURATED_SURFACES,
    as_of=as_of)` is `True` → `(True, CURATED_DIGEST_IMPRESSION)`; else `(False,
    NO_CURATED_IMPRESSION)`. The signals read is wrapped: **on any exception fail CLOSED** —
    `(False, CURATION_UNVERIFIED)`, increment `RATING_GATE_UNVERIFIED`, log with request context;
    **never** silently grant weight, **never** block the rating (DESIGN §8 row 2 / §5b).
  - Add the `RATING_GATE_UNVERIFIED` constant to `apps/core/observability.py` (DESIGN §8.4 — the
    one actionable alert: a spike means the signals read is degraded).
  - The judgement ("DIGEST = curation") lives **here**, never in `signals` (DESIGN §5d/§11 alt 3).
- **Dependencies.** T-01 (calls `signals.selectors.has_impression`), T-02 (uses `EligibilityBasis`).
- **Definition of done.** Unit tests against a **fake/patched `has_impression` seam** cover:
  - has DIGEST impression at/before `as_of` → `weight_eligible=True`, basis
    `CURATED_DIGEST_IMPRESSION`.
  - no qualifying impression → `weight_eligible=False`, basis `NO_CURATED_IMPRESSION` (AC7 path).
  - `has_impression` raises → **fail-closed**: `weight_eligible=False`, basis
    `CURATION_UNVERIFIED`, `RATING_GATE_UNVERIFIED` incremented, **no exception propagates** (AC5
    still satisfiable — a determination is always returned).
  - `CURATED_SURFACES == frozenset({Surface.DIGEST})` (a test pins the D-8 definition; `APP_PAGE`
    is not in it).
  - `ruff` clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/ratings/gate.py`, `apps/core/observability.py` (one constant),
  `apps/ratings/tests/test_gate.py`.

## T-04 — The single write path: `services.py` (`submit_rating` / `remove_rating`) + `errors.py` + config

- **Description.** Implement `apps/ratings/services.py` (+ `apps/ratings/errors.py`) exactly to the
  DESIGN §5a contract — **the only place `Rating` rows are created/updated/deleted**:
  - `submit_rating(user, app_id, *, score, review_text="") -> Rating`:
    1. `catalog.selectors.get_catalogued_app(app_id)`; `None` → raise `UnknownAppError` (AC9). A
       catalog read that **raises** (DB down) propagates **loud** (DESIGN §8 row 1 — a rating has
       no subject without it).
    2. `_validate(score, review_text)` at the boundary; on failure raise `RatingValidationError`
       and store **nothing** (AC2). Range `1 ≤ score ≤ config.rating_scale_max()`; `len(review_text)
       ≤ config.review_text_max_length()`.
    3. `determination = gate.determine_eligibility(user, app_id, as_of=now)` (AC5/AC7).
    4. **atomic** `update_or_create` on `(user, app_id)` writing `score`/`review_text` and the gate
       columns together, so `weight_eligible == (basis == CURATED_DIGEST_IMPRESSION)` can never
       drift (DESIGN §4.1 invariant). Create vs update distinguishes `RATING_SUBMITTED` vs
       `RATING_UPDATED` (AC1/AC8); both tagged `{weight_eligible, basis}` — **this is the §5 / §8.4
       gate-split metric** (expected ~all not-eligible at MVP, R3).
  - `remove_rating(user, app_id) -> bool`: delete the caller's row (hard-delete, DESIGN §4.2);
    increment `RATING_REMOVED`; return whether one existed (AC8).
  - `errors.py`: `UnknownAppError`, `RatingValidationError`. Both raised **before** any write; the
    write is atomic (no partial state).
  - Add `config.rating_scale_max()` (default 5) and `config.review_text_max_length()` (default 4000)
    to `apps/core/config.py` (DESIGN §10; same `_positive_int` precedence pattern as the existing
    tunables); add `validate_all()` entries. Add `RATING_SUBMITTED`/`_UPDATED`/`_REMOVED`/`_REJECTED`
    constants to `apps/core/observability.py`.
- **Dependencies.** T-02 (`Rating` store), T-03 (`gate.determine_eligibility`).
- **Definition of done.** Tests against the **real catalog + gate** (catalog fixtures; gate over a
  faked/real `has_impression`):
  - **AC1** signed-in submit on an accepted app → one row stored keyed `(user, app_id)` with
    `score`/`review_text`; `RATING_SUBMITTED` emitted.
  - **AC2** out-of-range score / over-length text → `RatingValidationError`, **DB row count
    unchanged**, `RATING_REJECTED` emitted.
  - **AC9** unknown / non-accepted `app_id` → `UnknownAppError`, nothing stored.
  - **AC5** every successful `submit_rating` writes a **non-null** `weight_eligible` + `basis` +
    `eligibility_determined_at`; the `CURATION_UNVERIFIED` path still stores (a determination is
    present 100% of the time).
  - **AC7** a non-curated rater's submit stores `weight_eligible=False`,
    `basis=NO_CURATED_IMPRESSION` (still stored, never dropped).
  - **AC8** a second `submit_rating` for the same `(user, app_id)` **updates the same row** (no
    duplicate; `RATING_UPDATED`) and **re-determines** eligibility as-of the edit instant;
    `remove_rating` deletes it and returns the existed-flag.
  - the write is atomic (a forced mid-write error leaves no partial row).
  - `ruff` clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/ratings/services.py` (new), `apps/ratings/errors.py` (new),
  `apps/core/config.py` (two tunables + `validate_all`), `apps/core/observability.py` (four
  constants), `apps/ratings/tests/test_services.py`.

## T-05 — The single display read path: `selectors.py` (`reviews_for_app` / `user_rating`) + DTOs

- **Description.** Implement `apps/ratings/selectors.py` exactly to the DESIGN §5c contract — the
  one display read surface:
  - `ReviewRow` (frozen dataclass: `score`, `review_text`, `author_display`, `created_at`) — **no
    eligibility field** (the gate flag is internal substrate, not public — DESIGN §5c).
  - `AppReviews` (frozen dataclass: `app_id`, `total_count`, `distribution: dict[int, int]`,
    `reviews: list[ReviewRow]`).
  - `reviews_for_app(app_id, *, limit) -> AppReviews` — **2 queries**: a grouped count per score
    value (the `distribution`) + the most-recent-first list capped at `limit`. The "summary" (AC4)
    is **count + raw distribution only — never an average / score** (AC6; a naive public average is
    deliberately absent — it is the gameable number the gate neutralizes, DESIGN §5c/§14). **All**
    ratings are returned regardless of `weight_eligible` (AC7 — openly participatory).
  - `user_rating(user, app_id) -> Rating | None` — the viewer's own row, to prefill the form.
  - Add `config.reviews_display_limit()` (default 20) to `apps/core/config.py` (DESIGN §10) +
    `validate_all` entry. The view/tag pass `limit=reviews_display_limit()` (T-07), keeping render
    bounded (DESIGN §9).
- **Dependencies.** T-02 (`Rating` store). (Independent of T-03/T-04 — reads only.)
- **Definition of done.** Tests over fixtures:
  - **AC4** an app with ≥1 rating → `total_count` and a `distribution` keyed by score value
    matching the fixtures + a list ordered most-recent-first; an app with 0 ratings →
    `total_count=0`, empty `distribution`, empty list (the empty-state data).
  - **AC6** no average / score / rank is computed anywhere in the selector; `distribution` is raw
    counts (a structural/grep assertion + value check).
  - **AC7** a not-weight-eligible rating **is included** in `reviews` and counted.
  - `reviews_for_app` honours `limit` (a fixture with > limit ratings returns exactly `limit`
    rows) and runs in a **bounded** query count (no N+1).
  - `user_rating` returns the caller's row or `None`.
  - `ruff` clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/ratings/selectors.py` (new), `apps/core/config.py` (one tunable +
  `validate_all`), `apps/ratings/tests/test_selectors.py`.

## T-06 — Thin HTTP views (`submit` / `remove`) + `urls.py` + the activation include

- **Description.** Implement `apps/ratings/views.py` + `apps/ratings/urls.py` exactly to the DESIGN
  §5e contract, then add `path("ratings/", include("apps.ratings.urls"))` to `config/urls.py` — the
  activation switch (DESIGN §12; its own prefix, no collision with the pages `apps/` include). The
  views hold **no business logic and no ORM access** (mirrors the pages/catalog house pattern:
  parse → call service → redirect):
  - `ratings:submit` → `apps/<uuid:app_id>/rating` (POST, `login_required`): parse `score` +
    `review_text` → `services.submit_rating` → **PRG redirect** to `pages:app-page`.
    `RatingValidationError` → a Django message + redirect back (AC2); `UnknownAppError` → **404**
    (AC9). Anonymous POST → `login_required` redirect to `/auth/signin?next=…` (AC3).
  - `ratings:remove` → `apps/<uuid:app_id>/rating/remove` (POST, `login_required`):
    `services.remove_rating` → redirect to `pages:app-page` (AC8).
  - **No IDOR (DESIGN §7):** the URL carries **no rating id**; the row is addressed by
    `request.user` + `app_id`, so a user can only ever touch their own rating. CSRF on both POSTs
    (`{% csrf_token %}` + Django middleware).
- **Dependencies.** T-04 (views call `services`). (Selectors/tag for the page itself land in T-05/
  T-07; the views only write.)
- **Definition of done.** Integration tests (Django test client, project URLconf):
  - **AC1** signed-in POST `apps/<accepted-id>/rating` with valid score → row stored, redirect to
    the app page (PRG).
  - **AC2** invalid score / over-length text → redirect back with a message, **nothing stored**;
    non-existent app → **404**.
  - **AC3** anonymous POST → redirect to `/auth/signin?next=…`; **no write**.
  - **AC8** re-POST updates the same row (no duplicate); POST `…/rating/remove` deletes it.
  - **AC9** POST for a `pending`/`rejected`/`withdrawn`/unknown id → 404, nothing stored; non-UUID
    path → 404 at routing.
  - `submit`/`remove` via GET (wrong method) → 405; POST without CSRF → 403.
  - `manage.py check` clean; `ruff` clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/ratings/views.py` (new), `apps/ratings/urls.py` (new),
  `config/urls.py` (the include), `apps/ratings/tests/test_views.py`.

## T-07 — The AP-1 slot fill: the `app_reviews` inclusion tag + partial + the one `app_page.html` edit

- **Description.** Implement the slot integration exactly to the DESIGN §5f/§5g contract — the
  third self-critique target (the closed-out-template edit), isolated here and **content-only**:
  - `apps/ratings/templatetags/ratings_tags.py` — `@register.inclusion_tag("ratings/_reviews_slot.html",
    takes_context=True) def app_reviews(context, app)`: calls `selectors.reviews_for_app(app.id,
    limit=config.reviews_display_limit())` + `selectors.user_rating(request.user, app.id)` for a
    signed-in viewer, returns `{request, app, reviews, own_rating, scale_max}`. **Fail-soft (DESIGN
    §8 row 4):** any selector error → a degraded slot + `RATING_DISPLAY_DEGRADED` metric, **never
    raises into the page render** (preserves `app-pages` AC5 / AP-1 — the page renders even if
    reviews degrade).
  - `apps/ratings/templates/ratings/_reviews_slot.html` — renders, inside the **unchanged**
    `<section aria-label="Reviews">`: the summary (count + score distribution) + the reviews list
    **or** the AC4 empty state ("No reviews yet — be the first") for everyone; for an
    **authenticated** viewer the rating form (prefilled with `own_rating` if present, score
    1–`scale_max` + optional review) + a Remove button (POST `ratings:remove`) when one exists; for
    an **anonymous** viewer a "Sign in to rate" link to `accounts:signin?next=<this page>` (AC3).
    `review_text` rendered through Django auto-escaping (no `|safe`) — XSS-safe (DESIGN §7).
  - The **one sanctioned edit** to `apps/pages/templates/pages/app_page.html` (DESIGN §5g): replace
    slot 6's `<p>Reviews coming soon.</p>` with `{% app_reviews app %}` and add `{% load
    ratings_tags %}` near the top. The `<section>`, its `aria-label`, heading, and position are
    **unchanged** — page uniformity (app-pages AC3/AP-1) holds. Rollback = restore the one `<p>`.
  - Add the `RATING_DISPLAY_DEGRADED` constant to `apps/core/observability.py` (DESIGN §8.4).
- **Dependencies.** T-05 (`reviews_for_app`/`user_rating`), T-06 (the `ratings:submit`/`remove`
  route names the form/Remove button target).
- **Definition of done.** Render tests (the tag rendered in isolation + the `app_page` page via the
  test client, with `apps.ratings.urls` included):
  - **AC4** an app with ≥1 review renders the summary (count + distribution) + the list; an app with
    0 reviews renders the defined empty state — no broken layout, the `<section aria-label="Reviews">`
    still present and uniform.
  - **AC3** anonymous render → read-only reviews + a "Sign in to rate" link, **no form**; the page
    renders fully. Signed-in render → the form (prefilled when `own_rating` exists) + Remove button.
  - **AC7** a not-weight-eligible rating appears in the rendered list (no eligibility badge shown).
  - **fail-soft:** with `reviews_for_app` patched to raise, the slot renders the degraded message,
    `RATING_DISPLAY_DEGRADED` is incremented, and **the rest of the page still renders** (no 500).
  - the slot edit changed **content only**: a structural test confirms the page still renders the
    six slots in order with the `Reviews` section's `aria-label`/heading intact (app-pages
    uniformity preserved).
  - `ruff`/template lint clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/ratings/templatetags/__init__.py` + `ratings_tags.py` (new),
  `apps/ratings/templates/ratings/_reviews_slot.html` (new),
  `apps/pages/templates/pages/app_page.html` (the one slot-6 + `{% load %}` edit),
  `apps/core/observability.py` (one constant), `apps/ratings/tests/test_templatetags.py`.

## T-08 — Read-only admin, README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: a thin read surface + docs + index — no behavioural change to the
  feature paths (DESIGN §4 admin / §11/§12).
  - `apps/ratings/admin.py` — a **read-only** `Rating` admin (list `app_id`, `user`,
    `weight_eligible`, `eligibility_basis`, `created_at`; no add/edit — writes go only through
    `services`, DESIGN §4 modules / §5a invariant). Mirrors the signals read-only admin pattern.
  - `apps/ratings/README.md` — the app's single responsibility (capture-only, no scoring), the two
    routes, the gate (`CURATED_SURFACES` = D-8), "owns one mutable table `ratings_rating`", and the
    two-line rollback (restore the `app_page.html` slot + remove the `config/urls` include; if
    needed `migrate ratings zero` + `migrate signals 0002`).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: `ratings.services.*`
    (the write path), `ratings.selectors.*` (the display read), `ratings.gate.*`
    (`determine_eligibility` + `CURATED_SURFACES`), the **new** `signals.selectors.has_impression`
    (additive D-7 read surface), the `ratings:*` route names, the `{% app_reviews %}` tag, the new
    config tunables, and the new observability constants.
  - [features/ratings-reviews/DECISIONS.md](DECISIONS.md) — mark **RR-4** (own store + freeze-and-
    re-derive) and **RR-5** (slot fill via inclusion tag) as built; note global **[D-8](../../DECISIONS.md)**
    APPROVED and implemented (`CURATED_SURFACES`). Note the named-not-built growth levers
    (a `recompute_eligibility` management path; a stronger review-text purge-on-deletion) per DESIGN
    §4.2/§5b/§14.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit
    artifact, produced alongside the build, not in this task.
- **Dependencies.** T-01…T-07.
- **Definition of done.** `apps/ratings/admin.py` registers a read-only `Rating` admin (a test or
  `check` confirms no add/change perms); `README.md` matches the shipped routes/gate/rollback;
  `CODEMAP.md` lists every new shared surface above; `DECISIONS.md` marks RR-4/RR-5 built and D-8
  implemented; `makemigrations --check` clean; **full suite green, `ruff` clean, no drift** (the
  close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/ratings/admin.py` (new), `apps/ratings/README.md` (new),
  [CODEMAP.md](../../CODEMAP.md), `features/ratings-reviews/DECISIONS.md`,
  `apps/ratings/tests/test_admin.py` (optional read-only assertion).

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §5d new factual `signals.selectors.has_impression` (additive D-7 read) | **T-01** |
| §4.3 additive reversible index `signals_imp_user_app_idx` + migration order | **T-01** |
| §4.1 `Rating` store + `EligibilityBasis` + unique constraint + display index; structural no-score (AC6) | **T-02** |
| §4.2 lifecycle (create/edit/remove hard-delete; account-deletion SET_NULL) | **T-02** (shape) + **T-04** (create/edit/remove) |
| §5b `gate.CURATED_SURFACES` (D-8) + `determine_eligibility` + fail-closed | **T-03** |
| §5a single write path `submit_rating`/`remove_rating` + `errors` + atomic/validated | **T-04** |
| §5c single display read `reviews_for_app`/`user_rating` + DTOs; count+distribution, no average (AC6) | **T-05** |
| §5e thin views + `urls` + `config/urls` activation include; no-IDOR | **T-06** |
| §5f inclusion tag + partial (fail-soft); §5g the one `app_page.html` slot edit | **T-07** |
| §7 security (auth-required, own-data-only/no IDOR, boundary validation, XSS, CSRF) | **T-04** (validation) + **T-06** (auth/CSRF/no rating-id) + **T-07** (autoescape) |
| §8 failure modes (loud catalog read · fail-closed gate · atomic write · fail-soft display) | **T-04** + **T-03** + **T-07** |
| §8.4 observability constants (`RATING_GATE_UNVERIFIED`/`SUBMITTED`/`UPDATED`/`REMOVED`/`REJECTED`/`DISPLAY_DEGRADED`) | **T-03** + **T-04** + **T-07** |
| §10 config tunables (scale max, review length, display limit, the gate definition) | **T-04** + **T-05** (+ gate def in **T-03**) |
| §4 read-only admin surface | **T-08** |
| §12 rollout/rollback (additive, no flag, design-for-deletion) + §11 CODEMAP/docs + D-8/RR-4/RR-5 | **T-08** |
| §13 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-04+T-05+T-07; AC2 → T-04+T-06; AC3 → T-06+T-07; AC4 → T-05+T-07; AC5 →
T-02+T-03+T-04; AC6 → T-02+T-05; AC7 → T-03+T-04+T-05/T-07; AC8 → T-02+T-04+T-06; AC9 → T-04+T-06.
All nine acceptance criteria are covered; no `L` tasks; every task has a checkable definition of done.
