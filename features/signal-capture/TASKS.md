# TASKS — signal-capture

*Stage 3 artifact (Planner / Tech Lead). Status: **complete — ready for Stage 4 (Senior
Engineer)**. Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED DN-5),
[DESIGN.md](DESIGN.md) (APPROVED DN-6, 2026-06-18), feature [DECISIONS.md](DECISIONS.md)
(SC-1…SC-10), feature [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) (OQ-1/2/3 RESOLVED,
OQ-4 → backlog), global [DECISIONS.md](../../DECISIONS.md) (D-1 niche, D-2 no-hard-targets,
D-3 identity, D-4 stack, D-5 taxonomy contract, D-6 catalogued-app contract, **D-7 the
event-schema contract this feature implements**), [CODEMAP.md](../../CODEMAP.md) (the `apps/`
shared surface from `identity-accounts` + `interest-taxonomy` + `submission-intake`). Every
task references the exact DESIGN.md section(s) and the acceptance criteria it satisfies, per
the traceability rule (CLAUDE.md §6.3). Produced by
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

---

## How to read this list

- Tasks are in **execution order**. Each is sized for one focused session and leaves the
  system **working and releasable** — this feature is **additive with no live emitter**
  (the emitting surfaces are out of scope / unbuilt — [DESIGN §5c/§12](DESIGN.md)), so every
  task ships green with the only writer being the visit middleware + tests.
- **Sequencing** follows DESIGN and the planner spec: scaffold → the closed-vocabulary enums
  → schema → the single write path → the visit middleware → the single read path → admin →
  docs. **Risk is front-loaded:** the four sharpest edges from [DESIGN §13](DESIGN.md) land
  before anything depends on them — (1) the **single `EngagementEvent` table with a `kind`
  discriminator** + the **no-score/weight/rank-column** structural guarantee and the
  **`SET_NULL`-anonymize vs `CASCADE`-purge** deletion semantics (T-03, AC9/SC-10); (2) the
  **capture invariants** — app validity via D-6, the frozen capture-time tag snapshot,
  impression linkage, and **fail-loud + counted** (T-04/T-05, AC1/AC2/AC3/AC11/§5d); and
  (3) **returns *derived* at read, never stored, no backfill** (T-07, AC4/AC8/SC-9). They
  are tested in isolation before the middleware and the funnel build on them.
- **No `L` tasks remain** (planner exit criterion). The one unit too big for a session —
  the single write path (`capture.py`, seven recorders + their invariants) — is split along
  its natural seam: the **impression anchor + visit substrate** (T-04) vs the **engagement
  events** (T-05), mirroring how `submission-intake` split content-writes (T-05) from
  lifecycle-writes (T-06).
- **Files/areas touched** are declared so parallel agents do not collide. `capture.py` is
  written by **T-04 then T-05** and `apps/core/observability.py` is touched by **T-04** —
  run those in the listed order (do not parallelize them). `config/settings.py` is edited by
  **T-01** (`INSTALLED_APPS` + tunables) and **T-06** (`MIDDLEWARE`) — also ordered.
