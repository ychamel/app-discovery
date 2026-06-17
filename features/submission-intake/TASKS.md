# TASKS — submission-intake

*Stage 3 artifact (Planner / Tech Lead). Status: **complete — ready for Stage 4 (Senior
Engineer)**. Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED A-SI),
[DESIGN.md](DESIGN.md) (APPROVED 2026-06-17), feature [DECISIONS.md](DECISIONS.md)
(SI-1…SI-7), feature [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) (OQ-1/2/3 all RESOLVED),
global [DECISIONS.md](../../DECISIONS.md) (D-1 niche, D-2 no-hard-targets, D-4 stack,
D-5 taxonomy contract, D-6 catalogued-app contract), [CODEMAP.md](../../CODEMAP.md) (the
`apps/` shared surface from `identity-accounts` + `interest-taxonomy`). Every task
references the exact DESIGN.md section(s) and the acceptance criteria it satisfies, per the
traceability rule (CLAUDE.md §6.3). Produced by
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

---

## How to read this list

- Tasks are in **execution order**. Each is sized for one focused session and leaves the
  system **working and releasable** (vertical slices over horizontal layers wherever the
  dependency graph allows).
- **Sequencing** follows DESIGN and CLAUDE.md §3-planner: scaffold → the two pure-logic
  cores (gate enum, URL normalizer) → schema → write logic → read logic → notifications →
  API → UI pages → admin → docs. **Risk is front-loaded:** the four sharpest correctness
  edges from [DESIGN.md §13](DESIGN.md) land before any HTTP/UI surface wires them —
  (1) the **gate as a fixed enum with no "other" value** so a taste rejection is
  unrepresentable (T-02, AC6/R1); (2) the **write-service invariants** — required fields,
  closed vocabulary, media limits (T-05, AC1/AC4); (3) the **decision atomicity +
  lifecycle state machine** — single decision under a row lock, re-review-on-edit (T-06,
  AC5/AC8); and (4) the **accepted-only downstream read contract** (T-07, AC9/D-6). They
  are tested in isolation before any view depends on them.
- **Every `L` has been split** — no `L` tasks remain (Planner exit criterion). Where a
  natural unit (the write path, the HTTP surface, the pages) was too big for one session it
  is split along its seam (content-writes vs lifecycle-decisions; developer API vs review
  API; developer pages vs review page).
- **Files/areas touched** are declared so parallel agents do not collide. Paths follow the
  layout fixed in [DESIGN.md §2](DESIGN.md) (new app `apps/catalog/` under the shared-code
  root `apps/`, D-4). The HTTP/UI tasks (T-09…T-12) all extend `catalog/views.py` and
  `catalog/urls.py`; they are **ordered, not parallel**, for that reason — run them in the
  listed sequence to avoid collisions on those two files.
- **Reuse, don't re-derive.** This feature *adds one app and modifies only*
  `config/settings.py`, `config/urls.py`, `pyproject.toml`, and `apps/core/` (metric
  constants + the typed tunables) (DESIGN §1). It reuses, **by name and without
  re-implementing**: the accounts fail-closed gate `require_role(DEVELOPER)` /
  `HasRole(ADMIN)`; the taxonomy `is_valid_tag` / `resolve_tag` / `list_active_tags`
  (D-5); `apps.core.observability.increment` + `check_health`; the `apps.core.config`
  typed-tunable pattern; `apps.core.email.get_email_sender()`; and the request-context
  logging middleware. None of these are rebuilt.
- **Standards apply to every task** (CLAUDE.md §5): optimize for the reader, one
  function/one job, fail-loud at the trust boundary, config over hardcoding, **single
  write path (`services.py`) / single read path (`selectors.py`)**, and **shared code must
  be registered in [CODEMAP.md](../../CODEMAP.md) as part of definition-of-done** — a
  shared selector/service added without a CODEMAP entry is an incomplete task.

---

## Dependency overview

```
T-01 scaffold (app + settings + Pillow + media tunables)
 ├─ T-02 gate.py: Criterion enum + CHECKLIST + GATE_RELEVANT_FIELDS   ◄ risk: no-"other" (AC6)
 ├─ T-03 urlnorm.py: normalize_url (one dup rule)
 └─ T-04 models + migration 0001 (App, AppTag, AppMedia, ReviewDecision)   [needs T-02]
      └─ T-05 write service: submit/edit/media + invariants + errors   ◄ risk: write invariants
           └─ T-06 lifecycle & decision service: accept/reject/withdraw/resubmit   ◄ risk: atomicity
                ├─ T-07 read selectors + accepted-only catalog + time-to-decision   ◄ risk: AC9
                │    └─ T-09 developer HTTP API (endpoints 1–8)
                │         └─ T-11 developer server-rendered pages
                ├─ T-08 decision notifications + email templates
                │    └─ T-10 review HTTP API (endpoints 9–10)
                │         └─ T-12 admin review page
                └─ T-13 Django admin registration (inspection)   [needs T-04]
T-14 docs + CODEMAP + D-6 confirm + rollout   [needs all]
```

---

