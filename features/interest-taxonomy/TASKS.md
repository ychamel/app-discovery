# TASKS — interest-taxonomy

*Stage 3 artifact (Planner / Tech Lead). Status: **complete — ready for Stage 4 (Senior
Engineer)**. Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED A4),
[DESIGN.md](DESIGN.md) (APPROVED A5), feature [DECISIONS.md](DECISIONS.md) (ITX-1…ITX-8),
global [DECISIONS.md](../../DECISIONS.md) (D-4 stack, D-5 taxonomy contract),
[CODEMAP.md](../../CODEMAP.md) (the `apps/` shared surface from identity-accounts). Every
task references the exact DESIGN.md section(s) and the acceptance criteria it satisfies,
per the traceability rule (CLAUDE.md §6.3). Produced by
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

---

## How to read this list

- Tasks are in **execution order**. Each is sized for one focused session and leaves the
  system **working and releasable** (vertical slices over horizontal layers).
- **Sequencing** follows DESIGN and CLAUDE.md §3-planner: scaffold → schema → core write
  logic → core read logic → API → ops surfaces (seed/check/admin) → editorial content →
  docs. **Risk is front-loaded:** the two sharpest correctness edges from
  [DESIGN.md §13](DESIGN.md) — the write-service invariants (≥1-cluster, non-redundancy,
  safe retire) and the cycle-guarded `resolve_tag` chain — land in T-03/T-04, immediately
  after the schema, and are tested in isolation before any HTTP or admin surface wires them.
- **Every `L` has been split** — no `L` tasks remain (Planner exit criterion).
- **Files/areas touched** are declared so parallel agents do not collide. Paths follow the
  layout fixed in [DESIGN.md §2](DESIGN.md) (new app `apps/taxonomy/` under the shared-code
  root `apps/`, D-4).
- **Reuse, don't re-derive.** This feature *adds one app and modifies no existing
  component* (DESIGN §1). It reuses, by name: `apps.core.observability.increment` +
  `check_health`/`/health`, the `apps.core.config` typed-tunable pattern, the structured-log
  middleware, and the accounts `is_staff`/`admin` gate. None of these are re-implemented.
- **Standards apply to every task** (CLAUDE.md §5): one function/one job, fail-loud,
  config over hardcoding, single write path / single read path, and **shared code must be
  registered in [CODEMAP.md](../../CODEMAP.md) as part of definition-of-done** — a shared
  selector/service added without a CODEMAP entry is an incomplete task.

---

## Dependency overview

```
T-01 app scaffold
 └─ T-02 models + migration (Tag, Cluster, M2M)
      ├─ T-03 write service + invariants + errors   ◄ risk: invariants
      │    ├─ T-04 read selectors + resolve_tag      ◄ risk: cycle-guarded resolution
      │    │    └─ T-05 JSON read API (3 endpoints)
      │    ├─ T-06 seed file + seed_taxonomy command
      │    │    └─ T-09 author founding vocabulary + populate (needs T-07)
      │    ├─ T-07 check_taxonomy command + integrity
      │    └─ T-08 Django admin registration
      └────────────────────────────────────────────► T-10 docs + CODEMAP + D-5 (needs all)
```

---

## T-01 — `apps/taxonomy/` app scaffold
- **Description.** Create the new Django app exactly as laid out in
  [DESIGN.md §2](DESIGN.md): `apps/taxonomy/` with `apps.py` (`AppConfig`),
  empty `models.py`, an empty `migrations/` package, an empty `urls.py` stub, and the
  `seed/` and `management/commands/` package directories. Register `apps.taxonomy` in
  `INSTALLED_APPS`. **Modifies no existing component** (DESIGN §1) — `core`/`accounts`
  are reused as-is, not touched.
- **Dependencies.** none.
- **Definition of done.**
  - `python manage.py check` passes with the new app installed; `makemigrations
    taxonomy` reports *no changes* (no models yet) — i.e. the app is wired but empty.
  - No edits to `apps/core/` or `apps/accounts/` (boundary check — DESIGN §1).
