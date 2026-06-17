# DESIGN — interest-taxonomy

*Stage 2 artifact (Software Architect). Status: **DRAFT — awaiting design approval (A5)**.
Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED A4), feature
[DECISIONS.md](DECISIONS.md) ITX-1…ITX-5, [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
(Q5/OQ-1/OQ-2/OQ-3), global [DECISIONS.md](../../DECISIONS.md) (D-1/D-2/D-3/D-4),
[CODEMAP.md](../../CODEMAP.md) (`apps/` shared surface from identity-accounts),
vision [§2.2/§5.4/§6](../../curated-app-platform-design.md). Produced by the 14-step
protocol in [phase-2-architect.md](../../process/personas/phase-2-architect.md).*

---

## 0. Reasoning trace (14-step protocol — condensed)

The protocol is the method; §1–§14 below are its output. Only the non-obvious steps are
recorded here; the rest are realized in the contract sections.

1. **SCOPE.** Provide the *one* shared controlled vocabulary (tags + clusters) that both a
   user's interests and an app's subject matter are written in, so every matching surface
   compares them in one language. Lifespan = **platform** (cross-feature substrate every
   downstream feature reads). OUT (re-stated from the brief): user interest *selection* &
   storage (`interest-profile`), app *tagging* (`submission-intake`), the matching/ranking
   algorithm, cluster *adjacency*/rings, a multi-niche ontology, folksonomy, localization,
   per-tag weighting, and the *rich* curation UI (`editorial-curation-tools`).
2. **REQUIREMENTS.** Functional = AC1–AC8. Non-functional = D-2 (no hard targets, but must
   hold at 100× or document the bounded trade-off). The four open items handed from Stage 1
   are resolved here: **Q5/OQ-1 taxonomy shape** (→ §3/§4/§7 flat tags + named clusters via
   M2M), **OQ-1 management surface** (→ §6 seed file + command + Django admin, no custom
   UI), **OQ-2 retire rule** (→ §4/§7 soft-retire + optional successor, non-destructive),
   **OQ-3 size band** (→ §12/§13, an editorial Stage-4 call against the founding catalog,
   not fixed here).
3. **CONTEXT.** **Not greenfield.** `identity-accounts` established the stack (D-4), the
   shared-code root `apps/`, the `apps/core/` cross-cutting surface, and the `admin` role +
   fail-closed gate (`HasRole`/`require_role`). This feature **reuses** all of them (no new
   stack decision) and adds a new Django app `apps/taxonomy/`. The only genuinely new global
   thing is the *cross-feature tag-reference contract* (→ new global **D-5**), because
   `interest-profile`, `submission-intake`, and the matcher must not contradict it.
8. **CHANGE.** Most-likely-to-change = the *content* (which tags/clusters exist) and the
   *size band* → both live in an editable **seed file**, never in code or schema. Named
   future change = **cluster adjacency** (AC8) → isolated as a future `ClusterAdjacency`
   table referencing existing `Cluster` rows; adding it touches no tag, no membership, no
   stored downstream reference. Irreversible = the **stable tag identity = UUID** contract
   (§4/§5) — justified with extra rigor because every downstream stored reference depends
   on it.
9. **TRADE-OFFS.** Two genuine forks decided below: **taxonomy shape** (flat-tags+clusters
   vs single-cluster-FK vs arbitrary tag hierarchy — §7/§13) and **retire rule** (soft-
   retire+successor vs hard-delete vs reference-rewrite — §7/§13). The chosen design
   **sacrifices** automatic synonym detection (editorial discipline + unique-key constraints
   instead) and a rich curation UI now (command + Django admin instead).
13. **SELF-CRITIQUE.** See §13 — the sharp edges are the slug-vs-UUID dual identity, the
    "≥1 cluster" invariant that no single DB constraint can express, and the decision to ship
    *no* dedicated audit table. Each is resolved or explicitly handed downstream.

---

## 1. Current-state summary

The repository is **no longer greenfield**. `identity-accounts` (released local/dev) has
established, and this feature builds on rather than re-derives:

- **Stack (global D-4):** Python 3.12+ / Django 5.x / DRF / PostgreSQL; shared-code root
  `apps/`; server-rendered pages where a surface needs UI.
- **`apps/core/`** cross-cutting surface this feature reuses verbatim:
  `observability.increment(...)` + `check_health()` (§9), the `config.py` typed-tunable
  pattern, and the structured-logging middleware. No duplication of these.
- **`apps/accounts/`** identity + authorization: the `admin` role and the **single
  fail-closed gate** — `HasRole(ADMIN)` (DRF) and `require_role(ADMIN)` (views) — plus the
  `is_staff` Django-admin surface. Curation authority in this feature is **exactly** that
  `admin` role (brief constraint, D-3); no new auth path is introduced.

This design therefore **adds one new Django app, `apps/taxonomy/`**, and **modifies no
existing component**. Its new outputs — the vocabulary data model and a small read/validate/
resolve contract — become the substrate `interest-profile`, `submission-intake`,
`editorial-curation-tools`, and the future matcher all read from.

---

## 2. Tech stack & project layout  *(reuses global D-4 — no new stack decision)*

The stack is fixed by **[D-4](../../DECISIONS.md)** and is **not** re-decided here (the
persona requires a stack decision only where one is needed; this feature inherits it). The
one global-worthy decision this feature *does* introduce — the cross-feature tag-reference
contract and taxonomy shape — is logged as new global **[D-5](../../DECISIONS.md)**.

**Project layout** (new app under the existing `apps/` root):

```
apps/                          ← SHARED-CODE ROOT (unchanged; D-4)
  core/                        ← reused as-is (observability, config pattern, middleware)
  accounts/                    ← reused as-is (admin role + HasRole/require_role gate)
  taxonomy/                    ← THIS feature (new Django app)
    models.py                  ← Tag, Cluster (+ Tag↔Cluster M2M)
    services.py                ← the single WRITE path: add/rename/retire, clustering
    selectors.py               ← the single READ path: list/get/validate/resolve  (shared)
    serializers.py             ← DRF read shapes (tags, clusters)
    views.py / urls.py         ← read API (§5c) — list tags/clusters, get tag
    admin.py                   ← Django-admin registration (cold-start curation surface)
    apps.py                    ← AppConfig
    seed/
      vocabulary.yaml          ← the authoritative founding vocabulary (editable data)
    management/commands/
      seed_taxonomy.py         ← idempotent apply of seed/vocabulary.yaml (§6)
      check_taxonomy.py        ← integrity check: no orphan active tags, etc. (AC5)
    migrations/0001_initial.py ← create tables (NO content — content lives in the seed file)
```

The **(shared)** items — the read/validate/resolve selectors and the role-gated write
services — are the cross-feature reusable surface this feature publishes; they are registered
in [CODEMAP.md](../../CODEMAP.md) by the Engineer in Stage 4 when the code exists (per the
CODEMAP maintenance rule).

---

## 3. Proposed architecture (components & responsibilities)

Each component has one responsibility, is testable in isolation, and depends only toward more
stable components (`models` ← `services`/`selectors` ← `views`). **Writes go through exactly
one path (`services.py`); reads through exactly one path (`selectors.py`)** — the same
single-write-path discipline `apps/accounts/services.py` uses for role changes.

| Component | Owns (single responsibility) | Exposes | Hides |
|-----------|------------------------------|---------|-------|
| **Tag model** (`taxonomy.models.Tag`) | One unit of interest vocabulary: stable identity, display label, optional definition, lifecycle state, optional successor. | `Tag` ORM model; `id` (UUID, the cross-feature reference), `slug`, `label`, `definition`, `status`, `replaced_by`, `clusters` (M2M). | Storage, normalization details. |
| **Cluster model** (`taxonomy.models.Cluster`) | A named grouping of related tags (AC5); the day-one anchor for future adjacency (AC8). | `Cluster` ORM model; `id` (UUID), `slug`, `name`, `description`; `tags` (reverse M2M). | — |
| **Write service** (`taxonomy.services`) | The **only** way the vocabulary changes: add/rename/retire tags, add/rename clusters, (un)assign membership — each validated, atomic, counted. Enforces invariants (≥1 cluster, non-redundancy, safe retire). | `add_tag`, `rename_tag`, `retire_tag`, `add_cluster`, `rename_cluster`, `assign_to_cluster`, `remove_from_cluster`, `check_integrity`. | Transaction handling; invariant enforcement; observability emits. |
| **Read selectors** (`taxonomy.selectors`) | The **one** read/validate/resolve surface every consumer (in-process and HTTP) calls. | `list_active_tags()`, `list_clusters()`, `get_tag(id)`, **`is_valid_tag(id) -> bool`** (AC2), **`resolve_tag(id) -> Tag`** (AC6/AC7 + successor remap). | Status filtering, successor-chain resolution + cycle guard. |
| **Read API** (`taxonomy.views`/`urls`/`serializers`) | HTTP/JSON projection of the selectors for out-of-process consumers / the eventual SPA. | `GET /taxonomy/tags`, `GET /taxonomy/tags/{id}`, `GET /taxonomy/clusters`. | Serialization only; no business logic (delegates to selectors). |
| **Seed mechanism** (`seed/vocabulary.yaml` + `seed_taxonomy`) | The authoritative, editable initial/maintained vocabulary content and its idempotent application (OQ-1). | `manage.py seed_taxonomy`. | Upsert-by-slug logic; calls the write service, never the ORM directly. |
| **Curation surface** (Django admin) | Cold-start ad-hoc edits before `editorial-curation-tools` exists — boring, built-in, `is_staff`-gated. | Registered `Tag`/`Cluster` admin. | — (no custom UI; that is `editorial-curation-tools`). |

**Coupling check.** Every component is replaceable behind its exposed surface: the read API is
a thin projection of `selectors` (swap transport freely); the seed file format is isolated
behind `seed_taxonomy` (swap YAML→JSON with no caller change); the write service is the only
mutator, so invariants live in one place. Cross-cutting concerns are reused, not duplicated:
**authorization** = the accounts `admin` gate; **observability/logging** =
`apps.core.observability`; **config** = the `apps.core.config` typed-tunable pattern.

---

## 4. Data design

One source of truth per fact. UUID primary keys (the platform convention from D-4; no
sequential enumeration). **The UUID `id` is the stable cross-feature reference (AC7).**

### `taxonomy_cluster`  (owns a named grouping of tags)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | Stable cluster reference; the future `ClusterAdjacency` rows (AC8) point here. |
| `slug` | citext, **unique**, immutable | Natural key for idempotent seeding/admin; never renamed (rename = change `name`). |
| `name` | varchar(80) | Display label; renameable (cluster analog of AC6). |
| `description` | text, blank | Optional short definition (editorial consistency, R5). |
| `created_at` / `updated_at` | timestamptz | Lifecycle. |

### `taxonomy_tag`  (owns one vocabulary unit)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | **The stable cross-feature reference** every downstream feature stores (AC7, R4). |
| `slug` | citext, **unique**, immutable | Natural key for seeding/admin/logs; **not** the downstream reference (see §7/§13); changing meaning = retire + new tag, never re-slug. |
| `label` | varchar(80), **unique (normalized)** | Human-readable display (AC3); **renameable** (AC6) — rename changes only this. Uniqueness on a normalized form prevents duplicate labels (AC1, R2). |
| `definition` | text, blank | Short meaning where not self-evident (AC3, R5). |
| `status` | enum(`active`,`retired`) | `active` = offered for new selection/labelling; `retired` = no longer offered (AC6). |
| `replaced_by` | FK → `Tag`, nullable, `SET_NULL` | Optional successor when a tag is retired *into* another (merge/de-dupe, AC1/OQ-2). NULL ⇒ retired-but-kept. |
| `created_at` / `updated_at` | timestamptz | Lifecycle. |
| `retired_at` | timestamptz, nullable | Set when `status`→`retired`; NULL while active. |

### `taxonomy_tag_clusters`  (M2M membership — Django through table)
`Tag.clusters = ManyToManyField(Cluster, related_name="tags")`. **Every *active* tag belongs
to ≥1 cluster (AC5)**; "one or more" per the brief, hence M2M, not a single FK. Unique
`(tag, cluster)` (Django default).

### Future (NOT created now) — `taxonomy_cluster_adjacency`  *(AC8 extension point)*
Documented, not built: a future table `(cluster_a_id, cluster_b_id, …)` over **existing**
`Cluster` rows. Adding it is a **purely additive migration** that touches no `Tag`, no
membership, and **no stored downstream reference** — so ring-based expansion arrives with **no
destructive migration and no re-tagging** (AC8). This is the structural payoff of making
clusters first-class from day one (ITX-2).

**Lifecycle.**
- *Cluster:* created → renamed (display) → may become empty if all its tags retire (allowed,
  flagged by `check_taxonomy`, never auto-deleted — deletion would be destructive).
- *Tag:* created `active` (in ≥1 cluster) → renamed (label only) → `retired` (kept, optionally
  with `replaced_by`). A tag row is **never hard-deleted** while any downstream reference could
  exist — retire, don't delete (this is what guarantees reference-break-rate = 0).

**One source of truth.** The vocabulary *content* lives in the DB (the authoritative set); the
**seed file is the source for the *initial/curated* content**, applied idempotently — it is
not a second live copy (the command upserts, then the DB is canonical). "What a tag *means
now*" is resolved in exactly one place: `selectors.resolve_tag` (§5a).

**Concurrency.** Curation is low-frequency, admin-only, single-writer in practice; each service
operation is wrapped in `transaction.atomic()`. Idempotent upsert-by-slug makes a re-run of
`seed_taxonomy` safe. No optimistic-locking machinery is added (no concurrent-editor
requirement at MVP — a bounded, documented choice).

**Crash/restart.** All state is DB-backed; no in-memory vocabulary cache that could drift. (A
read cache is a later, optional optimization, not needed at MVP scale — §9.)

**Migration/retention.** Migration 0001 creates the three tables only. **Vocabulary content is
applied by `seed_taxonomy` from the versioned seed file — deliberately *not* a data
migration** (§6/§13), so editorial content evolves without schema churn. Retention: tags are
retained (retired, never dropped) precisely so downstream references stay valid.

---

## 5. Interface contracts

Two consumer surfaces over **one** logic core (`selectors` for reads, `services` for writes).
In-process consumers (matcher, anything in the monolith) call the Python functions directly;
out-of-process consumers / a future SPA call the JSON API. Both share the same core, so there
is no second source of truth.

### 5a. Python read contract (`apps.taxonomy.selectors`) — the cross-feature substrate

```python
def list_active_tags() -> list[Tag]: ...        # status == active, clusters prefetched
def list_clusters() -> list[Cluster]: ...        # each with its active tags
def get_tag(tag_id: UUID) -> Tag | None: ...     # any status; None if absent
def is_valid_tag(tag_id: UUID) -> bool: ...      # AC2: True only for an existing ACTIVE tag
def resolve_tag(tag_id: UUID) -> Tag | None: ... # AC6/AC7: follow replaced_by to the active
                                                 # successor (cycle-guarded); a retired tag
                                                 # with no successor resolves to ITSELF
                                                 # (kept, never dropped); None only if the id
                                                 # never existed.
```

**Invariants (illegal states unrepresentable / enforced at the boundary):**
- **Stable identity:** a stored reference is a `Tag.id` (UUID). A rename changes `label` only,
  so the reference always resolves (AC7). `resolve_tag` **never returns None for a real id**
  and **never rewrites** the caller's stored value → reference-break-rate = 0.
- **Closed set (AC2):** `is_valid_tag` is the validator consumers call at their write
  boundary; an off-vocabulary value is rejected by *them* using it (this feature supplies the
  validator, the consumer enforces — mirroring `HasRole`).
- **≥1 cluster per active tag (AC5):** enforced by the write service (§5b) and asserted by
  `check_taxonomy`; never representable as "active + zero clusters" after a service call.
- **Tags confer description, never visibility/position** (vision §5.6 fairness) — nothing in
  this feature is read by any ranking path; enforced by convention + review.

### 5b. Python write contract (`apps.taxonomy.services`) — admin-only, single mutate path

```python
def add_tag(slug, label, *, clusters: list[Cluster], definition="") -> Tag
def rename_tag(tag, *, label: str) -> Tag                 # display only; id/slug unchanged (AC6)
def retire_tag(tag, *, replaced_by: Tag | None = None) -> Tag   # status→retired (AC6/OQ-2)
def add_cluster(slug, name, *, description="") -> Cluster
def rename_cluster(cluster, *, name: str) -> Cluster
def assign_to_cluster(tag, cluster) -> None
def remove_from_cluster(tag, cluster) -> None             # refuses if it would orphan an active tag
def check_integrity() -> IntegrityReport                  # AC5: orphans, empty clusters, dup labels
```

Errors (raised loudly, never swallowed): `DuplicateTagError` (slug or normalized-label
collision — AC1/R2), `OrphanTagError` (would leave an active tag in zero clusters — AC5),
`RetireSuccessorError` (successor missing/retired/would form a cycle — OQ-2). Each write is
`transaction.atomic()` and emits an observability counter.

### 5c. JSON read API (DRF) — for out-of-process consumers

| # | Endpoint | Auth | Success | Errors |
|---|----------|------|---------|--------|
| 1 | `GET /taxonomy/tags` | session (any role) | `200 [{id, slug, label, definition, clusters:[{id,slug,name}]}]` — **active tags only** | `401` |
| 2 | `GET /taxonomy/tags/{id}` | session | `200 {id, slug, label, definition, status, replaced_by, clusters:[…]}` — any status (lets a consumer render a retired/remapped reference) | `401` · `404` unknown id |
| 3 | `GET /taxonomy/clusters` | session | `200 [{id, slug, name, description, tags:[{id,label}]}]` (active tags) | `401` |

**Auth posture.** Reads require an authenticated session (DRF default `IsAuthenticated`,
inherited from D-4) but **no special role** — any signed-in user may read the vocabulary to
pick interests. **Writes are not exposed over HTTP at MVP** (curation = command + Django admin,
§6); when `editorial-curation-tools` adds a write API it will gate it with `HasRole(ADMIN)` and
call `services.py`. If a *public* (anonymous) read surface is later needed (e.g. public app
pages), relaxing endpoint #1/#3 to `AllowAny` is a one-line change — noted, not built (no
speculative abstraction).

