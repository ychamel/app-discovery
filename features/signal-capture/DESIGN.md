# DESIGN — signal-capture

*Stage 2 artifact (Software Architect). Status: **DRAFT — awaiting approval** (proposes
global **D-7**, the event-schema contract; → Stage 3-plan on approval).
Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED DN-5), feature
[DECISIONS.md](DECISIONS.md) SC-1…SC-8, [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
(OQ-1 proxy mechanism, OQ-2 privacy posture, OQ-3 proxy under-count), global
[DECISIONS.md](../../DECISIONS.md) (D-1…D-6), [CODEMAP.md](../../CODEMAP.md) (the `apps/`
shared surface from `identity-accounts` + `interest-taxonomy` + `submission-intake`), vision
[§3.1/§3.2/§5.4/§5.6, Open Q #4](../../curated-app-platform-design.md). Produced by the
14-step protocol in [phase-2-architect.md](../../process/personas/phase-2-architect.md).*

---

## 0. Reasoning trace (14-step protocol — condensed)

The protocol is the method; §1–§14 are its output. Only the non-obvious steps are recorded
here; the rest are realized in the contract sections.

1. **SCOPE.** Record every **on-platform** behavioral signal in the curated loop —
   impression → click-through → return-to-platform(3d/14d) → subscribe/follow → on-page
   re-engagement → share — as clean events keyed *user × `App.id` × impression*, tagged with
   the app's interest categories **at capture time**, **raw (never scored)**, so a future
   Quality Score is **backtested without re-instrumentation** (H3). Lifespan = **platform**:
   this is the schema-first spine every later surface emits into or reads from, so the model
   is the single most expensive thing in the MVP to get wrong (R2). OUT (re-stated from brief):
   the incentive **surfaces** that *generate* engagement (subscriptions, dev↔user comms,
   early-access — owned by `app-subscriptions`/`developer-updates`), the Quality Score / any
   scoring or normalization, the matcher/digest/app-page surfaces that *emit* events, ratings/
   reviews, the developer-dashboard UI, and native install / SDK attribution (web-only, D-1).
2. **REQUIREMENTS.** Functional = AC1–AC11. Non-functional = D-2 (no hard ceiling, but hold
   at 100× or document the bounded trade-off); capture must be **non-blocking** to the user
   surface (C5) **and never silently lossy** (AC11/R4) — the central tension this design
   resolves (§5d). The three Stage-1 opens are settled here: **OQ-2 privacy posture** (→ §10,
   the SC-6 posture realized as a stored-fields whitelist + a human-readable `PRIVACY` note),
   **OQ-1 proxy mechanism** (→ §8, a one-call seam, **not** an attribution engine — R1), and
   **OQ-3 proxy under-count** (→ §8/§13, documented limitation + a seam for a stronger later
   signal, not over-built now).
3. **CONTEXT.** **Not greenfield.** `identity-accounts` (D-4) fixed the stack, the `apps/`
   root, `apps/core/` (observability, config, middleware), and the `Account` identity +
   `require_role`/`HasRole` gate. `interest-taxonomy` (D-5) published `resolve_tag`/`Tag.id`.
   `submission-intake` (D-6) published the catalogued-app read contract
   (`get_catalogued_app`/`list_catalogued_apps`, `App.id`). This feature **reuses all of
   them** and adds one new Django app, `apps/signals/`. The one global-worthy new thing is the
   **event-schema contract** (proposed global **D-7**) — because the Quality Score, rings,
   integrity analysis, the developer-dashboard and `weekly-digest`/`app-pages` are all later
   producers/consumers of it and must not contradict it (R2, breakdown §4.5).
4. **MODULES.** A model layer (4 tables), one **capture** write path, one **read/funnel**
   path, and one thin visit-recording middleware — mirroring the `services`/`selectors` split
   `accounts`/`taxonomy`/`catalog` already use (§3).
6. **DATA & STATE.** One source of truth per fact: each behavioral act is **one immutable,
   append-only event row** (events are facts, never mutated). The **impression** is the anchor
   (its own identity, its capture-time tag snapshot); downstream acts reference it. **Return@3d
   /14d is *derived*, not stored** (SC-9): it is a relationship between a stored impression and
   stored platform-visit activity, so materializing it would invent a "did-not-return" event
   (an absence cannot be an event) and require a scheduled job — the read path computes it from
   stored data with **no backfill** (AC8).
9. **TRADE-OFFS.** Four genuine forks decided in §13: **one append-only event table with a
   `kind` discriminator** vs table-per-event-type; **derive returns at read** vs materialize a
   cohort table; **impression as a first-class anchor** vs a flat event with a self-reference;
   **`SET_NULL` (anonymize) on account deletion** vs CASCADE (purge) vs hard-block.
10. **SECURITY.** Events are pseudonymous behavioral data keyed to `Account.id` (SC-6); the
    stored-fields whitelist (§10) forbids IP / user-agent / off-platform PII. A user may only
    emit events as **themselves** (the surface passes `request.user`, never an arbitrary
    account); the raw read path is **internal/admin-only** (no public endpoint).
13. **SELF-CRITIQUE.** §13 — the sharp edges are the single-table discriminator, derived-not-
    stored returns, the non-blocking-vs-fail-loud reconciliation, and account-deletion
    anonymization. Each is resolved or flagged to revisit with data.

---

## 1. Current-state summary

The repository is **not greenfield**. This feature builds on, and does not re-derive:

- **Stack (global D-4):** Python 3.12+ / Django 5.x / DRF / PostgreSQL; shared root `apps/`.
- **`apps/core/`** reused verbatim: `observability.increment` + metric-name constants and
  `check_health` (§9/§10), the `config.py` typed-tunable pattern (the return windows live here
  — §9), and the request-context logging middleware (the new visit middleware sits beside it).
- **`apps/accounts/`** reused verbatim: the `Account` identity (the `user` FK target on every
  event) and the fail-closed gate (`HasRole(ADMIN)`/`require_role(ADMIN)` guards the raw read
  surface, §5c). **No new auth path.**
- **`apps/taxonomy/`** reused: `selectors.resolve_tag(id)` to render a captured tag's *current*
  label at read (the capture-time tag *set* is frozen — AC2 — so resolution is for display only,
  never to change which tags were captured).
- **`apps/catalog/`** reused via the **D-6** read contract: `selectors.get_catalogued_app(id)`
  validates that an event keys to a real **accepted** app and supplies the **capture-time tag
  snapshot** for impressions. Nothing reads `catalog_app` directly (D-6 honored).

This design therefore **adds one new Django app, `apps/signals/`**, and **modifies only**
`config/settings.py` (register the app + the visit middleware; add the two return-window
tunables) and `apps/core/observability.py` (add this feature's metric-name constants, exactly
as `taxonomy`/`catalog` did). Its output — the **raw event corpus + the per-app funnel read
path** — is the substrate the future Quality Score, the developer-dashboard, and editorial
backtesting all consume.

---

## 2. Tech stack & project layout  *(reuses global D-4 — no new stack decision)*

The stack is fixed by **[D-4](../../DECISIONS.md)** and is **not** re-decided here. The one
global-worthy decision this feature introduces — the **event-schema contract** — is proposed as
new global **D-7** (§11), recorded in [DECISIONS.md](../../DECISIONS.md) on approval.

**Project layout** (new app under the existing `apps/` root):

```
apps/                          ← SHARED-CODE ROOT (unchanged; D-4)
  core/                        ← reused; +signals metric constants (observability.py), +2 tunables (config.py)
  accounts/                    ← reused as-is (Account FK target; admin gate on the read surface)
  taxonomy/                    ← reused as-is (resolve_tag at read — display only — D-5)
  catalog/                     ← reused as-is (get_catalogued_app: app validity + tag snapshot — D-6)
  signals/                     ← THIS feature (new Django app)
    models.py                  ← Impression, ImpressionTag, EngagementEvent, PlatformVisit
    kinds.py                   ← EventKind enum + Surface enum (the closed, code-fixed vocabularies)
    capture.py                 ← the single WRITE path (record_impression / _click_through / …)
    selectors.py               ← the single READ path (app_funnel — the H3 backtest; raw counts only)
    middleware.py              ← PlatformVisitMiddleware (idempotent per-user-per-day return substrate)
    errors.py                  ← loud capture failures (UnknownAppError, ImpressionMismatchError)
    apps.py                    ← AppConfig
    admin.py                   ← read-only inspection of the corpus (cold-start ops)
    PRIVACY.md                 ← human-readable what/why/retention posture (AC10)
    migrations/0001_initial.py ← create the four tables (no content)
    tests/
```

The **(shared)** surface this feature publishes is the **capture contract** (`capture.py` —
the one write path every emitting surface calls) and the **funnel read path** (`selectors.py`);
both are registered in [CODEMAP.md](../../CODEMAP.md) by the Engineer in Stage 4 when the code
exists. There is **no DRF/HTTP surface and no template** here at MVP — signal-capture is
instrumentation: emitting surfaces call `capture.*` **in-process**, and the only reader
(future developer-dashboard / editorial backtest) calls `selectors.*` in-process or through the
admin (§5c). A public/REST projection is a one-feature-later addition, noted not built (§5c).

---

## 3. Proposed architecture (components & responsibilities)

Each component has one responsibility, is testable in isolation, and depends only toward more
stable components (`models` ← `capture`/`selectors` ← emitting surfaces; `capture`/`selectors`
→ `catalog.selectors`, `taxonomy.selectors`, `core`). **Writes go through exactly one path
(`capture.py`); reads through exactly one path (`selectors.py`)** — the discipline
`accounts`/`taxonomy`/`catalog` already use.

| Component | Owns (single responsibility) | Exposes | Hides |
|-----------|------------------------------|---------|-------|
| **Impression** (`signals.models.Impression`) | One shown instance: its own identity (the anchor every conversion attributes to, AC1/AC3), `user × App.id`, surface, time. | `id` (UUID — the impression identity), `user`, `app_id`, `surface`, `occurred_at`. | — |
| **ImpressionTag** (`signals.models.ImpressionTag`) | The **capture-time** category snapshot: which `Tag.id`s the app carried *when shown* (AC1/AC2). | through-rows `(impression, tag_id)`. | — (never re-resolved to change the set). |
| **EngagementEvent** (`signals.models.EngagementEvent`) | One downstream behavioral act (click-through / subscribe / on-page re-engagement / share / off-platform proxy), append-only. | `kind`, `user`, `app_id`, `impression` (nullable), `is_proxy`, `occurred_at`. | The `kind` discriminator's per-type meaning (validated in `capture`). |
| **PlatformVisit** (`signals.models.PlatformVisit`) | The **directly-observed return substrate**: that a user was active on the platform on a given UTC day (one row per user per day). | `(user, visit_date)`, unique. | — |
| **EventKind / Surface** (`signals.kinds`) | The **closed, code-fixed** event-kind and surface vocabularies (no free-text type, no editorial mutation). | `EventKind` (TextChoices), `Surface` (TextChoices). | — |
| **Capture service** (`signals.capture`) | The **only** way an event is written: validate the app (D-6) and impression linkage, snapshot tags, write one append-only row, count it, fail loud. | `record_impression`, `record_click_through`, `record_subscribe`, `record_page_reengagement`, `record_share`, `record_off_platform_proxy`, `record_platform_visit`. | Transactions, validation, the tag snapshot, observability. |
| **Read/funnel selectors** (`signals.selectors`) | The **one** read surface: the per-app **raw** funnel over an evaluation window (the H3 backtest), incl. **derived** returns. | `app_funnel`, `funnel_for_apps`, `category_impressions`. | Return derivation, window math, GROUP BY — all behind a DTO; **never scores** (AC9). |
| **Visit middleware** (`signals.middleware`) | Turn an authenticated request into an idempotent daily visit (the return substrate), non-blocking. | `PlatformVisitMiddleware`. | Dedup, fail-soft-but-counted. |
| **Admin** (`signals.admin`) | Read-only inspection of the corpus for ops cold-start. | Registered models (no add/change/delete). | — (rich analytics = future consumers). |

**Coupling check.** Every component is replaceable behind its exposed surface: the funnel UI
(future developer-dashboard) is a thin projection over `selectors.app_funnel`; the return
definition lives only in `selectors` + two config tunables; app validity + tag snapshot are
delegated to `catalog`/`taxonomy` (not reimplemented). Cross-cutting concerns are reused, not
duplicated: **authz** = the accounts gate; **observability/config/logging** = `apps.core`;
**app validity + tags** = `catalog.get_catalogued_app`; **tag display** = `taxonomy.resolve_tag`.

---

## 4. Data design  *(the proposed global D-7 schema)*

One source of truth per fact. UUID primary keys (platform convention, D-4). **Four tables**,
all under `apps/signals/`, referencing no other app's *schema* except the `Account` `user` FK
(apps and tags are **soft `App.id`/`Tag.id` UUID references** under D-6/D-5 — so `signals` stays
independently deletable apart from that one identity edge). **Every event is append-only**:
created once, never updated or deleted (a behavioral fact does not change). There is **no
score, rank, normalized, or weight column anywhere** — the raw-only guarantee (AC9/R5) is
structural, not a convention.

### `signals_impression`  (the anchor — one shown instance)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | **The impression identity** every conversion attributes to (AC1/AC3). |
| `user` | FK → `accounts.Account`, `on_delete=SET_NULL`, null | Who was shown the app. `SET_NULL` = anonymize-on-deletion (§13, SC-10): the behavioral fact survives as corpus, unlinked from the person. |
| `app_id` | UUID, indexed | The **accepted** `catalog.App.id` shown (D-6 soft ref). Validated at capture via `get_catalogued_app`; not a DB FK (catalog stays decoupled; a later app withdrawal doesn't cascade-erase history). |
| `surface` | enum (`Surface`) | Where it was shown — `digest` only at MVP (SC-1), extensible by adding an enum value (app-page, feed) with **no migration to the others**. |
| `occurred_at` | timestamptz, indexed | When the app was shown (the funnel/return clock starts here). Defaults to now; an emitter may pass the true show time (digest send time). |
| `created_at` | timestamptz | Row insertion time (audit; ordinarily == `occurred_at`). |

Index `(app_id, occurred_at)` — the funnel reads "impressions of app A in [start,end]".

### `signals_impression_tag`  (capture-time category snapshot — soft `Tag.id`, D-5)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `impression` | FK → `Impression`, `CASCADE` | — |
| `tag_id` | UUID, indexed | A `Tag.id` the app carried **at show time**, copied from `get_catalogued_app(app_id).tags` (AC1). **Frozen** — never re-derived; the set is the historical truth for per-category baselines (AC2). A tag later renamed/merged still resolves for *display* via `resolve_tag`, but membership is not changed. |
| | | **Unique `(impression, tag_id)`** — a tag appears at most once per impression. |

### `signals_engagement_event`  (one downstream behavioral act — append-only)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `kind` | enum (`EventKind`) | `click_through` · `subscribe` · `page_reengagement` · `share` · `off_platform_proxy`. The discriminator; **closed code enum**, no free-text (an unknown event type is unrepresentable). |
| `user` | FK → `accounts.Account`, `SET_NULL`, null | The acting user (anonymize-on-deletion, as above). |
| `app_id` | UUID, indexed | The `catalog.App.id` the act concerns (D-6 soft ref); validated at capture. |
| `impression` | FK → `Impression`, `SET_NULL`, null | **The originating impression where known** (AC3/AC5). **Required** for `click_through` and `off_platform_proxy` (a conversion must attribute to the instance); **optional** for `subscribe`/`page_reengagement`/`share` (may happen with no traceable impression). |
| `is_proxy` | bool, default `False` | **True only** for `off_platform_proxy` — the flag that marks a **secondary**, proxy-derived signal (AC7); on-platform events are always `False`. |
| `occurred_at` | timestamptz, indexed | When the act happened. |
| `created_at` | timestamptz | Insertion time. |

Index `(app_id, kind, occurred_at)` — the funnel reads conversions of app A by kind in a window.

### `signals_platform_visit`  (the return-to-platform substrate)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | — |
| `user` | FK → `accounts.Account`, `CASCADE` | The active user. **CASCADE** (not SET_NULL): a visit is a low-value, per-day retention tick that is **only** meaningful while joined to a live user's impressions — once the account is gone, anonymized visit ticks carry no corpus value and are pure noise, so they go with the account (§13). |
| `visit_date` | date (UTC), indexed | The day the user was active. **Unique `(user, visit_date)`** → idempotent: one row per user per day, however many requests. |
| `created_at` | timestamptz | First-seen-that-day insertion time. |

**Returns are derived, never stored (SC-9).** "Returned within 3d/14d of impression *I*" =
*∃* a `PlatformVisit` for `I.user` with `visit_date ∈ (I.occurred_at.date, I.occurred_at.date + N]`.
This is computed by the read path (§5b) from stored impressions + stored visits — **no
return-event row, no scheduled job, no backfill** (AC4/AC8). A *not-returned* outcome is the
absence of such a visit, which a stored "return event" could never represent.

**Lifecycle.** Impressions, impression-tags, and engagement events are **append-only** — written
once at capture, never mutated, never deleted except by the `user` anonymization edge above and
the no-auto-purge retention rule (§10/A3). Platform visits are inserted once per user-day and
likewise immutable. **One source of truth:** "what was shown" = `Impression`; "what categories
it had when shown" = `ImpressionTag` (frozen); "what the user then did" = `EngagementEvent`;
"was the user active on day D" = `PlatformVisit`; "what a tag means *now*" = `taxonomy.resolve_tag`
(not copied); "is the app real/accepted + its current tags" = `catalog.get_catalogued_app` (not
copied — only the snapshot is).

**Concurrency.** Events are independent inserts — no contended row, no lock needed. The only
idempotent write is `PlatformVisit`, made safe by the `(user, visit_date)` unique constraint +
`get_or_create` (a lost race raises `IntegrityError`, caught → treated as "already recorded").

**Crash/restart.** All state is DB-backed; no in-memory queue or counter. Each capture is a
single-row `transaction.atomic()` insert (impression + its tag rows are one transaction), so a
partial write never persists (AC11 fail-loud).

**Migration/retention.** Migration 0001 creates the four tables only (no content). The corpus is
retained for the full MVP with **no auto-purge** (A3/§10) because the H3 backtest needs the
history. Reverse = `migrate signals zero` drops the four tables (§12).

---

## 5. Interface contracts

One logic core: `capture` writes, `selectors` reads. **In-process only at MVP** — emitting
surfaces (`weekly-digest`, `app-pages`, `app-subscriptions`, `developer-updates`) call the
Python capture functions directly; the one reader (future developer-dashboard / editorial
backtest) calls the selectors directly or uses the read-only admin. No HTTP surface here (§2).

### 5a. Python capture contract (`apps.signals.capture`) — the single write path

```python
def record_impression(user, app_id: UUID, *, surface: Surface,
                      occurred_at: datetime | None = None) -> Impression   # AC1/AC2
def record_click_through(user, app_id: UUID, *, impression: Impression,
                        occurred_at=None) -> EngagementEvent               # AC3 (impression REQUIRED)
def record_subscribe(user, app_id: UUID, *, impression: Impression | None = None,
                    occurred_at=None) -> EngagementEvent                   # AC5
def record_page_reengagement(user, app_id: UUID, *, impression=None,
                            occurred_at=None) -> EngagementEvent           # AC5
def record_share(user, app_id: UUID, *, impression=None,
                occurred_at=None) -> EngagementEvent                       # AC6
def record_off_platform_proxy(user, app_id: UUID, *, impression: Impression,
                             occurred_at=None) -> EngagementEvent          # AC7 (is_proxy=True; the seam, §8)
def record_platform_visit(user, *, on_date: date | None = None) -> PlatformVisit  # AC4 substrate (idempotent)
```

**Invariants (enforced at this one boundary; illegal states unrepresentable):**
- **App must be real & accepted (D-6):** every `app_id` is validated with
  `catalog.get_catalogued_app(app_id)`; a missing/non-accepted app raises **`UnknownAppError`**
  and **nothing is written**. (`record_impression` already needs this call for the tag snapshot,
  so it is not an extra cost there; for high-volume conversion events a lightweight
  `catalog.is_catalogued_app(app_id) -> bool` is the named cheap-optimization seam — §9 — not
  built now, no out-of-area change made yet.)
- **Capture-time tag snapshot (AC1/AC2):** `record_impression` copies the app's **current**
  resolved `tag_id`s from `get_catalogued_app(...).tags` into `ImpressionTag` rows in the **same
  transaction** as the impression. The set is then frozen (never re-derived at read).
- **Impression linkage (AC3):** `record_click_through` and `record_off_platform_proxy` **require**
  an `impression`; the service asserts `impression.app_id == app_id` and `impression.user == user`,
  else **`ImpressionMismatchError`** — a click cannot be attributed to another app's or user's
  shown instance. For the optional-impression kinds, a supplied impression is validated the same
  way; `None` is allowed.
- **Actor is the caller (security, §10):** `user` is the authenticated account the surface holds
  (`request.user`); capture never accepts an arbitrary actor id from client input. A user emits
  events **only as themselves**.
- **`is_proxy` is set by the service, not the caller:** only `record_off_platform_proxy` writes
  `is_proxy=True`; the on-platform recorders force `False`. The secondary-vs-primary distinction
  (AC7) is structural, not a caller-supplied flag.
- **Idempotent visit (AC4):** `record_platform_visit` does `get_or_create(user, visit_date)`;
  a duplicate day is a no-op (the unique index guarantees one row/user/day).
- **Atomic + counted (AC11):** each recorder wraps its write(s) in `transaction.atomic()` and,
  on success, calls `observability.increment(<metric>, …)`. On failure it increments
  `capture_error` and re-raises (fail loud — §5d governs how the *surface* handles the raise).

Errors (raised loudly, never swallowed) in `signals.errors`: `UnknownAppError`,
`ImpressionMismatchError`. Bad argument types surface as Django `ValidationError`/`TypeError`.

### 5b. Python read contract (`apps.signals.selectors`) — raw funnel only (AC8/AC9)

```python
@dataclass(frozen=True)
class AppFunnel:
    app_id: UUID
    impressions: int
    click_throughs: int
    returns_3d: int            # DERIVED: impressed users active in (impression, +3d]
    returns_14d: int           # DERIVED: … +14d
    subscribes: int
    page_reengagements: int
    shares: int
    off_platform_proxy: int    # SECONDARY, is_proxy=True — reported separately (AC7)

def app_funnel(app_id: UUID, *, start: datetime, end: datetime) -> AppFunnel        # AC8 — the H3 backtest
def funnel_for_apps(app_ids: list[UUID], *, start, end) -> list[AppFunnel]          # AC9 — bulk, no N+1
def category_impressions(tag_id: UUID, *, start, end) -> int                        # per-category baseline (AC2)
```

**Invariants:**
- **Raw only — never scored (AC9/R5):** every field is a **count** (or a derived count). There
  is no normalization, weighting, ranking, or score anywhere in this path or schema. Turning
  these counts into a Quality Score is a *consumer's* job, out of scope (R5).
- **Returns derived from stored data, no backfill (AC4/AC8):** `returns_3d/14d` are computed by
  joining each in-window impression to the existence of a `PlatformVisit` for that user inside
  the window; window lengths come from `config.return_window_short_days/_long_days` (§9). The
  whole funnel is reconstructable from stored rows alone.
- **Proxy is segregated (AC7):** `off_platform_proxy` (is_proxy=True) is counted in its own
  field and is **never folded into** `click_throughs` or any on-platform count — the funnel is
  complete from on-platform signal alone, with the proxy reported honestly beside it.
- **Read surface is internal/admin (security, §5c/§10):** there is no anonymous projection.

### 5c. Surfaces (callers) and the admin

- **Emitting surfaces (writers)** — `weekly-digest` calls `record_impression` when it sends an
  issue (per app per recipient) and `record_click_through` when a recipient follows a curated
  link; `app-pages` calls `record_page_reengagement`/`record_share`; `app-subscriptions` calls
  `record_subscribe`. **Those surfaces are out of scope (brief A6/R6); signal-capture defines
  the contract they call** — they do not exist yet, so capture has no live emitter at ship time
  beyond tests + the visit middleware (a thin corpus until they ship is a product-surface gap,
  R6, not a capture defect).
- **Reading surface** — the future **developer-dashboard** and **editorial backtest** read
  `selectors.app_funnel`/`funnel_for_apps` in-process. There is **no DRF endpoint** at MVP; when
  developer-dashboard needs an HTTP projection it adds a thin `HasRole`-gated read view over
  these selectors (a one-feature-later addition, noted not built — no speculative abstraction).
- **Admin** — `signals.admin` registers the four models **read-only** (no add/change/delete
  permission) so ops can inspect the corpus during cold-start. Append-only is enforced in code,
  not left to admin discipline.

### 5d. The capture-failure contract (AC11 vs C5 — fail loud **and** non-blocking)

The brief sets a real tension: capture must be **non-blocking** to the user surface (C5) yet
**never silently lossy** (AC11/R4). Resolution — **loud = observable, not = breaks the user's
action**:

- Capture functions **raise on failure** (a half-written corpus is worse than a visible gap),
  and **always** increment `capture_error{kind=…}` + log with request context before re-raising.
  The error is therefore never silent — it is counted and alertable (§10).
- Each **emitting surface** chooses how to treat the raise, and the contract states the policy:
  - **Impression capture is corpus-critical** — `weekly-digest` treats a failed
    `record_impression` as part of *its own* send outcome (logged/counted against send
    completeness), because an uncaptured impression is a permanent corpus hole (the
    impression-completeness metric is the AC11 signal).
  - **Interactive conversion capture** (`click_through`/`subscribe`/`share`/`reengagement`) is
    wrapped by the surface so a capture failure is **counted but does not break the user's
    click** — the `capture_error` counter is the loud signal; the user still navigates.
- **Visit capture** (middleware, §3) is **fail-soft-but-counted**: a failed daily visit tick
  logs + increments `capture_error{kind=visit}` and never breaks page navigation (a single
  missed visit-day marginally under-counts returns, which the metric surfaces).

A durable **outbox/queue** (zero-loss async capture) is the named growth path if `capture_error`
is ever nonzero-and-unacceptable at scale — **not built now** (D-2; over-built for MVP volume).

---

## 6. The event model — why this shape (resolves R2)

The brief's R2 ("schema modeled badly → near-irreversible debt for the whole north-star
architecture") is the reason this is a **global** decision (D-7). The shape is chosen against
the brief's hard requirements, not taste:

- **The impression is a first-class anchor**, not just another event, because (a) it carries the
  **capture-time tag snapshot** no other event has, and (b) it has an **identity that downstream
  events reference** (AC3 "attributable to the instance"). Collapsing it into the generic event
  table would force nullable tag columns and a self-referential FK that means different things
  per row — illegal states made representable. So impression = its own table + a tag through-table.
- **Every other behavioral act shares one identical shape** — `(user, app_id, kind, impression?,
  is_proxy, occurred_at)` — with **no kind-specific columns** (even the proxy is just
  `is_proxy=True`). So they are **one append-only `EngagementEvent` table with a `kind`
  discriminator**, not five near-identical tables. Adding a future kind (e.g. `comment`,
  `rating_opened`) is **one enum value + one `record_*` wrapper**, no new table, no migration of
  the others — the cheapest place to change (CLAUDE.md §5.2).
- **Returns are a *derivation*, not a row** (SC-9, §4): they are a relationship between an
  impression and platform-visit activity, computed at read with no backfill — the only model
  that can represent "did **not** return" (an absence) and needs no scheduled job.
- **Keys are `user × App.id × impression`** with `App.id`/`Tag.id` as **soft UUID references**
  (D-6/D-5) — never a label, URL, or hard FK — so renames, merges, and the catalog's own
  schema stay decoupled from the corpus (the same discipline `catalog.AppTag` uses for tags).
- **Raw, never scored** — there is **no score/weight/rank column** in any table or read DTO
  (R5/AC9). The corpus stores facts; scoring is a downstream consumer.

This is the boring, well-understood "fact table + derivation" event model, which is exactly
what a future Quality-Score / rings / integrity pipeline expects to consume.

---

## 7. (No lifecycle state machine)

Unlike `submission-intake`, signal-capture has **no mutable lifecycle**: events are immutable
facts (append-only, §4). There is no state to transition, so there is no state machine and no
"current vs history" drift to manage. The only time-ordering that matters — *which impression a
conversion belongs to* — is captured explicitly by the `impression` FK, not inferred from
ordering. This is intentional and is what makes the corpus trustworthy for a backtest.

---

## 8. The off-platform proxy seam  *(resolves OQ-1; bounds R1/OQ-3)*

The SC-7 pivot demoted off-platform open/return to a **best-effort secondary** signal. This
design therefore builds a **seam, not an attribution engine** (R1: "do not over-engineer
attribution now"):

- The **only** mechanism shipped is `capture.record_off_platform_proxy(user, app_id,
  impression)`, which writes one `EngagementEvent(kind=off_platform_proxy, is_proxy=True)` linked
  to the originating impression. The funnel reports it as a **separate, flagged** number (§5b).
- **Who calls it and how an off-platform open/return is detected** (redirect-bounce, a
  return-to-platform ping, or tying an open to the user's next observed on-platform action) is
  **left open** (OQ-1) and **not built** — the niche is web-only (D-1), the spine is on-platform
  (SC-7), and any of those detectors is a self-contained future enhancement that calls this one
  seam. **The under-count is a documented limitation, not a bug** (OQ-3/R1): a user who clicks
  through and never returns is invisible to the proxy, which only depresses the *secondary*
  number, never the funnel's completeness (AC7 guarantees the funnel is whole from on-platform
  signal alone). A stronger return signal later plugs into the same seam with no schema change.

---

## 9. Non-functional handling

**Performance / scale.** Every read is a bounded, indexed aggregate. `app_funnel` is a small set
of `COUNT`/`GROUP BY` queries filtered by `(app_id, occurred_at)` and `(app_id, kind,
occurred_at)` (both indexed). **Return derivation** is the one non-trivial query: for each
in-window impression, an `EXISTS` of a `PlatformVisit` in the window — expressed as a single
correlated-aggregate query per app (not per-impression Python looping), so it is one indexed
query, not N. At founding volume (tens of apps, a small trusted cohort) this is trivial. **At
100× (D-2/§5.2):** the documented growth paths, **not built now**, are (a) a materialized
per-app/per-window funnel projection refreshed on a schedule, and (b) the
`catalog.is_catalogued_app(app_id) -> bool` cheap-existence selector so high-volume conversion
capture skips the heavier `get_catalogued_app`. Both are additive; neither is speculated today.
No O(n²), no in-memory state, no unbounded query.

**Return windows are config, not constants (CLAUDE.md §5.2 names "evaluation windows").** Added
to `apps.core.config` as typed tunables: `return_window_short_days` (default **3**) and
`return_window_long_days` (default **14**) — change-cheap, validated at startup, the single
source of truth the read path reads (no magic `3`/`14` in logic). A2's "exact tolerance" is thus
a one-line config change.

**Security (threat model).** See §10.

**Observability.** Reuses `apps.core.observability.increment`. New metric-name constants (added
to `apps/core/observability.py`, exactly as `taxonomy`/`catalog` did), 1:1 with the brief's
success metrics: `impression_captured`, `click_through_captured`, `subscribe_captured`,
`page_reengagement_captured`, `share_captured`, `platform_visit_captured`,
`off_platform_proxy_captured` (tagged `secondary`), and **`capture_error`** (tags: `kind`) —
the AC11/R4 loud-loss signal that **must stay 0** in a healthy system (**alert on any nonzero**).
Impression-completeness, click-through-attribution rate, return-rate observability, and per-app
reception availability are **computed by the read path** from stored rows (observable, not
counters), mirroring how `catalog` computes time-to-decision (CLAUDE.md §6.2). **Actionable
alerts only:** any nonzero `capture_error`; a sustained drop in impression-completeness.

**Rollback.** Additive new app with **no live emitter** yet (the emitting surfaces are out of
scope / unbuilt — §5c). There is nothing to feature-flag *off*; safety = **reversible migration**
(`migrate signals zero` drops the four tables) + removing the visit middleware from
`MIDDLEWARE`. A bad release is rolled back by reverting the deploy and, if needed, the last
migration (§12).

---

## 10. Security & privacy posture  *(resolves OQ-2 / realizes SC-6 / AC10)*

**Privacy posture (SC-6, ratified by brief approval DN-5).** The corpus records **only
pseudonymous, in-platform behavioral events keyed to `Account.id`**, for the **single purpose**
of backtesting a future Quality Score (H3), under **signup-ToS consent** (no per-event opt-in,
justified by the small hand-recruited trusted cohort), **retained for the full MVP with no
auto-purge** (A3 — the backtest needs the history). This is stated in human-readable form in
**`apps/signals/PRIVACY.md`** (AC10): *what* is recorded (the fields below), *why* (H3 backtest),
*how long* (no auto-purge), and *the deletion behavior* (below).

**Stored-fields whitelist (AC10 — "only posture-permitted fields").** An event row stores **only**:
the `Account` FK, the `App.id`, the `Tag.id` snapshot (impressions), the `EventKind`, the
`Surface`, the `impression` link, `is_proxy`, and timestamps. It **does NOT store** IP address,
user-agent, device fingerprint, precise geolocation, referrer, off-platform identifiers, or any
free-text — by schema (those columns do not exist). This makes over-collection unrepresentable.

**Account deletion (resolves the catalog §13 flag; SC-10).** `accounts.delete_account` **hard-
deletes** the `Account` row. Signal-capture's `user` FKs on `Impression`/`EngagementEvent` are
**`SET_NULL`**, so a deleted user's behavioral facts **survive as anonymized corpus rows**
(unlinked from any person) — respecting both the deletion right (the person is unlinked) and the
no-auto-purge corpus rule (the aggregate signal is kept). `PlatformVisit.user` is **`CASCADE`**
(a per-day tick is worthless once it can't be joined to a live user's impressions — §4/§13). The
deletion behavior is stated in `PRIVACY.md`. *(Whether anonymize-and-retain is the desired
deletion semantics is the one posture nuance to confirm with data; flagged SC-10, consistent
with how `catalog` flagged this exact interaction.)*

**Threat model.**
- *Forged actor / attribution:* a user can emit events **only as `request.user`** — capture
  never accepts an actor id from client input (§5a). One user cannot manufacture another's
  behavior.
- *Cross-app attribution forgery:* `record_click_through`/`record_off_platform_proxy` assert the
  impression's `app_id` and `user` match (§5a) → a conversion cannot be pinned to an app the
  user was not shown.
- *Data leakage:* the raw read path is **internal/admin-only** (no public endpoint, §5c); the
  admin is **read-only**. Behavioral data never leaves the platform through this feature.
- *Injection / bad input:* `app_id`/`tag_id` are UUIDs validated through the `catalog`/`taxonomy`
  selectors (no raw label/URL); `kind`/`surface` are closed code enums (no free-text). All at
  the single capture boundary, fail loud.
- *Attributability of the corpus itself:* every event is append-only with `created_at`; the
  read-only admin + `capture_error` metric make tampering/loss observable.

---

## 11. Cross-feature contract handed downstream  *(proposed global D-7)*

Recorded as global **D-7** on approval so the Quality Score, rings, integrity analysis,
`weekly-digest`, `app-pages`, `app-subscriptions`, `developer-updates`, and the
developer-dashboard build on it consistently:

- **A behavioral signal is an append-only event** in one of two shapes: an **`Impression`**
  (the anchor — its own UUID identity, `user × App.id`, surface, a **frozen capture-time
  `Tag.id` snapshot**) or an **`EngagementEvent`** (`kind ∈ {click_through, subscribe,
  page_reengagement, share, off_platform_proxy}`, `user × App.id`, an optional `impression`
  link, `is_proxy`). Events are **never mutated, never scored.**
- **Emit only through `signals.capture.*`** — the single write path that validates the app
  (D-6), snapshots tags, links the impression, and counts the write. No surface writes
  `signals_*` tables directly.
- **Apps are referenced by `App.id` (D-6) and tags by `Tag.id` (D-5)** — soft UUID refs,
  resolved at read; never by label/URL, never a hard FK.
- **Read only raw counts through `signals.selectors.*`** — the funnel is raw; **scoring/
  normalization is the consumer's job, never done here** (AC9/R5).
- **Returns are derived (impression × platform-visit), not stored;** the off-platform proxy is a
  **flagged secondary** signal, never required for funnel completeness (AC7).

A downstream feature that writes events outside `capture.*`, scores inside this layer, keys to
anything but `App.id`/`Tag.id`, or treats the proxy as primary would **break** this contract —
flagged here so it is not done.

---

## 12. Rollout strategy

Additive new app; **no live emitter exists yet** (the emitting surfaces are out of scope / not
built — §5c), so there is no backward-compat burden and no flag to protect a pre-existing surface:

1. Add `return_window_short_days`/`return_window_long_days` tunables to `apps/core/config.py`
   (+ `validate_all`); add this feature's metric-name constants to `apps/core/observability.py`.
2. Register `apps.signals` in `INSTALLED_APPS` and `signals.middleware.PlatformVisitMiddleware`
   in `MIDDLEWARE` (after `AuthenticationMiddleware` and `RequestContextMiddleware`).
3. Apply migrations (`migrate signals`) — creates the four tables. No content.
4. Capture goes live **as each emitting surface ships** (`weekly-digest` first — it produces the
   impressions). Until then the only writer is the visit middleware (return substrate) + tests.
5. No recurring job is scheduled (returns are derived at read; nothing expires — no auto-purge).

Rollback = revert deploy + remove the middleware + `migrate signals zero`.
**Handed downstream:** emitting/consuming features adopt the §11 / D-7 contract before they
emit or read any signal.

---

## 13. Self-critique & alternatives

**Attacks on the design and resolutions:**
- *"One `EngagementEvent` table with a `kind` discriminator is an EAV anti-pattern — won't it
  rot?"* No: the five kinds share an **identical** column shape (no kind-specific columns; even
  the proxy is just `is_proxy`), so this is a *fact table with a type tag*, not sparse EAV. The
  one field that legitimately varies — the impression link — is `nullable` with a per-kind
  required/optional rule enforced at the single capture boundary. Table-per-kind would add five
  near-identical tables and a five-way UNION in every funnel read for **zero** schema benefit.
  Chose the single table; recorded as an alternative.
- *"Deriving returns at read won't scale / isn't 'recorded'."* The brief's own AC4/metric say
  the return outcome must be **"determinable from on-platform data"** including **"returned vs.
  not"** — a *not-returned* outcome is an **absence**, which a stored event can never represent;
  derivation is the only correct model, and it needs **no backfill** (AC8). Scale: it is one
  indexed `EXISTS`-aggregate per app, trivial at founding volume; a materialized projection is
  the named 100× path (§9). Recorded as **SC-9**.
- *"Fail-loud (AC11) vs non-blocking (C5) is a contradiction."* Resolved in §5d: **loud =
  counted + logged + alertable**, not = throw in the user's face. Capture raises and counts;
  the *emitting surface* decides propagation per a stated policy (impression = corpus-critical;
  interactive conversion = counted-not-blocking; visit = fail-soft-but-counted). The
  `capture_error` metric is the never-silent guarantee.
- *"`SET_NULL` on deletion keeps behavioral data about a deleted user — is that allowed?"*
  At MVP the posture is pseudonymous, the cohort small/trusted, and `SET_NULL` **unlinks the
  person** while keeping the aggregate fact the H3 backtest needs (no-auto-purge, A3). The
  alternatives are CASCADE (purges corpus — defeats H3) and hard-block-deletion (violates the
  user's deletion right). Chose anonymize-and-retain; flagged **SC-10** to confirm with data.
  `PlatformVisit` is CASCADE because an unlinked visit tick is pure noise.
- *"No app-existence check could let signals key to a withdrawn/fake app."* Every `app_id` is
  validated via `catalog.get_catalogued_app` at capture (D-6); a non-accepted app raises
  `UnknownAppError`. The soft (non-FK) `app_id` is deliberate — a *later* app withdrawal must
  **not** cascade-erase historical signal (the corpus records that it *was* shown); that is the
  same soft-reference discipline `catalog.AppTag` uses for tags.
- *Simplification pass:* dropped a separate per-kind table set, a stored return-event table + its
  scheduled job, a generic JSON `metadata` column (no kind needs it — would invite silent schema
  drift), a session/page-view firehose (PlatformVisit's per-day tick is all returns need), and
  any score/weight column. Nothing remaining is untied to an AC.

**Alternatives considered (full rationale → DECISIONS on approval):**
- *Single wide polymorphic event table* (one table, nullable tag/window/impression columns, a
  type tag) — rejected: makes illegal states representable (a share with a return window; an
  impression with no tags) and buries the anchor's special role; chose impression-anchor +
  uniform engagement table.
- *Table-per-event-type* (5–6 tables) — rejected: identical shapes, so it adds tables + UNION
  reads for no benefit; a new kind would mean a new table instead of an enum value.
- *Materialized return-cohort table refreshed by a scheduled job* — rejected for MVP: invents a
  "did-not-return" representation problem, needs batch infra, and risks drift vs the source rows;
  derivation at read is exact and backfill-free (kept as the named 100× projection path).
- *Async outbox/queue capture (zero-loss)* — rejected for MVP: over-built for the volume (D-2);
  the synchronous fail-loud-and-count path is honest now, with the outbox as the named growth
  path if `capture_error` is ever nonzero-and-unacceptable.
- *CASCADE-delete a user's signals on account deletion* — rejected: destroys the corpus the H3
  backtest depends on; `SET_NULL` anonymization respects the deletion right without that loss.

**What the chosen design sacrifices:** no first-class stored "return" row (derived instead — a
read cost, bounded); no DB referential integrity on `app_id`/`tag_id` (boundary validation +
soft refs instead, by D-5/D-6 design); behavioral facts about a deleted user are *retained but
anonymized* (a posture call, SC-10); a thin corpus until the out-of-scope emitting surfaces ship
(R6 — a product-surface gap, by design not this feature's to solve); synchronous capture can
*visibly* (counted) drop an event under failure rather than guaranteeing zero-loss (the outbox is
the named path) — all documented, bounded trade-offs.

---

## 14. Traceability — every acceptance criterion maps to a design element

| AC | Design element(s) |
|----|-------------------|
| **AC1** Impression w/ user, `App.id`, unique id, timestamp, capture-time tags | `Impression` (UUID identity, `user`, `app_id`, `surface`, `occurred_at`) + `ImpressionTag` snapshot copied from `get_catalogued_app` in one txn (§4/§5a/§6) |
| **AC2** Stable user×App.id×impression keys; tags captured at show-time, not resolved live | UUID keys on every row; `ImpressionTag` frozen at capture; `resolve_tag` used only for display (§4/§6) |
| **AC3** Click-through linked to the originating **impression** (instance, not just app) | `record_click_through` **requires** `impression`; asserts `impression.app_id==app_id & user==user`; `EngagementEvent.impression` FK (§5a/§4) |
| **AC4** Return-to-platform @3d & @14d, distinguishable by window, user×app, directly observed | `PlatformVisit` substrate (middleware) + **derived** `returns_3d`/`returns_14d` in `app_funnel`; windows from config (§4/§5b/§9; SC-9) |
| **AC5** Subscribe + on-page re-engagement tied to user×App.id (+ impression where known) | `record_subscribe` / `record_page_reengagement` → `EngagementEvent` (optional `impression`) (§5a/§4) |
| **AC6** Share tied to App.id + sharing user | `record_share` → `EngagementEvent(kind=share)` (§5a/§4) |
| **AC7** Off-platform proxy = flagged **secondary**; funnel complete without it | `record_off_platform_proxy` (`is_proxy=True`, service-set); `off_platform_proxy` reported in its own funnel field, never folded in (§5b/§8) |
| **AC8** Full on-platform funnel reconstructable from stored data, no backfill | `app_funnel(app_id, start, end)` — counts + derived returns from stored rows only (§5b/§6) |
| **AC9** Developer-readable **raw** funnel via a defined read path; never scored | `funnel_for_apps` returns raw counts; **no score/weight column** in schema or DTO (§5b/§4/§11; R5) |
| **AC10** Privacy posture: only permitted fields; what/why/retention human-readable | Stored-fields whitelist (no IP/UA/PII by schema) + `apps/signals/PRIVACY.md`; SC-6 posture (§10) |
| **AC11** Failed capture surfaces (logged/alertable) + completeness metric reflects it — never silent | Capture raises + increments `capture_error{kind}`; per-surface policy (§5d); completeness computed at read (§9/§10) |

Every component's failure behavior is documented in §5d/§9/§10; no contract above contains "TBD"
(OQ-1 seam'd in §8, OQ-2 resolved in §10, OQ-3 bounded in §8/§13).
