# DECISIONS — developer-updates

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 — Product Analyst (RESOLVED, DN-20 approved 2026-06-24)

These were the scoping calls bundled into the brief-approval decision **DN-20** (CONTROL.md).
The user approved the brief + all three as recommended (2026-06-24) — **DU-1/DU-2/DU-3 → RESOLVED**.

### DU-1 (DN-20.a) — Early-access is a notice *kind*, not an entitlement mechanism
**Choice:** At MVP, "early-access" is one **kind** of notice (an announcement), matching the
already-pinned AS-3 contract (`kind ∈ {"update", "early_access"}`). Gating actual access to a
pre-release build/key is **out of scope**.
**Why:** The render contract `app-subscriptions` pinned already enumerates `early_access` as a
notice kind — honoring it is the minimum honest surface (CLAUDE.md §5.5, no speculative
machinery). Entitlement enforcement is a separate, larger problem (auth to a build, keys,
revocation) with no upstream dependency built.
**Rejected:** A third dedicated feature for early-access (the Stage-1 review already chose not
to split — revisit only if it grows); building access-gating now (speculative).

### DU-2 (DN-20.b) — Distribution at MVP = the in-platform followed-apps feed only
**Choice:** Notices are delivered by repointing the AS-3 `notices_for_apps` seam so they
render in the **existing followed-apps feed**. **No email/push** at MVP.
**Why:** The seam, DTO, and single call site already ship (AS-3 = option A); this is the
exact surface `app-subscriptions` built developer-updates to fill. Email/push is new infra
(deliverability, templates, opt-out, queues) the MVP slice doesn't need to prove H2.
**Rejected:** Email/push delivery at MVP (deferred, out of scope); a brand-new standalone
notices page divorced from the follow graph (the feed *is* the follow graph's surface).

### DU-3 (DN-20.c) — Posting emits no score-bearing signal; posts are rate-limited
**Choice:** The act of posting a notice emits **no** curated/weighted D-7 signal. The only
corpus entries are the followers' **own genuine returns**, recorded by `signal-capture`
through existing kinds. Posting is **rate-limited** (config-driven).
**Why:** Directly answers the "gaming manual" risk (vision Open Q #5 / seeded OQ): a
developer must not be able to manufacture engagement signal by posting. A notice is *content*,
not an impression/event. This must hold because it feeds the same corpus the Quality Score
will trust. The rate limit caps follower-spam and trivial-bump abuse (vision §5.2 spirit).
**Rejected:** Emitting a "notice published" engagement event (would let posting move the
corpus — gameable); unlimited posting (spam + signal-manufacture vector).

## Stage 2 — Software Architect (RATIFIED, DN-DU-DESIGN approved 2026-06-24)

Logged with the [DESIGN.md](DESIGN.md) draft, **RATIFIED** when the user approved
DN-DU-DESIGN (2026-06-24) — these bound Stage 3 and are now all **BUILT** at Stage 4 (Senior
Engineer, 2026-06-24) across tasks T-01…T-06, full suite green (828 tests). Full rationale +
rejected alternatives live in DESIGN.md §10/§14; the per-AC verification is in
[TEST_PLAN.md](TEST_PLAN.md).

**Built status:** DU-DESIGN-1 **BUILT** (pull delivery, `app_id`-keyed — T-02/T-05, M5=0
asserted) · DU-DESIGN-2 **BUILT** (the single `PublishedNotice → Notice` adapter, DAG proven —
T-02 `test_seam.py`) · DU-DESIGN-3 **BUILT** (`updates_notice` table, hard-delete withdraw, no
score/`updated_at`/`withdrawn_at` — T-01) · DU-DESIGN-4 **BUILT** (durable table-derived rate
limit — T-03) · DU-DESIGN-5 **BUILT** (no-`signals` import, AST-enforced — T-05
`test_imports.py`) · DU-DESIGN-6 **BUILT** (additive `subscriber_count` + `subscriptions_app_idx`
— T-04).

### DU-DESIGN-1 — Pull delivery; notices keyed by `app_id` (resolves OQ-DU-1 delivery half; AC5/M5)
**Choice:** The followed-apps feed *pulls* notices for the apps it already resolved
(`notices_for_apps(followed_ids)`); the producer never enumerates followers. A notice is keyed
by `app_id`, so a non-follower is **structurally** unreachable (M5 = 0) and there is no post-time
fan-out (R3 dissolved).
**Rejected:** push/fan-out (a feed-item row per follower) — O(followers) per post + a new
per-user table + a scoping risk of over-reach.

### DU-DESIGN-2 — The AS-3 repoint is the single adapter (keeps the dependency graph a DAG)
**Choice:** `subscriptions.notices.notices_for_apps` delegates to
`updates.selectors.published_notices_for_apps` and maps `PublishedNotice → Notice`. `updates`
returns its own read DTO and imports nothing from `subscriptions` on the notice path; the render
`Notice` stays owned by `subscriptions`. Dependency points consumer → producer only.
**Rejected:** `updates` importing `subscriptions.notices.Notice` directly (forms a module cycle);
a pluggable provider registry (AS-3 explicitly rejected speculative registry machinery).

### DU-DESIGN-3 — `apps/updates/` owns the `updates_notice` table (resolves C6)
**Choice:** A new feature-owned app owning one mutable table `updates_notice` (soft D-6 `app_id`
ref, `author` FK CASCADE, `kind`/`title`/`summary`/`published_at`). **No** score/`updated_at`/
`withdrawn_at` column; **withdraw = hard delete** (the store is exactly the currently-published
set — one source of truth, mirrors unfollow). Not model-less (notices are durable authored
content with no existing home).
**Rejected:** a model-less consumer (mirrors `apps/pages`/`dashboard` — but there is nothing to
read); soft-delete withdraw (no retention requirement).

### DU-DESIGN-4 — Durable, table-derived rate limit (AC8)
**Choice:** `post_notice` counts the author's own recent notices for the app
(`published_at >= now − updates_post_window_hours()`) against `updates_max_posts_per_window()`;
over the limit ⇒ `RateLimitedError`, nothing created. Exact and multi-worker-correct without
cache infra. The count→create TOCTOU is an accepted bounded trade-off (a spam guardrail, not a
correctness invariant — no locking).
**Rejected:** the cache-window approach (`core.ratelimit`) — that suits the auth path which leaves
no durable row; here durable rows exist, so counting them is strictly more correct.

### DU-DESIGN-5 — Transparency line verified (resolves OQ-DU-2 / R1, vision Open Q #5)
**Choice:** The post → feed → return path writes no developer-triggerable score-bearing signal.
`apps/updates` imports **no `signals.capture`** (enforced by an AST import-absence test, the
`apps/discovery`/`apps/dashboard` precedent); posting writes only content; the only corpus entries
are followers' **own** returns via the existing `apps/pages` `APP_PAGE`/`page_reengagement` kinds.
The developer controls content (to opt-in followers only), never signal.
**Rejected:** emitting any "notice published" event (would let posting move the corpus — gameable).

### DU-DESIGN-6 — Additive reverse-audience read + backing index (resolves OQ-DU-1 reporting half)
**Choice:** Add `subscriptions.selectors.subscriber_count(app_id) -> int` (one indexed COUNT) +
the additive `subscriptions_app_idx` index on `subscriptions_subscription(app_id)`. Backs the
post-form audience hint and the M2 reach metric; bounded and follower-count-independent in query
terms. Additive, reversible, contract-preserving (the open-search-browse precedent of additively
extending a closed app's read surface).
**Rejected:** computing reach by materializing the follower set (unbounded); leaving the count
unindexed (an `app_id`-only filter is unindexed today — L5).

> **Global ADRs:** none proposed. This feature **reuses D-3** (role gate), **D-6** (owner
> scoping / accepted catalogue), **D-7** (the signal corpus — consumed, not extended), and
> the **AS-3** producer contract from `app-subscriptions`. The Stage-2 model-vs-model-less call
> (C6) is resolved by **DU-DESIGN-3** (owns a table). Stack unchanged (D-4: Django + PostgreSQL).

## Stage 5 — Release Engineer (RELEASED local/dev 2026-06-24)

### DU-REL-1 — The honest rollback is broader than DESIGN §12's "three parts" → `git revert` of the build commit
**Context:** `developer-updates` is the first feature to repoint a **closed** app's seam
(`subscriptions.notices`). DESIGN §12 framed rollback as a three-part revert (seam → `return []`
\+ remove the `updates/` include + the `INSTALLED_APPS` line). The Stage-5 up→down→up rehearsal
found that framing captures the *activation surface* but not the full revert, on two counts:
1. **Seam imports (finding #1):** reverting only the `notices_for_apps` *body* to `return []`
   leaves the module-level `from apps.updates import selectors` / `from apps.core import config`
   imports and the `_to_notice` helper in place. Once `"apps.updates"` leaves `INSTALLED_APPS`,
   importing `subscriptions.notices` then raises `RuntimeError: model … isn't in INSTALLED_APPS`.
   The seam revert must also drop those imports + the helper.
2. **Closed-app tests (finding #2):** the build **rewrote** three `apps/subscriptions/tests/`
   files (`test_notices.py`, `test_views.py`, `test_selectors.py`) from asserting the
   empty-until-producer seam to asserting producer-coupled behaviour. Left as-is against the
   reverted seam, the `subscriptions` suite goes red; they must be restored to their pre-feature
   versions.
**Choice:** The clean, atomic operational rollback is **`git revert` of the build commit
`eb5b05d`**, which performs both findings + all three activation parts in one reversible step;
the optional DB down-migration (`migrate updates zero`, `migrate subscriptions 0001`) is
independent and coordination-free (the table holds only notice content). [RELEASE_NOTES.md §5]
documents the manual five-part equivalent for completeness.
**Why recorded:** this is the first closed-seam repoint; the same broader-than-it-looks rollback
shape will recur for any future feature that becomes the producer for an already-shipped seam.
**Verified (rehearsal up→down→up):** up = 828 green, routes resolve, both migrations' backward
SQL clean; down = five-part revert, `check` clean, `subscriptions`+`catalog`+`signals` **306
green**, seam returns `[]`; up = restored from HEAD, `git status` clean, **828 green**.
