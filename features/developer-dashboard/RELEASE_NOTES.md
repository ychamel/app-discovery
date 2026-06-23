# RELEASE_NOTES — developer-dashboard

*Stage 5 artifact (Release Engineer). Status: **RELEASED to local/dev** 2026-06-24.
Production promotion + the live-metrics window defer until a prod target/traffic exists
(as the prior nine features).*

Traces to [DESIGN §12 Rollout](DESIGN.md) · [FEATURE_BRIEF.md](FEATURE_BRIEF.md) success
metrics M1–M6 · [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC10).

---

## 1. What changed

A new **read-only developer-facing surface** — the **developer-dashboard** — that lets a
developer see the **reception** of the apps they own: *reach* (impressions, as a combined
total + per-`Surface` breakdown with curated `DIGEST` first), *engagement* (the D-7 funnel:
click-throughs, returns, subscribes, re-engagements, shares, off-platform proxy shown
separately), an **impressions-over-time trend** carrying a distinguished curated line, and
*incoming reviews* (count + distribution + recent list, no average), all over a fixed
8-window selector.

**Shipped components:**

- **NEW model-less app `apps/dashboard/`** (owns **no** schema — mirrors `apps/pages/` /
  `apps/discovery/`):
  - Two role-gated **GET** views — [`dashboard:my-apps`](../../apps/dashboard/urls.py) at
    `/dashboard/` (the developer's accepted apps + per-app reception summaries) and
    [`dashboard:app`](../../apps/dashboard/urls.py) at `/dashboard/apps/<uuid>/` (the
    full per-app reception view).
  - [`reception.py`](../../apps/dashboard/reception.py) — the composition layer producing
    frozen view-model DTOs: curated-first split via `ratings.gate.CURATED_SURFACES` (the
    single **D-8** source, reused), trend densify onto a continuous axis, loud-core /
    soft-reviews failure split, bounded my-apps no-N+1 (AC9), owner-scope→`None` (AC8).
  - [`windows.py`](../../apps/dashboard/windows.py) — the 8 `ReportingWindow`s (1w / 2w /
    1m / 3m / 6m / 1y / 3y / all-time) + per-window bucket granularity + `resolve_window`
    fail-safe + `ALL_TIME_START` epoch sentinel (so the existing range-based selectors are
    reused unchanged).
  - [`charts.py`](../../apps/dashboard/charts.py) — a pure stdlib **inline-SVG** sparkline
    (total + distinguished curated polyline; no JS, no external chart lib; `None` on
    empty/all-zero).
  - 3 server-rendered templates (base / my_apps / app_reception — no JS, all auto-escaped).
  - 6 `DASHBOARD_*` observability counters in
    [`apps/core/observability.py`](../../apps/core/observability.py).

- **TWO additive, neutral reads on the closed `apps/signals`** — in
  [`apps/signals/selectors.py`](../../apps/signals/selectors.py) (the only D-7-permitted
  `signals_*` reader): `TrendGranularity` (DAY/WEEK/MONTH) + `impression_breakdown` /
  `impression_breakdown_for_apps` (per-`Surface` counts, every `Surface` zero-filled →
  AC3/AC4, bulk no-N+1) + `impression_trend` (per-`Surface` per-UTC-time-bucket, sparse).
  **No model, no migration, no new index** — backed by the existing
  `signals_imp_app_time_idx`. Signals stays **neutral** (it never judges "curated"); the
  dashboard composes the curated split itself.

**Verified before ship:** **740 tests** green (+64 over the 676 baseline), `ruff check`
clean, `python manage.py check` no issues, `makemigrations --check --dry-run` → *No changes
detected* (no schema drift; the app owns no model).

## 2. Who is affected

- **Developers** (the `developer` role) with ≥1 **accepted** app — the new audience; this
  is the Phase-3 **H2** payoff (a $0-marketing app can see its real reception).
- **No one else.** Every change is **additive**: existing consumers of
  `signals.selectors` / `ratings` / `catalog` are untouched (the two new signals reads are
  inert until called); no existing route, model, or template changes. Signed-out and
  non-developer users get **404** on the dashboard routes (owner-scope is indistinguishable
  from non-existence — AC8/M5).

## 3. How to use it

A developer (logged in, `developer` role) opens **`/dashboard/`** to see their accepted
apps with reception summaries, then **`/dashboard/apps/<app-id>/`** for one app's full
reception (reach breakdown, engagement funnel, impressions trend, reviews), choosing a
reporting window. All reads are **owner-scoped**: a developer can only ever see their own
apps; any other app id → 404.

## 4. Operator rollout

- **Stack:** reuse **D-4** (Python/Django + PostgreSQL, server-rendered templates) — no new
  global ADR; the app lives at `apps/dashboard/`.
- **Activation switch = two lines, already in place:**
  1. `path("dashboard/", include("apps.dashboard.urls"))` in
     [`config/urls.py`](../../config/urls.py).
  2. `"apps.dashboard"` in `INSTALLED_APPS`
     ([`config/settings.py`](../../config/settings.py)).
  The two additive signals selectors ship with it but are **inert until called**.
- **No migration, no feature flag, no data backfill** — the app owns no schema. Deploy
  order is irrelevant (the additive selectors can land before or with the app).
- **Promotion table:**

  | Stage | Target | Promotion criterion |
  |-------|--------|---------------------|
  | local/dev | **done (2026-06-24)** | 740 tests green; routes resolve; rollback rehearsed |
  | internal | _deferred_ | no error spike; `DASHBOARD_RECEPTION_DEGRADED` flat for the soak window |
  | prod (% → full) | _deferred_ | M5 owner-scope leak = 0; read p95 (M6) within budget; error rate < threshold for the soak window — **deferred: no prod target/traffic** |

## 5. Rollback (rehearsed)

**One action, fully reversible, zero data migration** (the app owns no schema):

1. Remove the `path("dashboard/", …)` include from `config/urls.py`.
2. Remove `"apps.dashboard"` from `INSTALLED_APPS`.

→ Both routes return **404**; the rest of the platform is unaffected.

**Who can trigger it:** any operator with repo/deploy access (a two-line revert; no DB
step, no coordination with data).

**Rehearsal (2026-06-24, performed this session):**
- With the switch present: `/dashboard/` and `/dashboard/apps/<uuid>/` resolve; full suite
  **740 green**.
- Switch removed: both routes **404**; `python manage.py check` clean; upstream apps
  (`apps.signals` / `apps.ratings` / `apps.catalog`, **310 tests**) stay **green** — the
  additive signals reads are harmless to leave and break nothing when the dashboard is gone.
- Switch restored: routes resolve again; `git diff` on `config/urls.py` + `config/settings.py`
  **empty** (exact restore).

The `apps/dashboard/` package and the two `signals.selectors` additions may optionally be
deleted afterward, but leaving them is harmless (inert).

## 6. Monitoring — metrics → signals → alert

Six counters in [`apps/core/observability.py`](../../apps/core/observability.py):

| Counter | Feeds | Notes |
|---------|-------|-------|
| `DASHBOARD_MY_APPS_VIEWED` | M1 adoption, M2 return rate | dashboard page-view (own instrumentation, **not** a D-7 app-impression — viewing emits no `Impression`; AST-enforced no `signals.capture` import, AC8) |
| `DASHBOARD_RECEPTION_VIEWED` (tag: window) | M1, M2 | per-app reception view |
| `DASHBOARD_NONEMPTY_RECEPTION` | **M3** non-empty reception rate | a viewed app with a non-zero funnel — the literal H2 demo |
| `DASHBOARD_ACCESS_DENIED` | **M5** owner-scope integrity | a non-owner / non-existent app id → 404; baseline for the leak invariant (target 0) |
| `DASHBOARD_RECEPTION_DEGRADED` | **the one actionable alert** | the **core** reception read raised → loud **500**; a fake-empty dashboard would lie about H2/R1, so it fails loud, never silent |
| `DASHBOARD_REVIEWS_DEGRADED` | health (fail-soft) | the **reviews** slot fell back → soft **200** (the page still serves reach/engagement) |

- **The single Sev-worthy alert is `DASHBOARD_RECEPTION_DEGRADED`** (core read failure).
  `DASHBOARD_REVIEWS_DEGRADED` is fail-soft (informational).
- **M4** (curated-reach coverage) and **M3/M4 thinness** are analyst-derived from the
  surface split and **expected ~0 at MVP** — the only live impression emitter is `app-pages`
  (`APP_PAGE`); there is **no `DIGEST` emitter yet** (it arrives with `weekly-digest` /
  `editorial-curation-tools`). A true zero is reported **honestly** (AC4 affordance), **not
  a bug** (brief R1).
- **M5** owner-scope leak target = **0**, enforced structurally (every read goes through the
  owner-scoped `get_owned_app` / `list_owned_apps`; AC1/AC2/M5 are explicit test targets).
- **M6** read latency (p95): no global budget (D-2 "scale as we go"); the my-apps list is
  bounded-query (AC9) and per-app views are constant-query reads.

## 7. Known limitations

- **No live metrics yet** — local/dev only, no prod traffic; M1–M6 are instrumented but
  the measurement window opens when a prod/consumer target exists.
- **Curated reach (M4) is thin by design** until a `DIGEST` emitter ships — reported
  honestly, not a defect.
- **MVP draws one trend** (impressions over time + the curated line, AC10) and otherwise
  windowed counts; user-selectable graph series + funnel-over-time are deferred
  (DN-19.a "maybe later").
- **Read-only** — no re-boost, no "talk to subscribers", no score/ring/allocation (those
  do not exist at MVP); the dashboard shows **raw reception only**.

---

*Reuses **D-3/D-5/D-6/D-7/D-8** — no new global ADR. Feature-local decisions
DD-DESIGN-1…5 in [DECISIONS.md](DECISIONS.md).*
