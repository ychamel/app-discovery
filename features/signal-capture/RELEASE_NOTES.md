# RELEASE_NOTES — signal-capture

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway database (2026-06-18).*
Sources: verified Stage-4 build, [DESIGN.md §9/§11/§12](DESIGN.md) (rollout + rollback +
the downstream contract), [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (success metrics /
error conditions), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC11 coverage),
[apps/signals/PRIVACY.md](../../apps/signals/PRIVACY.md) (the AC10 posture), global
[D-7](../../DECISIONS.md) (the event-schema contract this feature establishes) and the
reused [D-5](../../DECISIONS.md) (tags) / [D-6](../../DECISIONS.md) (catalogued apps).

---

## 1. What this release is

The platform's **behavioral-signal capture spine** — the schema-first heart of Phase 0.
It records every **on-platform** interaction in the curated loop (impression shown →
click-through → return-to-platform @3d/@14d → subscribe/follow → on-page re-engagement →
share) as clean, **append-only, raw (never scored)** events keyed *user × `App.id` ×
impression*, tagged with the app's interest categories **at capture time**, so a future
Quality Score can be **backtested without re-instrumentation** (hypothesis H3, feeding
H1/H2). Off-platform open/return is a **flagged secondary** signal, never load-bearing.

It ships as a **new Django app, `apps/signals/`**, and changes no existing feature's
behavior. It satisfies all eleven acceptance criteria AC1–AC11 (mapping in
[TEST_PLAN.md](TEST_PLAN.md)). The event schema it lands is the global, near-irreversible
**[D-7](../../DECISIONS.md)** contract every later producer/consumer must build on.

## 2. What changed (since "nothing recorded behavior")

- **Data model** — four **append-only** tables under `apps/signals/`, all UUID-keyed
  (D-4 convention), referencing no other app's schema except the `Account` `user` FK
  (apps/tags are **soft `App.id`/`Tag.id` UUID refs** under D-6/D-5):
  - `signals_impression` — the **anchor**: one shown instance with its own `id` identity
    (every conversion attributes to *that* instance, AC1/AC3), `user`, `app_id`, `surface`
    (`digest` only at MVP, enum-extensible), and `occurred_at` (the funnel/return clock).
  - `signals_impression_tag` — the **frozen** capture-time category snapshot: the `Tag.id`s
    the app carried **when shown**, copied once from `get_catalogued_app` and never
    re-resolved (AC2). Unique `(impression, tag_id)`.
  - `signals_engagement_event` — **one uniform table**, a `kind` discriminator over
    `click_through` · `subscribe` · `page_reengagement` · `share` · `off_platform_proxy`
    (closed code enum — an unknown event type is unrepresentable), with `user`, `app_id`,
    a nullable `impression` link, and `is_proxy`.
  - `signals_platform_visit` — the **directly-observed return substrate**: one row per user
    per UTC day (unique `(user, visit_date)` → idempotent).
- **Returns are derived, never stored (SC-9)** — `returns_3d`/`returns_14d` are computed at
  read by joining each in-window impression to the existence of a `PlatformVisit` in the
  window; window lengths come from config (§5 below). **No return-event row, no scheduled
  job, no backfill** (AC4/AC8) — the only model that can represent "did *not* return" (an
  absence).
- **Two structural guarantees, not conventions** — there is **no score/weight/rank column**
  on any table or read DTO (raw-only, AC9/R5), and **no IP / user-agent / device / geo /
  referrer / free-text column** anywhere (the privacy whitelist, AC10). Both are enforced by
  the schema (the columns do not exist) and asserted by tests.
- **Single write path** (`capture.py`) — the only way an event is written: `record_impression`
  + `record_click_through` / `record_subscribe` / `record_page_reengagement` / `record_share`
  / `record_off_platform_proxy` + `record_platform_visit`. Each validates the app via
  `catalog.get_catalogued_app` (D-6 — non-accepted ⇒ `UnknownAppError`, nothing written),
  snapshots tags in one transaction, enforces **impression linkage** (`click_through` /
  `off_platform_proxy` require an impression whose `app_id`/`user` match ⇒ else
  `ImpressionMismatchError`), sets `is_proxy` **itself** (never the caller), is atomic, and
  is **fail-loud**: on any failure it increments `capture_error{kind=…}` and re-raises.
