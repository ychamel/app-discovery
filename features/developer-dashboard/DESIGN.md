# DESIGN — developer-dashboard

*Stage 2 artifact (Software Architect). Status: **DRAFT — awaiting approval** (DN-DD-DESIGN,
raised in CONTROL.md). Reads the **APPROVED** [FEATURE_BRIEF.md](FEATURE_BRIEF.md) + the
codebase; produces the architecture, data design, contracts, UX, failure modes, and rollout.
Resolves **OQ-DD-4**. Reuses **D-3/D-5/D-6/D-7/D-8 as-is — no new global ADR.*

---

## 0. Protocol trace (the 14 steps, condensed)

> The persona's reasoning method. Each step's output is folded into the sections below; this
> trace is the audit that none was skipped.

1. **SCOPE** — A read-only developer-facing surface that presents an owned, accepted app's
   *reception* (reach breakdown + curated-line trend, engagement funnel, incoming reviews)
   over a chosen window, sourced faithfully from the D-7/D-8 corpus, strictly owner-scoped.
   Lifespan = **feature** (a durable product surface). Out: any write/score/allocation,
   funnel-over-time, user-selectable series, public API (brief *Out of scope*).
2. **REQUIREMENTS** — Functional = AC1–AC10. Non-functional = bounded reads at 100×
   (AC9/M6), owner-scope integrity (M5=0), honest-zero reporting (AC4/R1), read-only
   (AC8). Assumptions = brief C1–C10, **all verified against code** (this session re-read
   `signals.selectors`, `signals.kinds`, `ratings.selectors`, `ratings.gate`,
   `catalog.selectors`, `accounts.permissions`, and the `apps/discovery`/`apps/pages`
   consumer pattern). The one open gap (C7/OQ-DD-4) is resolved in §4/§5 below.
3. **CONTEXT** — Everything needed already exists as in-process read surfaces; this feature
   adds **two thin things**: a model-less consumer app (`apps/dashboard/`, mirroring
   `apps/pages/` + `apps/discovery/`) and **two additive reads** on the closed `signals`
   selector surface. No new table, no migration, no new index, no new global ADR.
4. **MODULES** — §3. Four cohesive units: the two HTTP views, a reception-composition layer,
   the reporting-window vocabulary, and (in signals) the surface-aware/time-bucketed reads.
5. **INTERFACES** — §5. Every signature, DTO, error, and invariant fixed — no "TBD".
6. **DATA & STATE** — §4. The dashboard owns **no** state (stateless consumer). Signals'
   tables remain the single source of truth; the two new reads are pure aggregates.
7. **FAILURE** — §7. Core reception read fails **loud** (a fake-empty dashboard would lie
   about H2 — R1); the reviews slot fails **soft**; owner-scope mismatch is an
   indistinguishable 404.
8. **CHANGE** — The window set + per-window bucket granularity are a code-fixed declarative
   table (§4.3); the curated definition is reused from `ratings.gate.CURATED_SURFACES` (one
   source); the per-surface reads enumerate the `Surface` vocabulary so a new surface needs
   **no dashboard change** (§5.1, AC3). Irreversible surface = the two public selector
   signatures + the two URL routes (§5, §8).
9. **TRADE-OFFS** — §10. Chief choice: add the time-bucketed read to **signals.selectors**
   (honours D-7) vs. read `signals_*` from the dashboard (rejected — breaks D-7/R4).
10. **SECURITY** — §6. Role gate (`require_role(developer)`) + owner-scope on every read +
    GET-only + no `signals.capture` import (viewing a dashboard records **no** impression).
11. **OPERATIONS** — §8. Activation/rollback = one `config/urls` include; six counters;
    one actionable alert (`DASHBOARD_RECEPTION_DEGRADED`).
12. **TESTS** — §9 maps AC1–AC10 + M1–M6 to concrete verifications, each module in isolation.
13. **SELF-CRITIQUE** — §11. Attacked: the all-time unbounded read, the SVG chart's
    necessity, breakdown/funnel double-counting, the role-gate-vs-owner-scope redundancy.
14. **DELIVER** — §5 contracts + §12 rollout + the feature-local decisions (DD-DESIGN-1…5).

---

## 1. Current-state summary (what already exists)

Everything the dashboard presents is **already captured and already readable** through
in-process selector surfaces. Nothing here is changed; the dashboard is a pure reader.