- **Reuse, don't re-derive.** This feature *adds one app* (`apps/signals/`) and **modifies
  only** `config/settings.py` (register app + middleware), `apps/core/config.py` (two return-
  window tunables), and `apps/core/observability.py` (this feature's metric constants) —
  exactly as `taxonomy`/`catalog` did ([DESIGN §1](DESIGN.md)). It reuses, **by name and
  without re-implementing**: `catalog.selectors.get_catalogued_app` (app validity + the
  capture-time tag snapshot — D-6); `taxonomy.selectors.resolve_tag` (display-only tag
  resolution — D-5); the `accounts` `Account` FK target and the `HasRole(ADMIN)`/
  `require_role(ADMIN)` fail-closed gate (no new auth path — only the read surface needs it,
  §5c/§10); `apps.core.observability.increment`; the `apps.core.config` typed-tunable pattern;
  and the request-context logging middleware (the new visit middleware sits beside it). None
  of these are rebuilt.
- **Standards apply to every task** (CLAUDE.md §5): optimize for the reader, one
  function/one job, fail-loud at the trust boundary, config over hardcoding, **single write
  path (`capture.py`) / single read path (`selectors.py`)**, and **shared code must be
  registered in [CODEMAP.md](../../CODEMAP.md) as part of definition-of-done** — a shared
  capture/selector added without a CODEMAP entry is an incomplete task.
- **The corpus is raw and append-only by construction.** No task may add a score, weight,
  rank, or normalized column to any table or read DTO (AC9/R5 — structural, enforced by a
  test in T-03), and no task may write a `signals_*` row outside `capture.py` (D-7).

---

## Dependency overview

```
T-01 scaffold (apps/signals + INSTALLED_APPS + return-window tunables)
 ├─ T-02 kinds.py: EventKind + Surface enums   ◄ risk: closed vocabulary
 └─ T-03 models + migration 0001 (Impression, ImpressionTag, EngagementEvent, PlatformVisit)   [needs T-02]
      │     ◄ risk: single-table kind discriminator · no-score guarantee · SET_NULL/CASCADE deletion
      ├─ T-04 capture A: record_impression (+ tag snapshot) + record_platform_visit + errors + metrics   ◄ risk: app validity, frozen snapshot, fail-loud+counted
      │    └─ T-05 capture B: record_click_through/subscribe/page_reengagement/share/off_platform_proxy   ◄ risk: impression linkage, is_proxy
      │         ├─ T-06 PlatformVisitMiddleware (+ MIDDLEWARE wiring)   [needs T-04]   ◄ §5d fail-soft-but-counted
      │         └─ T-07 selectors: app_funnel/funnel_for_apps/category_impressions   ◄ risk: derived returns, raw-only
      └─ T-08 read-only admin (inspection)   [needs T-03]
T-09 PRIVACY.md + README + .env.example + CODEMAP reconcile + finalize D-7 + rollout   [needs all]
```

---

## T-01 — `apps/signals/` scaffold + settings/config wiring
- **Description.** Create the new Django app exactly as laid out in [DESIGN §2](DESIGN.md):
  `apps/signals/` with `apps.py` (`AppConfig`), empty `models.py`, an empty `migrations/`
  package, and a `tests/` directory. Wire the infrastructure this feature needs
  ([DESIGN §1/§9/§12](DESIGN.md)):
  - register `apps.signals` in `INSTALLED_APPS` (the visit-middleware registration is
    **deferred to T-06**, once the middleware class exists — registering a not-yet-defined
    class would break startup);
  - add the two typed tunables to `apps/core/config.py` following the established pattern
    (a `DEFAULT_*` literal + a `_positive_int(...)` accessor + inclusion in
    `validate_all`): `return_window_short_days` (default **3**) and
    `return_window_long_days` (default **14**) — the single source of truth the read path
    reads, so A2's "exact tolerance" is a one-line config change and there is **no magic
    `3`/`14`** in logic (DESIGN §9; CLAUDE.md §5.2 "evaluation windows are config").
  **Modifies no existing component's behavior** — `core` gains two tunables only; `accounts`/
  `taxonomy`/`catalog` are reused as-is, not touched.
- **Dependencies.** none.
- **Definition of done.**
  - `python manage.py check` passes with the new app installed; `makemigrations signals`
    reports *no changes* (no models yet) — the app is wired but empty.
  - `return_window_short_days` / `return_window_long_days` are readable through
    `apps.core.config` with the documented defaults and **fail loud** at startup if mis-set
    (a test asserts a non-positive value raises `ImproperlyConfigured` via `validate_all`,
    matching the existing tunables).
  - No edits to `apps/accounts/`, `apps/taxonomy/`, or `apps/catalog/` (boundary check —
    DESIGN §1).
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/__init__.py`, `apps/signals/apps.py`,
  `apps/signals/models.py`, `apps/signals/migrations/__init__.py`,
  `apps/signals/tests/__init__.py`, `apps/core/config.py` (two tunables),
  `config/settings.py` (`INSTALLED_APPS`).

## T-02 — `kinds.py`: `EventKind` + `Surface` enums (risk-first, closed vocabulary) — AC1, AC6, AC7
- **Description.** Implement `apps/signals/kinds.py` exactly as specified in
  [DESIGN §3/§4](DESIGN.md) — the **closed, code-fixed** vocabularies (no free-text type, no
  editorial mutation), so an unknown event kind or surface is **unrepresentable**:
  - `EventKind(models.TextChoices)` with **exactly** the five values `CLICK_THROUGH`,
    `SUBSCRIBE`, `PAGE_REENGAGEMENT`, `SHARE`, `OFF_PLATFORM_PROXY` — the `EngagementEvent`
    discriminator (§4). Adding a future kind (e.g. `comment`) is **one enum value + one
    `record_*` wrapper**, no new table (DESIGN §6) — but it is a deliberate code change, not
    runtime data.
  - `Surface(models.TextChoices)` with `DIGEST` at MVP (SC-1), extensible by adding a value
    (`app_page`, `feed`) with **no migration to the others** (DESIGN §4).
- **Dependencies.** T-01.
- **Definition of done.**
  - `EventKind` has **exactly** those five members and `Surface` has **exactly** `DIGEST`; a
    test asserts each member set (so a new kind/surface cannot be slipped in unreviewed — it
    must be a deliberate edit that updates the test).
  - `kinds.py` holds **no business logic and no DB access** (pure declaration — one job;
    per-kind meaning is validated in `capture`, not here).
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/kinds.py`, `apps/signals/tests/test_kinds.py`.

## T-03 — Data model & initial migration (4 tables) — AC1, AC2, AC3, AC4, AC7, AC9, AC10 (whitelist), SC-9, SC-10
- **Description.** Implement the four append-only tables from [DESIGN §4](DESIGN.md) — the
  schema is the proposed/now-approved global **[D-7](../../DECISIONS.md)** spine, so model it
  exactly:
  - `Impression` (`signals_impression`) — UUID PK (**the impression identity** every
    conversion attributes to, AC1/AC3); `user` FK → `accounts.Account`,
    **`on_delete=SET_NULL`, null=True** (anonymize-on-deletion, SC-10); `app_id` UUID
    **indexed** (the accepted `catalog.App.id`, **soft ref — no DB FK**, D-6); `surface` enum
    (`Surface`); `occurred_at` timestamptz **indexed** (default now; an emitter may pass the
    true show time); `created_at` timestamptz. Index **`(app_id, occurred_at)`**.
  - `ImpressionTag` (`signals_impression_tag`) — UUID PK; `impression` FK → `Impression`
    **`CASCADE`**; `tag_id` UUID **indexed** (a `Tag.id` carried **at show time** — soft ref,
    D-5; **frozen**, AC2); **unique `(impression, tag_id)`**.
  - `EngagementEvent` (`signals_engagement_event`) — UUID PK; `kind` enum (`EventKind`); `user`
    FK → `accounts.Account` **`SET_NULL`, null=True** (SC-10); `app_id` UUID **indexed** (soft
    ref, D-6); `impression` FK → `Impression` **`SET_NULL`, null=True** (the originating
    impression where known — AC3/AC5); `is_proxy` bool **default `False`**; `occurred_at`
    timestamptz **indexed**; `created_at` timestamptz. Index **`(app_id, kind, occurred_at)`**.
    *(The per-kind required/optional rule for `impression` is enforced in `capture`, T-04/T-05 —
    the column is nullable so the optional kinds are representable; §13.)*
  - `PlatformVisit` (`signals_platform_visit`) — UUID PK; `user` FK → `accounts.Account`
    **`CASCADE`** (an unlinked daily tick is pure noise — SC-10/§4); `visit_date` date (UTC)
    **indexed**; `created_at` timestamptz; **unique `(user, visit_date)`** (idempotent — one
    row per user per day).
  Migration `0001_initial` creates **only the four tables (no content)** and is **reversible**
  (`migrate signals zero` drops all four — DESIGN §9/§12). The **raw-only guarantee is
  structural** (AC9/R5/§4): **no score, rank, normalized, or weight column exists on any
  table**; the **privacy whitelist is structural** (AC10/§10): **no IP, user-agent, device,
  geolocation, referrer, off-platform-id, or free-text column exists** — over-collection is
  unrepresentable.
- **Dependencies.** T-01, T-02 (`kind`/`surface` use `EventKind`/`Surface` for `choices`).
- **Definition of done.**
  - Migration applies cleanly on a fresh PostgreSQL DB; `migrate signals zero` drops all four
    tables (reversible — DESIGN §9/§12 rollback). No content rows created.
  - Tests: UUID PKs on all four; **unique `(impression, tag_id)`** and **unique
    `(user, visit_date)`** enforced; `EngagementEvent.is_proxy` defaults `False`; the indexes
    above exist.
  - **Deletion semantics (SC-10):** deleting an `Account` **`SET_NULL`s** its
    `Impression.user` and `EngagementEvent.user` (the rows **survive** as anonymized corpus,
    `user IS NULL`) and **`CASCADE`-deletes** its `PlatformVisit` rows (one test per edge).
  - **Structural guarantees (review note + tests):** no model has a `score`/`weight`/`rank`/
    `normalized` attribute (AC9); no model has an `ip`/`user_agent`/`device`/`geo`/`referrer`/
    free-text attribute (AC10 whitelist) — assert by field-list review note + a test that the
    attributes are absent.
  - `app_id`/`tag_id` are plain `UUIDField`s with **no DB FK** to `catalog`/`taxonomy`
    (decoupled soft refs — a later app withdrawal does not cascade-erase history; §13).
- **Estimated size.** M.
- **Files/areas touched.** `apps/signals/models.py`,
  `apps/signals/migrations/0001_initial.py`, `apps/signals/tests/test_models.py`.

## T-04 — Capture write path A: impression anchor + visit substrate + errors + metrics (risk-first) — AC1, AC2, AC4, AC11
- **Description.** Implement the **anchor half** of the single write path `apps/signals/capture.py`
  ([DESIGN §5a/§5d/§10](DESIGN.md)) plus the shared error/metric surface the whole path uses:
  - `record_impression(user, app_id, *, surface, occurred_at=None) -> Impression` — validates
    the app via `catalog.get_catalogued_app(app_id)` (missing/non-accepted → **`UnknownAppError`**,
    nothing written), then **in one `transaction.atomic()`** writes the `Impression` **and** copies
    the app's **current resolved `tag_id`s** from `get_catalogued_app(...).tags` into
    `ImpressionTag` rows (the **frozen** capture-time snapshot — AC1/AC2); on success increments
    `IMPRESSION_CAPTURED`.
  - `record_platform_visit(user, *, on_date=None) -> PlatformVisit` — **idempotent**
    `get_or_create(user, visit_date)` (a duplicate day is a no-op; a lost race raising
    `IntegrityError` is caught and treated as "already recorded" — DESIGN §4 concurrency); on a
    created row increments `PLATFORM_VISIT_CAPTURED`. This is the AC4 return *substrate*.
  Create `apps/signals/errors.py` with the **full loud error set** used across the write path
  (DESIGN §5a): `UnknownAppError`, `ImpressionMismatchError` (the latter used by T-05). Add this
  feature's metric-name constants to `apps/core/observability.py` (matching the established
  location, as `taxonomy`/`catalog` did — DESIGN §9): `IMPRESSION_CAPTURED`,
  `CLICK_THROUGH_CAPTURED`, `SUBSCRIBE_CAPTURED`, `PAGE_REENGAGEMENT_CAPTURED`, `SHARE_CAPTURED`,
  `PLATFORM_VISIT_CAPTURED`, `OFF_PLATFORM_PROXY_CAPTURED`, and **`CAPTURE_ERROR`** (the AC11/R4
  loud-loss signal that **must stay 0** — alert on any nonzero); reuse `increment(...)` as-is.
  **Fail-loud contract (AC11/§5d):** every recorder wraps its write(s) in `transaction.atomic()`
  and, on **any** failure, increments `CAPTURE_ERROR` (tagged with the event kind) + logs with
  request context **before re-raising** — capture is never silently lossy, and a partial write
  never persists. **Actor is the caller (§10):** `user` is the authenticated account the surface
  holds; capture never accepts an arbitrary actor id.