- **Estimated size.** S.
- **Files/areas touched.** `apps/taxonomy/__init__.py`, `apps/taxonomy/apps.py`,
  `apps/taxonomy/models.py`, `apps/taxonomy/migrations/__init__.py`,
  `apps/taxonomy/urls.py`, `apps/taxonomy/seed/`,
  `apps/taxonomy/management/commands/__init__.py`, `config/settings*.py` (`INSTALLED_APPS`).

## T-02 — Data model & initial migration (Tag, Cluster, M2M) — AC5, AC7, AC8
- **Description.** Implement the three tables from [DESIGN.md §4](DESIGN.md):
  - `Cluster` — UUID PK; `slug` (citext, **unique**, immutable); `name` varchar(80);
    `description` text blank; `created_at`/`updated_at`.
  - `Tag` — UUID PK (**the stable cross-feature reference**, AC7); `slug` (citext,
    **unique**, immutable); `label` varchar(80) with a **unique constraint on a normalized
    form** (AC1/R2 dedupe); `definition` text blank; `status` enum(`active`,`retired`);
    `replaced_by` FK→`Tag` nullable `SET_NULL`; `created_at`/`updated_at`; `retired_at`
    nullable.
  - `Tag.clusters = ManyToManyField(Cluster, related_name="tags")` — the membership table,
    unique `(tag, cluster)`.
  Migration `0001_initial` creates **only the three tables (no content)** and enables the
  `citext` extension idempotently via `CreateExtension("citext")` (Django emits
  `IF NOT EXISTS`), so `taxonomy` does **not** depend on an `accounts` migration —
  apps stay independently deletable (DESIGN §1, CLAUDE.md §5.4).
- **Dependencies.** T-01.
- **Definition of done.**
  - Migration applies cleanly on a fresh PostgreSQL DB **and** on a DB where `citext`
    already exists (idempotent extension); rolling back via `migrate taxonomy zero` drops
    all three tables (reversible — DESIGN §9 rollback).
  - Tests: UUID PKs; `slug` uniqueness is case-insensitive (citext); two tags whose labels
    differ only by case/whitespace **cannot both exist** (normalized-label uniqueness);
    `replaced_by` is nullable and deleting the successor sets it NULL (no FK block);
    `status` defaults to `active`.
  - No tag content is created by the migration (content is T-06/T-09 seed territory —
    DESIGN §4 "NO content").
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/models.py`,
  `apps/taxonomy/migrations/0001_initial.py`, `apps/taxonomy/tests/test_models.py`.

## T-03 — Write service: invariants & lifecycle (risk-first) — AC1, AC5, AC6
- **Description.** Implement `apps/taxonomy/services.py` — the **single write path**
  ([DESIGN.md §3/§5b/§7](DESIGN.md)) with every function wrapped in `transaction.atomic()`
  and emitting an observability counter:
  - `add_tag(slug, label, *, clusters, definition="")` — requires **≥1 cluster** (AC5);
  - `rename_tag(tag, *, label)` — changes **label only**, never `id`/`slug` (AC6/AC7);
  - `retire_tag(tag, *, replaced_by=None)` — `status→retired` + `retired_at`, optional
    successor; **never deletes** the row (AC6/OQ-2);
  - `add_cluster(slug, name, *, description="")`, `rename_cluster(cluster, *, name)`;
  - `assign_to_cluster(tag, cluster)`, `remove_from_cluster(tag, cluster)` — the latter
    **refuses if it would orphan an active tag** (AC5);
  - `check_integrity() -> IntegrityReport` — orphan active tags, empty clusters,
    duplicate labels.
  Errors raised **loudly, never swallowed** ([DESIGN.md §5b/§10](DESIGN.md)):
  `DuplicateTagError` (slug or normalized-label collision — AC1/R2), `OrphanTagError`
  (would leave an active tag in zero clusters — AC5), `RetireSuccessorError` (successor
  missing / already retired / would form a `replaced_by` cycle at write time — OQ-2).
  Define the taxonomy metric-name constants
  (`taxonomy_tag_added`/`_renamed`/`_retired`, `taxonomy_integrity_violation`,
  `taxonomy_reference_break`) **alongside the existing constants in
  `apps/core/observability.py`** (matching the established location used by
  identity-accounts — CODEMAP "Observability"); reuse `increment(...)` as-is.
- **Dependencies.** T-02.
- **Definition of done.**
  - `add_tag` with zero clusters → `OrphanTagError`; with a duplicate slug **or**
    normalized label → `DuplicateTagError`; nothing written on any error path
    (atomic — DESIGN §10).
  - `rename_tag` changes `label` only; `id` and `slug` are byte-for-byte unchanged after.
  - `retire_tag` sets `status`/`retired_at`, keeps the row; a successor that is missing /
    retired / cyclic → `RetireSuccessorError`.
  - `remove_from_cluster` that would orphan an active tag → `OrphanTagError`.
  - Each successful write emits its counter; `services.py` is the **only** module that
    mutates taxonomy rows (no ORM writes elsewhere — verified by review note in the DoD).
  - `services.py` registered in [CODEMAP.md](../../CODEMAP.md) (shared write surface).
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/services.py`, `apps/taxonomy/errors.py`,
  `apps/core/observability.py` (add taxonomy metric constants only),
  `apps/taxonomy/tests/test_services.py`, CODEMAP.