| Capability | Existing surface (unchanged) | Shape |
|---|---|---|
| Owner's apps, owner-scoped | `catalog.selectors.list_owned_apps(owner)` / `get_owned_app(owner, id)` | `App` (any status); a non-owner's id ⇒ `None` (AC8 — no leak) |
| Per-app engagement funnel | `signals.selectors.app_funnel(app_id, *, start, end)` | `AppFunnel` (counts + derived returns; **no score**) |
| Bulk funnels, bounded | `signals.selectors.funnel_for_apps(app_ids, *, start, end)` | `list[AppFunnel]`, 2 grouped queries regardless of K (AC9) |
| Curated definition (single source) | `ratings.gate.CURATED_SURFACES` (= `{Surface.DIGEST}`, global **D-8**) | `frozenset[str]` |
| Incoming reviews | `ratings.selectors.reviews_for_app(app_id, *, limit)` | `AppReviews` (count + raw distribution + capped list; **no average**) |
| Role gate | `accounts.permissions.require_role(DEVELOPER)` (fail-closed) | Django view decorator → 403 |
| Return windows (config) | `config.return_window_short_days()` / `…_long_days()` | the labels for `AppFunnel.returns_3d/14d` |
| Reviews display cap (config) | `config.reviews_display_limit()` (= 20) | reused for the reviews list |
| Model-less consumer pattern | `apps/pages/`, `apps/discovery/` | view + urls + templates; one `config/urls` include = activation/rollback |

**The one gap (brief C7 / OQ-DD-4), confirmed by re-reading the code:**
`AppFunnel.impressions` counts **all surfaces collapsed** and is **not time-bucketed**, and
`signals.selectors` has **no** per-`Surface` and **no** time-bucketed read. The Steam-style
per-source breakdown (AC3) and the impressions-over-time trend (AC10) therefore need a new
read. D-7 forbids reading `signals_*` tables outside `signals.selectors` (R4), so that read
**must be added to `signals.selectors`** — §5.1 does exactly that, additively, with no model,
migration, or index change.

---

## 2. Proposed architecture (one diagram)

```
                         HTTP (GET only, login_required + require_role(developer))
                                            │
        ┌───────────────────────────────────┴───────────────────────────────────┐
        │                            apps/dashboard/  (NEW, model-less)            │
        │                                                                          │
        │  views.py                 reception.py (composition)        windows.py    │
        │  ─ my_apps(request)  ───►  build_my_apps_summaries(owner,w)  REPORTING_   │
        │  ─ app_reception(        ─ build_app_reception(owner,id,w)   WINDOWS (8)  │
        │       request, app_id)                                       resolve_     │
        │                          charts.py: build_sparkline(series)  window(key)  │
        └───────┬───────────────┬───────────────┬───────────────┬─────────────────┘
                │ owner-scope   │ reach+funnel  │ reach split   │ reviews
                ▼               ▼               ▼               ▼
   catalog.selectors    signals.selectors (D-7, the ONLY signals_* reader)   ratings.selectors
   list_owned_apps      app_funnel / funnel_for_apps        (D-8)            reviews_for_app
   get_owned_app        impression_breakdown[_for_apps]  ◄── NEW (§5.1)
        (D-6)           impression_trend                 ◄── NEW (§5.1)
                        (reuses ratings.gate.CURATED_SURFACES for "which surface is curated")
```

**Dependencies point toward stability:** the dashboard depends only on the closed, stable
read surfaces of catalog (D-6), signals (D-7), ratings (D-8), accounts (D-3). It is depended
on by **nothing**. Removing it (delete the app + the one include) leaves every dependency
untouched — *design for deletion* by construction.

**Coupling/cohesion check:** each module has one job (§3); the dashboard holds **no ORM
access and no business logic** beyond calling the four read surfaces and composing a
view-model — exactly the `apps/discovery` house rule. The two new signals reads are testable
in isolation at the ORM level (no HTTP).

---

## 3. Modules (single responsibilities)

| Module | Owns / does | Hides | Depends on |
|---|---|---|---|
| `apps/dashboard/views.py` | Two thin GET views; parse the trust-boundary `window` param; gate (role + owner-scope); pick fail-loud vs fail-soft; render. **No ORM, no `signals.capture` import.** | HTTP wiring, the failure split | `reception`, `windows`, `accounts.permissions`, `catalog.selectors`, `observability` |
| `apps/dashboard/reception.py` | Compose the view-models: call the read surfaces, order surfaces **curated-first** via `CURATED_SURFACES`, densify the trend axis, project to frozen DTOs. The one place that *assembles* reception. | Which selectors are called and in what order; the curated-first ordering | `signals.selectors`, `ratings.selectors`, `ratings.gate`, `catalog.selectors`, `charts`, `windows`, `config` |
| `apps/dashboard/windows.py` | The fixed **8 reporting windows** + each window's bucket **granularity**; resolve a window key → `(start, end, granularity)`; the default key. | The window arithmetic + the all-time epoch sentinel | `signals.selectors.TrendGranularity`, stdlib `datetime` |
| `apps/dashboard/charts.py` | Pure function: dense trend series → inline-SVG polyline points (total line + curated line) + the same series for a `<table>` fallback. No I/O. | SVG coordinate math | stdlib only |
| `apps/signals/selectors.py` **(additive)** | **NEW** surface-aware (`impression_breakdown[_for_apps]`) and time-bucketed (`impression_trend`) reads + `TrendGranularity`. The **only** code that may read `signals_*` for these (D-7). | The ORM grouping; stays **neutral** — counts per `Surface`, never judges which surface "means" curation | `signals.models`, Django ORM |