- **Visit middleware** (`middleware.py`) — `PlatformVisitMiddleware`, wired into `MIDDLEWARE`
  **after** auth + request-context: turns an authenticated request into an idempotent daily
  `PlatformVisit`. **Fail-soft-but-counted** (a failed tick logs + counts `capture_error`
  but never breaks navigation), anonymous-safe.
- **Single read path** (`selectors.py`) — the raw per-app funnel: `app_funnel` /
  `funnel_for_apps` (bulk, **no N+1** — 2 queries) / `category_impressions`, returning a
  frozen `AppFunnel` DTO of **counts only** (with derived returns). Proxy is segregated into
  its own field, never folded into on-platform counts (AC7). **Never scores** (AC9).
- **Admin** — the four models registered **read-only** (no add/change/delete) for ops
  cold-start; append-only is enforced in code, not admin discipline.
- **Account-deletion semantics (SC-10)** — the event `user` FKs are **`SET_NULL`**
  (a deleted user's behavioral facts survive as anonymized corpus; the no-auto-purge H3
  rule is respected while the person is unlinked); `PlatformVisit.user` is **`CASCADE`**
  (an unlinkable per-day tick is pure noise). This **resolves the `submission-intake`
  DESIGN §13 deletion flag** — flagged SC-10 to confirm anonymize-and-retain with data.
- **Shared-surface touches** — 8 new metric constants in `apps/core/observability.py`
  (§7 below); two new tunables in `apps/core/config.py` — `return_window_short_days`
  (default 3) and `return_window_long_days` (default 14), validated at startup;
  `apps.signals` added to `INSTALLED_APPS` and the middleware appended to `MIDDLEWARE`.
  `apps/accounts`, `apps/taxonomy`, `apps/catalog` reused **as-is, not modified**. No
  existing behavior changed.

## 3. Who is affected

- **The platform / data team** — the corpus now exists to capture into and backtest against
  (H3). They read reception through `signals.selectors.app_funnel` / `funnel_for_apps`
  in-process or via the read-only admin. **Nothing is captured until an emitting surface
  ships** (see §9) — the corpus is intentionally thin at release.
- **End users** — **no public-facing change.** The only live writer is the visit middleware,
  which records a pseudonymous per-day activity tick (no IP/UA/PII, by schema). The posture
  is stated in human-readable form in [apps/signals/PRIVACY.md](../../apps/signals/PRIVACY.md):
  *what* is recorded, *why* (the H3 backtest), *how long* (no auto-purge), and *deletion
  behavior* (anonymize-and-retain).