## T-01 — `apps/catalog/` scaffold + settings/deps wiring
- **Description.** Create the new Django app exactly as laid out in
  [DESIGN.md §2](DESIGN.md): `apps/catalog/` with `apps.py` (`AppConfig`), empty
  `models.py`, an empty `migrations/` package, an empty `urls.py` stub, and the
  `templates/catalog/` + `templates/email/` + `tests/` directories. Wire the infrastructure
  this feature needs (DESIGN §1/§9/§12):
  - register `apps.catalog` in `INSTALLED_APPS` and mount `catalog.urls` (empty for now) in
    `config/urls.py`;
  - add `Pillow` to `pyproject.toml` (image validation — as `interest-taxonomy` added
    `PyYAML`);
  - add `MEDIA_ROOT` / `MEDIA_URL` to `config/settings.py` and serve media in dev per the
    project convention;
  - add the two typed tunables to `apps/core/config.py` following the established pattern
    (DESIGN §9): `catalog_media_max_count` (default **8**) and `catalog_media_max_bytes`
    (default **5 MB**) — **validated at startup**, never hardcoded in logic.
  **Modifies no existing component's behavior** — `core` gains two tunables only; `accounts`
  / `taxonomy` are reused as-is, not touched.
- **Dependencies.** none.
- **Definition of done.**
  - `python manage.py check` passes with the new app installed; `makemigrations catalog`
    reports *no changes* (no models yet) — the app is wired but empty.
  - `catalog_media_max_count` / `catalog_media_max_bytes` are readable through
    `apps.core.config` with the documented defaults and fail loud if mis-set at startup.
  - No edits to `apps/accounts/` or `apps/taxonomy/` (boundary check — DESIGN §1).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/__init__.py`, `apps/catalog/apps.py`,
  `apps/catalog/models.py`, `apps/catalog/migrations/__init__.py`, `apps/catalog/urls.py`,
  `apps/catalog/templates/catalog/`, `apps/catalog/templates/email/`,
  `apps/catalog/tests/__init__.py`, `apps/core/config.py` (two tunables),
  `config/settings.py` (`INSTALLED_APPS`, `MEDIA_ROOT`/`MEDIA_URL`), `config/urls.py`
  (mount `catalog/`), `pyproject.toml` (`Pillow`).

## T-02 — Gate module: `Criterion` enum + checklist wording (risk-first) — AC5, AC6, AC8
- **Description.** Implement `apps/catalog/gate.py` exactly as specified in
  [DESIGN.md §6](DESIGN.md) — the **fixed five objective floors**, in code, not editable
  data:
  - `Criterion(models.TextChoices)` with the five values `WORKS`, `NOT_SPAM`,
    `NOT_DUPLICATE`, `HONEST`, `POLICY` — **and no "other"/"quality"/"not-for-us" value**
    (this is the structural guarantee behind AC6/R1: a taste rejection cannot be recorded
    because the value does not exist);
  - `CHECKLIST: dict[Criterion, str]` — the reviewer-facing "what to check" wording for
    each floor (the OQ-2 deliverable filled in here against the design's intent in §6/§6c;
    duplicate-check wording references the URL-collision hint); editing wording is a
    one-file change;
  - `GATE_RELEVANT_FIELDS = {"name", "description", "url", "tags", "media"}` — the named set
    whose edit on an accepted app forces re-review (consumed by `edit_app`, T-05/AC8).
- **Dependencies.** T-01.
- **Definition of done.**
  - `Criterion` has exactly the five floors and **no catch-all value**; a test asserts the
    member set is exactly those five (so a future "other" can't be slipped in unreviewed).
  - `CHECKLIST` has a non-empty entry for **every** `Criterion` member (test-enforced — no
    floor ships without reviewer wording).
  - `GATE_RELEVANT_FIELDS` equals the documented set; `gate.py` holds **no business logic
    and no DB access** (pure declaration — one job).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/gate.py`, `apps/catalog/tests/test_gate.py`.

## T-03 — URL normalizer: `normalize_url` (the one duplicate rule) — AC5 (duplicate floor)
- **Description.** Implement `apps/catalog/urlnorm.py` with `normalize_url(raw) -> str`
  ([DESIGN.md §3/§6c](DESIGN.md)) — the **single source of truth** for "these two URLs are
  the same app": canonicalize scheme/host/path (e.g. lowercase host, strip default ports,
  normalize trailing slash) deterministically. This is the value stored in
  `App.normalized_url` and the key for the duplicate **signal** (`apps_sharing_url`, T-07).
  It is a **signal, not a constraint** (SI-2: review is manual) — `normalize_url` decides
  equality only; it never rejects.
