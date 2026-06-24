# DESIGN — developer-updates

*Stage 2 artifact (Software Architect). Status: **PENDING APPROVAL** (DN-DU-DESIGN — see
CONTROL.md). Reads the **APPROVED** [FEATURE_BRIEF.md](FEATURE_BRIEF.md) + the codebase
contracts it composes. No Stage advance until the user approves.*

This design was produced via the 14-step protocol in
[phase-2-architect.md](../../process/personas/phase-2-architect.md). It resolves the two
Stage-2 open questions the brief carried — **OQ-DU-1** (the reverse-audience read) and
**OQ-DU-2** (the transparency line, vision Open Q #5) — and decides the two calls the brief
deferred to design: **model-vs-model-less** (C6) and the **rate-limit shape** (AC8).

---

## 1. Problem, in one sentence (SCOPE)

Give a developer a single-producer write path to post **update** / **early-access** notices
about an app they own, so those notices appear — newest-first, to **only that app's current
followers** — in the existing followed-apps feed (filling the **AS-3** empty-until-producer
seam), **without** posting ever emitting a score-bearing signal or buying reach.

- **Stakeholders:** developers (post), followers (receive), the platform (integrity — the
  channel must not become a "gaming manual").
- **Lifespan:** platform feature (the dev↔audience relationship is a north-star surface,
  vision §6/§8). Effort matches: a feature-owned table + a clean producer seam, no hacks.
- **Out of scope** (from the brief, unchanged): email/push, update re-boosts/impression
  allocation, early-access *entitlement* enforcement, two-way messaging, billing, showing
  reception/analytics (that is `developer-dashboard`), rich media/formatting, a new D-7
  `EventKind`/`Surface`, scheduling/drafts, and **editing** a posted notice (correct = withdraw
  + repost at MVP; a named future seam).

---

## 2. Requirements & assumption ledger (REQUIREMENTS)

**Functional (each maps to an AC in §9):** post an update (AC2) / early-access note (AC3),
owner+role gated (AC1); the notices surface as the AS-3 feed producer (AC4); reach is
audience-scoped and buys nothing (AC5); posting emits no manufactured signal (AC6); the owner
can list + withdraw their notices (AC7); posting is rate-limited (AC8).

**Non-functional:** the feed producer read and the audience read must be **bounded /
independent of follower count** (R3); posting must be **structurally** incapable of reaching a
non-follower (M5 = 0) or of writing into the corpus (R1); all limits config-driven (§5.2).

**Assumption ledger** — every dependency was read in the codebase before designing:

| # | Assumption | Status | Evidence |
|---|------------|--------|----------|
| L1 | The AS-3 seam is `apps/subscriptions/notices.py` — frozen `Notice` DTO + `notices_for_apps(app_ids) -> []`, one call site (`subscriptions/views.py::_notices_fail_soft`), rendered fail-soft. | **verified** | read [notices.py](../../apps/subscriptions/notices.py), [views.py](../../apps/subscriptions/views.py) |
| L2 | The feed already passes the **followed** app_ids into `notices_for_apps` (it computes `followed_apps` first). The producer therefore never enumerates followers — delivery is **pull**. | **verified** | `views.feed` → `_notices_fail_soft([app.id for app in apps])` |
| L3 | Owner-scoping = `catalog.get_owned_app(owner, app_id)` / `list_owned_apps(owner)` (D-6); a non-owner id is `None`, indistinguishable from "not found". | **verified** | [catalog/selectors.py](../../apps/catalog/selectors.py) L76–90 |
| L4 | Role gate = `accounts.permissions.require_role(DEVELOPER)` (D-3), fail-closed. | **verified** | [permissions.py](../../apps/accounts/permissions.py), [roles.py](../../apps/accounts/roles.py) |
| L5 | The audience store `subscriptions_subscription(user, app_id)` has **no** reverse "who follows X" selector; the unique `(user, app_id)` index leads with `user`, so an `app_id`-only count is unindexed today. | **verified** | [subscriptions/selectors.py](../../apps/subscriptions/selectors.py), [models.py](../../apps/subscriptions/models.py) |
| L6 | Returns are already captured by existing kinds (`apps/pages` emits `APP_PAGE` / `page_reengagement`); `signals.kinds` has no notice kind and none is needed. | **verified** | observability `PAGE_REENGAGEMENT_CAPTURED`, brief C5 |
| L7 | Stack = Django + PostgreSQL (D-4); config/observability house patterns in `apps/core`. | **verified** | [config.py](../../apps/core/config.py), [observability.py](../../apps/core/observability.py) |
| L8 | Durable rate-limiting can be **derived from the notice table** (count rows in a window) — no cache infra needed, unlike the auth path which leaves no durable row. | **verified** | [core/ratelimit.py](../../apps/core/ratelimit.py) (cache-window) vs. the durable rows here |

---

## 3. Current state (CONTEXT — diffable against reality)

```
follower (user)                          developer (owner)
   │ GET /subscriptions/feed                  │  (no surface today)
   ▼                                          ▼
subscriptions/views.feed
   ├─ selectors.followed_apps(user, limit)  → [CatalogApp]      (2 queries, bounded)
   └─ notices.notices_for_apps([app.id…])   → []   ◄────────────  AS-3 SEAM: no producer
        rendered fail-soft in feed.html (auto-escaped)
```

The follow graph (`subscriptions_subscription`), the destination (`apps/pages` app-page +
its `APP_PAGE`/`page_reengagement` emit), and the corpus (`apps/signals`) are all built and
released. The **only** missing piece is a producer authoring `Notice`s and the one repoint of
`notices_for_apps`. Nothing reads `subscriptions_subscription` by `app_id` yet.

---

## 4. Proposed architecture (MODULES)

A **new feature-owned app, `apps/updates/`**, that owns notices and the developer-facing
channel UI, plus **two minimal, additive edits to the closed `apps/subscriptions/`**: the
AS-3 seam repoint and one reverse-audience selector (+ its backing index).

```
DEVELOPER SIDE (new: apps/updates/)                    FOLLOWER SIDE (existing: apps/subscriptions/)
────────────────────────────────────                   ──────────────────────────────────────────────
views (role+owner gated, GET/POST)                     views.feed (unchanged)
  GET  /updates/                  my channels             └─ notices.notices_for_apps(followed_ids)   ← REPOINTED
  GET  /updates/apps/<id>/        one channel                    │  (the single adapter: maps → Notice)
  POST /updates/apps/<id>/post    create notice                  ▼
  POST /updates/apps/<id>/notices/<nid>/withdraw          updates.selectors.published_notices_for_apps(ids, limit)
        │            │                                           (1 query, bounded by limit — R3)
        ▼            ▼
  services.post_notice / withdraw_notice                 selectors.subscriber_count(app_id)  ← NEW reverse read
    • get_owned_app gate (D-6, AC1)                            (1 indexed COUNT — backs the audience hint + M2)
    • validate kind/title/summary
    • rate-limit: count own recent rows (AC8)
    • CREATE/DELETE updates_notice
    • imports NO signals.capture (AC6, AST-enforced)
        │
        ▼
  models.Notice  →  table  updates_notice
  selectors.notices_for_channel(owner, app_id)  → [PublishedNotice]  (AC7 manage/withdraw list)
```

**Dependency direction is a strict DAG (no cycle):**
`subscriptions.notices → updates.selectors → updates.models` (consumer → producer), and
`updates.views → subscriptions.selectors.subscriber_count` (producer's UI → audience read).
`subscriptions.selectors` imports nothing from `updates`; `updates.selectors`/`models`/`services`
import nothing from `subscriptions`. The two packages reference each other only at the two
named seams above, and never in a way that forms a module-load cycle (verified file-by-file in
§13). This is why the AS-3 render DTO stays owned by `subscriptions` and the seam function is
the **adapter** (see DU-DESIGN-2).

**Single responsibilities:**
- `updates.models.Notice` — the durable shape only (no logic).
- `updates.services` — the **only** writer of `updates_notice`; owns the owner-gate, validation,
  and rate-limit; the **only** place a notice is created or withdrawn.
- `updates.selectors` — the read API: `published_notices_for_apps` (the AS-3 producer feed read)
  and `notices_for_channel` (the owner's manage list). Returns frozen `PublishedNotice` DTOs,
  never ORM rows.
- `updates.views`/`urls`/templates — thin HTTP: parse, call service/selector, render/redirect;
  no ORM, no business logic (mirrors the pages/ratings/subscriptions house pattern).
- `subscriptions.notices.notices_for_apps` — repointed to the adapter (the one place, per AS-3).
- `subscriptions.selectors.subscriber_count` — the additive reverse-audience read (OQ-DU-1).

---

## 5. Data design (DATA & STATE)

### 5.1 New table — `updates_notice` (owned by `apps/updates/`; C6 → owns a table)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID pk | `uuid4`, non-editable |
| `app_id` | UUID | **soft D-6 ref** (no DB FK) — validated at the write boundary via `get_owned_app`; mirrors `subscriptions`/`ratings`. A later app withdrawal must not cascade-erase posted notices; the feed silently drops a withdrawn app (accepted-only resolution upstream). |
| `author` | FK → `AUTH_USER_MODEL`, **`CASCADE`**, `related_name="notices"` | who posted — drives attribution, the per-developer/per-app rate-limit, and the "my notices" list. **CASCADE** (not `SET_NULL`): a notice is withdrawable **content**, not retained D-7 corpus, so account deletion removes it with **no edit to `accounts`** (the AS-5 pattern). The behavioral residue of engagement still survives as the followers' own anonymized return events. |
| `kind` | `CharField(choices=NoticeKind)` | `"update"` \| `"early_access"` — exactly the pinned `Notice.kind` enum (DU-1). |
| `title` | `CharField(max_length=200)` | defensive DB cap; the **product** limit is `config.updates_title_max_length()` (≤200), validated at the boundary. |
| `summary` | `TextField` | validated at the boundary against `config.updates_summary_max_length()` (mirrors `ratings.review_text`). |
| `published_at` | `DateTimeField(auto_now_add=True)` | post is immediate (no drafts/scheduling); drives feed + manage order. |

No `updated_at` (notices are immutable — edit is out of scope), **no score/weight/rank
column** (structural — posting confers no corpus value, AC6), no `withdrawn_at` (withdraw =
hard delete; the store is *exactly* the currently-published set — one source of truth, mirrors
unfollow). `db_table = "updates_notice"`, `ordering = ["-published_at"]`.

**Indexes:**
- `updates_app_published_idx` on `(app_id, published_at)` — backs the AS-3 producer feed read
  (`app_id IN (...) ORDER BY published_at DESC LIMIT n`), the owner manage list (`app_id=` +
  `author=` residual), and the rate-limit window count (`app_id=` + `author=` + `published_at >= t`).
  One composite index serves all three because `app_id` leads every query; `author` is a cheap
  residual filter on the inherently small per-app notice set (posting is rate-limited).
  *Growth seam (named, not built):* if cross-app feed ordering ever dominates, add a global
  `published_at` index — recorded here, not pre-built (§5.5 no speculation).

### 5.2 Additive change to the closed `apps/subscriptions/` — the reverse-audience index

`subscriptions_subscription` gains one **additive** index `subscriptions_app_idx` on `(app_id)`
to back `subscriber_count(app_id)` (an `app_id`-only COUNT — unindexed today, L5). Additive,
reversible, contract-preserving (the precedent is open-search-browse adding columns/indexes to
the closed `catalog`). No new column, no behavior change to existing follow reads/writes.

### 5.3 Lifecycle
- **Create:** `post_notice` (owner-gated, validated, rate-limited); `published_at = now`.
- **Mutate:** none — notices are immutable (correct via withdraw + repost).
- **Delete:** withdraw = **hard delete**, scoped by `author` + `app_id` + `id` (AC7, no IDOR);
  account deletion → `CASCADE` removes the author's notices.
- **Retain:** none required (not corpus). **Concurrency:** the rate-limit count→create has a
  benign TOCTOU window (two concurrent posts could both pass the count by one). This is an
  accepted, bounded trade-off — the limit is a **spam guardrail**, not a correctness invariant
  (contrast `subscriptions.follow_app`, whose M5 1:1 *did* need `transaction.atomic`). Posting is
  a low-frequency human action; no `SELECT FOR UPDATE` is warranted (§13 self-critique).

---

## 6. Interface contracts (INTERFACES — no "TBD")

### 6.1 `apps/updates/selectors.py`
```python
@dataclass(frozen=True)
class PublishedNotice:
    id: UUID            # for the owner's withdraw control (AC7); dropped by the feed adapter
    app_id: UUID
    kind: str           # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime

def published_notices_for_apps(app_ids: list[UUID], *, limit: int) -> list[PublishedNotice]:
    """Notices for the given apps, newest-first, capped at `limit` — the AS-3 producer read.
    One query (filter app_id IN, order -published_at, slice limit). [] for empty input.
    Bounded by `limit` and independent of follower count (R3)."""

def notices_for_channel(owner, app_id: UUID) -> list[PublishedNotice]:
    """The owner's own notices for one app, newest-first (AC7 manage list). One query."""
```

### 6.2 `apps/updates/services.py` (the only writer; imports **no** `signals.capture`)
```python
def post_notice(author, app_id: UUID, *, kind: str, title: str, summary: str) -> PublishedNotice:
    """Create one notice on an app `author` owns.
    Raises AppNotOwnedError  → get_owned_app(author, app_id) is None (AC1; 404, no oracle).
    Raises InvalidNoticeError → kind not in NoticeKind, or blank/over-length title/summary (AC2/3).
    Raises RateLimitedError   → ≥ updates_max_posts_per_window() own notices for this app within
                                updates_post_window_hours() (AC8; nothing created).
    On success: one updates_notice row; counts UPDATES_NOTICE_POSTED{kind}."""

def withdraw_notice(author, app_id: UUID, notice_id: UUID) -> bool:
    """Hard-delete the author's own notice (scoped author+app_id+id → no IDOR). Idempotent:
    returns False if no matching row (a non-owner/unknown id deletes nothing — AC7). Counts
    UPDATES_NOTICE_WITHDRAWN on a real delete."""
```

### 6.3 `apps/subscriptions/selectors.py` (additive — OQ-DU-1)
```python
def subscriber_count(app_id: UUID) -> int:
    """How many users currently follow `app_id` — one indexed COUNT (subscriptions_app_idx).
    Bounded, follower-count-independent in query terms. Backs the post-form audience hint and
    the M2 reach metric. Reverse of the user-scoped is_following/followed_apps."""
```

### 6.4 `apps/subscriptions/notices.py` (the AS-3 repoint — the single adapter, DU-DESIGN-2)
```python
def notices_for_apps(app_ids: list[UUID]) -> list[Notice]:
    """Now delegates to updates.selectors.published_notices_for_apps(app_ids,
    limit=config.updates_feed_notice_limit()) and maps each PublishedNotice → the frozen
    render Notice (drops id). Newest-first; [] when none. The feed template renders unchanged."""
```
The `Notice` DTO and its single call site are **untouched** — only the body changes, exactly as
AS-3 promised ("the one place to repoint; the feed renders `Notice`s unchanged").

### 6.5 UI states (UX — server-rendered, auto-escaped, no JS)
- **GET `/updates/`** — *My channels*: the developer's owned **accepted** apps (`list_owned_apps`
  filtered to accepted via the catalog shape), each linking to its channel. Empty state: "You
  have no accepted apps yet." (role-gated; non-developers 403 via `require_role`).
- **GET `/updates/apps/<id>/`** — *Channel*: the post form (kind/title/summary), an **audience
  hint** ("Reaches N current followers" via `subscriber_count`, fail-soft → hidden), and the
  owner's notices (newest-first) each with a **Withdraw** button. Non-owner/unknown id → **404**
  (AC1, indistinguishable). Empty notices state: "No notices yet — post your first update."
- **POST post** — success → PRG to the channel with a success message; `RateLimitedError`/
  `InvalidNoticeError` → PRG back with a clear error message, **nothing created** (AC8/AC2).
- **POST withdraw** — PRG to the channel; the withdrawn notice is gone from the list and from
  every follower's feed (the feed re-reads each request — AC7, no dangling ref, no error).

---

## 7. Failure modes (FAILURE — detection + response, never silent)

| Component | Failure | Response |
|-----------|---------|----------|
| `post_notice` create | DB write raises | **Fail-soft to the user** (message + PRG, durable state = *not posted*; logged `UPDATES_POST_FAILED`), mirroring `subscriptions.follow`'s view contract. No corpus coupling → no 500 needed. |
| owner gate | `get_owned_app` is `None` | `AppNotOwnedError` → **404** (no ownership oracle, AC1). |
| validation | bad kind / blank / over-length | `InvalidNoticeError` → message, nothing created (`UPDATES_POST_REJECTED{reason=invalid}`). |
| rate limit | over the window limit | `RateLimitedError` → message, nothing created (`UPDATES_POST_REJECTED{reason=rate_limited}` — M6). |
| channel notices read | `notices_for_channel` raises | **Fail-soft**: render the post form + a "couldn't load your notices" notice; `UPDATES_CHANNEL_DEGRADED`. The dev can still post. |
| audience hint | `subscriber_count` raises | **Fail-soft**: hide the hint; `UPDATES_AUDIENCE_DEGRADED`. Never blocks posting. |
| **AS-3 producer** | `published_notices_for_apps` raises | Caught by the **existing** `subscriptions.views._notices_fail_soft` → "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`. The feed **never errors** (AC4/AC7) — preserved structurally; the producer changes the body, not the wrapper. |

**Trust boundaries:** every write validates at the boundary (owner, role, kind, lengths,
rate); the `app_id` is a soft ref validated via `get_owned_app`; `notice_id` is scoped by
`author`+`app_id` (no IDOR). Blast radius is contained to `updates_notice`; a producer fault
degrades only the feed's notice region, never the follow graph or the corpus.

---

## 8. The transparency line — OQ-DU-2 resolved (SECURITY / R1)

Traced end-to-end, the post → feed → return path writes **no developer-triggerable score-bearing
signal** into the corpus the Quality Score will trust:

1. **Post** writes one row to `updates_notice`. `apps/updates` **imports no `signals.capture`**
   — enforced **structurally** by an AST import-absence test (the precedent: `apps/discovery`,
   `apps/dashboard`). A notice is *content*, not an impression/event (AC6).
2. **Feed render** shows the notice region — pure read/render, emits nothing (viewing the feed
   is not an `APP_PAGE` impression). The notice is keyed by `app_id` and the feed only requests
   the user's **followed** app_ids → a non-follower is **structurally** unreachable (M5 = 0, the
   pull model — §10/DU-DESIGN-1), and no impression is injected (AC5).
3. **Return** — only when a follower *chooses* to click through does the **existing** `apps/pages`
   emit an `APP_PAGE`/`page_reengagement` event: the **user's own** action, which the developer
   cannot trigger at will. Rate-limiting (AC8) caps even the content-spam vector.

So the developer controls *content* (reaching only an audience they already earned) but never
*signal*. That is the line. The structural guarantee is the no-`signals.capture` import; the
behavioral guarantee is that every corpus entry requires a real user action.

**Other security:** role gate (D-3, fail-closed) + owner gate (D-6) on every mutation; POST+CSRF;
no IDOR (own-data-only scoping); title/summary are untrusted dev input shown to followers →
**must stay auto-escaped** in both the channel and the feed (`feed.html` already renders `Notice`
fields with Django's default escaping; the producer must never `mark_safe`), bounded by the
length caps; author FK makes every notice attributable/auditable.

---

## 9. Acceptance criteria → design element (TESTS map)

| AC | Design element |
|----|----------------|
| AC1 owner+role gate | `require_role(DEVELOPER)` on every view + `get_owned_app` in `post_notice`/channel (`None`→404, indistinguishable) |
| AC2 post update | `post_notice(kind="update")` → `updates_notice` row honoring the pinned `Notice` shape |
| AC3 post early-access | `post_notice(kind="early_access")`, same contract |
| AC4 AS-3 producer | `notices_for_apps` repoint → `published_notices_for_apps` mapped to `Notice`, newest-first; `[]`→existing empty state |
| AC5 audience-scoped, M5=0 | pull model (notices keyed by `app_id`; feed pulls followed ids) — non-follower structurally unreachable; no impression injected |
| AC6 no manufactured signal | `apps/updates` imports no `signals.capture` (AST test); returns counted only via existing pages kinds |
| AC7 manage/withdraw | channel view (`notices_for_channel`) + `withdraw_notice` (hard delete, scoped) + feed re-read tolerance |
| AC8 rate limit | `post_notice` counts own recent rows in `updates_post_window_hours()` vs `updates_max_posts_per_window()`; config-driven |

**Metrics:** M1 `UPDATES_NOTICE_POSTED` (first post per dev) · M2 analyst-derived from
`subscriber_count` × posting apps · M3/M4 from existing `signal-capture` returns (not this
feature's emit) · **M5 structural** (asserted in tests: a non-follower's feed never contains the
notice) · M6 `UPDATES_POST_REJECTED{reason=rate_limited}` + post rate.

**Edge cases:** empty followed set; app withdrawn after a notice (feed drops it, no error);
over-length title/summary; unknown kind; concurrent posts at the limit boundary; withdraw of an
already-withdrawn/foreign id (no-op, no leak); huge follower count (producer stays `limit`-bounded).

---

## 10. Trade-offs & alternatives (TRADE-OFFS — ≥2 approaches)

**Chosen: pull delivery + feature-owned table + seam-adapter.** Notices live in `updates_notice`
keyed by `app_id`; the feed *pulls* notices for the apps it already resolved. Sacrifices: no
per-user read/unread state, no edit, no drafts/scheduling (all named future seams); a benign
rate-limit TOCTOU (§5.3); and a rollback that is a **seam-revert + app-removal**, not a single
include-removal (§12) — the honest cost of being the AS-3 producer.

Rejected:
1. **Push / fan-out** (write a feed-item row per follower at post time) — O(followers) write per
   post (R3 fan-out), needs a per-user feed-item table, and *risks* reaching beyond current
   followers if scoping drifts. The pull model makes **M5 = 0 structural** and posting O(1).
2. **Provider registry** in `subscriptions.notices` (pluggable producers) — AS-3 **explicitly**
   rejected speculative registry machinery; one named producer = a direct repoint (§5.5).
3. **`updates` imports `subscriptions.notices.Notice` directly** — forms a `subscriptions ↔
   updates` module cycle. The seam **adapter** maps `PublishedNotice → Notice` instead, keeping
   the dependency a clean DAG and the render DTO owned by its definer (DU-DESIGN-2).
4. **Soft-delete withdraw** (`withdrawn_at`) — no retention requirement; hard delete keeps one
   source of truth = the current published set (mirrors unfollow).
5. **Cache-window rate limit** (reuse `core.ratelimit`) — durable notice rows exist, so counting
   them is **exact and multi-worker-correct without Redis**; cache windows suit the auth path,
   which leaves no durable row (DU-DESIGN-4).
6. **Model-less `updates`** (mirror `apps/pages`/`dashboard`) — notices are durable authored
   content with no existing home; a table is required (C6 → DU-DESIGN-3).

---

## 11. Non-functional handling (OPERATIONS)

- **Performance:** producer read = 1 query, `limit`-bounded (R3); audience read = 1 indexed
  COUNT; rate-limit = 1 indexed COUNT; post = 1 owner read + 1 insert. No N+1, all bounded at
  100× followers/notices.
- **Config (CHANGE — the change-cheap constants, §5.2):** add to `apps/core/config.py`
  (validated at startup by `validate_all`): `updates_max_posts_per_window` (default 5),
  `updates_post_window_hours` (default 24), `updates_feed_notice_limit` (default 50),
  `updates_title_max_length` (default 120), `updates_summary_max_length` (default 4000). No
  magic numbers in logic.
- **Observability (new counters):** `UPDATES_NOTICE_POSTED{kind}`, `UPDATES_NOTICE_WITHDRAWN`,
  `UPDATES_POST_REJECTED{reason}`, `UPDATES_POST_FAILED`, `UPDATES_CHANNEL_DEGRADED`,
  `UPDATES_AUDIENCE_DEGRADED`. **The feed-producer health signal is the existing
  `SUBSCRIPTION_NOTICE_DEGRADED`** (not re-added). **No new hard "must stay 0" alert** — M5=0 is
  structural (asserted in tests), and post failures fail soft; an operator watches
  `SUBSCRIPTION_NOTICE_DEGRADED` (feed) and `UPDATES_POST_FAILED` (write) as the actionable health
  signals, with `UPDATES_POST_REJECTED{reason=rate_limited}` as the M6 trend (expected, not an alert).
- **Logging:** house pattern — contextual `logger.info`/`warning`; the request filter carries the
  actor UUID. No PII in notice logs (log `app_id`/`notice_id`, never email).

---

## 12. Rollout & rollback (ROLLOUT)

**Activation (three parts):** (1) `"apps.updates"` in `INSTALLED_APPS`; (2)
`path("updates/", include("apps.updates.urls"))` in `config/urls.py`; (3) the **seam repoint**
in `subscriptions/notices.py`. Migrations: `updates/0001_initial` (the table) + `subscriptions/0002`
(the additive `subscriptions_app_idx` index). Both additive and reversible; existing data is
untouched.

**Rollback** (honest — this is the first feature that repoints a *closed* app's seam, so it is
**not** a single-include removal): revert `subscriptions/notices.py::notices_for_apps` to the
empty-seam body (`return []`) **and** remove the `updates/` include + the `INSTALLED_APPS` line.
The feed instantly returns to its empty-until-producer state; `updates_notice` + the
`subscriptions_app_idx` index can remain inert or be migrated down (`migrate updates zero`,
`migrate subscriptions 0001`). Rehearsal (Stage 5): up → both routes resolve + feed shows posted
notices → revert the seam + remove include/INSTALLED_APPS → feed shows the empty state again,
`subscriptions`/`catalog`/`signals` suites stay green, `git diff` on the reverted seam empty.

**Backward compat:** the `Notice` render DTO and its call site are unchanged, so the feed is
forward/backward compatible across the repoint; a withdrawn or post-withdrawal-stale id simply
drops out (the producer returns only current rows).

---

## 13. Self-critique & assumption recheck (SELF-CRITIQUE)

- **Cycle check (the load-bearing risk):** traced module-by-module — `subscriptions.notices →
  updates.selectors → updates.models/core.config`; `updates.views → subscriptions.selectors
  (subscriber_count) / updates.services / updates.selectors`; `subscriptions.selectors → catalog,
  subscriptions.models` (no `updates`). No module imports back into a module that (transitively)
  imports it at load time → **no import cycle**. The package-level mutual reference is confined to
  the two named seams and is a DAG.
- **Is the reverse read even needed for delivery?** No — and that is the key finding (OQ-DU-1):
  the AS-3 seam is **pull**, so delivery needs zero reverse read; the reverse read is only for the
  **audience hint + M2**. This is what makes M5=0 structural and kills the R3 fan-out.
- **Rate-limit TOCTOU** — acknowledged and accepted as a bounded spam guardrail, not a correctness
  invariant (§5.3); no locking added (would be premature).
- **Editing notices** — deliberately omitted; withdraw + repost is the honest MVP. Named seam.
- **Simplification pass:** one table, one new selector + one new index on `subscriptions`, one
  seam repoint, five config tunables, six counters. No registry, no fan-out table, no soft-delete,
  no new D-7 kind/Surface, no global ADR. Nothing here is unattached to an AC/metric/risk.

---

## 14. Decisions (DELIVER — logged PROPOSED in [DECISIONS.md](DECISIONS.md))

- **DU-DESIGN-1** — **Pull delivery, notices keyed by `app_id`** (resolves OQ-DU-1's delivery
  half + AC5/M5): the feed pulls notices for followed apps; no fan-out, M5=0 structural.
- **DU-DESIGN-2** — **AS-3 repoint is the single adapter**; `updates` returns `PublishedNotice`,
  the seam maps → the `subscriptions`-owned `Notice`. Keeps the dependency graph a DAG.
- **DU-DESIGN-3** — **`apps/updates/` owns `updates_notice`** (C6 resolved: a table, not
  model-less); hard-delete withdraw; no score/`updated_at`/`withdrawn_at` columns.
- **DU-DESIGN-4** — **Durable, table-derived rate limit** (AC8): count own recent rows in a
  config window; exact + multi-worker-correct without cache infra.
- **DU-DESIGN-5** — **Transparency line verified** (OQ-DU-2): `updates` imports no
  `signals.capture` (AST-enforced); the only corpus entries are users' own returns via existing
  kinds. Posting is inert to the corpus.
- **DU-DESIGN-6** — **Additive reverse-audience read** `subscriptions.selectors.subscriber_count`
  + the additive `subscriptions_app_idx` index (OQ-DU-1's reporting half / the audience hint).

**Global ADRs:** none. Reuses **D-3** (role gate), **D-6** (owner-scoping / accepted catalogue),
**D-7** (corpus — consumed, not extended), and the **AS-3** producer contract. Stack unchanged
(D-4: Django + PostgreSQL).

**Smallest useful first version = the whole brief slice** (post update/early-access, the AS-3
producer, manage/withdraw, rate limit). **Revisit once real usage exists:** edit-a-notice, a
dedicated notice `Surface` for click-attribution, per-user read state, and cross-app feed
ordering at scale (the global `published_at` index seam).

---

## 15. Exit checklist

- [x] Every AC (AC1–AC8) maps to ≥1 design element (§9).
- [x] All interfaces fully specified — no "TBD" (§6).
- [x] Every component's failure behavior documented (§7).
- [x] OQ-DU-1 (reverse read) + OQ-DU-2 (transparency line) resolved (§6.3/§8/§14).
- [x] Honors CLAUDE.md §5 (scalable/bounded, readable, partitioned, fail-loud-or-soft-by-design,
      one source of truth, design-for-deletion) with no speculative abstraction.
- [ ] **User approval (DN-DU-DESIGN)** — pending; no Stage advance until approved.
```