## T-04 — Read selectors & cycle-guarded `resolve_tag` (risk-first) — AC2, AC6, AC7
- **Description.** Implement `apps/taxonomy/selectors.py` — the **single read/validate/
  resolve path** every consumer (in-process and HTTP) calls ([DESIGN.md §5a/§7](DESIGN.md)):
  - `list_active_tags() -> list[Tag]` (status active, clusters prefetched);
  - `list_clusters() -> list[Cluster]` (each with its active tags);
  - `get_tag(tag_id) -> Tag | None` (any status);
  - `is_valid_tag(tag_id) -> bool` — **True only for an existing ACTIVE tag** (AC2 — the
    validator downstream features enforce at *their* write boundary; this feature supplies
    it, the consumer enforces, mirroring `HasRole`);
  - `resolve_tag(tag_id) -> Tag | None` — follow `replaced_by` to the active successor;
    a **retired tag with no successor resolves to itself** (kept, never dropped); `None`
    **only** if the id never existed; **never rewrites** the caller's stored value
    (reference-break-rate = 0). The successor walk is **bounded by a config step-limit**
    (add `taxonomy_resolve_max_steps()` to `apps.core.config` following the typed-tunable
    pattern — never hardcoded); on hitting the limit it **logs loudly** and increments
    `taxonomy_reference_break`, returning the last good tag (never loops — DESIGN §10).
- **Dependencies.** T-03 (tests build data through the write service).
- **Definition of done.**
  - `is_valid_tag`: True for an active tag; **False** for a retired tag and for an unknown
    id (AC2) — no path coins a tag.
  - `resolve_tag`: a renamed tag resolves to itself with the new label (AC7, transparent
    rename); a retired-with-successor id resolves to the **active successor** (OQ-2 remap);
    a retired-**no**-successor id resolves to **itself** (kept — AC6); an unknown id → `None`;
    a hand-built `replaced_by` **cycle** stops at the step-limit, **logs + increments
    `taxonomy_reference_break`**, and returns the last good tag (never infinite-loops).
  - `list_active_tags`/`list_clusters` exclude retired tags and prefetch membership
    (no N+1).
  - `selectors.py` + `taxonomy_resolve_max_steps()` registered in
    [CODEMAP.md](../../CODEMAP.md) (the cross-feature read substrate — D-5).
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/selectors.py`, `apps/core/config.py`
  (add `taxonomy_resolve_max_steps`), `apps/taxonomy/tests/test_selectors.py`, CODEMAP.

## T-05 — JSON read API (3 endpoints) — AC2, AC5
- **Description.** Implement `apps/taxonomy/serializers.py`, `views.py`, `urls.py` and wire
  the app's URLs into `config/urls.py`, exposing the three read endpoints from
  [DESIGN.md §5c](DESIGN.md), each a **thin projection of `selectors`** (no business logic
  in views):
  - `GET /taxonomy/tags` → `200 [{id,slug,label,definition,clusters:[{id,slug,name}]}]`,
    **active only**;
  - `GET /taxonomy/tags/{id}` → `200 {id,slug,label,definition,status,replaced_by,
    clusters:[…]}`, any status; `404` unknown id;
  - `GET /taxonomy/clusters` → `200 [{id,slug,name,description,tags:[{id,label}]}]`
    (active tags).
  Auth = DRF default `IsAuthenticated` (inherited from D-4) — any signed-in user, **no
  special role**; `401` unauthenticated. **No write endpoints** at MVP (DESIGN §5c/§6).
- **Dependencies.** T-04.
- **Definition of done.**
  - All three contracts return the specified shapes/statuses; `GET /tags` and
    `GET /clusters` expose **active tags only**; unknown id on `GET /tags/{id}` → `404`;
    unauthenticated → `401` on all three.
  - Views contain serialization only and delegate to `selectors` (no ORM/business logic in
    `views.py` — review note in DoD).
  - Tests cover each endpoint's success shape, the `404`, and the `401`.
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/serializers.py`, `apps/taxonomy/views.py`,
  `apps/taxonomy/urls.py`, `config/urls.py` (mount `taxonomy/`),
  `apps/taxonomy/tests/test_api.py`.