- **Dependencies.** T-01.
- **Definition of done.**
  - URLs differing only by scheme case, host case, default port, or trailing slash
    normalize to the **same** string; genuinely different paths/hosts normalize to
    **different** strings (table-driven test of equivalence classes).
  - Pure function — no DB, no I/O; deterministic and idempotent
    (`normalize_url(normalize_url(x)) == normalize_url(x)`).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/urlnorm.py`,
  `apps/catalog/tests/test_urlnorm.py`.

## T-04 — Data model & initial migration (4 tables) — AC1, AC3, AC4, AC5, AC9
- **Description.** Implement the four tables from [DESIGN.md §4](DESIGN.md) and the
  lifecycle enum (§7):
  - `App` — UUID PK (**the stable cross-feature reference**, AC9/D-6); `owner` FK →
    `accounts.Account` `on_delete=CASCADE`; `name` varchar(120) non-blank;
    `description` text non-blank, length-bounded; `url` varchar(2000); `normalized_url`
    citext **indexed (not unique)**; `status` enum(`pending`,`accepted`,`rejected`,
    `withdrawn`) **indexed**; `last_submitted_at` timestamptz; `created_at`/`updated_at`.
  - `AppTag` — UUID PK; `app` FK CASCADE; `tag_id` UUID **indexed, plain UUID (no DB FK)** —
    the D-5 soft reference; **unique `(app, tag_id)`**.
  - `AppMedia` — UUID PK; `app` FK CASCADE; `image` `ImageField(upload_to="app_media/%Y/%m/")`;
    `position` smallint with **unique `(app, position)`**; `alt_text` varchar(160) blank;
    `created_at`.
  - `ReviewDecision` — **append-only** UUID PK; `app` FK CASCADE; `reviewer` FK →
    `accounts.Account` `SET_NULL`; `outcome` enum(`accepted`,`rejected`);
    `failed_criteria` `ArrayField(varchar, choices=Criterion)` (empty for accepted, ≥1 for
    rejected — enforced in service, T-06); `note` text blank; `created_at`.
  Migration `0001_initial` creates **only the four tables (no content)** and enables the
  `citext` extension idempotently via `CreateExtension("citext")` (Django emits
  `IF NOT EXISTS`), so `catalog` does **not** depend on another app's migration beyond the
  intended `accounts` ownership FK (DESIGN §1/§4 — independently deletable apart from that
  edge). The fairness invariant is **structural** here: **no payment / tier / budget /
  brand / priority / fast-lane field exists on any table** (AC3 — unfair state
  unrepresentable).
- **Dependencies.** T-01, T-02 (`failed_criteria` uses `gate.Criterion` for `choices`).
- **Definition of done.**
  - Migration applies cleanly on a fresh PostgreSQL DB **and** where `citext` already
    exists (idempotent extension); `migrate catalog zero` drops all four tables (reversible
    — DESIGN §9/§12 rollback).
  - Tests: UUID PKs on all four; `unique (app, tag_id)`; `unique (app, position)`;
    `status` defaults to `pending`; `normalized_url` is indexed but **not** unique
    (a second row with the same normalized URL is insertable — SI-2/§6c); deleting an
    `Account` cascades its apps; deleting a reviewer `SET_NULL`s `ReviewDecision.reviewer`
    (decision survives); **no** monetary/priority field is present on any model (AC3 — assert
    by field-list review note + a test that the model has no such attribute).
  - No content rows created by the migration.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/models.py`,
  `apps/catalog/migrations/0001_initial.py`, `apps/catalog/tests/test_models.py`.

## T-05 — Write service: submit/edit/media + boundary invariants (risk-first) — AC1, AC3, AC4, AC8
- **Description.** Implement the **content-write half** of the single write path
  `apps/catalog/services.py` ([DESIGN.md §5a/§10](DESIGN.md)), each function wrapped in
  `transaction.atomic()` and emitting an observability counter:
  - `submit_app(owner, *, name, description, url, tag_ids, media) -> App` — creates a
    `pending` app, sets `normalized_url` via `urlnorm.normalize_url`, sets
    `last_submitted_at`, emits `submission_created`;
  - `edit_app(app, *, name=…, description=…, url=…, tag_ids=…) -> App` — owner edit; if the
    app is `accepted` and a **gate-relevant** field (`gate.GATE_RELEVANT_FIELDS`) changed,
    return it to `pending` (AC8 — leaves the catalog until re-reviewed);
  - `add_media(app, image, *, alt_text="") -> AppMedia` / `remove_media(media) -> None`
    (AC8) — bounded by the media cap; `remove_media` refuses to drop below 1.
  Enforce the **invariants at this one boundary** (illegal states unrepresentable):
  - **Required fields (AC1):** refuse unless `name`, `description`, a well-formed http(s)
    `url`, **≥1** `tag_id`, and **≥1** `media` are present → `ValidationError`, **no partial
    row/file written** (atomic);
  - **Closed vocabulary (AC4):** every `tag_id` checked with `taxonomy.is_valid_tag`; any
    off-vocabulary id → `InvalidTagError`, nothing written, increment
    `tag_off_vocabulary_rejected` (the metric must read **0** in normal use); no tag is ever
    coined here;
  - **Media validation (§9):** each upload validated by **Pillow** as a real, decodable
    image of an allowed format (**PNG/JPEG/WebP**) within `catalog_media_max_bytes`, and
    the per-app count kept within `catalog_media_max_count` → `MediaLimitError` otherwise;
    files stored via Django storage with **framework-generated names** (never the client
    filename) under `MEDIA_ROOT`;
  - **URL validation:** well-formed http(s), length-bounded, at the boundary (fail loud).
  Create `apps/catalog/errors.py` with the **full loud error set** used across the write
  path (DESIGN §5a/§10): `InvalidTagError`, `MediaLimitError`, `InvalidTransitionError`
  (used by T-06), `NotOwnerError`. Add the catalog metric-name constants alongside the
  existing ones in `apps/core/observability.py` (matching the established location —
  DESIGN §9): `submission_started`, `submission_completed`, `submission_created`,
  `app_withdrawn`, `app_resubmitted`, `tag_off_vocabulary_rejected`, `duplicate_flagged`
  (the decision/email counters land with T-06/T-08); reuse `increment(...)` as-is.