**Evolution without breaking consumers.** The cross-feature contract is intentionally tiny:
**`Tag.id`** (the reference), **`is_valid_tag` / `resolve_tag` / `list_active_tags`**, and the
JSON shapes above. New fields are additive; new lifecycle (e.g. adjacency) is a new endpoint,
never a change to these. The JSON shapes are URL-prefix-versionable if ever needed.

---

## 6. Management surface — seed file + command + Django admin  *(resolves OQ-1)*

The brief scopes the **vocabulary + lifecycle rules** here and the **rich curation UI** to
`editorial-curation-tools` (ITX-5), mirroring how identity-accounts owns the admin *role* but
not the admin *tooling*. The MVP seed/maintain mechanism is therefore deliberately minimal and
reuses existing surfaces — **no custom curation UI is built here**:

1. **Authoritative seed file** — `apps/taxonomy/seed/vocabulary.yaml`, a human-editable,
   version-controlled declaration of the founding vocabulary (clusters, then tags with their
   slug/label/definition/cluster-membership). This **is** the "defined initial tag set"
   deliverable (brief In-Scope), and the maintenance channel until richer tooling exists.
2. **`manage.py seed_taxonomy`** — applies the file **idempotently** by upsert-on-`slug`:
   inserts new clusters/tags, updates labels/definitions/membership for existing ones, and runs
   `check_integrity` at the end inside one transaction (no partial apply). It calls
   `services.py` (never the ORM directly), so every invariant is enforced uniformly.
   Retirements are **explicit** (a tag marked retired in the file, or a `retire_tag` admin
   action) — the seeder never deletes a tag that drops out of the file (that would risk silent
   reference breakage; AC6).