## T-06 — Seed file format + `seed_taxonomy` command — AC1, AC6
- **Description.** Implement the editable vocabulary seed mechanism
  ([DESIGN.md §6](DESIGN.md)): commit `apps/taxonomy/seed/vocabulary.yaml` with the
  **documented structure** (clusters, then tags with slug/label/definition/cluster-
  membership; a tag may be marked `retired` with an optional successor slug) — a minimal
  valid skeleton now; the **founding content is authored in T-09**. Implement
  `manage.py seed_taxonomy`: parse the file and apply it **idempotently by upsert-on-`slug`**
  inside **one `transaction.atomic()`** — inserting new clusters/tags and updating
  labels/definitions/membership for existing ones — calling **`services.py` only** (never
  the ORM directly, so all invariants hold), then running `check_integrity()` at the end.
  Retirements are **explicit** (a tag flagged retired in the file): the seeder **never
  deletes** a tag that merely drops out of the file (silent reference breakage — AC6).
  On a malformed file or a bad reference, **abort the whole run** and report the offending
  entry (**no partial apply** — DESIGN §10).
- **Dependencies.** T-03.
- **Definition of done.**
  - Re-running `seed_taxonomy` on an unchanged file is a **no-op** (idempotent upsert);
    editing a label in the file and re-running updates only that label (id/slug stable).
  - A malformed entry / unknown cluster reference aborts the run with a clear message and
    **writes nothing** (atomic, no partial apply).
  - A tag removed from the file is **not** deleted; retiring requires an explicit `retired`
    flag, which routes through `retire_tag`.
  - Tests: idempotent re-run; label update; malformed-file abort; explicit retire.
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/seed/vocabulary.yaml`,
  `apps/taxonomy/management/commands/seed_taxonomy.py`,
  `apps/taxonomy/tests/test_seed.py`.

## T-07 — `check_taxonomy` integrity command — AC5
- **Description.** Implement `manage.py check_taxonomy` ([DESIGN.md §6/§10](DESIGN.md)):
  run `services.check_integrity()` and report **orphan active tags** (active + zero
  clusters), **empty clusters** (warn — never auto-delete, AC8 keeps clusters stable), and
  **duplicate labels**. On any violation, increment `taxonomy_integrity_violation` and exit
  **non-zero** (so it is usable as a CI/ops gate); clean → exit 0. This is the runnable
  assertion of the "every active tag in ≥1 cluster" invariant that no single DB constraint
  can express (DESIGN §13).
- **Dependencies.** T-03.
- **Definition of done.**
  - Clean vocabulary → exit 0, no violation counter.
  - A seeded orphan active tag → reported + `taxonomy_integrity_violation` + **non-zero
    exit**; an empty cluster → **warned, not failed, not deleted**.
  - Tests cover the clean case, the orphan case (non-zero exit), and the empty-cluster warn.
- **Estimated size.** S.
- **Files/areas touched.** `apps/taxonomy/management/commands/check_taxonomy.py`,
  `apps/taxonomy/tests/test_check_taxonomy.py`.

## T-08 — Django admin registration (cold-start curation) — AC1, AC6
- **Description.** Register `Tag` and `Cluster` on the Django admin
  ([DESIGN.md §6/§8](DESIGN.md)) as the `is_staff`-gated cold-start curation surface (the
  same pattern identity-accounts used before its tooling existed — **no custom UI**; rich
  curation is `editorial-curation-tools`, ITX-5). Admin add/change/retire actions **route
  through `services.py`** so the same invariants (≥1 cluster, dedupe, safe retire) are
  enforced — the admin must **not** bypass the write service into the ORM.
- **Dependencies.** T-03.
- **Definition of done.**
  - `Tag`/`Cluster` appear in the admin; creating/editing/retiring through it goes via
    `services.py` (an admin edit that would orphan/duplicate raises the same error, not a
    silent bad write).
  - Test (or admin-action unit test) confirms an invariant-violating admin edit is refused.
- **Estimated size.** S.
- **Files/areas touched.** `apps/taxonomy/admin.py`,
  `apps/taxonomy/tests/test_admin.py`.

## T-09 — Author founding vocabulary & populate — AC3, AC4 (OQ-3 size band)
- **Description.** Author the real founding vocabulary into
  `apps/taxonomy/seed/vocabulary.yaml` for the beachhead niche **vibecoded webapps**
  (D-1): named clusters plus tags with human-readable labels and, where meaning isn't
  self-evident, short definitions (AC3), each tag in ≥1 cluster (AC5). **Decide the size
  band editorially here** (OQ-3 — DESIGN §12 leaves it to this stage, not a fixed number):
  enough tags to let users declare interests (AC3) and distinguish apps (AC4), without
  synonym bloat (R2 non-redundancy). Then run `seed_taxonomy` + `check_taxonomy` and
  confirm both green.
  - **Known deferral (record in [DECISIONS.md](DECISIONS.md) + [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)):**
    DESIGN §12 says size against "the real founding catalog," but **no app catalog exists
    yet** — it comes from `submission-intake`, which is downstream of this Phase-0
    foundation (D2 build order). So author against the **niche definition + representative
    app archetypes**; full **app-coverage measurement against a real submitted catalog is
    deferred** until catalog data exists, exactly as identity-accounts deferred live
    metrics (R1). Re-validate coverage when `submission-intake` lands. *This deferral is
    surfaced to the user in CONTROL — it does not block Stage 4.*
- **Dependencies.** T-06, T-07.
- **Definition of done.**
  - `vocabulary.yaml` holds the founding clusters + tags (labels + definitions where
    needed); `seed_taxonomy` applies it cleanly and `check_taxonomy` exits 0 (zero orphan
    active tags, no duplicate labels — AC5).
  - The chosen size band and its editorial rationale are recorded in
    [DECISIONS.md](DECISIONS.md) (closes OQ-3); the catalog-coverage deferral is recorded
    in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
  - A test asserts the shipped seed file applies idempotently and passes integrity (so the
    founding content can't rot silently).
- **Estimated size.** M.
- **Files/areas touched.** `apps/taxonomy/seed/vocabulary.yaml`,
  `apps/taxonomy/tests/test_founding_vocabulary.py`,
  `features/interest-taxonomy/DECISIONS.md`,
  `features/interest-taxonomy/OPEN_QUESTIONS.md`.

## T-10 — Docs, CODEMAP reconcile & cross-feature contract (D-5)
- **Description.** Finalize the operator/consumer docs and the durable channels:
  a README section for `apps/taxonomy/` (how to migrate, seed, check, and **read the
  vocabulary**); `.env.example` entries for any new tunable (`taxonomy_resolve_max_steps`);
  reconcile [CODEMAP.md](../../CODEMAP.md) so its taxonomy entries (`selectors` read
  surface, `services` write surface, the metric constants, the config tunable) match the
  shipped code exactly; and confirm the **cross-feature reference contract** is recorded as
  global **[D-5](../../DECISIONS.md)** ([DESIGN.md §11](DESIGN.md)) so `interest-profile`,
  `submission-intake`, and the matcher build on it: *store the `Tag.id` UUID (never the
  label); validate at the write boundary with `is_valid_tag`; resolve at read with
  `resolve_tag`*.
- **Dependencies.** all prior tasks.
- **Definition of done.**
  - README documents migrate → seed → check → read; `.env.example` covers every taxonomy
    tunable used in code.
  - CODEMAP reflects exactly the shared taxonomy surface that exists (no stale/missing
    entries).
  - [D-5](../../DECISIONS.md) is present and states the three-rule consumer contract; the
    rollout note (DESIGN §12) that consumers must adopt it before storing a reference is
    captured.
- **Estimated size.** S.
- **Files/areas touched.** `README.md`, `.env.example`, `CODEMAP.md`,
  `DECISIONS.md` (confirm/finalize D-5).

---

## Coverage check (Planner exit criterion — every design element appears in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §2 project layout / new `apps/taxonomy/` app | T-01 |
| §3 Tag model | T-02 |
| §3 Cluster model | T-02 |
| §3 Write service (single mutate path) | T-03 |
| §3 Read selectors (single read path) | T-04 |
| §3 Read API (thin projection) | T-05 |
| §3 Seed mechanism | T-06, T-09 |
| §3 Curation surface (Django admin) | T-08 |
| §4 data model: UUID PK, citext slug, normalized-label unique, status, `replaced_by` SET_NULL, M2M, `retired_at` | T-02 |
| §4 migration 0001 (tables only, citext, reversible) | T-02 |
| §4 lifecycle (retire-not-delete; ≥1 cluster invariant) | T-03 |
| §5a `list_active_tags`/`list_clusters`/`get_tag`/`is_valid_tag`/`resolve_tag` | T-04 |
| §5b `add/rename/retire_tag`, `add/rename_cluster`, `assign/remove_from_cluster`, `check_integrity` + 3 error types | T-03 |
| §5c JSON endpoints #1/#2/#3 + auth posture | T-05 |
| §6 seed file + `seed_taxonomy` (idempotent, no partial apply) | T-06 |
| §6 `check_taxonomy` | T-07 |
| §6 Django admin via services | T-08 |
| §7 shape (flat tags + clusters M2M) | T-02 |
| §7 stable identity (UUID; rename = label only) | T-02 (schema), T-03 (rename), T-04 (resolve) |
| §7 retire rule (soft-retire + successor, read-time resolve, cycle guard) | T-03 (retire), T-04 (resolve) |
| §9 perf (bounded scans, indexed lookups, prefetch, no N+1) | T-02 (indexes), T-04 (prefetch) |
| §9 security (single write path, admin-gated, no HTTP write, no PII) | T-03, T-05, T-08 |
| §9 observability (metric constants, `increment` reuse, `/health` reuse) | T-03 (constants+write counters), T-04 (`taxonomy_reference_break`), T-07 (`taxonomy_integrity_violation`) |
| §9 rollback (reversible migration, re-runnable seed) | T-02, T-06 |
| §10 failure modes (loud errors; resolve fallbacks; seed abort; empty-cluster warn) | T-03, T-04, T-06, T-07 |
| §11 cross-feature contract / D-5 | T-10 (+ supplied by T-04 `is_valid_tag`/`resolve_tag`) |
| §12 rollout (migrate → author seed → seed → check) | T-02, T-09 |
| §13 ≥1-cluster invariant enforced at write + verified | T-03 (enforce), T-07 (verify) |
| §13 slug-vs-UUID dual identity (UUID = reference) | T-02, T-04, T-10 |
| §14 all 8 ACs | AC1 T-03 · AC2 T-04/T-05 · AC3 T-09 · AC4 T-09 · AC5 T-02/T-03/T-07 · AC6 T-03/T-04 · AC7 T-02/T-04 · AC8 T-02 (clusters first-class; adjacency = future additive table) |

All design elements are covered; all tasks have a definition of done; no `L` tasks remain.

> **Note for Stage 4 (Senior Engineer):** the `TEST_PLAN.md` you produce must show every
> acceptance criterion (AC1–AC8) is exercised by the tests in these tasks — the AC→task row
> above is the starting map. **AC8 is a design-time guarantee** (clusters are first-class so
> adjacency is a future additive `taxonomy_cluster_adjacency` table over existing clusters);
> verify it by argument + schema review, not a runtime test. **One open item is handed to
> you in T-09:** author the founding vocabulary against the niche definition and record the
> size band (OQ-3); app-coverage against a *real* catalog is a recorded deferral, not a
> Stage-4 blocker (see CONTROL).
