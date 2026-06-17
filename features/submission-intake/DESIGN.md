# DESIGN — submission-intake

*Stage 2 artifact (Software Architect). Status: **APPROVED 2026-06-17** (D-6 recorded global; → Stage 3-plan).
Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED A-SI), feature
[DECISIONS.md](DECISIONS.md) SI-1…SI-7, [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
(OQ-2 gate wording, OQ-3 media limits), global [DECISIONS.md](../../DECISIONS.md)
(D-1/D-2/D-3/D-4/D-5), [CODEMAP.md](../../CODEMAP.md) (the `apps/` shared surface from
`identity-accounts` + `interest-taxonomy`), vision
[§2.1/§5.5/§5.6/§6](../../curated-app-platform-design.md). Produced by the 14-step protocol
in [phase-2-architect.md](../../process/personas/phase-2-architect.md).*

---

## 0. Reasoning trace (14-step protocol — condensed)

The protocol is the method; §1–§14 are its output. Only the non-obvious steps are recorded
here; the rest are realized in the contract sections.

1. **SCOPE.** Give a developer one free, standardized way to submit a web app and run it
   through an **objective** quality gate, producing an owned, correctly-tagged, accepted app
   downstream features consume. Lifespan = **platform** (the catalog is the substrate every
   Phase-1 feature reads). OUT (re-stated from brief): public app-page rendering (`app-pages`),
   matching/digest assembly, signal capture, the Quality Score / any taste judgement, versioned
   updates + re-boost, automated malware/dup/uptime detection, team ownership, paid tiers, the
   vocabulary itself, the role grant.
2. **REQUIREMENTS.** Functional = AC1–AC9. Non-functional = D-2 (no hard targets, but hold at
   100× or document the bounded trade-off); manual review at founding volume (SI-2); web-only
   (SI-1); individual ownership (SI-4). The two open items handed from Stage 1 are resolved
   here: **OQ-2 gate wording** (→ §6, a fixed five-criterion enum + reviewer-facing checklist
   text in one module) and **OQ-3 media slots/limits** (→ §4/§9, concrete limits set here and
   published as the contract `app-pages` adopts).
3. **CONTEXT.** **Not greenfield.** `identity-accounts` (D-4) established the stack, the `apps/`
   root, `apps/core/` (observability, config, email, ratelimit), and the `developer`/`admin`
   roles + the single fail-closed gate (`HasRole`/`require_role`). `interest-taxonomy` (D-5)
   published the tag substrate (`is_valid_tag`/`resolve_tag`/`list_active_tags`, `Tag.id`). This
   feature **reuses all of them** and adds one new Django app, `apps/catalog/`. The one
   global-worthy new thing is the *catalogued-app cross-feature contract* (→ proposed global
   **D-6**), because `app-pages`, `editorial-curation-tools`, `signal-capture`, and
   `developer-dashboard` must not contradict it.
5. **INTERFACES.** Two consumer surfaces (developer self-serve + admin review) over one logic
   core (`services` writes, `selectors` reads), mirroring the taxonomy split. The gate is the
   sharp contract: a **fixed** set of objective floors with **no "other/quality" option**, so a
   taste rejection (R1/AC6) is *unrepresentable* in the decision shape, not merely discouraged.
6. **DATA & STATE.** One `App` row per submitted app carries its lifecycle `status` (one source
   of truth for "where it is"); an append-only `ReviewDecision` log is the source of truth for
   "what the gate said." They cannot drift because the only transitions into `accepted`/
   `rejected` are the same service calls that write the decision atomically.
9. **TRADE-OFFS.** Five genuine forks decided in §13: **App-as-submission single entity** vs
   separate App+Submission; **soft tag reference (UUID + `is_valid_tag`)** vs hard M2M FK;
   **gate as fixed code enum** vs editable criteria table; **re-review on any accepted-app edit**
   vs edit-in-place; **local Django file storage** vs external object store now.
10. **SECURITY.** Submit/edit/withdraw require the `developer` role **and** ownership (owner-
    scoped queries → 404 on someone else's app, no enumeration); review requires `admin`. URLs
    and uploaded images are validated at the trust boundary (fail loud). No payment/tier/priority
    field exists anywhere — the unfair state (AC3) is unrepresentable.
13. **SELF-CRITIQUE.** See §13 — the sharp edges are the App/Submission collapse, the soft tag
    reference without a DB FK, the conservative "re-review on edit" rule, and account-deletion
    cascade. Each is resolved or explicitly flagged to revisit with real data.

---

## 1. Current-state summary

The repository is **not greenfield**. This feature builds on, and does not re-derive:

- **Stack (global D-4):** Python 3.12+ / Django 5.x / DRF / PostgreSQL; shared root `apps/`;
  server-rendered Django templates for human flows, DRF JSON for machine/SPA consumers.
- **`apps/core/`** reused verbatim: `observability.increment` + `check_health` (§9), the
  `config.py` typed-tunable pattern (§9), the **`email.py` `EmailSender`** seam for the decision
  notification (§5/AC7 — reused, not rebuilt), `ratelimit.rate_limited`, and the request-context
  logging middleware.
- **`apps/accounts/`** reused verbatim: the `Account` identity (the ownership FK target), and the
  **single fail-closed gate** — `HasRole(DEVELOPER)`/`require_role(DEVELOPER)` for submit/own,
  `HasRole(ADMIN)`/`require_role(ADMIN)` for review. No new auth path is introduced.
- **`apps/taxonomy/`** reused verbatim: `selectors.is_valid_tag(id)` at the tag write boundary
  (AC4) and `selectors.resolve_tag(id)` at read (AC9) — the D-5 contract, consumed exactly as
  published.

This design therefore **adds one new Django app, `apps/catalog/`**, and **modifies only**
`config/settings.py` (register the app; add `MEDIA_ROOT`/`MEDIA_URL`; add one tunable) and
`pyproject.toml` (add `Pillow` for image validation, as `interest-taxonomy` added `PyYAML`). Its
output — the **accepted-App record** — is the substrate `app-pages`, `editorial-curation-tools`,
`signal-capture`, and `developer-dashboard` all read.

---

## 2. Tech stack & project layout  *(reuses global D-4 — no new stack decision)*

The stack is fixed by **[D-4](../../DECISIONS.md)** and is **not** re-decided here. The one
global-worthy decision this feature introduces — the catalogued-app cross-feature contract — is
proposed as new global **D-6** (§11), recorded in [DECISIONS.md](../../DECISIONS.md) on approval.

**Project layout** (new app under the existing `apps/` root):

```
apps/                          ← SHARED-CODE ROOT (unchanged; D-4)
  core/                        ← reused as-is (observability, config, email, ratelimit, middleware)
  accounts/                    ← reused as-is (Account FK target; developer/admin gate)
  taxonomy/                    ← reused as-is (is_valid_tag / resolve_tag — D-5)
  catalog/                     ← THIS feature (new Django app)
    models.py                  ← App, AppTag (through), AppMedia, ReviewDecision
    gate.py                    ← the five objective floors: Criterion enum + checklist text (OQ-2)
    urlnorm.py                 ← URL normalization for duplicate detection (one source of truth)
    services.py                ← the single WRITE path (submit/edit/withdraw/resubmit/accept/reject)
    selectors.py               ← the single READ path (owner views, review queue, downstream catalog)
    notifications.py           ← decision email (reuses apps.core.email; AC7)
    forms.py                   ← server-rendered submission/edit form
    serializers.py             ← DRF read/write shapes
    views.py / urls.py         ← developer pages + API; admin review queue + decision endpoint
    admin.py                   ← Django-admin registration (inspection; cold-start)
    errors.py                  ← loud write-service failures
    apps.py                    ← AppConfig
    templates/catalog/         ← submit form, my-apps, app detail/edit, review queue
    templates/email/           ← app_accepted.{subject,body}.txt, app_rejected.{subject,body}.txt
    migrations/0001_initial.py ← create tables (no content)
    tests/
```

The **(shared)** surface this feature publishes is the downstream read selectors in
`selectors.py` (§5/§11); they are registered in [CODEMAP.md](../../CODEMAP.md) by the Engineer in
Stage 4 when the code exists.

---

## 3. Proposed architecture (components & responsibilities)

Each component has one responsibility, is testable in isolation, and depends only toward more
stable components (`models` ← `services`/`selectors` ← `views`; `services`/`selectors` →
`taxonomy.selectors`, `accounts` gate, `core`). **Writes go through exactly one path
(`services.py`); reads through exactly one path (`selectors.py`)** — the same discipline
`accounts` and `taxonomy` already use.

| Component | Owns (single responsibility) | Exposes | Hides |
|-----------|------------------------------|---------|-------|
| **App model** (`catalog.models.App`) | One submitted web app: stable identity, ownership, metadata, lifecycle state. | `App`; `id` (UUID — the cross-feature reference, AC9), `owner`, `name`, `description`, `url`, `normalized_url`, `status`, `last_submitted_at`. | Normalization, transition rules. |
| **AppTag** (`catalog.models.AppTag`) | The app↔tag link, stored as a **soft `tag_id` reference** (D-5). | through-rows: `(app, tag_id)`, unique. | — |
| **AppMedia** (`catalog.models.AppMedia`) | One screenshot belonging to an app, ordered. | `image`, `position`, `alt_text`. | File storage. |
| **ReviewDecision** (`catalog.models.ReviewDecision`) | An **append-only** record of one gate decision (the audit + metrics source). | `app`, `reviewer`, `outcome`, `failed_criteria`, `note`, `created_at`. | — |
| **Gate** (`catalog.gate`) | The **fixed** five objective floors and their reviewer-facing checklist wording (OQ-2). | `Criterion` (TextChoices), `CHECKLIST` (criterion→what-to-check), `GATE_RELEVANT_FIELDS`. | — (no "other/quality" value exists). |
| **URL normalizer** (`catalog.urlnorm`) | The single rule for "these two URLs are the same app" (duplicate signal). | `normalize_url(raw) -> str`. | scheme/host/path canonicalization. |
| **Write service** (`catalog.services`) | The **only** way an app or decision changes: submit, edit, add/remove media, withdraw, resubmit, accept, reject — each validated, atomic, counted, transition-checked. | `submit_app`, `edit_app`, `add_media`/`remove_media`, `withdraw_app`, `resubmit_app`, `accept_app`, `reject_app`. | Transactions, transition guards, invariant enforcement, observability. |
| **Read selectors** (`catalog.selectors`) | The **one** read surface: owner views, the review queue, the **downstream catalog** (accepted only, tags resolved). | `get_owned_app`, `list_owned_apps`, `list_review_queue`, `apps_sharing_url`, **`list_catalogued_apps`**, **`get_catalogued_app`**. | Status filtering, `resolve_tag` dereference, prefetch. |
| **Notifications** (`catalog.notifications`) | Turn a decision into the developer email (AC7). | `notify_decision(decision)`. | Templates; reuses `apps.core.email`. |
| **HTTP surfaces** (`catalog.views`/`urls`/`forms`/`serializers`) | Projection of services/selectors for the developer form/API and the admin review surface. | Developer pages + API (§5); admin review queue + decision endpoint. | Serialization only; no business logic. |
| **Admin** (`catalog.admin`) | Read/inspection of apps + decisions for ops cold-start. | Registered `App`/`ReviewDecision`. | — (rich review tooling = `editorial-curation-tools`). |

**Coupling check.** Every component is replaceable behind its exposed surface: the review UI is a
thin projection over `services.accept_app`/`reject_app`; the duplicate rule lives only in
`urlnorm`; media storage is behind Django's storage API (swap local→S3 by config). Cross-cutting
concerns are reused, not duplicated: **authz** = the accounts gate; **observability/logging** =
`apps.core.observability`; **config** = `apps.core.config`; **email** = `apps.core.email`;
**tag validity/resolution** = `apps.taxonomy.selectors`.

---

## 4. Data design

One source of truth per fact. UUID primary keys (platform convention, D-4). Four tables, all
under `apps/catalog/`, referencing no other app's *schema* except the `Account` ownership FK
(tags are a **soft** UUID reference — below — so `catalog` stays independently deletable apart
from that one intended ownership edge).

### `catalog_app`  (owns one submitted web app)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | **The stable cross-feature reference** downstream stores (AC9, D-6). |
| `owner` | FK → `accounts.Account`, `on_delete=CASCADE` | Individual ownership (SI-4). Cascade = a developer's apps are their content, removed on account deletion (§13, flagged to revisit when `signal-capture` exists). |
| `name` | varchar(120) | Honest display name (AC1). Required, non-blank. |
| `description` | text | What the app is (AC1). Required, non-blank, length-bounded. |
| `url` | varchar(2000) | The app URL **as entered** (displayed back). Validated http(s) + well-formed at the boundary (AC1 fail-loud). |
| `normalized_url` | citext, indexed (not unique) | Canonical form from `urlnorm.normalize_url` for the duplicate **signal** (§6c). Not a DB unique constraint — review is manual (SI-2) and rejected/withdrawn dupes may legitimately coexist. |
| `status` | enum(`pending`,`accepted`,`rejected`,`withdrawn`) | Lifecycle state — one source of truth for "where it is" (§7). Indexed (queue + catalog reads). |
| `last_submitted_at` | timestamptz | Set on each entry into `pending`; FIFO queue order **and** the start point for time-to-decision. |
| `created_at` / `updated_at` | timestamptz | Lifecycle. |

### `catalog_app_tag`  (owns the app↔tag link — soft reference, D-5)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `app` | FK → `App`, `CASCADE` | — |
| `tag_id` | UUID, indexed | **A taxonomy `Tag.id`, stored as a plain UUID, not a DB FK** — exactly the D-5 soft-reference contract: validated at the write boundary with `is_valid_tag` (AC4) and dereferenced at read with `resolve_tag` (AC9). Keeps `catalog` decoupled from `taxonomy`'s schema and lets a tag retire/merge without a cascade. |
| | | **Unique `(app, tag_id)`** — a tag is applied to an app at most once. |

### `catalog_app_media`  (owns one screenshot)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `app` | FK → `App`, `CASCADE` | — |
| `image` | ImageField (`upload_to="app_media/%Y/%m/"`) | Validated by Pillow at the boundary (real image, allowed format/size — §9). |
| `position` | smallint | Display order (AC9). **Unique `(app, position)`**. |
| `alt_text` | varchar(160), blank | Accessibility / `app-pages` alt text. |
| `created_at` | timestamptz | — |

### `catalog_review_decision`  (append-only gate audit — the metrics source)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `app` | FK → `App`, `CASCADE` | — |
| `reviewer` | FK → `accounts.Account`, `SET_NULL` | Survives reviewer deletion (mirrors `RoleGrant`). |
| `outcome` | enum(`accepted`,`rejected`) | — |
| `failed_criteria` | `ArrayField(varchar, choices=Criterion)`; empty for `accepted` | **≥1 of the five fixed floors** on a rejection; **no "other" value exists** (AC6/R1 — §6). Backs the rejection-reason distribution metric. |
| `note` | text, blank | The editor's actionable, developer-facing explanation (AC7). |
| `created_at` | timestamptz | The decision time → time-to-decision = `created_at − app.last_submitted_at`. |

**Lifecycle.**
- *App:* created `pending` (submit) → `accepted` / `rejected` (decision) → `pending` again
  (resubmit / edit of an accepted app) → `withdrawn` (owner). Rows are **never hard-deleted**
  except by owner account cascade; withdrawal is a state, not a delete (so a downstream id never
  dangles silently). See the transition table in §7.
- *ReviewDecision:* **append-only** — one row per decision, never updated or deleted. The latest
  row for an app is "what the gate last said"; `App.status` is "where it is now." They are written
  in the **same transaction** as the accept/reject, so they cannot drift.
- *Media:* added/removed by the owner while the app is editable; bounded count + size (§9).

**One source of truth.** "Where the app is" = `App.status` (authoritative for lifecycle, because
`withdraw`/`resubmit` move state with no decision). "What the gate decided" = `ReviewDecision`
(authoritative for the gate history + metrics). "What a tag means now" = `taxonomy.resolve_tag`
(not copied here). "Are two apps the same" = `urlnorm.normalize_url` (one rule).

**Concurrency.** Two editors deciding the same pending app: the decision service takes
`select_for_update()` on the `App` row and re-checks `status == pending`, raising
`InvalidTransitionError` if it already moved (no double decision). Owner edits are last-write-wins
on independent fields (acceptable at MVP single-owner volume — documented).

**Crash/restart.** All state is DB- or storage-backed; no in-memory queue or cache that could
drift. Each service op is `transaction.atomic()`, so a partial submit/decision writes nothing
(AC1 fail-loud).

**Migration/retention.** Migration 0001 creates the four tables only (no content). Apps and
decisions are retained (withdrawn, not deleted) so downstream references stay valid; media files
live under `MEDIA_ROOT`. Reverse = `migrate catalog zero` drops the tables (§12).

---

## 5. Interface contracts

Two consumer surfaces over **one** logic core (`selectors` reads, `services` writes). In-process
consumers (the matcher, `editorial-curation-tools`, `app-pages` server views) call the Python
selectors directly; the developer form/SPA and the review UI use the HTTP API. Both share the
core, so there is no second source of truth.

### 5a. Python write contract (`apps.catalog.services`) — the single mutate path

```python
def submit_app(owner, *, name, description, url, tag_ids: list[UUID],
               media: list[UploadedImage]) -> App          # AC1/AC2/AC4 — creates pending
def edit_app(app, *, name=…, description=…, url=…, tag_ids=…) -> App   # AC8 — owner edit
def add_media(app, image, *, alt_text="") -> AppMedia      # AC8 — bounded by media cap
def remove_media(media) -> None                            # AC8
def withdraw_app(app) -> App                               # AC8 — → withdrawn
def resubmit_app(app) -> App                               # AC7 — rejected/withdrawn → pending
def accept_app(app, reviewer) -> ReviewDecision            # AC5 — pending → accepted (+ notify)
def reject_app(app, reviewer, *, failed_criteria: list[Criterion],
               note: str) -> ReviewDecision                # AC5/AC6/AC7 — pending → rejected
```

**Invariants (enforced at this one boundary; illegal states unrepresentable):**
- **Required fields (AC1):** `submit_app` refuses unless `name`, `description`, a well-formed
  http(s) `url`, **≥1** `tag_id`, and **≥1** `media` are present — else `ValidationError` (no
  partial row written). `edit_app` keeps the same minimums.
- **Closed vocabulary (AC4):** every `tag_id` is checked with `taxonomy.is_valid_tag`; any
  off-vocabulary id raises `InvalidTagError` and **nothing is written** (off-vocabulary attempts
  counted → the metric must read 0). No tag is ever coined here.
- **Authorization is the caller's gate, ownership is the service's:** views apply
  `require_role(DEVELOPER)`/`HasRole(ADMIN)`; `edit/withdraw/resubmit` are only ever handed an app
  fetched **owner-scoped** (§5b), and `accept/reject` assert `status == pending` under a row lock.
- **Lawful transitions only (§7):** every state change validates the current `status` and raises
  `InvalidTransitionError` otherwise (e.g. accept on a non-pending app).
- **Re-validation on edit (AC8):** editing any **gate-relevant** field (`name`, `description`,
  `url`, tags, media — the named set in `gate.GATE_RELEVANT_FIELDS`) of an **accepted** app
  returns it to `pending` (it leaves the catalog until re-reviewed). Editing a non-gate field
  (none today; the set is the extension point) would not.
- **Decision atomicity (AC5):** `accept_app`/`reject_app` write the `ReviewDecision` **and** flip
  `App.status` in one transaction; a rejection requires ≥1 `failed_criteria` (else
  `ValidationError`). The notification is sent **after commit** (§5d).

Errors (raised loudly, never swallowed) in `catalog.errors`: `InvalidTagError`,
`InvalidTransitionError`, `MediaLimitError`, `NotOwnerError`. Generic field problems use Django/
DRF `ValidationError` (→ 400 with per-field messages).

### 5b. Python read contract (`apps.catalog.selectors`) — incl. the cross-feature substrate

```python
def get_owned_app(owner, app_id) -> App | None        # owner-scoped; None if not theirs (no leak)
def list_owned_apps(owner) -> list[App]               # the developer's "my apps", any status
def list_review_queue() -> list[ReviewRow]            # pending apps, FIFO, + duplicate hint (§6c)
def apps_sharing_url(normalized_url, *, exclude=None) -> list[App]   # the dup signal
def list_catalogued_apps() -> list[CatalogApp]        # ACCEPTED only; tags resolved; media ordered
def get_catalogued_app(app_id) -> CatalogApp | None   # ACCEPTED only; None otherwise (AC9)
```

**Invariants:**
- **Downstream sees accepted only (AC9):** `list_catalogued_apps`/`get_catalogued_app` return
  **only** `status == accepted` apps; a pending/rejected/withdrawn app is **not** presented as
  catalogued (returns `None`/absent). This is the AC9 / D-6 guarantee.
- **Tags resolved at read (D-5):** catalogued reads dereference each stored `tag_id` through
  `taxonomy.resolve_tag` (follows renames/merges, never drops a retired ref) and drop nothing —
  the catalog never shows a stale label.
- **Owner isolation:** `get_owned_app`/`list_owned_apps` filter by `owner`, so one developer can
  never read or act on another's app (AC8) — non-ownership is indistinguishable from "not found".

### 5c. HTTP API (DRF) + server-rendered pages

**Developer surface** — session + `developer` role (AC2); all app-scoped routes are owner-scoped
(404 on someone else's app):

| # | Endpoint | Method | Success | Errors |
|---|----------|--------|---------|--------|
| 1 | `/apps` | `POST` (multipart) | `201 {app}` — created `pending` (AC1) | `400` per-field (missing/invalid/malformed url, <1 tag, <1 media, off-vocab tag) · `403` not a developer |
| 2 | `/apps/mine` | `GET` | `200 [{app, status, latest_decision}]` (AC4/US5) | `403` |
| 3 | `/apps/{id}` | `GET` | `200 {app, media, tags(resolved), status, latest_decision}` | `403` · `404` not owner |
| 4 | `/apps/{id}` | `PATCH` | `200 {app}` — edit; accepted→pending if gate-relevant (AC8) | `400` · `403` · `404` |
| 5 | `/apps/{id}/media` | `POST` (multipart) | `201 {media}` | `400` (bad image / over cap) · `404` |
| 6 | `/apps/{id}/media/{mid}` | `DELETE` | `204` | `400` (would drop below 1) · `404` |
| 7 | `/apps/{id}/withdraw` | `POST` | `200 {app}` — `withdrawn` (AC8) | `404` · `409` bad transition |
| 8 | `/apps/{id}/resubmit` | `POST` | `200 {app}` — → `pending` (AC7) | `404` · `409` bad transition |

**Review surface** — session + `admin` role (AC5); identical for every app (AC3):

| # | Endpoint | Method | Success | Errors |
|---|----------|--------|---------|--------|
| 9 | `/review/queue` | `GET` | `200 [{app, owner, submitted_at, duplicate_hint}]` — **FIFO**, no priority field | `403` |
| 10 | `/apps/{id}/decision` | `POST` | `200 {decision}` — `{outcome, failed_criteria[], note}` → accept/reject (AC5/AC6/AC7) | `400` (reject with 0 criteria / unknown criterion) · `403` · `409` not pending |

**Server-rendered pages** (the human flow, mirroring `accounts`' page+API split): submit form
(`GET/POST /submit`), my-apps (`GET /apps`), app detail/edit/withdraw (`/apps/{id}`), and the
admin review queue + decision form (`/review`). Pages post to the same services as the API.

> **Unauthenticated = `403`** under the platform's DRF `SessionAuthentication` (no
> `WWW-Authenticate` challenge), matching `accounts`/`taxonomy` (taxonomy ITX-9). The `409` on a
> bad lifecycle transition is the loud, specific signal that the app already moved.

**Auth posture.** Reads/writes of an app require the developer role **and** ownership; review
requires admin. There is **no anonymous surface here** — public rendering of an accepted app is
`app-pages`' job, which will call `selectors.get_catalogued_app` (in-process) or a future
`AllowAny` read endpoint; relaxing a catalogued-read endpoint to anonymous is a one-line change,
noted not built (no speculative abstraction).

**Evolution without breaking consumers.** The cross-feature contract is intentionally tiny:
**`App.id`** (the reference), **`list_catalogued_apps`/`get_catalogued_app`**, and the accepted-app
JSON shape (id, name, description, url, resolved tags, ordered media). New fields are additive; new
lifecycle is a new endpoint, never a change to these. JSON shapes are URL-prefix-versionable if
ever needed.

### 5d. Notification contract (AC7) — reuses `apps.core.email`

`notifications.notify_decision(decision)` renders `email/app_accepted.*` or `email/app_rejected.*`
(the latter listing the failing criteria labels + the editor's note, in actionable terms) and
sends via `apps.core.email.get_email_sender()`. It is called **after** the decision transaction
commits: the **decision is authoritative**, the email is a notification. A send failure is logged
and counted (`EMAIL_SEND_FAILURE`) and surfaced in the review UI, but **does not roll back the
decision** (the developer still sees the outcome + reason in "my apps") — fail loud without making
notification a single point of failure for the gate.

---

## 6. The objective intake gate  *(resolves OQ-2)*

The brief fixes the **five objective floors** (AC5) as the product requirement; this design makes
them deterministic for review (CLAUDE.md §6.2) and makes a taste rejection (R1/AC6) *structurally
impossible*.

### 6a. The criteria — a fixed code enum, not editable data
`catalog/gate.py` defines:

```python
class Criterion(models.TextChoices):
    WORKS         = "works",           "Reachable & functional"
    NOT_SPAM      = "not_spam",        "Not malware or spam"
    NOT_DUPLICATE = "not_duplicate",   "Not a duplicate of a catalogued app"
    HONEST        = "honest_metadata", "Metadata honestly describes the app"
    POLICY        = "policy",          "Meets basic platform policy"

CHECKLIST: dict[Criterion, str] = { … }   # the reviewer-facing "what to check" text (OQ-2)
GATE_RELEVANT_FIELDS = {"name", "description", "url", "tags", "media"}
```

The floors are **product-fixed** (vision §5.5), so they live in **code** (type-safe, no migration
to read them, no editorial mutation path). `CHECKLIST` holds the concrete reviewer wording for each
floor (the OQ-2 deliverable) in one place — editing wording is a one-file change; the *set* of
floors changes only by a deliberate code change (a product/vision-level event, not editorial).

### 6b. Why this kills the taste-gate risk (R1/AC6)
`ReviewDecision.failed_criteria` accepts **only** values from `Criterion`. There is **no
"other"/"low-quality"/"not-for-us" value**, so an editor *cannot record a taste rejection* — the
decision shape makes it unrepresentable, not merely discouraged. Acceptance requires **all five**
floors to pass; rejection requires **≥1 named floor**. This turns AC6 from a hope into an enforced
data constraint, and makes the "rejection-reason distribution" metric exact (every rejection maps
to one of the five floors; a creeping "other" bucket cannot exist).

### 6c. Duplicate detection stays manual (SI-2), but deterministic
"Not a duplicate" is reviewed by a human (SI-2 — no automated detection built). To make that human
check *deterministic and cheap*, `urlnorm.normalize_url` computes `normalized_url`, and
`list_review_queue` attaches a **duplicate hint**: "N other apps share this URL"
(`apps_sharing_url`). The editor decides (AC5/AC6 keep authority with the human). It is **not** a DB
unique constraint and **not** an auto-reject — rejected/withdrawn dupes may legitimately coexist,
and acceptance is the editor's call. Hardening to a partial-unique index on accepted URLs is a
named, deferred option (§13), not built now.

---

## 7. Submission lifecycle  *(the state machine)*

`App.status` is the single source of truth for where an app is. The **only** code that changes it
is `catalog.services`; every transition is validated, else `InvalidTransitionError` (loud).

| From | Event | To | Notes |
|------|-------|----|-------|
| (none) | `submit_app` | `pending` | sets `last_submitted_at`; emits `submission_created` |
| `pending` | `accept_app` | `accepted` | writes a `ReviewDecision(accepted)`; notifies; in catalog (AC9) |
| `pending` | `reject_app` | `rejected` | writes `ReviewDecision(rejected, ≥1 criterion, note)`; notifies |
| `rejected` | `resubmit_app` | `pending` | rejection is non-terminal (AC7); new `last_submitted_at` |
| `accepted` | `edit_app` (gate-relevant) | `pending` | leaves catalog until re-reviewed (AC8) |
| `pending`/`accepted`/`rejected` | `withdraw_app` | `withdrawn` | drops from catalog (AC8) |
| `withdrawn` | `resubmit_app` | `pending` | owner re-offers a withdrawn app |

Accept/reject are guarded by `status == pending` under `select_for_update()` (no double decision).
Withdraw of an already-withdrawn app is a `409` (no-op transition). Any other transition from an
unlisted state raises `InvalidTransitionError`. An edit to a `pending`/`rejected` app updates in
place (a `rejected` app moves to `pending` only via the explicit `resubmit_app`).

---

## 8. UX flow (server-rendered states)

**Developer — submit (`/submit`):** empty form (name, description, url, tag picker fed by
`taxonomy.list_active_tags`, image uploader) → on invalid, re-render with **per-field** errors and
no row created (AC1) → on success, redirect to the app's detail showing `pending`.
**Developer — my apps (`/apps`):** empty state ("You haven't submitted an app yet"); list with a
status badge per app; for a rejected app, the **failing criteria + note** are shown inline
(actionable, AC7) with a "correct & resubmit" action.
**Developer — app detail/edit (`/apps/{id}`):** edit metadata/tags/media; withdraw; resubmit; an
edit to an accepted app warns "this returns your app to review" (AC8).
**Admin — review queue (`/review`):** FIFO list of pending apps, each with owner, submitted-at, and
the **duplicate hint**; opening one shows the metadata, media, resolved tags, the **five-floor
checklist**, and accept / reject(criteria+note) actions. Empty state = "No apps awaiting review."
Loading/error states reuse the project's standard templates.

This feature renders **no public app page** — that is `app-pages` (out of scope), which reads
`get_catalogued_app`.

---

## 9. Non-functional handling

**Performance / scale.** Reads are bounded, indexed queries: the review queue filters
`status=pending` ordered by `last_submitted_at` (indexed); the catalog filters `status=accepted`;
owner lists filter by `owner` (FK indexed). Tag dereference is a point lookup per stored `tag_id`
via `resolve_tag`; media and tags are prefetched to avoid N+1. No O(n²), no in-memory state. At
100× (D-2 / §5.2): the queue is paginated and the catalog read gains a cached projection — the
documented growth path, **not** built now (founding volume is 50–150 apps).

**Media (resolves OQ-3 — published as the contract `app-pages` adopts).** Screenshots/images only
(SI-7). **Per app: 1 ≤ media ≤ 8.** **Formats: PNG, JPEG, WebP.** **Max 5 MB/file.** Validated by
**Pillow** at the boundary (real, decodable image of an allowed type within size) — a non-image or
oversize upload fails loud with a per-field error (no row/file written). Stored via Django's
storage API under `MEDIA_ROOT` (local disk at MVP; swap to S3/object storage by changing the
storage backend, no caller change). The numeric limits live in `apps.core.config` as typed
tunables (`catalog_media_max_count`, default 8; `catalog_media_max_bytes`, default 5 MB), so they
are change-cheap and validated at startup. **`app-pages` must consume these slots/limits** — OQ-3
is closed here, with `app-pages` to adopt.

**Security (threat model).**
- *Privilege escalation / unauthorized action:* submit/edit/withdraw require `developer` **and**
  ownership (owner-scoped queries → 404, no enumeration); review requires `admin`. Reuses the
  accounts fail-closed gate; **no new auth path**.
- *Injection / bad input:* the `url` is validated as well-formed http(s) and length-bounded;
  text fields are bounded; uploaded files are Pillow-validated and stored with framework-generated
  names (never the client filename) under a non-executable media root; tag ids are validated with
  `is_valid_tag`. All at the single write boundary, fail loud.
- *Fairness (AC3):* there is **no** payment, tier, budget, brand, priority, or fast-lane field on
  any model, queue, or endpoint — the unfair state is unrepresentable; the queue is strictly FIFO.
- *Data leakage / PII:* an app record is the developer's own public-intended metadata (no third-
  party PII); owner isolation prevents cross-developer reads; the reviewer (admin) sees submissions
  by design.
- *Attributability:* every gate decision is an **append-only `ReviewDecision`** row naming the
  reviewer; lifecycle changes are counted via observability; Django-admin `LogEntry` covers ad-hoc
  admin edits.

**Observability.** Reuses `apps.core.observability.increment`. New metric-name constants (1:1 with
the brief's success metrics, added to `apps/core/observability.py`):
`submission_started` / `submission_completed` (completion rate), `submission_created`,
`review_decision` (tags: `outcome`, and on reject each `criterion` → gate-pass-rate +
rejection-reason distribution), `app_accepted` / `app_rejected` / `app_withdrawn` /
`app_resubmitted`, `tag_off_vocabulary_rejected` (must stay **0** — AC4), `duplicate_flagged`.
**Time-to-decision** is computed from stored timestamps (`ReviewDecision.created_at −
App.last_submitted_at`) by a reporting selector — not a counter (CLAUDE.md §6.2: observable, no
hard SLA). **Actionable alerts only:** any nonzero `tag_off_vocabulary_rejected`; a
rejection-reason distribution skew (the AC6 drift signal); `EMAIL_SEND_FAILURE` for decisions.

**Rollback.** Additive new app; the only live consumer (`app-pages`) is not built yet, so there is
nothing to feature-flag *off*. Safety = **reversible migration** (`migrate catalog zero` drops the
four tables) + media files removable from `MEDIA_ROOT`. A bad release is rolled back by reverting
the deploy and, if needed, the last migration.

---

## 10. Failure modes (detection → response, never silent)

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| `submit_app` / `edit_app` | missing/invalid field, malformed url, <1 tag, <1 media | boundary validation in one txn | Refuse with per-field `400`; **no partial row/file** (AC1). |
| tag validation | off-vocabulary / non-UUID `tag_id` | `taxonomy.is_valid_tag` | Raise `InvalidTagError` → `400`; nothing written; count `tag_off_vocabulary_rejected` (AC4). |
| media upload | non-image / wrong format / over size / over count | Pillow + count check | Refuse `400`; no file stored (`MediaLimitError`). |
| `accept_app`/`reject_app` | app not `pending` (already decided / concurrent editor) | `select_for_update` + status check | Raise `InvalidTransitionError` → `409`; no second decision. |
| `reject_app` | zero `failed_criteria` | service guard | `400` — a rejection must name ≥1 floor (AC5/AC7). |
| any transition | unlawful from→to | `services` transition guard | `InvalidTransitionError` → `409`, loud (§7). |
| owner action | app not owned by caller | owner-scoped query returns None | `404` — no leak of others' apps (AC8). |
| `notify_decision` | email transport down | `EmailSendError` post-commit | Log + count `EMAIL_SEND_FAILURE`; **decision stands**; dev sees outcome in "my apps" (§5d). |
| `resolve_tag` (read) | stored tag retired/merged/cycle | taxonomy selector | Resolved transparently (renames/merges) or last-good-on-cycle (taxonomy already counts `TAXONOMY_REFERENCE_BREAK`); the catalog never shows a stale/dropped label (AC9). |
| DB / storage down | exception/timeout | exception | Fail loud (`500`/exception) — never present an empty catalog or a half-saved app as success. |

---

## 11. Cross-feature contract handed downstream  *(proposed global D-6)*

Recorded as global **D-6** on approval so `app-pages`, `editorial-curation-tools`,
`signal-capture`, and `developer-dashboard` build on it consistently:

- **The catalogued unit is an `accepted` `catalog.App`; its stable reference is `App.id` (UUID).**
  Downstream stores that id and nothing else as the app handle (signals key to it, digests
  reference it, pages render it).
- **Read the catalog only through `selectors.list_catalogued_apps` / `get_catalogued_app`**, which
  return **accepted apps only** — a pending/rejected/withdrawn app is **never** presented as
  catalogued (AC9). Do not read `catalog_app` directly past this surface.
- **Tags on an app are taxonomy `Tag.id`s under the D-5 contract** — resolve them with
  `taxonomy.resolve_tag`; never store or compare an app's tag by label.
- **Media is an ordered list of images** (the §9 slots/limits) exposed with stable order.

A downstream feature that reads non-accepted apps as catalogued, stores the app by anything other
than `App.id`, or dereferences a tag by label would **break** this contract — flagged here so it is
not done.

---

## 12. Rollout strategy

Additive new app; the first consumer (`app-pages`) ships later, so there is no backward-compat
burden and no flag to protect a pre-existing surface:

1. Add `Pillow` to `pyproject.toml`; add `MEDIA_ROOT`/`MEDIA_URL` and the `catalog_media_*`
   tunables to settings/`config.py`; register `apps.catalog` in `INSTALLED_APPS` and `catalog.urls`
   in the root URLconf.
2. Apply migrations (`migrate catalog`) — creates the four tables. No content.
3. Founding catalog enters through the **same** developer form (SI-5 — recruitment is offline; no
   in-product recruitment surface).
4. No recurring job is scheduled (nothing expires here).

Rollback = revert deploy + `migrate catalog zero` (+ clear `MEDIA_ROOT` if desired).
**Handed downstream:** consumers adopt the §11 / D-6 contract before they store any app reference.

---

## 13. Self-critique & alternatives

**Attacks on the design and resolutions:**
- *"App and Submission collapsed into one row — is that right?"* The brief treats them as near-
  synonymous ("a submission … together with the record it creates"). A single `App` with a
  lifecycle `status` + an append-only `ReviewDecision` log keeps **one** source of truth for
  catalog membership and avoids a "which submission is current" ambiguity. The cost — no first-
  class per-attempt snapshot — only matters for *versioned updates*, which are **explicitly
  deferred** (SI-6); when they arrive, a `SubmissionVersion` table is added then, not speculated
  now (§5.5).
- *"A soft `tag_id` UUID with no DB FK can store a garbage/zombie id."* It is validated with
  `is_valid_tag` at the **single** write boundary (AC4) and dereferenced with `resolve_tag` at
  read — exactly the D-5 contract, which exists *because* a hard FK fights read-time rename/merge
  resolution and would couple `catalog` to `taxonomy`'s schema. The boundary check is the guard,
  mirroring how consumers enforce `HasRole`. Accepted, consistent with the published substrate.
- *"Re-reviewing an accepted app on any edit is heavy — a typo fix drops it from the catalog."*
  True, and deliberate: the honest-metadata/works floors can break on an edit (R3), so the safe
  default is re-review (AC8 says re-validate where an edit touches a gated floor — and every
  current field is gate-relevant). `GATE_RELEVANT_FIELDS` is the named seam so a future non-gated
  field skips re-review. **Decided 2026-06-17 (user):** keep this "re-review, app goes dark"
  behavior for MVP over the alternatives — *stay-live + async re-review* (better UX, modest extra,
  but exposes a brief unreviewed window) and *two-state published/pending-update staging* (Steam-
  like, never dark). The two-state model **is** the deferred versioned-updates machinery (SI-6) and
  is the **named growth path** that lands with that feature; a *stay-live* variant or a "trivial-
  edit" allowance remains a revisit-with-data option. (Pure trust-after-first-approval with
  report/AI-only re-review contradicts AC8 and depends on out-of-scope controls (SI-2) — a brief
  change, not a design tweak.)
- *"Why no audit beyond `ReviewDecision`?"* The decision log **is** the audit for the gate
  (append-only, names the reviewer); lifecycle is counted; Django-admin `LogEntry` covers ad-hoc
  edits. A richer review/audit UI is `editorial-curation-tools` (out of scope); adding one here
  would be speculative.
- *"Account-deletion cascade deletes a developer's apps — downstream dangling?"* At MVP there is no
  downstream consumer yet, and CASCADE is the privacy-respecting "the dev's content is theirs"
  default (consistent with `delete_account`). Flagged to revisit (withdraw-instead-of-delete, or
  `SET_NULL` to an anonymized owner) when `signal-capture` keys signals to apps.
- *Simplification pass:* dropped a separate `Submission` entity, a per-criterion result table (an
  `ArrayField` suffices), a draft/persisted-partial state (a partial row would violate AC1 — funnel
  is measured by counters), an in-memory queue, and any niche/priority/tier column. Nothing
  remaining is untied to an AC.

**Alternatives considered (full rationale → DECISIONS on approval):**
- *Separate `App` + `Submission` entities* — rejected: two sources of truth for catalog membership
  and "current submission" ambiguity for no MVP benefit; the deferred need (versioning) gets its
  own table when it's real.
- *Hard M2M FK `App.tags → taxonomy.Tag`* — rejected: couples schemas and fights `resolve_tag`'s
  read-time remap (the reason D-5 is a soft reference); chose the D-5 soft `tag_id`.
- *Editable criteria table for the gate* — rejected: it would let an editor add a "quality"
  criterion — the exact AC6/R1 violation we must prevent. A fixed code enum with **no "other"**
  makes a taste rejection unrepresentable.
- *Edit-in-place keeping an accepted app accepted* — rejected: a metadata edit can break the
  honest/works floor (R3); conservative re-review is the safe default.
- *External object store (S3) for media now* — rejected as premature; Django's storage API behind
  a config switch is the boring, swappable choice at founding volume.
- *DB partial-unique index on accepted `normalized_url`* — rejected for MVP: SI-2 keeps duplicate
  detection manual and the editor authoritative; kept as a documented hardening once real duplicate
  volume justifies it.

**What the chosen design sacrifices:** no first-class submission-attempt history (until versioning
is built); no DB referential integrity on `tag_id` (boundary validation instead); conservative
re-review churn on accepted-app edits; manual (human) duplicate/spam/works checks at MVP (a bounded
SI-2 choice); local file storage at MVP — all documented, bounded trade-offs.

---

## 14. Traceability — every acceptance criterion maps to a design element

| AC | Design element(s) |
|----|-------------------|
| **AC1** Submit w/ required fields; fail loud on missing/malformed | `services.submit_app` boundary validation (name/description/url/≥1 tag/≥1 media) in one txn; per-field `400`; no partial row (§4/§5a/§10) |
| **AC2** Developer-gated submission | `require_role(DEVELOPER)`/`HasRole(DEVELOPER)` on all submit/own routes (§5c) — reuses the accounts gate (D-3) |
| **AC3** Identical free intake (fairness) | One `App`, one form, one FIFO queue, one five-floor gate; **no** payment/tier/priority field anywhere — unfair state unrepresentable (§3/§5c/§9) |
| **AC4** Closed vocabulary; store by `Tag.id` | `AppTag.tag_id` soft UUID ref; `is_valid_tag` at the write boundary rejects off-vocabulary; `tag_off_vocabulary_rejected`=0 (§4/§5a/§11; D-5) |
| **AC5** Accept only if all objective floors pass; record failing criterion | `gate.Criterion` (5 fixed floors); `accept_app` needs all-pass; `reject_app` records ≥1 criterion in append-only `ReviewDecision` (§6/§7) |
| **AC6** No taste gate | `failed_criteria` allows **only** the 5 floors — **no "other"/"quality" value exists** → taste rejection unrepresentable (§6b); rejection-reason metric surfaces drift (§9) |
| **AC7** Actionable decision + non-terminal rejection | `notify_decision` emails outcome + failing criteria + note (§5d); `resubmit_app` rejected→pending (§7) |
| **AC8** Ownership + correction + withdrawal + re-validation | owner-scoped queries (404 on non-owner); `edit_app`/`add_media`/`remove_media`; gate-relevant edit on accepted → pending; `withdraw_app` (§5/§7) |
| **AC9** Downstream contract (accepted-only, stable id, resolved tags + media) | `selectors.list_catalogued_apps`/`get_catalogued_app` (accepted only); `App.id` stable ref; `resolve_tag` at read; ordered media — proposed global **D-6** (§5b/§11) |

Every component's failure behavior is documented in §10; no contract above contains "TBD"
(OQ-2 resolved in §6, OQ-3 in §9).