3. **Django admin** (`apps/taxonomy/admin.py`) — the `is_staff`/admin-gated built-in surface for
   ad-hoc cold-start edits, exactly as identity-accounts leaned on Django admin before its
   tooling existed. Admin actions route through `services.py` so they enforce invariants.

This keeps the feature's surface area focused on the *substrate*; the elaborate editor UX is
`editorial-curation-tools` (out of scope, ITX-5).

---

## 7. Tag identity, clustering & the retire rule  *(resolves Q5/OQ-1 shape + OQ-2)*

**Shape (Q5/OQ-1):** **flat tags + named clusters joined by a many-to-many membership.** No
tag→tag parenting. Clusters are a separate grouping dimension (a tag may sit in one *or more*
clusters, per the brief). This is "flat-to-shallow with clusters" made concrete, and it is the
shape that makes **AC8 cheap**: adjacency is a *cluster-to-cluster* relation, so it is added as
a new table over existing clusters with zero impact on tags, membership, or stored references.
(Alternatives — single-cluster FK, arbitrary tag hierarchy — rejected in §13.)

**Stable identity (AC7/R4):** the **UUID `id` is the cross-feature reference**; downstream
features store it and never store the label. A `slug` (immutable, unique) also exists but is an
**internal** natural key for seeding/admin/logs only — *not* the downstream reference (§13
explains why one canonical reference is kept). A rename changes `label` only ⇒ every stored
reference stays valid.