- **Dependencies.** T-04 (models), T-02 (`GATE_RELEVANT_FIELDS`), T-03 (`normalize_url`).
- **Definition of done.**
  - `submit_app` missing any required field / malformed url / 0 tags / 0 media →
    `ValidationError`, **nothing written** (no row, no file — atomic).
  - An off-vocabulary `tag_id` → `InvalidTagError`, nothing written, `tag_off_vocabulary_rejected`
    incremented.
  - A non-image / wrong-format / oversize upload, or one exceeding the count cap →
    `MediaLimitError`, **no file stored**; stored files use generated names, not client names.
  - Editing a gate-relevant field of an **accepted** app returns it to `pending`; editing a
    `pending`/`rejected` app updates in place (no status flip here — resubmit is explicit,
    T-06); `remove_media` that would leave 0 media is refused.
  - `services.py` is the **only** module that creates/mutates catalog content rows (no ORM
    writes elsewhere — review note in the DoD); each successful write emits its counter.
  - The write surface + `errors.py` are registered in [CODEMAP.md](../../CODEMAP.md).
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/services.py`, `apps/catalog/errors.py`,
  `apps/core/observability.py` (catalog metric constants), `apps/catalog/tests/test_services_write.py`,
  CODEMAP.

## T-06 — Lifecycle & decision service: accept/reject/withdraw/resubmit (risk-first) — AC5, AC6, AC7, AC8
- **Description.** Implement the **lifecycle half** of `apps/catalog/services.py`, the only
  code that changes `App.status` ([DESIGN.md §5a/§7/§10](DESIGN.md)), each atomic and
  counted:
  - `accept_app(app, reviewer) -> ReviewDecision` — `pending → accepted`; writes a
    `ReviewDecision(outcome=accepted, failed_criteria=[])` **and** flips `status` in **one
    transaction**; emits `app_accepted` + `review_decision{outcome=accepted}`;
  - `reject_app(app, reviewer, *, failed_criteria, note) -> ReviewDecision` —
    `pending → rejected`; requires **≥1** `failed_criteria` (each a `gate.Criterion`) else
    `ValidationError`; writes the decision + flips status atomically; emits `app_rejected` +
    `review_decision{outcome=rejected, criterion=…}` per failed floor (backs the
    rejection-reason distribution metric, AC6 drift signal);
  - `withdraw_app(app) -> App` — `pending`/`accepted`/`rejected` → `withdrawn` (AC8);
    emits `app_withdrawn`;
  - `resubmit_app(app) -> App` — `rejected`/`withdrawn` → `pending`, new `last_submitted_at`
    (AC7 non-terminal rejection); emits `app_resubmitted`.
  **Transition guard:** every change validates the current `status` against the §7 table and
  raises `InvalidTransitionError` (loud → `409`) otherwise. `accept`/`reject` take
  `select_for_update()` on the `App` row and **re-check `status == pending`** so two editors
  cannot double-decide (DESIGN §4 concurrency / §10). The notification is **not** sent here
  — it is triggered after commit by the caller via T-08 (kept out of the transaction).
- **Dependencies.** T-05 (shares `services.py`, `errors.py`, the metric constants).
- **Definition of done.**
  - `accept_app`/`reject_app` write the `ReviewDecision` **and** flip `status` in the same
    transaction (a forced failure mid-call leaves neither — test by patching to raise);
    `reject_app` with 0 `failed_criteria` → `ValidationError`, nothing written.
  - Accept/reject on a non-`pending` app → `InvalidTransitionError`; a simulated concurrent
    second decision (two `select_for_update` paths) yields exactly **one** decision, the
    second raising `InvalidTransitionError`.
  - `withdraw_app` from each allowed state → `withdrawn`; withdraw of an already-`withdrawn`
    app raises `InvalidTransitionError`; `resubmit_app` from `rejected` and from `withdrawn`
    → `pending` with a fresh `last_submitted_at`.
  - `ReviewDecision` rows are **never updated or deleted** by any service path (append-only
    — review note + test that no service mutates an existing decision).
  - Each transition emits its counter.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/services.py`,
  `apps/catalog/tests/test_services_lifecycle.py` (extends `errors.py` /
  `apps/core/observability.py` from T-05 — no new files there).