- **Dependencies.** T-03 (models). Reuses `catalog.get_catalogued_app` (D-6) — not rebuilt.
- **Definition of done.**
  - `record_impression` with an unknown/non-accepted `app_id` → `UnknownAppError`, **nothing
    written** (no impression, no tag rows — atomic); with a valid app, writes one `Impression`
    + one `ImpressionTag` per current app tag **in one transaction** (a forced mid-call failure
    leaves neither — test by patching to raise) and increments `IMPRESSION_CAPTURED`.
  - The captured tag set equals `get_catalogued_app(app_id).tags` **at capture time** and does
    **not** change when a tag is later renamed/retired (frozen — AC2; a test renames a tag and
    asserts the stored `tag_id` set is unchanged).
  - `record_platform_visit` is **idempotent**: two calls for the same user-day yield exactly
    **one** row; the second is a no-op (no second `PLATFORM_VISIT_CAPTURED`).
  - **Fail-loud:** a simulated write failure increments `CAPTURE_ERROR` and **re-raises** (the
    error is never swallowed); a test asserts the counter and the raise.
  - `capture.py` is the **only** module that creates `signals_*` rows (no ORM writes elsewhere —
    review note in the DoD); the capture surface + `errors.py` are registered in
    [CODEMAP.md](../../CODEMAP.md).