- **Downstream feature teams** (`weekly-digest`, `app-pages`, `app-subscriptions`,
  `developer-updates`, `developer-dashboard`) — must now build against the
  **[D-7](../../DECISIONS.md)** contract. **Action required of them:** emit **only** through
  `signals.capture.*` (never write `signals_*` tables directly); key to `App.id` (D-6) and
  `Tag.id` (D-5) as soft UUID refs, never a label/URL/hard-FK; read only **raw** counts
  through `signals.selectors.*` (scoring is the consumer's job, never done here); treat the
  off-platform proxy as a flagged secondary, never required for funnel completeness. Each
  emitting surface also adopts the §5d **capture-failure policy** (impression =
  corpus-critical; interactive conversion = counted-not-blocking; visit = fail-soft).
- **Support** — **no support-facing change** at this release.

## 4. How to use it (operators)

The rollout is the ordered steps from [DESIGN.md §12](DESIGN.md) — no separate runbook, and
**no recurring job** (returns are derived at read; nothing expires — no auto-purge):

1. Optionally tune `RETURN_WINDOW_SHORT_DAYS` (default 3) and `RETURN_WINDOW_LONG_DAYS`
   (default 14) — see [`.env.example`](../../.env.example). Both have defaults; no new env
   var is *required*.
2. `python manage.py migrate signals` — creates the four `signals_*` tables. **No content.**
   (Depends only on the `Account` model; no new extension.)
3. `python manage.py check` — must report no issues before the surface is considered live.
4. The `PlatformVisitMiddleware` registration (already in `config/settings.py`, after
   `AuthenticationMiddleware` + `RequestContextMiddleware`) makes the visit tick live on
   deploy; on-platform capture goes live **as each emitting surface ships** (§9).

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with
> `identity-accounts`, `interest-taxonomy`, and `submission-intake`
> ([CONTROL.md](../../CONTROL.md)); the platform is still mid-development. The feature is
> verified locally (migration applies, four tables created, `check` clean, 374 tests green).
> **Production promotion and a live-metrics monitoring window are deferred** until the first
> emitting surface (`weekly-digest`) exists to produce real signal.

This is an **additive new app with no live emitter yet** (the emitting surfaces are out of
scope / unbuilt — DESIGN §5c), so there is **no pre-existing behavior to protect and nothing
to feature-flag off** (an honest deviation from the internal→%→full template — there is no
surface to ramp against, DESIGN §9). Safety comes from a **reversible migration** + a
**removable middleware**, not a kill switch. (Until an emitter ships the only writer is the
visit middleware — itself removable in one line if it ever misbehaves.)

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate signals` applied; the four `signals_*` tables exist; `/health` → `200`; `capture_error` reads 0. |
| Visit substrate live | An authenticated request records exactly one `PlatformVisit` per user per day (idempotent); `manage.py check` clean. |
| First emitter integrates | `weekly-digest` adopts the [D-7](../../DECISIONS.md) contract and calls `record_impression` / `record_click_through` — at which point the §7 funnel carries real signal. |
| First funnel readable | At least one app that received ≥1 impression returns non-zero counts from `app_funnel` (per-app reception availability, H2). |
| H3 backtest ready | For ≥1 app over a full evaluation window, the funnel answers *"would a score from these signals have matched the editorial pick?"* from stored data alone — the feature's reason to exist. |
| Stable at target | Above holds with `capture_error` = 0 and no sustained drop in impression-completeness through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**One action: revert the deploy to the previous release** (which also removes the
`PlatformVisitMiddleware` registration — the only live writer). If the schema must also be
undone (safe here — no live emitter or downstream reader exists yet):

```bash
python manage.py migrate signals zero    # drops the four signals_* tables
```

**Rehearsed 2026-06-18** on a throwaway PostgreSQL database (`signals_release_rehearsal`,
dropped afterward): `migrate` created the four `signals_*` tables (`signals_impression`,
`signals_impression_tag`, `signals_engagement_event`, `signals_platform_visit`);
`manage.py check` clean; then `migrate signals zero` reversed cleanly to **0 `signals_*`
tables** while **keeping the shared `citext` extension** (used by `accounts` / `taxonomy` /
`catalog`); a re-`migrate signals` re-applied cleanly (the migration is confirmed
reversible). **Who can trigger:** any operator with deploy access and the DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; DB reachability is already
covered by the existing `GET /health`. The eight new constants live in
`apps/core/observability.py`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| Event loss / capture-error rate (**core safety, target 0**) | `capture_error` (tagged `kind`) | **Page on any nonzero** — the AC11/R4 never-silent loss signal. Must read 0 in a healthy system; a half-written corpus invalidates H3. |
| Impression-capture completeness | `impression_captured` ÷ apps actually shown in digests (the denominator arrives with `weekly-digest`) | **Alert on a sustained drop** once an emitter is live — an uncaptured impression is a permanent corpus hole (DESIGN §5d). |
| Click-through attribution rate | `click_through_captured` linked to an impression ÷ all click-throughs (unlinked clicks are structurally refused — the signal is the `ImpressionMismatchError` rate at the emitter) | Trend only — unlinked clicks are weak signal. |
| Return-rate observability | derived `returns_3d`/`returns_14d` ÷ impressed users (computed at read from `PlatformVisit`, not a counter); `platform_visit_captured` confirms the substrate is live | Trend — target ≈ 100% (directly observed, the point of the SC-7 pivot). |
| Engagement-event capture | `subscribe_captured` / `page_reengagement_captured` / `share_captured` per app that received impressions | Trend only — feeds the retention picture; thin until the incentive surfaces ship (R6). |
| Off-platform proxy coverage (**secondary**) | `off_platform_proxy_captured` (tagged `secondary`) | **Not a gate** — reported honestly, low by design (R1). |
| Per-app reception availability | every app with ≥1 impression has readable `app_funnel` counts (computed, not a counter) | Trend toward H2 / developer-dashboard readiness. |
| H3 backtest readiness (gate, qualitative→binary) | the funnel answers the editorial-match question from stored data alone | The feature's reason to exist — assessed once an emitter + full window exist. |

## 8. Verification at release (2026-06-18)

- **374 automated tests pass** (315 baseline + 59 new signals tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model
  drift (model ↔ migration in sync).
- Rollout→rollback **rehearsed** on a scratch DB (§6): `migrate` → four `signals_*` tables →
  `check` clean → `migrate signals zero` reverses to 0 signals tables (shared `citext`
  retained) → re-`migrate signals` re-applies (reversible).
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC11 to tests; `capture_error` reads 0 on
  every happy path and the fail-loud tests assert it increments (tagged `kind`) **and**
  re-raises.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §13](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **No live emitter at ship** — the surfaces that *generate* events (`weekly-digest`,
  `app-pages`, `app-subscriptions`, `developer-updates`) are out of scope (brief A6/R6) and
  unbuilt, so the only live writer is the visit middleware (+ tests). A thin corpus until
  they ship is a **product-surface gap (R6), by design — not a capture defect**. signal-capture
  defines the contract those surfaces call.
- **Off-platform proxy is a seam, not an attribution engine** (OQ-1/R1) — only the
  `record_off_platform_proxy` call exists; *who calls it and how an off-platform open/return
  is detected* is left open and unbuilt. The under-count is a **documented limitation**
  (OQ-3): it only depresses the *secondary* number, never the funnel's completeness (AC7).
- **Synchronous fail-loud capture can visibly (counted) drop an event under failure** rather
  than guaranteeing zero-loss. A durable **outbox/queue** is the named growth path if
  `capture_error` is ever nonzero-and-unacceptable at scale — not built now (D-2, over-built
  for MVP volume).
- **Returns derived at read** carry a (bounded, indexed) read cost; a **materialized
  per-app/per-window funnel projection** and a `catalog.is_catalogued_app` cheap-existence
  selector are the named **100×** growth paths (DESIGN §9), additive, not built now.
- **No HTTP/DRF read projection** — selectors are in-process / admin only; a thin
  `HasRole`-gated read view is a one-feature-later addition (developer-dashboard), noted not
  built (no speculative abstraction).
- **Account-deletion = anonymize-and-retain (SC-10)** — a deleted user's events survive
  `SET_NULL`-anonymized (H3 needs the aggregate); visits `CASCADE`. Flagged to confirm the
  anonymize-and-retain posture with data (consistent with how `catalog` flagged this exact
  interaction).
- **No live-metrics window measured** — deferred with the local/dev target until an emitter
  exists (mirrors `identity-accounts` / `interest-taxonomy` / `submission-intake`).

## 10. Stakeholder notification

On the first real promotion (when `weekly-digest` integrates): notify downstream feature
owners that the capture spine is live and buildable against, and hand them the
**[D-7](../../DECISIONS.md)** contract — **emit only through `signals.capture.*`; key to
`App.id` (D-6) and `Tag.id` (D-5) as soft UUID refs; read only raw counts through
`signals.selectors.*` and never score in this layer; treat the off-platform proxy as a
flagged secondary, never required for funnel completeness**, and adopt the §5d
capture-failure policy per surface. Hand the privacy/data owner
[apps/signals/PRIVACY.md](../../apps/signals/PRIVACY.md) and the SC-10 anonymize-and-retain
posture to confirm against the live deletion flow. No support-facing change at this release —
there is no end-user surface yet.