## T-07 — Read selectors + accepted-only catalog + time-to-decision (risk-first) — AC8, AC9, plus metrics
- **Description.** Implement the **single read path** `apps/catalog/selectors.py`
  ([DESIGN.md §5b/§9/§11](DESIGN.md)), every consumer (in-process + HTTP) calls these and
  nothing reads `catalog_app` directly past this surface (D-6):
  - `get_owned_app(owner, app_id) -> App | None` and `list_owned_apps(owner) -> list[App]`
    — **owner-scoped**; non-ownership is indistinguishable from not-found (AC8 — no leak,
    no enumeration);
  - `list_review_queue() -> list[ReviewRow]` — `status=pending`, **FIFO by
    `last_submitted_at`**, with a **duplicate hint** ("N other apps share this URL" via
    `apps_sharing_url`); **no priority field** (AC3);
  - `apps_sharing_url(normalized_url, *, exclude=None) -> list[App]` — the duplicate signal;
  - `list_catalogued_apps() -> list[CatalogApp]` and `get_catalogued_app(app_id) ->
    CatalogApp | None` — **ACCEPTED ONLY** (a pending/rejected/withdrawn app is **never**
    presented as catalogued — the AC9 / D-6 guarantee), tags dereferenced via
    `taxonomy.resolve_tag` (follows renames/merges, never drops a retired ref — D-5), media
    returned in **stable `position` order**, prefetched (no N+1);
  - a **time-to-decision reporting selector** (e.g. `decision_latencies()` /
    `time_to_decision(app)`) computing `ReviewDecision.created_at − App.last_submitted_at`
    from stored timestamps — observable, **not** an SLA counter (DESIGN §9 / D-2).
- **Dependencies.** T-06 (tests build apps through the write+lifecycle services).
- **Definition of done.**
  - `get_owned_app`/`list_owned_apps` return only the caller's apps; another owner's id
    yields `None`/absent (AC8).
  - `list_catalogued_apps`/`get_catalogued_app` return **only** `accepted` apps — a
    pending, rejected, **and** withdrawn app each return `None`/absent (AC9, one test per
    non-accepted state); tags are returned **resolved** (a renamed tag shows the new label;
    a retired-with-successor tag shows the successor; nothing dropped); media in `position`
    order; a list read does not N+1 (assert query count).
  - `list_review_queue` is strictly FIFO by `last_submitted_at` and carries the duplicate
    hint; it exposes **no** priority/tier field (AC3).
  - The time-to-decision selector returns the stored-timestamp delta and is covered by a
    test.
  - `selectors.py` (esp. `list_catalogued_apps`/`get_catalogued_app` as the D-6 substrate)
    registered in [CODEMAP.md](../../CODEMAP.md).
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/selectors.py`,
  `apps/catalog/tests/test_selectors.py`, CODEMAP.

## T-08 — Decision notifications + email templates — AC7
- **Description.** Implement `apps/catalog/notifications.py` with
  `notify_decision(decision)` ([DESIGN.md §5d](DESIGN.md)): render
  `templates/email/app_accepted.{subject,body}.txt` or `app_rejected.{subject,body}.txt`
  (the rejected body lists the **failing criteria labels** + the editor's **note** in
  actionable terms — AC7) and send via `apps.core.email.get_email_sender()` (reused, not
  rebuilt). It is called **after** the decision transaction commits — the **decision is
  authoritative, the email is a notification**: a send failure is logged and counted
  (`EMAIL_SEND_FAILURE`, added to `apps/core/observability.py`) and surfaced to the review
  UI, but **does not roll back the decision** (the developer still sees the outcome + reason
  in "my apps"). Add the `review_decision` / `EMAIL_SEND_FAILURE` constants if not already
  present from T-06.
- **Dependencies.** T-06 (consumes a committed `ReviewDecision`).
- **Definition of done.**
  - An accepted decision sends the accepted template; a rejected decision sends the rejected
    template listing **each** failing criterion's label + the note (assert rendered body
    content).
  - A simulated email-send failure is **logged + counts `EMAIL_SEND_FAILURE`** and the
    decision **stands** (status unchanged, decision row intact) — not rolled back.
  - `notify_decision` performs **no** status mutation (it only notifies — one job).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/notifications.py`,
  `apps/catalog/templates/email/app_accepted.subject.txt`,
  `app_accepted.body.txt`, `app_rejected.subject.txt`, `app_rejected.body.txt`,
  `apps/core/observability.py` (if `EMAIL_SEND_FAILURE`/`review_decision` not yet added),
  `apps/catalog/tests/test_notifications.py`.

## T-09 — Developer HTTP API (endpoints 1–8) — AC1, AC2, AC4, AC7, AC8
- **Description.** Implement `apps/catalog/serializers.py` (read/write shapes), the
  developer DRF views in `apps/catalog/views.py`, and routes in `apps/catalog/urls.py` for
  the **eight developer endpoints** in [DESIGN.md §5c](DESIGN.md), each a **thin projection
  of `services`/`selectors`** (no business logic in views):
  1 `POST /apps` (multipart) → `201 {app}`; 2 `GET /apps/mine`; 3 `GET /apps/{id}`;
  4 `PATCH /apps/{id}`; 5 `POST /apps/{id}/media`; 6 `DELETE /apps/{id}/media/{mid}`;
  7 `POST /apps/{id}/withdraw`; 8 `POST /apps/{id}/resubmit`.
  Auth: session + **`require_role(DEVELOPER)`/`HasRole(DEVELOPER)`** (AC2, reuses the
  accounts gate — no new auth path); **all app-scoped routes owner-scoped via
  `get_owned_app`** → `404` on someone else's app (no enumeration). Map service errors to
  status (DESIGN §5c/§10): `ValidationError`→`400` (per-field), `InvalidTagError`/
  `MediaLimitError`→`400`, non-developer→`403`, not-owner→`404`,
  `InvalidTransitionError`→`409`. **Unauthenticated = `403`** under the platform's
  `SessionAuthentication` (matching `accounts`/`taxonomy` ITX-9 — no `401`).