- **Estimated size.** M.
- **Files/areas touched.** `apps/signals/capture.py`, `apps/signals/errors.py`,
  `apps/core/observability.py` (signals metric constants),
  `apps/signals/tests/test_capture_impression.py`, CODEMAP.

## T-05 — Capture write path B: engagement events (risk-first) — AC3, AC5, AC6, AC7, AC11
- **Description.** Implement the **engagement half** of `apps/signals/capture.py`
  ([DESIGN §5a/§5d](DESIGN.md)), each recorder writing **one append-only `EngagementEvent`**,
  atomic + counted + fail-loud (same contract as T-04), validating the app via
  `catalog.get_catalogued_app` (→ `UnknownAppError`):
  - `record_click_through(user, app_id, *, impression, occurred_at=None)` — **impression
    REQUIRED** (AC3); writes `kind=CLICK_THROUGH`; increments `CLICK_THROUGH_CAPTURED`.
  - `record_subscribe(...)` / `record_page_reengagement(...)` / `record_share(...)` —
    `impression` **optional** (AC5/AC6); write `kind=SUBSCRIBE` / `PAGE_REENGAGEMENT` / `SHARE`;
    increment the matching counter.
  - `record_off_platform_proxy(user, app_id, *, impression, occurred_at=None)` — **impression
    REQUIRED**; writes `kind=OFF_PLATFORM_PROXY`, **`is_proxy=True`** (the flagged-secondary seam,
    §8); increments `OFF_PLATFORM_PROXY_CAPTURED` (tagged `secondary`). **No detector is built**
    (OQ-1) — this is the only off-platform mechanism shipped.
  **Invariants at this one boundary (illegal states unrepresentable — §5a):**
  - **Impression linkage (AC3):** for the two impression-required kinds, the service asserts
    `impression.app_id == app_id` **and** `impression.user == user`, else **`ImpressionMismatchError`**
    — a conversion cannot be pinned to another app's or user's shown instance. For the optional
    kinds, a supplied impression is validated the same way; `None` is allowed.
  - **`is_proxy` is service-set, never caller-supplied:** only `record_off_platform_proxy` sets
    `True`; the on-platform recorders force `False` (the secondary-vs-primary distinction is
    structural, AC7).