Cross-cutting concerns are reused, not duplicated: auth/role = `accounts`; config = `apps/core/config`
+ `windows.py`; logging/metrics = `apps/core/observability`; errors = let the loud ones
propagate to a 500 (§7).

---

## 4. Data design

### 4.1 Ownership & state
The dashboard owns **no model, no migration, no table, no new index** — it is a stateless
consumer (like `apps/pages/` and `apps/discovery/`). The single source of truth for every
figure stays in the signals/ratings/catalog tables. On crash/restart there is nothing to
recover; every read is recomputed from stored rows (the D-7 "backtestable without
re-instrumentation" guarantee). No concurrency conflict is possible — all reads are
read-only and each request is independent.

### 4.2 The two new reads are pure aggregates (no new schema)
`impression_breakdown` and `impression_trend` (§5.1) are `GROUP BY` aggregates over the
existing `signals_impression` table, both filtered by `app_id + occurred_at` and so backed
by the **existing** `signals_imp_app_time_idx (app_id, occurred_at)` index — **no migration**.
Their counts are reconstructable from stored rows alone (no backfill), consistent with the
existing funnel reads. **Invariant:** `impression_breakdown(app,w).total ==
app_funnel(app,w).impressions` (both count Impression rows in the same window) — asserted in
tests (§9), so the reach section and the funnel section can never silently disagree.

### 4.3 The reporting-window vocabulary (`windows.py`) — resolves DD-2 carry-forward

A **code-fixed declarative table** (the change-cheap place: add/remove a window = edit one
tuple), modelled on how `ratings.gate.CURATED_SURFACES` and `catalog.gate.CHECKLIST` live in
their feature app rather than in env config. It is not env-overridable (it is a closed
vocabulary, like `Surface`), so it belongs in code, not `apps/core/config`.

```python
class TrendGranularity(...):  # lives in signals.selectors (a signals read concept)
    DAY; WEEK; MONTH

@dataclass(frozen=True)
class ReportingWindow:
    key: str            # URL/query value, e.g. "month"
    label: str          # "Last month"
    duration: timedelta | None   # None ⇒ all-time
    granularity: TrendGranularity

REPORTING_WINDOWS: tuple[ReportingWindow, ...] = (   # order = selector display order
    ReportingWindow("1w",  "Last week",     timedelta(days=7),    DAY),
    ReportingWindow("2w",  "Last 2 weeks",  timedelta(days=14),   DAY),
    ReportingWindow("1m",  "Last month",    timedelta(days=30),   DAY),
    ReportingWindow("3m",  "Last 3 months", timedelta(days=90),   WEEK),
    ReportingWindow("6m",  "Last 6 months", timedelta(days=180),  WEEK),
    ReportingWindow("1y",  "Last year",     timedelta(days=365),  MONTH),
    ReportingWindow("3y",  "Last 3 years",  timedelta(days=1095), MONTH),
    ReportingWindow("all", "All time",      None,                 MONTH),
)
DEFAULT_WINDOW_KEY = "1m"
ALL_TIME_START = datetime(1970, 1, 1, tzinfo=UTC)  # predates any possible event
```

Granularity is chosen per window to keep bucket counts bounded (the M6/AC9 lever): DAY for
≤1-month windows (≤31 points), WEEK for 3–6-month windows (≤26), MONTH for ≥1-year and
all-time (≤12·years — all-time is bounded by data age precisely *because* it is monthly).

`resolve_window(key, *, now) -> ResolvedWindow(start, end, granularity)`: unknown/blank key
→ `DEFAULT_WINDOW_KEY` (fail-safe, never an error); `end = now`; `start = now − duration`,
or `ALL_TIME_START` for all-time. The concrete `start` lets the **existing** range-based
selectors (`app_funnel`, `funnel_for_apps`, and the two new reads) be reused **unchanged** —
all-time is just a very early lower bound, not a special code path.

### 4.4 Retention / privacy
No retention concern — the dashboard stores nothing. It exposes only **aggregate counts**
and the already-anonymized review list (`reviews_for_app` shows "a former user" for deleted
authors); it surfaces no PII the dependencies do not already publish (brief C10).

---

## 5. Interface contracts (no "TBD")

### 5.1 NEW — `apps/signals/selectors.py` (additive; the OQ-DD-4 resolution)

> **Why here, not in the dashboard:** D-7 forbids any consumer reading `signals_*` directly
> (R4). The surface-aware/time-bucketed read is therefore an *additive read-surface
> extension* to the closed signals app — the same precedent as ratings adding `has_impression`.
> Signals stays **neutral**: it returns counts per `Surface` and never decides which surface
> "means" curation (that judgement remains `ratings.gate.CURATED_SURFACES`, reused by the
> dashboard). No model/migration/index change.

```python
class TrendGranularity(models.TextChoices):
    """Time-bucket grain for impression_trend. Maps to Trunc{Date,Week,Month} (UTC)."""
    DAY = "day"; WEEK = "week"; MONTH = "month"

@dataclass(frozen=True)
class ImpressionBreakdown:
    app_id: UUID
    total: int                    # == app_funnel(...).impressions for the same window (invariant)
    by_surface: dict[str, int]    # EVERY Surface value, zero-filled (AC4 honest zero)

@dataclass(frozen=True)
class ImpressionBucket:
    bucket_start: datetime        # the truncated bucket key (UTC), ordered ascending
    total: int
    by_surface: dict[str, int]    # every Surface value, zero-filled, for this bucket

def impression_breakdown(app_id: UUID, *, start: datetime, end: datetime) -> ImpressionBreakdown:
    """Per-Surface impression counts over [start, end] — ONE grouped query.

    by_surface enumerates Surface.values (a surface with no impressions reads 0 — AC4), so a
    surface ADDED later appears automatically with no caller change (AC3 extensibility).
    Backed by signals_imp_app_time_idx; no ordering/score (raw, AC9).
    """

def impression_breakdown_for_apps(
    app_ids: list[UUID], *, start: datetime, end: datetime
) -> dict[UUID, ImpressionBreakdown]:
    """Bulk per-Surface breakdown for several apps in ONE grouped query — no N+1 (AC9).

    Apps with no impressions are present with an all-zero breakdown. Keyed by app_id.
    """

def impression_trend(
    app_id: UUID, *, start: datetime, end: datetime, granularity: TrendGranularity
) -> list[ImpressionBucket]:
    """Impressions bucketed by `granularity`, split per Surface — ONE grouped query.

    Returns only buckets that have ≥1 impression (sparse on the time axis), ascending by
    bucket_start; the caller densifies to a continuous axis (reception.py). Trunc is in UTC,
    matching the returns-derivation date math. Bucket count is bounded by the granularity the
    window chose (§4.3), so this is bounded at 100× (M6).
    """
```

**Evolution:** additive functions + one new enum; the existing `AppFunnel` reads are
untouched, so every current signals consumer (the ratings gate, future backtest) is
unaffected. A new `Surface` value flows through `by_surface` automatically — no signature
change.

### 5.2 NEW — `apps/dashboard/reception.py` (composition view-models)

```python
@dataclass(frozen=True)
class SurfaceReach:
    surface: str            # Surface value
    label: str              # Surface.label (human)
    count: int
    is_curated: bool        # surface in ratings.gate.CURATED_SURFACES (D-8, reused)

@dataclass(frozen=True)
class ReachView:
    total: int
    surfaces: list[SurfaceReach]   # CURATED FIRST (DIGEST highlighted), then the rest (AC3)
    trend: "TrendView"

@dataclass(frozen=True)
class TrendBucket:
    label: str              # bucket axis label (e.g. "2026-06-17", "Wk of …", "Jun 2026")
    total: int
    curated: int            # sum over CURATED_SURFACES (AC10 distinguished line)

@dataclass(frozen=True)
class TrendView:
    granularity_label: str
    buckets: list[TrendBucket]   # DENSE (every bucket in the window, zero-filled)
    sparkline: "SparklineSvg | None"   # None when the window is empty (AC4)
    is_empty: bool

@dataclass(frozen=True)
class FunnelView:        # a presentation projection of AppFunnel (no new numbers)
    impressions: int; click_throughs: int
    returns_short: int; returns_long: int; short_days: int; long_days: int  # labels from config
    subscribes: int; page_reengagements: int; shares: int
    off_platform_proxy: int        # shown SEPARATELY, never folded in (AC5)

@dataclass(frozen=True)
class ReviewsView:
    available: bool                # False ⇒ the slot degraded (fail-soft, §7)
    total_count: int
    distribution: dict[int, int]   # raw per-score; NO average (AC6)
    reviews: list[ReviewRow]       # ratings.selectors.ReviewRow, capped at reviews_display_limit()

@dataclass(frozen=True)
class ReceptionSummary:            # one row of the my-apps list (S1)
    app_id: UUID; app_name: str
    total_impressions: int; curated_impressions: int; click_throughs: int

@dataclass(frozen=True)
class AppReception:                # the per-app view (S2–S5)
    app_id: UUID; app_name: str
    window: ReportingWindow; available_windows: tuple[ReportingWindow, ...]
    reach: ReachView; funnel: FunnelView; reviews: ReviewsView

def build_my_apps_summaries(owner, *, window: ReportingWindow) -> list[ReceptionSummary]:
    """The S1 list — accepted owned apps + a bounded reception summary each (AC1/AC9).

    Owned, ACCEPTED-only (list_owned_apps filtered to status=ACCEPTED). Bounded: ONE
    funnel_for_apps (2 queries) + ONE impression_breakdown_for_apps (1 query) for ALL K apps
    — total query count independent of K. curated_impressions = Σ over CURATED_SURFACES.
    Empty owner ⇒ [] (the own-nothing state, AC2). RAISES on a signals DB error (fail loud).
    """

def build_app_reception(owner, app_id, *, window: ReportingWindow) -> AppReception | None:
    """The S2–S5 per-app view, or None if the app is not the caller's accepted app (AC1/AC2).

    None when get_owned_app(owner, app_id) is None OR status != ACCEPTED (a non-owner's id is
    indistinguishable from not-found — AC8/R3). Reach = impression_breakdown (curated-first)
    + densified impression_trend. Funnel = app_funnel (RAISES loud on DB error). Reviews =
    reviews_for_app, but a reviews-read failure degrades soft (ReviewsView.available=False),
    never failing the whole view (§7).
    """
```

### 5.3 NEW — `apps/dashboard/views.py` (HTTP)

```
GET /dashboard/                      name="dashboard:my-apps"
GET /dashboard/apps/<uuid:app_id>/   name="dashboard:app"
```

Both: `@require_http_methods(["GET"])` + `@login_required` + `@require_role(DEVELOPER)`
(GET-only ⇒ no mutation possible, AC8). `?window=<key>` selects the window (coerced via
`resolve_window`; unknown/blank → default; AC7). Responses:

| View | 200 | 404 | 403 | 500 |
|---|---|---|---|---|
| `my-apps` | renders `my_apps.html` with the summaries (incl. **empty** own-nothing state, AC2) | — | non-developer (role gate) | signals read raised (loud, §7) |
| `app` | renders `app_reception.html` | `build_app_reception` returns `None` (not owner / not accepted) | non-developer | core reception (signals) read raised (loud) |

The reviews-slot degradation never changes the status code (200 with a "reviews unavailable"
affordance). **No `from apps.signals import capture`** anywhere in the app — enforced by an
AST import-absence test (mirrors `apps/discovery/tests/test_imports.py`), so viewing a
dashboard can never emit a D-7 impression of the developer's own app (AC8, structural).

### 5.4 Contract evolution
The two URL names + the two selector signatures are the irreversible public surface; the
DTOs are internal (template + tests only). A future surface, a 9th window, or a
funnel-over-time addition each extend an enumerated table or add a function — none breaks the
above.

---

## 6. UX flow & states

**Screen A — My apps (`/dashboard/`).** A list of the developer's *accepted* apps, each a
card: app name (→ link to the per-app view), **Reach: N shown (C curated)**, **Click-throughs:
X**, over a default window with a window selector applying to the whole list. States:
- *own-nothing* (developer owns no accepted app): a friendly empty panel ("You have no
  accepted apps yet" + link to submit) — **200**, AC2.
- *loading*: server-rendered (no async); no spinner state needed.
- *error*: signals read down → a normal 500 page (loud, never a fake-empty list, R1).

**Screen B — App reception (`/dashboard/apps/<id>/`).** Sections top-to-bottom:
1. **Header** — app name + the 8-window selector (`1w…all`), current selection highlighted.
2. **Reach** — the combined **total**, then a per-source breakdown list **curated `DIGEST`
   first and highlighted** ("shown to N matched users"), then `APP_PAGE` and any later
   surfaces; each source labelled; a source with 0 reads **"0"** with a *"no curated shows
   yet"* affordance for an empty `DIGEST` (AC3/AC4).
3. **Reach trend** — an inline **SVG line chart**: a total-impressions line + a distinguished
   **curated line**, over the window's buckets, with a `<table>` fallback carrying the exact
   per-bucket numbers (accessibility + exact-value testability). Empty window → "no
   impressions in this window" (no chart). (AC10.)
4. **Engagement funnel** — impressions → click-throughs → returns @ *short*/*long* (labelled
   with the configured day counts) → subscribes → page-reengagements → shares; the
   **off-platform proxy shown separately** (AC5).
5. **Reviews** — total count + the raw per-score distribution + the recent review list (no
   average, no eligibility flag, AC6); degraded → "reviews unavailable right now".
- *not-found / not-owned*: **404** (indistinguishable, AC8/R3).

House style: extends a minimal `dashboard/base.html` (mirrors `discovery/base.html`),
server-rendered, no JS dependency.

---

## 7. Failure modes (per component)

| Component | Failure | Detection | Response |
|---|---|---|---|
| Core reception read — `app_funnel` / `impression_breakdown` / `impression_trend` / `funnel_for_apps` | DB slow/down/garbage | exception propagates | **FAIL LOUD**: increment `DASHBOARD_RECEPTION_DEGRADED` (the one alert) and let it 500. A fake-empty dashboard would lie about H2 and corrupt M1/M3/M4 (R1). Mirrors discovery's `DISCOVERY_LISTING_DEGRADED`. |
| Reviews slot — `reviews_for_app` | DB error in the ratings read | try/except in `reception.build_app_reception` | **FAIL SOFT**: `ReviewsView.available=False`, increment `DASHBOARD_REVIEWS_DEGRADED`, render the rest of the view. Reviews are secondary to the reception headline; mirrors ratings' `RATING_DISPLAY_DEGRADED`. |
| Owner-scope — `get_owned_app` returns `None` / app not accepted | normal control flow | `build_app_reception` → `None` | **404** (indistinguishable from a real non-existent app — no enumeration, AC8/R3). Increment `DASHBOARD_ACCESS_DENIED`. |
| Role gate | non-developer requests the surface | `require_role(DEVELOPER)` (fail-closed) | **403** (`ROLE_GATE_DECISION` already counted in accounts). |
| `window` param | malformed/unknown key | `resolve_window` | coerce to `DEFAULT_WINDOW_KEY` — never an error (a bad bookmark must not 500). |
| Trend densify / sparkline | empty window (no impressions) | `is_empty` | render "no impressions in this window"; `sparkline=None` — not an error (AC4). |

Idempotency/timeouts: all reads are idempotent GETs; DB timeouts surface as the loud 500
above (no retry — a read either succeeds fast or the operator sees the alert). Blast radius:
a failure affects only the requesting developer's request; nothing is written.

---

## 8. Non-functional handling

**Performance (AC9/M6).** My-apps list = `funnel_for_apps` (2 queries) + `impression_breakdown_for_apps`
(1 query) = **3 queries independent of K apps** (no per-app funnel — the AC9 N+1 trap). Per-app
view = `app_funnel` (2) + `impression_breakdown` (1) + `impression_trend` (1) + `reviews_for_app`
(2) + `get_owned_app` (1) = a **fixed** ~7 queries. All filtered by indexed `(app_id, occurred_at)`;
the trend's bucket count is bounded per §4.3, so the surface holds at 100× corpus (M6). No hard
global latency budget (D-2 "scale as we go"); these are bounded reads by construction.

**Security (§6/§10).** Authn = `login_required`; authz = `require_role(DEVELOPER)` **and**
owner-scope on every read (defence in depth — owning an app already implies the developer role,
but both gates are explicit so a future ownership path can't bypass scope). GET-only ⇒ no CSRF
write surface, no mutation (AC8). No IDOR: the only id accepted is `app_id`, always checked
against `owner` (a non-owner id ⇒ 404). No `signals.capture` import ⇒ a developer cannot inflate
their own reach by viewing the dashboard (structural).

**Observability (new constants in `apps/core/observability.py`):**
`DASHBOARD_MY_APPS_VIEWED` (M1/M2), `DASHBOARD_RECEPTION_VIEWED` (M1/M2, tags: window),
`DASHBOARD_ACCESS_DENIED` (probing/owner-scope-deny signal), `DASHBOARD_RECEPTION_DEGRADED`
(**the one alert** — core read raised), `DASHBOARD_REVIEWS_DEGRADED` (fail-soft fell back),
`DASHBOARD_NONEMPTY_RECEPTION` (M3 — a viewed app whose funnel is non-zero). M4 (curated-reach
coverage) and M5 (leak count = 0) are analyst-derived from the breakdown/tests, not runtime
counters (a leak would not increment a counter — M5 is a test target, R3). M6 = request timing.

**Rollback (§12).** Remove the one `config/urls` include (+ delete the app) — zero data
migration, since the dashboard owns no schema. The two additive signals selectors are inert
when unused and harmless to leave (no behavior change to existing consumers).

---

## 9. Tests — AC & metric coverage map

Each module is unit-testable in isolation (signals reads at the ORM level; `reception` with
the selectors; views via the test client).

| AC / M | Verification |
|---|---|
| **AC1** owner-scoped list | dev with 2 accepted apps (+ a 3rd owned by another dev) → list shows exactly the 2; never the 3rd. |
| **AC2** non-dev / own-nothing | non-developer → 403; developer owning nothing → 200 empty own-nothing; another dev's app id → 404. |
| **AC3** total + per-source breakdown | 5 DIGEST + 20 APP_PAGE → `ReachView.total==25`; `surfaces` lists DIGEST(5, curated, first) then APP_PAGE(20); a *new* `Surface` value appears in `by_surface` with **no dashboard code change** (enumeration test). |
| **AC4** honest zero | app with 0 DIGEST → DIGEST source reads `0` with the "no curated shows yet" affordance; never blank/omitted/fabricated. |
| **AC10** trend + curated line | impressions across the window → dense `buckets` with a `total` and a distinct `curated` series; empty window → `is_empty`, no chart. Exact per-bucket numbers asserted via the `<table>` fallback. |
| **AC5** funnel = corpus | every `FunnelView` count == the matching `app_funnel` field for the same window; off-platform proxy shown separately, never folded into click-throughs. |
| **AC6** reviews faithful, no average | total + raw distribution + recent list rendered; assert **no** average/score/rank/eligibility appears anywhere. |
| **AC7** window bounds figures | events in/out of each of the 8 windows → figures recompute to in-window only; all-time counts every event; bad `window` → default. |
| **AC8** read-only | views are GET-only (POST → 405); AST test: **no `signals.capture` import**; viewing records no Impression/EngagementEvent row. |
| **AC9** bounded reads | assert constant query count for the my-apps list at K=2 vs K=20 apps (`assertNumQueries`); per-app view fixed query count. |
| **M1/M2/M3** | counters emitted on view; `DASHBOARD_NONEMPTY_RECEPTION` only when funnel non-zero. |
| **M5** leak=0 | AC1/AC2 owner-scope tests are the M5 guard (target 0). |
| **Invariant** | `impression_breakdown(app,w).total == app_funnel(app,w).impressions` for random fixtures. |
| **Regression** | the full existing `apps.signals` + `apps.ratings` + `apps.catalog` suites stay green after the additive signals selectors (contract-preserving). |

---

## 10. Alternatives considered (≥1 genuinely different, rejected)

1. **Read `signals_*` tables directly from the dashboard for the breakdown/trend.** *Rejected
   — breaks D-7/R4* (nothing reads `signals_*` past `signals.selectors`); it would duplicate
   the funnel's query knowledge and let the dashboard drift from the corpus's one read path.
   Chosen instead: add the reads to `signals.selectors` (additive, neutral).
2. **Put the "curated" judgement in the dashboard (hardcode `DIGEST`).** *Rejected — two
   sources of truth* for what "curated" means; the D-8 definition already lives in
   `ratings.gate.CURATED_SURFACES`. Chosen: reuse it, so a future change to the curated set is
   one line in one place.
3. **Derive the breakdown by summing trend buckets (drop `impression_breakdown`).** *Rejected*
   — couples the windowed totals to the chart granularity and risks disagreeing with
   `app_funnel.impressions`. Chosen: a separate 1-query aggregate with the equality invariant
   (§4.2). The marginal cost is one tiny grouped query.
4. **Client-side JS charting (Chart.js etc.) for the trend.** *Rejected — adds a JS build/
   dependency* against the D-4 server-rendered-templates default for a single MVP line. Chosen:
   a pure-Python inline-SVG polyline + a `<table>` fallback (no dependency, accessible, exactly
   testable).
5. **A custom date-range picker (arbitrary start/end).** *Rejected by DN-19.b* — unbounded
   query surface for no MVP need. Chosen: the fixed 8-window table.

**What the chosen design sacrifices:** windows are *rolling* approximations (30/365-day, not
calendar months), and the trend is a fixed total+curated line (no per-series toggle) — both
deliberate MVP simplifications (DN-19.a/b "maybe later"), cheap to revisit.

---

## 11. Self-critique (skeptical senior engineer)

- *"All-time over a huge corpus is unbounded."* → Bounded **by design**: all-time uses MONTH
  granularity (§4.3), so bucket count is ≈12·(data-age-years); the underlying counts are
  index-backed grouped aggregates, not row scans in Python. Acceptable at 100×.
- *"Is the SVG chart over-engineering?"* → AC10 explicitly requires impressions *plotted over
  time with a distinguished curated line*; a line chart is in scope. The `<table>` fallback
  keeps it accessible and makes the exact numbers testable without parsing SVG. Kept minimal
  (one pure function).
- *"Role gate AND owner-scope is redundant."* → Owning an app already implies the developer
  role, but the two gates guard different things (surface visibility vs per-app leakage) and
  defence-in-depth on an integrity-sensitive read (R3/M5) is worth one decorator. Kept.
- *"Breakdown vs funnel could double-count or disagree."* → The §4.2 equality invariant is a
  test; both read the same table/window.
- *"Touching the closed signals app is risk."* → Additive functions + one enum, no
  model/migration/index, existing reads untouched, full signals suite re-run (regression in
  §9). Same precedent as ratings' `has_impression` and open-search-browse's catalog additions.
- *Simplification pass:* dropped any my-apps review-count column (would need a bulk ratings
  count to stay bounded; reviews live on the per-app view — S4). Nothing else trimmed without
  losing an AC.

---

## 12. Rollout strategy

- **Stack:** reuse **D-4** (Python/Django + PostgreSQL, server-rendered templates) — **no new
  global ADR**; shared-code root stays `apps/` (CODEMAP). The dashboard is `apps/dashboard/`.
- **Activation switch = one line:** add `path("dashboard/", include("apps.dashboard.urls"))`
  to `config/urls.py` and `"apps.dashboard"` to `INSTALLED_APPS`. The two additive signals
  selectors ship with it but are inert until called.
- **No migration, no feature flag, no data backfill** (the app owns no schema). Order is
  irrelevant — the additive selectors can land before or with the app.
- **Backward compatibility:** every existing consumer of `signals.selectors`/`ratings`/`catalog`
  is unaffected (additive only).
- **Rollback = remove the include** (+ optionally delete the app). Zero data migration; the
  unused selectors are harmless to leave. Rehearsal: confirm the routes resolve, then confirm
  removing the include 404s them with the rest of the platform green.
- **Promotion:** local/dev now (no prod target/traffic, as the prior nine features); the
  live-metrics window (M1–M6) defers until a consumer/prod target exists — and M3/M4 are
  expected **thin** until a `DIGEST` emitter ships (brief R1/AC4), reported honestly, not a bug.

---

## 13. Assumption ledger (all verified this session)

| # | Assumption | Status |
|---|---|---|
| A1 | `signals.selectors` has the funnel reads but **no** per-surface / time-bucketed read | **verified** — read `apps/signals/selectors.py` |
| A2 | `Surface` = `{DIGEST, APP_PAGE}`, documented extensible; `Surface.values`/`.label` available | **verified** — `apps/signals/kinds.py` |
| A3 | `ratings.gate.CURATED_SURFACES = {Surface.DIGEST}` is the single D-8 curated definition | **verified** — `apps/ratings/gate.py` |
| A4 | `reviews_for_app` gives count + raw distribution + capped list, **no average/eligibility** | **verified** — `apps/ratings/selectors.py` |
| A5 | `get_owned_app`/`list_owned_apps` are owner-scoped; a non-owner id ⇒ `None` | **verified** — `apps/catalog/selectors.py` |
| A6 | `require_role(DEVELOPER)` is a fail-closed Django view decorator (403 on deny) | **verified** — `apps/accounts/permissions.py` |
| A7 | The `(app_id, occurred_at)` index exists, backing the new grouped aggregates (no new index) | **verified** — `signals_imp_app_time_idx` in `apps/signals/models.py` |
| A8 | Model-less consumer pattern + one-`config/urls`-include activation is the house norm | **verified** — `apps/pages/`, `apps/discovery/` |
| A9 | `config.return_window_short_days()/_long_days()` label the funnel's returns | **verified** — `apps/core/config.py` |

---

## 14. Decisions (feature-local; PROPOSED — ratified on DESIGN approval)

Logged in [DECISIONS.md](DECISIONS.md) as **DD-DESIGN-1…5 (PROPOSED)**; **OQ-DD-4 →
RESOLVED-in-design**. No new **global** ADR (reuses D-3/D-5/D-6/D-7/D-8).

- **DD-DESIGN-1** — New model-less consumer app `apps/dashboard/` (mirrors `pages`/`discovery`);
  activation/rollback = one `config/urls` include; owns no schema.
- **DD-DESIGN-2** — **Resolves OQ-DD-4.** Two additive, **neutral** reads on `signals.selectors`
  — `impression_breakdown[_for_apps]` (per-`Surface` counts, all surfaces zero-filled, AC3/AC4)
  and `impression_trend` (per-`Surface` per-time-bucket, AC10) + `TrendGranularity`. No model/
  migration/index. Signals never judges "curated"; the dashboard composes curated via
  `ratings.gate.CURATED_SURFACES` (one source).
- **DD-DESIGN-3** — The 8 reporting windows + per-window bucket granularity are a code-fixed
  declarative table in `apps/dashboard/windows.py`; all-time is lower-bounded by an epoch
  sentinel so the existing range-based selectors are reused unchanged (AC7).
- **DD-DESIGN-4** — Failure split: core reception (signals) read **fails loud** (500 +
  `DASHBOARD_RECEPTION_DEGRADED` alert); reviews slot **fails soft**; owner-scope ⇒ 404
  indistinguishable; role-gated GET-only with **no `signals.capture` import** (read-only, AC8).
- **DD-DESIGN-5** — Reach total/curated split reuses `CURATED_SURFACES`; the trend is a
  pure-Python inline-SVG line (total + curated) with a `<table>` fallback (no JS dependency).
```