- **Dependencies.** T-05, T-06, T-07.
- **Definition of done.**
  - Each endpoint returns the specified success shape/status; a non-developer gets `403`; a
    valid-but-not-owner app id gets `404` on 3–8; a bad lifecycle transition (e.g. withdraw
    an already-withdrawn app) gets `409`; a missing field / off-vocab tag / bad media gets
    `400` with per-field messages and **no** partial write.
  - Views contain serialization + error→status mapping only and delegate to
    `services`/`selectors` (no ORM/business logic in `views.py` — review note in DoD).
  - Tests cover each endpoint's success path + its documented error statuses.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/serializers.py`, `apps/catalog/views.py`,
  `apps/catalog/urls.py`, `apps/catalog/tests/test_api_developer.py`.

## T-10 — Review HTTP API (endpoints 9–10) — AC3, AC5, AC6, AC7
- **Description.** Implement the **two admin review endpoints** in
  [DESIGN.md §5c](DESIGN.md), extending `serializers.py`/`views.py`/`urls.py`:
  9 `GET /review/queue` → `200 [{app, owner, submitted_at, duplicate_hint}]` — **FIFO, no
  priority field** (AC3), from `list_review_queue`;
  10 `POST /apps/{id}/decision` → `200 {decision}` with body `{outcome, failed_criteria[],
  note}` routing to `accept_app`/`reject_app` (AC5/AC6/AC7). Auth: session +
  **`HasRole(ADMIN)`** (AC5); identical handling for every app (AC3 — no per-developer
  branch). After a committed decision, call `notify_decision` (T-08). Error mapping:
  reject with **0 criteria or an unknown criterion** → `400` (the closed-enum check makes a
  taste rejection a `400`, AC6); non-admin → `403`; app not `pending` → `409`.
- **Dependencies.** T-06, T-07, T-08.
- **Definition of done.**
  - `GET /review/queue` returns pending apps **FIFO** with the duplicate hint and **no**
    priority/tier field; non-admin → `403`.
  - `POST …/decision` accepts (all-pass) and rejects (≥1 criterion + note) a `pending` app,
    writing exactly one `ReviewDecision` and triggering `notify_decision`; reject with 0 or
    an unknown criterion → `400`; decision on a non-`pending` app → `409`; non-admin → `403`.
  - Views delegate to `services`/`selectors` only (review note in DoD).
  - Tests cover queue ordering/shape, accept, reject, the `400`/`403`/`409` paths, and that
    the notification is invoked after commit.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/serializers.py`, `apps/catalog/views.py`,
  `apps/catalog/urls.py`, `apps/catalog/tests/test_api_review.py`.

## T-11 — Developer server-rendered pages — AC1, AC7, AC8
- **Description.** Implement the developer human flow ([DESIGN.md §8](DESIGN.md)) as
  server-rendered pages that **post to the same `services`/`selectors`** as the API (no
  second source of truth): `forms.py` (submission/edit form), page views, and
  `templates/catalog/`:
  - submit (`GET/POST /submit`) — name, description, url, **tag picker fed by
    `taxonomy.list_active_tags`**, image uploader; on invalid, re-render with **per-field**
    errors and **no row created** (AC1); on success, redirect to the app detail showing
    `pending`;
  - my-apps (`GET /apps`) — empty state; per-app status badge; for a **rejected** app the
    **failing criteria + note** shown inline with a "correct & resubmit" action (AC7);
  - app detail/edit/withdraw/resubmit (`/apps/{id}`) — edit metadata/tags/media; withdraw;
    resubmit; an edit to an **accepted** app warns "this returns your app to review" (AC8).
  Owner-scoped (a non-owner gets the same not-found as the API); developer-role-gated.
- **Dependencies.** T-09 (shares `views.py`/`urls.py`; run after to avoid collision).
- **Definition of done.**
  - Submitting a complete form creates a `pending` app and redirects to its detail; an
    invalid form re-renders with per-field errors and creates **nothing** (AC1).
  - my-apps shows the empty state with no apps, a status badge per app, and for a rejected
    app the failing criteria + note + a resubmit control (AC7).
  - The accepted-app edit page shows the "returns to review" warning; withdraw/resubmit
    controls drive the lifecycle services (AC8).
  - Page views delegate to `services`/`selectors`/`forms` only.
  - Tests (Django test client) cover submit success/invalid, my-apps states, and
    edit/withdraw/resubmit.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/forms.py`, `apps/catalog/views.py`,
  `apps/catalog/urls.py`, `apps/catalog/templates/catalog/submit.html`,
  `my_apps.html`, `app_detail.html` (+ edit), `apps/catalog/tests/test_pages_developer.py`.