- **Dependencies.** T-04 (shares `capture.py`, `errors.py`, the metric constants; tests build an
  `Impression` via `record_impression`). **Run after T-04 — do not parallelize on `capture.py`.**
- **Definition of done.**
  - `record_click_through` / `record_off_platform_proxy` **require** an impression (omitting it
    is a type/`ValidationError`); a mismatched `app_id` or `user` → `ImpressionMismatchError`,
    **nothing written**.
  - The optional-impression recorders write with `impression=None` **and** with a valid
    impression; a mismatched supplied impression still raises.
  - `record_off_platform_proxy` writes `is_proxy=True`; **every** on-platform recorder writes
    `is_proxy=False` (test asserts the caller cannot flip it).
  - Each recorder is atomic + increments its counter on success and `CAPTURE_ERROR` + re-raises
    on failure (AC11).
  - No new file under `errors.py`/`observability.py` (extends T-04's); the capture surface entry
    in [CODEMAP.md](../../CODEMAP.md) covers all seven recorders.
- **Estimated size.** M.
- **Files/areas touched.** `apps/signals/capture.py`,
  `apps/signals/tests/test_capture_engagement.py` (CODEMAP entry updated to list all recorders).

## T-06 — PlatformVisit middleware + `MIDDLEWARE` wiring — AC4, AC11 (§5d fail-soft-but-counted)
- **Description.** Implement `apps/signals/middleware.py` with `PlatformVisitMiddleware`
  ([DESIGN §3/§5d/§12](DESIGN.md)): turn an **authenticated** request into an idempotent daily
  visit by calling `capture.record_platform_visit(request.user)` — the **return-to-platform
  substrate** AC4 derives from. Register it in `config/settings.py` `MIDDLEWARE` **after**
  `AuthenticationMiddleware` and `apps.core.middleware.RequestContextMiddleware` (so
  `request.user` is resolved and the failure log carries request context). The middleware is
  **non-blocking and fail-soft-but-counted** (§5d): an anonymous request records nothing; a
  capture failure is logged + increments `CAPTURE_ERROR{kind=visit}` and **never breaks page
  navigation** (a single missed visit-day marginally under-counts returns, which the metric
  surfaces). It does **one job** — record the visit — and delegates all write logic to
  `capture.record_platform_visit` (no ORM in the middleware).
- **Dependencies.** T-04 (`record_platform_visit`). Edits `config/settings.py` after T-01 — run
  in order (no parallel edit of `settings.py`).
- **Definition of done.**
  - An authenticated request results in exactly **one** `PlatformVisit` for that user-day;
    repeated requests the same day add **no** further rows (idempotent via T-04).
  - An **anonymous** request records **nothing** and passes through unaffected.
  - A simulated `record_platform_visit` failure is **logged + counts `CAPTURE_ERROR{kind=visit}`**
    and the response is still returned normally (the user's navigation is not broken) — test
    asserts both the counter and the unbroken response.
  - The middleware contains no DB access of its own (delegates to `capture`); it is registered in
    `MIDDLEWARE` at the documented position.
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/middleware.py`, `config/settings.py` (`MIDDLEWARE`),
  `apps/signals/tests/test_middleware.py`.

## T-07 — Read/funnel selectors: raw counts + derived returns (risk-first) — AC4, AC7, AC8, AC9, SC-9
- **Description.** Implement the **single read path** `apps/signals/selectors.py`
  ([DESIGN §5b/§9/§11](DESIGN.md)) — every consumer (future developer-dashboard / editorial
  backtest) reads through these; nothing reads `signals_*` directly past this surface. Define the
  `AppFunnel` frozen dataclass (the DTO with `impressions`, `click_throughs`, `returns_3d`,
  `returns_14d`, `subscribes`, `page_reengagements`, `shares`, `off_platform_proxy`) and:
  - `app_funnel(app_id, *, start, end) -> AppFunnel` — the **H3 backtest** (AC8): the per-app
    **raw** funnel over `[start, end]`, all counts from stored rows.
  - `funnel_for_apps(app_ids, *, start, end) -> list[AppFunnel]` — bulk, **no N+1** (AC9).
  - `category_impressions(tag_id, *, start, end) -> int` — per-category baseline (AC2).
  **Invariants (§5b):**
  - **Returns are DERIVED, never stored, no backfill (AC4/AC8/SC-9):** `returns_3d`/`returns_14d`
    count in-window impressions whose `user` has a `PlatformVisit` with
    `visit_date ∈ (impression.occurred_at.date, +N]`, where `N` =
    `config.return_window_short_days` / `return_window_long_days` (no magic `3`/`14`). Expressed
    as a **single correlated-aggregate/`EXISTS` query per app** (not per-impression Python
    looping — DESIGN §9), so the whole funnel is reconstructable from stored rows alone, with a
    *not-returned* outcome represented as the **absence** of a qualifying visit.
  - **Raw only — never scored (AC9/R5):** every field is a count or derived count; **no
    normalization, weighting, ranking, or score** anywhere in this path.
  - **Proxy is segregated (AC7):** `off_platform_proxy` (`is_proxy=True`) is counted in its own
    field and **never folded into** `click_throughs` or any on-platform count — the funnel is
    complete from on-platform signal alone.
  - **Read surface is internal/admin (§5c/§10):** in-process selectors only — **no public/DRF
    endpoint** at MVP (when developer-dashboard needs HTTP it adds a thin `HasRole(ADMIN)`-gated
    read view over these selectors — a one-feature-later addition, noted **not built**).
- **Dependencies.** T-04, T-05 (tests build the full funnel via the capture recorders + visits).
- **Definition of done.**
  - `app_funnel` reconstructs every funnel field from stored `Impression`/`EngagementEvent`/
    `PlatformVisit` rows with **no backfill**; a test builds a known corpus and asserts each
    count.
  - **Returns derivation** is correct at the window boundary: an impressed user with a visit on
    day +3 counts in `returns_3d`/`returns_14d`; a visit on day +10 counts only in `returns_14d`;
    an impressed user with **no** in-window visit counts in **neither** (the *not-returned* case
    is representable). Window lengths come from config (changing the tunable changes the result).
  - `off_platform_proxy` appears **only** in its own field and is never added into
    `click_throughs` (test mixes proxy + on-platform events and asserts segregation).
  - `funnel_for_apps([...])` over several apps does **not** N+1 (assert query count); the DTO
    carries **no** score/weight/rank field (AC9).
  - `category_impressions(tag_id, …)` counts impressions whose frozen snapshot includes `tag_id`.
  - `selectors.py` (the `app_funnel`/`funnel_for_apps` read surface — the downstream substrate) is
    registered in [CODEMAP.md](../../CODEMAP.md).
- **Estimated size.** M.
- **Files/areas touched.** `apps/signals/selectors.py`, `apps/signals/tests/test_selectors.py`,
  CODEMAP.

## T-08 — Read-only admin (corpus inspection / cold-start) — AC11 (attributability)
- **Description.** Implement `apps/signals/admin.py` ([DESIGN §3/§5c/§9](DESIGN.md)): register the
  four models on the Django admin as the `is_staff`-gated **read-only inspection** surface so ops
  can inspect the corpus during cold-start. **No add/change/delete permission on any of the four**
  — append-only is enforced in code (capture is the only writer) and must not be circumventable
  through the admin. No rich analytics here (that is a future consumer); inspection + the
  `CAPTURE_ERROR` metric make loss/tampering observable (§10 attributability).
- **Dependencies.** T-03 (models).
- **Definition of done.**
  - `Impression`, `ImpressionTag`, `EngagementEvent`, `PlatformVisit` appear in the admin and are
    **not** add/change/delete-able (test the admin permissions for each).
  - No admin path can mutate a `signals_*` row (review note — capture remains the sole writer).
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/admin.py`, `apps/signals/tests/test_admin.py`.

## T-09 — PRIVACY.md, README, .env.example, CODEMAP reconcile, finalize D-7 & rollout — AC9 (contract), AC10, §11/§12
- **Description.** Finalize the privacy artifact, operator/consumer docs, and the durable
  channels ([DESIGN §10/§11/§12](DESIGN.md)):
  - **`apps/signals/PRIVACY.md`** (AC10/§10/SC-6) — the human-readable posture: **what** is
    recorded (the stored-fields whitelist — `Account` FK, `App.id`, the `Tag.id` snapshot,
    `EventKind`, `Surface`, the impression link, `is_proxy`, timestamps; and explicitly **not**
    IP/UA/device/geo/referrer/off-platform-id/free-text), **why** (the H3 backtest), **how long**
    (full MVP, **no auto-purge** — A3), and **deletion behavior** (`SET_NULL` anonymize-not-purge
    on the event `user` FKs; `CASCADE` on `PlatformVisit` — SC-10; note the confirm-with-data
    nuance).
  - a **README** section for `apps/signals/` — how to migrate (`migrate signals`), the **capture
    contract** every emitting surface calls (`signals.capture.*` — the D-7 write rules), the
    **read path** downstream consumers use (`signals.selectors.app_funnel`/`funnel_for_apps`,
    raw-only), and the **rollback** note (`migrate signals zero` + remove
    `PlatformVisitMiddleware` from `MIDDLEWARE` — §9/§12);
  - **`.env.example`** entries for the two new tunables (`RETURN_WINDOW_SHORT_DAYS=3`,
    `RETURN_WINDOW_LONG_DAYS=14`) with their defaults;
  - reconcile [CODEMAP.md](../../CODEMAP.md) so its `apps/signals/` entries (the `capture` write
    surface incl. all seven recorders, the `selectors` read surface incl. `app_funnel`/
    `funnel_for_apps`/`category_impressions`, `errors.py`, `kinds.py`, the middleware, the metric
    constants, the config tunables) match the shipped code exactly (no stale/missing entries);
  - **finalize the cross-feature contract** as global **[D-7](../../DECISIONS.md)** — verify it
    is recorded **APPROVED** and states: a behavioral signal is an **append-only** `Impression`
    (anchor, frozen capture-time `Tag.id` snapshot) or `EngagementEvent` (`kind` discriminator,
    optional `impression`, `is_proxy`); **emit only through `signals.capture.*`**; reference apps
    by `App.id` (D-6) and tags by `Tag.id` (D-5) as soft refs; **read raw counts only** via
    `signals.selectors.*` (scoring is the consumer's job); returns are **derived not stored**; the
    off-platform proxy is a **flagged secondary** never required for funnel completeness — and
    that the §12 note (a feature adopts D-7 **before** it emits/reads any signal) is captured.
- **Dependencies.** all prior tasks.
- **Definition of done.**
  - `apps/signals/PRIVACY.md` exists and states what/why/retention/deletion (AC10) including the
    whitelist and the SC-10 deletion semantics.
  - README documents migrate → the capture contract → the downstream read path → rollback;
    `.env.example` covers both return-window tunables.
  - CODEMAP reflects exactly the shared `apps/signals/` surface that exists.
  - [D-7](../../DECISIONS.md) is present, marked **APPROVED**, and states the contract above; the
    "adopt before emit/read" §12 note is captured.
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/PRIVACY.md`, `README.md`, `.env.example`,
  `CODEMAP.md`, `DECISIONS.md` (verify/finalize D-7).

---

## Coverage check (Planner exit criterion — every design element appears in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §2 project layout / new `apps/signals/` app + `INSTALLED_APPS` + return-window tunables | T-01 |
| §3/§4 `EventKind` / `Surface` closed vocabularies (`kinds.py`) | T-02 |
| §3/§4 `Impression` model (anchor: UUID identity, soft `app_id`, surface, occurred_at) | T-03 |
| §3/§4 `ImpressionTag` model (frozen capture-time `Tag.id` snapshot, soft ref, unique) | T-03 |
| §3/§4 `EngagementEvent` model (uniform shape, `kind` discriminator, nullable `impression`, `is_proxy`) | T-03 |
| §3/§4 `PlatformVisit` model (per-user-per-day, unique, CASCADE) | T-03 |
| §4 migration 0001 (4 tables only, reversible) | T-03 |
| §4/§9 raw-only — no score/weight/rank column anywhere (AC9/R5) | T-03 (structural), T-07 (DTO) |
| §10 privacy whitelist — no IP/UA/device/geo/referrer/PII/free-text column (AC10) | T-03 (structural), T-09 (PRIVACY.md) |
| §4/§10/§13 deletion semantics — `SET_NULL` anonymize (events) / `CASCADE` (visits) (SC-10) | T-03 |
| §5a capture write path: `record_impression` (+ tag snapshot) + `record_platform_visit` | T-04 |
| §5a capture write path: `record_click_through`/`_subscribe`/`_page_reengagement`/`_share`/`_off_platform_proxy` | T-05 |
| §5a `errors.py` (`UnknownAppError`, `ImpressionMismatchError`) | T-04 (defined), T-05 (used) |
| §5a app-validity via `catalog.get_catalogued_app` (D-6) at every recorder | T-04, T-05 |
| §5a frozen capture-time tag snapshot in one txn (AC1/AC2) | T-04 |
| §5a impression linkage + `app_id`/`user` match (AC3); `is_proxy` service-set (AC7) | T-05 |
| §5a/§5d atomic + counted + fail-loud (`CAPTURE_ERROR`) (AC11) | T-04, T-05 |
| §3/§5d `PlatformVisitMiddleware` (idempotent, fail-soft-but-counted) + MIDDLEWARE wiring | T-06 |
| §5b read path: `app_funnel` / `funnel_for_apps` / `category_impressions` (raw counts) | T-07 |
| §5b/§9 returns **derived** at read from impression × `PlatformVisit`, no backfill (SC-9) | T-07 |
| §5b proxy segregated in its own funnel field, never folded in (AC7) | T-07 |
| §5c read surface internal/admin only; no DRF endpoint at MVP (noted not built) | T-07, T-08 |
| §3/§5c/§9 read-only admin (corpus inspection; append-only preserved) | T-08 |
| §8 off-platform proxy seam — one capture call, no detector built (OQ-1/OQ-3) | T-05 (seam), T-09 (limitation documented) |
| §9 return windows as config tunables (no magic 3/14) | T-01 (tunables), T-07 (consumed) |
| §9 observability metric constants + `increment` reuse (1:1 with brief metrics) | T-04 (constants + impression/visit), T-05 (engagement), T-06 (visit-failure) |
| §9/§12 rollback (reversible migration, removable middleware) | T-03, T-06, T-09 |
| §10 security (single write path, actor=caller, cross-app attribution guard, internal read) | T-04, T-05, T-07 |
| §10 privacy posture human-readable (`PRIVACY.md`) + SC-6/SC-10 | T-09 |
| §11 cross-feature contract / global D-7 (capture+selectors+soft refs+raw+derived+proxy) | T-04/T-05 (write), T-07 (read), T-09 (record/verify) |
| §12 rollout (migrate, middleware wiring, no recurring job, emitter adoption note) | T-01, T-03, T-06, T-09 |
| §13 self-critique edges (single-table discriminator; derived returns; fail-loud-vs-non-blocking; deletion anonymize) | T-03 (schema + deletion), T-04/T-05 (fail-loud), T-06 (non-blocking), T-07 (derived) |
| §14 all 11 ACs | AC1 T-02/T-03/T-04 · AC2 T-03/T-04/T-07 · AC3 T-03/T-05 · AC4 T-03/T-04/T-06/T-07 · AC5 T-05 · AC6 T-02/T-05 · AC7 T-03/T-05/T-07 · AC8 T-07 · AC9 T-03/T-07 · AC10 T-03/T-09 · AC11 T-04/T-05/T-06 |

All design elements are covered; all tasks have a definition of done; **no `L` tasks remain**
(the single write path is split T-04 anchor / T-05 engagement; the read path is one M task).

> **Note for Stage 4 (Senior Engineer):**
> - The `TEST_PLAN.md` you produce must show **every acceptance criterion (AC1–AC11)** is
>   exercised by the tests in these tasks — the AC→task row above is the starting map.
> - **Risk-first order is load-bearing:** do T-03 (schema: single-table `kind` discriminator,
>   the no-score guarantee, the `SET_NULL`/`CASCADE` deletion edges), T-04/T-05 (capture
>   invariants + frozen tag snapshot + fail-loud), and T-07 (derived-not-stored returns) with
>   their tests **before** the middleware and any consumer relies on them — these are the
>   [DESIGN §13](DESIGN.md) sharp edges.
> - **`capture.py` is written by T-04 then T-05**, and `apps/core/observability.py` by T-04;
>   `config/settings.py` by T-01 (app + tunables) then T-06 (middleware). **Run those in the
>   listed order — do not parallelize edits to those files.**
> - **Register shared code in [CODEMAP.md](../../CODEMAP.md) as you go** (the capture surface in
>   T-04/T-05, the read surface in T-07) — a shared capture/selector shipped without a CODEMAP
>   entry is an incomplete task. Finalize global **D-7** in T-09.
> - **`CAPTURE_ERROR` must read 0 in every green test** (CLAUDE.md §6.6 — never mark work done
>   with a silent loss). The fail-loud tests assert it is incremented **and** the call re-raises.
> - **One design carry-over flagged for data (not a Stage-4 blocker):** the SC-10
>   anonymize-and-retain deletion posture — keep `SET_NULL` the implementation so a future
>   purge-on-deletion policy is a localized change. There is **no live emitter** at ship time
>   (the emitting surfaces are out of scope, R6) — a thin corpus until they ship is by design,
>   not a capture defect.