**Retire rule (OQ-2/AC6) — soft-retire + optional successor, non-destructive:**
- **Default = keep.** Retiring sets `status=retired` + `retired_at`. The tag stops being
  offered (`list_active_tags`/`is_valid_tag` exclude it) but the **row stays**, so existing
  references still resolve (kept, not dropped).
- **Merge/de-dupe = remap.** When a tag is retired *because it duplicates/merges into* another
  (AC1 non-redundancy), the editor sets `replaced_by` to the successor. `resolve_tag` then
  returns the active successor for that id.
- **Non-destructive everywhere.** Remapping happens at **read time in `resolve_tag`** — it
  **never rewrites** the references stored in `interest-profile`/`submission-intake` (data this
  feature does not own). So a retire/merge invalidates **zero** stored references
  (reference-break-rate = 0, the brief's core safety metric). Cycle/forward-chains in
  `replaced_by` are guarded (resolve walks at most N steps, then logs loudly and returns the
  last good tag).

Resolution lives in exactly one place (`resolve_tag`), so "what this tag id means now" has a
single source of truth.

---

## 8. UX flow

This feature has **no end-user screens of its own**. It exposes data (JSON read API §5c) and a
curation surface (Django admin §6). The user-facing *picker* (interest-profile) and *app
tagging UI* (submission-intake) are owned elsewhere and render **from** `list_active_tags`. The
only human surface here is the admin/staff curation via Django admin — its states are
Django-admin's standard list/add/change/error views; no custom states are introduced.

---

## 9. Non-functional handling

**Performance / scale.** All reads are bounded scans over a small, curated table (tens to
low-hundreds of tags at MVP — OQ-3) with prefetch of cluster membership; all validation is an
indexed point lookup on the UUID PK or unique `slug`/`label`. No O(n²), no in-memory state. At
100× (many niches, a far larger tag space — CLAUDE.md §5.2) the same shape holds: a per-niche
scope filter and an optional cached `list_active_tags` projection are the documented growth
path — a **deliberate, bounded** choice not built now (no current niche-scoping requirement;
D-1 is single-niche). Recorded rather than pre-built (§5.5).

**Security (threat model).**
- *Unauthorized curation / privilege escalation:* every write goes through `services.py`,
  reachable only via the `is_staff`/`admin`-gated Django admin (and, later, an
  `HasRole(ADMIN)`-gated tooling API). There is **no** self-serve vocabulary write and **no**
  HTTP write endpoint at MVP. Reuses the accounts fail-closed gate; no new auth path.
- *Injection / bad input:* labels/definitions are validated and length-bounded at the service
  boundary; the seed command validates the file and fails loudly on a malformed entry (no
  partial apply).
- *Data leakage / PII:* the vocabulary contains **no PII** — only editorial labels. Read
  endpoints expose only public vocabulary terms.
- *Attributability:* lifecycle changes are counted via observability and captured by Django
  admin's built-in `LogEntry` (who changed what in the admin). A dedicated append-only audit
  table is **not** added at MVP (§13 — deferred to `editorial-curation-tools`, which owns rich
  curation + its audit).

**Observability.** Reuses `apps.core.observability.increment`. New metric-name constants map
1:1 to the brief's enabler metrics: `taxonomy_tag_added`, `taxonomy_tag_renamed`,
`taxonomy_tag_retired`, `taxonomy_reference_break` (must stay **0** — alert on any nonzero),
`taxonomy_integrity_violation` (orphan active tag / duplicate label — from `check_taxonomy`),
plus health via the existing `/health` (DB reachability already covers this app's store).
**Actionable alerts only:** any `taxonomy_reference_break`, any `taxonomy_integrity_violation`.

**Rollback.** New, additive app with no live downstream consumer yet → nothing to feature-flag
*off*. Safety = **reversible migration** (`migrate taxonomy zero` drops the three tables) + the
seed being re-runnable. A bad release is rolled back by reverting the deploy and, if needed, the
last migration.

---

## 10. Failure modes (detection → response, never silent)

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| Read selectors | DB down/slow | exception/timeout | Fail loud (`500` on the API; exception in-process) — never return a partial/empty vocabulary that would look like "no tags". |
| `is_valid_tag` | id not in vocab / retired | point lookup | Returns **False** → the *consumer* rejects the off-vocabulary value at its boundary (AC2). Never coins a tag. |
| `resolve_tag` | retired-no-successor | status check | Returns the **tag itself** (kept, never dropped) — reference stays valid (AC6/AC7). |
| `resolve_tag` | `replaced_by` cycle/long chain | step counter | Stops at N steps, **logs loudly**, returns last good tag; counts `taxonomy_reference_break` for alerting. Never loops. |
| Write service | duplicate slug/label | unique constraint / normalized check | Raise `DuplicateTagError` → editor sees it (AC1/R2); nothing written. |
| Write service | would orphan an active tag | pre-check in `remove_from_cluster`/`retire` | Raise `OrphanTagError`; refuse (AC5). |
| `seed_taxonomy` | malformed file / bad reference | parse + `check_integrity` in one txn | Abort whole run, report the offending entry; **no partial apply**. |
| Cluster | emptied by retirements | `check_taxonomy` | **Flag** (warn), never auto-delete (deletion would be destructive — AC8 keeps clusters stable). |

---

## 11. Cross-feature contract handed downstream  *(R4 safety, AC2/AC7)*

Recorded as global **[D-5](../../DECISIONS.md)** so `interest-profile`, `submission-intake`,
and the matcher build on it consistently:

- **Store the `Tag.id` (UUID), never the label.** This is the only durable reference.
- **Validate at your write boundary with `is_valid_tag(id)`** — reject off-vocabulary input
  (AC2); do not coin tags.
- **Resolve at read with `resolve_tag(id)`** to follow renames (transparent) and retire/merge
  successors (OQ-2) — and to render retired references rather than dropping them.
- **Cluster membership** (`list_clusters` / a tag's `clusters`) is the substrate the matcher
  uses for same-cluster fallback (AC5) and that future ring expansion grows over (AC8).

A downstream feature that dereferences a tag by label string, or hard-copies a label into its
own store, would **break** the safety contract — flagged here so it is not done.

---

## 12. Rollout strategy

Additive new app; first consumer (`interest-profile`/`submission-intake`) ships later, so there
is no backward-compat burden and no flag to protect a pre-existing surface:

1. Apply migrations (`migrate taxonomy`) — creates `taxonomy_cluster`, `taxonomy_tag`, and the
   M2M table. No content.
2. Populate the founding vocabulary: author `seed/vocabulary.yaml` against the **real founding
   catalog** (so app-coverage/user-coverage are met, R1) and run `manage.py seed_taxonomy`.
   (The concrete size/band — OQ-3 — is decided here, editorially, with the catalog in view; it
   is **not** a fixed number in this design.)
3. Verify with `manage.py check_taxonomy` (zero orphan active tags, no duplicate labels).
4. No recurring job is scheduled (unlike token purge — nothing expires here).

Rollback = revert deploy + `migrate taxonomy zero`. **Handed downstream:** consumers must adopt
the §11 contract before they store any tag reference.

---

## 13. Self-critique & alternatives

**Attacks on the design and resolutions:**
- *"Slug **and** UUID is two identities — which is the source of truth?"* Resolved by rule: the
  **UUID is the only cross-feature reference**; the slug is an *internal* immutable natural key
  whose sole jobs are idempotent seeding and human-readable admin/logs. Downstream never stores
  the slug. The small redundancy is justified — a hand-curated seed file needs a human key for
  idempotency; UUIDs in YAML would be unmaintainable. Stated explicitly so it isn't misused (§7).
- *"'Every active tag in ≥1 cluster' isn't a single DB constraint."* True — a `≥1` M2M
  cardinality can't be one column constraint. Handled the boring way: the **write service**
  enforces it on every mutation (add requires clusters; remove/retire refuse to orphan), and
  **`check_taxonomy`** asserts it as a CI/ops check. Invariant held at the only write path +
  verified, rather than pretended in the schema.
- *"No audit table for a curated, consequential vocabulary?"* Deliberate MVP simplification:
  lifecycle **state + timestamps** live on the rows (the source of truth for the safety
  properties), changes are **counted** via observability, and Django admin's `LogEntry` records
  who-did-what in the admin. A rich append-only audit belongs with the rich curation UX in
  `editorial-curation-tools` (ITX-5); adding one here would be speculative (§5.5). Flagged for
  revisit when that feature lands.
- *"Read-time `resolve_tag` adds a lookup on every dereference."* Accepted at MVP scale (small
  table, indexed PK). It is the price of **reference-break-rate = 0** without rewriting data
  this feature doesn't own — the right trade (the brief's core safety metric). A cached
  projection is the documented growth path (§9), not built now.
- *Simplification pass:* dropped a dedicated audit table, dropped any niche-scoping column (D-1
  single niche; added when a second niche is real), dropped tag→tag hierarchy, dropped an
  in-memory cache. Nothing remaining is untied to an AC.

**Alternatives considered (full rationale → DECISIONS):**
- *Shape — single-cluster FK on Tag:* simpler, but the brief requires "one **or more** clusters"
  (In-Scope, AC5) and a single FK forecloses a tag spanning clusters; rejected.
- *Shape — arbitrary tag→tag hierarchy:* over-scope (R2); adjacency in the vision is a
  *cluster*-level relation, not a tag tree, so a tag hierarchy buys nothing AC8 needs and adds
  traversal complexity; rejected.
- *Retire — hard-delete the tag:* breaks every stored reference (violates AC6/AC7,
  reference-break-rate > 0); rejected.
- *Retire — rewrite downstream references on merge:* would touch `interest-profile`/
  `submission-intake` tables this feature doesn't own and momentarily break references; rejected
  in favor of non-destructive read-time resolution.
- *Seed — bake vocabulary into a data migration:* couples editorial content to schema migrations
  and makes routine label edits a migration; rejected — vocabulary is **data**, so it lives in a
  re-runnable seed file (§6).

**What the chosen design sacrifices:** automatic synonym/near-duplicate detection (relies on
unique slug + normalized-label uniqueness + editorial discipline + the non-redundancy check, not
fuzzy matching); a rich curation UI now (command + Django admin instead); a per-dereference
`resolve_tag` lookup (vs a cache) — all bounded, documented trade-offs.

---

## 14. Traceability — every acceptance criterion maps to a design element

| AC | Design element(s) |
|----|-------------------|
| **AC1** Single authoritative, non-redundant set | `taxonomy_tag` unique `slug` + normalized-`label`; `services.add_tag` raises `DuplicateTagError`; `check_taxonomy` duplicate report (§4/§5b/§10) |
| **AC2** Closed set; off-vocabulary rejected | `selectors.is_valid_tag` (active-only) — the validator consumers enforce at their boundary; no write path coins tags (§5a/§11) |
| **AC3** User coverage; clear labels + definitions | `Tag.label` + `Tag.definition`; `list_active_tags` feeds the picker; size authored against the catalog (§4/§6/§12) |
| **AC4** App coverage; adequate tags | Founding `seed/vocabulary.yaml` authored against the real catalog (R1); app-coverage check at seed time (§6/§12) |
| **AC5** Every tag in ≥1 cluster; related grouping | `Tag.clusters` M2M; service enforces ≥1 on add/remove/retire; `check_taxonomy` asserts zero orphans (§4/§5b/§7/§10) |
| **AC6** Safe rename + retire (defined rule) | `rename_tag` (label only); `retire_tag` soft-retire + optional `replaced_by`; `resolve_tag` keeps/remaps, never drops (§7) |
| **AC7** Stable identity across rename | UUID `id` is the reference; rename changes `label` only; `resolve_tag` always resolves a real id (§4/§5a/§7/§11) |
| **AC8** Adjacency addable without destructive migration | Clusters first-class from day one; adjacency = future `taxonomy_cluster_adjacency` over existing `Cluster` rows — additive, no re-tag (§4/§7) |

Every component's failure behavior is documented in §10; no contract above contains "TBD".