## T-12 — Admin review page — AC3, AC5, AC6
- **Description.** Implement the admin review human flow ([DESIGN.md §8](DESIGN.md)):
  `GET /review` — a **FIFO** list of pending apps, each with owner, submitted-at, and the
  **duplicate hint**; opening one shows the metadata, media, **resolved tags**, the
  **five-floor checklist** (from `gate.CHECKLIST`), and accept / reject(criteria + note)
  actions posting to `accept_app`/`reject_app`. Empty state = "No apps awaiting review."
  Admin-role-gated; identical for every app (AC3). Reuses the project's standard
  loading/error templates. **Renders no public app page** — that is `app-pages`
  (out of scope).
- **Dependencies.** T-10 (shares `views.py`/`urls.py`; run after).
- **Definition of done.**
  - `/review` lists pending apps **FIFO** with the duplicate hint and shows the empty state
    when none; non-admin is refused.
  - The detail view renders the five-floor checklist and resolved tags; accept moves the app
    to `accepted`; reject with ≥1 floor + note moves it to `rejected` and surfaces the
    decision; a reject attempt with no floor selected is refused with a per-field error
    (AC6 — the UI cannot express a taste rejection).
  - Page views delegate to `services`/`selectors` only.
  - Tests (Django test client) cover queue render/empty state, accept, reject, and the
    no-criterion refusal.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/views.py`, `apps/catalog/urls.py`,
  `apps/catalog/templates/catalog/review_queue.html`, `review_detail.html`,
  `apps/catalog/tests/test_pages_review.py`.

## T-13 — Django admin registration (inspection / cold-start) — AC5 (attributability)
- **Description.** Register `App` and `ReviewDecision` on the Django admin
  ([DESIGN.md §3/§9](DESIGN.md)) as the `is_staff`-gated **inspection** surface for ops
  cold-start (same pattern prior features used — **no rich review tooling**, that is
  `editorial-curation-tools`). `ReviewDecision` is **read-only in admin** (append-only — it
  must not be editable/deletable there); `App` is registered for inspection. Any
  state-changing admin path must route through `services.py`, not raw ORM writes — but the
  primary intent here is **read/inspect**, with `LogEntry` covering ad-hoc edits (DESIGN §9
  attributability).
- **Dependencies.** T-04.
- **Definition of done.**
  - `App` and `ReviewDecision` appear in the admin; `ReviewDecision` is **not** add/change/
    delete-able (append-only preserved — test the admin's permissions).
  - No admin path mutates `App.status` outside `services.py` (review note).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/admin.py`,
  `apps/catalog/tests/test_admin.py`.

## T-14 — Docs, CODEMAP reconcile, D-6 confirm & rollout — AC9 (contract), §11/§12
- **Description.** Finalize the operator/consumer docs and the durable channels
  ([DESIGN.md §11/§12](DESIGN.md)):
  - a README section for `apps/catalog/` — how to install (`Pillow`, `MEDIA_ROOT`), migrate
    (`migrate catalog`), submit/review via pages+API, and **read the catalog** downstream
    (`list_catalogued_apps`/`get_catalogued_app`); the rollback note (`migrate catalog
    zero` + clear `MEDIA_ROOT`);
  - `.env.example` entries for any new tunable (`catalog_media_max_count`,
    `catalog_media_max_bytes`, `MEDIA_ROOT`);
  - reconcile [CODEMAP.md](../../CODEMAP.md) so its catalog entries (the `selectors` read
    surface incl. the `list_catalogued_apps`/`get_catalogued_app` D-6 substrate, the
    `services` write surface, `errors.py`, the metric constants, the config tunables) match
    the shipped code exactly (no stale/missing entries);
  - confirm the **cross-feature contract** is recorded as global **[D-6](../../DECISIONS.md)**
    (already recorded at design approval — verify it states: the catalogued unit is an
    `accepted` `catalog.App`; its stable reference is `App.id`; read only via
    `list_catalogued_apps`/`get_catalogued_app` (accepted only); tags are `Tag.id` under
    D-5, resolved with `resolve_tag`; media is an ordered image list per §9 limits) and that
    the §12 note — consumers adopt it before storing any app reference — is captured. **OQ-3
    media limits** are the published contract `app-pages` must adopt; restate that in the
    README so the two do not diverge.
- **Dependencies.** all prior tasks.
- **Definition of done.**
  - README documents install → migrate → submit/review → downstream read → rollback;
    `.env.example` covers every catalog tunable used in code.
  - CODEMAP reflects exactly the shared catalog surface that exists.
  - [D-6](../../DECISIONS.md) is present and states the four-part contract above; the
    `app-pages`-adopts-OQ-3 note is captured.
- **Estimated size.** S.
- **Files/areas touched.** `README.md`, `.env.example`, `CODEMAP.md`,
  `DECISIONS.md` (confirm/finalize D-6).

---

## Coverage check (Planner exit criterion — every design element appears in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §2 project layout / new `apps/catalog/` app + settings/deps/tunables | T-01 |
| §3/§6 Gate (`Criterion` enum, `CHECKLIST`, `GATE_RELEVANT_FIELDS`) | T-02 |
| §3/§6c URL normalizer (`normalize_url`) | T-03 |
| §3/§4 `App` model | T-04 |
| §3/§4 `AppTag` model (soft `tag_id`, D-5) | T-04 |
| §3/§4 `AppMedia` model (ordered, unique position) | T-04 |
| §3/§4 `ReviewDecision` model (append-only, `failed_criteria` choices=Criterion) | T-04 |
| §4 migration 0001 (4 tables only, citext, reversible) | T-04 |
| §4/§9 fairness — no pay/tier/priority field anywhere (AC3) | T-04 (schema), T-07 (queue), T-10 (review API) |
| §5a write service: `submit_app`/`edit_app`/`add_media`/`remove_media` + invariants | T-05 |
| §5a write service: `accept_app`/`reject_app`/`withdraw_app`/`resubmit_app` | T-06 |
| §5a `errors.py` (InvalidTag/MediaLimit/InvalidTransition/NotOwner) | T-05 (defined), T-06/T-09 (used) |
| §4/§7 lifecycle state machine + transition guards + `select_for_update` | T-06 |
| §5b read selectors: owner views, review queue + dup hint, `apps_sharing_url` | T-07 |
| §5b/§11 `list_catalogued_apps`/`get_catalogued_app` (accepted-only, resolve_tag, ordered media) | T-07 |
| §9 time-to-decision reporting selector | T-07 |
| §5d notifications (`notify_decision`, after-commit, EMAIL_SEND_FAILURE) | T-08 |
| §5c developer HTTP API endpoints 1–8 + owner-scope + auth + error→status | T-09 |
| §5c review HTTP API endpoints 9–10 + admin gate + decision routing | T-10 |
| §8 developer server-rendered pages (submit / my-apps / detail-edit-withdraw-resubmit) | T-11 |
| §8 admin review page (queue + five-floor checklist + decision) | T-12 |
| §3/§9 Django admin (inspection; append-only decision) | T-13 |
| §6 media limits/formats (Pillow, count/size, config tunables) | T-01 (tunables), T-05 (validation) |
| §6b no-"other" → taste rejection unrepresentable (AC6/R1) | T-02 (enum), T-06 (≥1 criterion), T-10 (400 on 0/unknown) |
| §6c duplicate hint (manual, deterministic, not a constraint) | T-03 (rule), T-07 (hint), T-12 (surfaced) |
| §9 observability metric constants + `increment` reuse | T-05 (constants+write), T-06 (decision/lifecycle), T-08 (email-failure), T-07 (time-to-decision) |
| §9 security (single write/read path, owner-scope 404, admin gate, Pillow, generated filenames) | T-04, T-05, T-07, T-09, T-10 |
| §9/§12 rollback (reversible migration, removable media) | T-04, T-14 |
| §11 cross-feature contract / global D-6 | T-07 (substrate), T-14 (record/verify) |
| §12 rollout (Pillow/MEDIA_ROOT, migrate, founding catalog via same form) | T-01, T-04, T-14 |
| §13 self-critique edges (App/Submission collapse; soft tag ref; re-review-on-edit; cascade) | T-04 (single-row + cascade), T-05 (boundary tag check + re-review), T-06 (transitions) |
| §14 all 9 ACs | AC1 T-04/T-05/T-09/T-11 · AC2 T-09 · AC3 T-04/T-07/T-10 · AC4 T-04/T-05 · AC5 T-02/T-06/T-10/T-12 · AC6 T-02/T-06/T-10/T-12 · AC7 T-06/T-08/T-11 · AC8 T-05/T-06/T-07/T-09/T-11 · AC9 T-07/T-14 |

All design elements are covered; all tasks have a definition of done; **no `L` tasks
remain** (the write path is split T-05/T-06, the HTTP surface T-09/T-10, the pages
T-11/T-12).

> **Note for Stage 4 (Senior Engineer):**
> - The `TEST_PLAN.md` you produce must show **every acceptance criterion (AC1–AC9)** is
>   exercised by the tests in these tasks — the AC→task row above is the starting map.
> - **Risk-first order is load-bearing:** do T-02 (no-"other" enum), T-05 (write
>   invariants), T-06 (decision atomicity + lifecycle), and T-07 (accepted-only catalog)
>   with their tests **before** any HTTP/UI task depends on them — these are the four §13
>   sharp edges.
> - **T-09…T-12 all edit `catalog/views.py` and `catalog/urls.py`** — run them in the
>   listed order (developer API → review API → developer pages → review page), not in
>   parallel, to avoid collisions on those two files.
> - **Register shared code in [CODEMAP.md](../../CODEMAP.md) as you go** (write surface in
>   T-05, read surface in T-07) — a shared selector/service shipped without a CODEMAP entry
>   is an incomplete task. Confirm global **D-6** in T-14.
> - **Two design carry-overs flagged for data (not Stage-4 blockers):** the re-review-on-
>   any-accepted-edit churn (DESIGN §13, decided for MVP) and the owner-account-deletion
>   `CASCADE` (revisit when `signal-capture` keys signals to apps). Keep `GATE_RELEVANT_FIELDS`
>   the named seam so a future non-gated field skips re-review.
