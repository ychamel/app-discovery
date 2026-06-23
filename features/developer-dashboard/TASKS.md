# TASKS — developer-dashboard

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-19 → approved) and the **ratified** [DESIGN.md](DESIGN.md) (DN-DD-DESIGN → approved;
DD-DESIGN-1…5 ratified; reuses
[D-3](../../DECISIONS.md)/[D-5](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md)/[D-8](../../DECISIONS.md)
as-is — **no new global ADR**). Produces an ordered, independently-verifiable task list; full per-AC
verification is written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a contract or
> decision the design does not already make. Two kinds of change exist here:
> 1. **An additive, neutral extension to the closed [signal-capture](../signal-capture/) (`apps/signals`)
>    read surface** — `TrendGranularity` + `impression_breakdown[_for_apps]` + `impression_trend` on
>    `signals.selectors` (DESIGN §5.1, DD-DESIGN-2; resolves OQ-DD-4). It touches a closed app but
>    **changes no existing contract** — `AppFunnel` and every existing selector are unchanged, **no
>    model / migration / index** (backed by the existing `signals_imp_app_time_idx`, A7). Signals stays
>    **neutral**: it counts per `Surface` and never judges which surface "means" curation.
> 2. **A new model-less consumer app `apps/dashboard/`** (DESIGN §3/§4.1, DD-DESIGN-1) — owns no table,
>    activated/rolled back by one `config/urls` include (+ the `INSTALLED_APPS` line), a **near-twin of
>    the closed-out `apps/discovery/` + `apps/pages/`** (match their conventions, CLAUDE.md §5.5). It
>    **imports nothing from `signals.capture`** (AC8 structural — DESIGN §5.3/§6).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces → UI → telemetry → docs.** There is **no** schema/data step
   (the dashboard owns no model and the two new signals reads are pure aggregates over existing rows,
   no migration — DESIGN §4.1/§4.2). The spine is therefore: the additive signals reads (**T-01**) →
   the reporting-window vocabulary (**T-02**) → the pure SVG chart helper (**T-03**) → the
   reception-composition layer (**T-04**) → the HTTP views + templates + observability + the activation
   include (**T-05**) → docs/CODEMAP/DECISIONS (**T-06**).
2. **Risk first (DESIGN §3/§9/§11).** The single load-bearing, most-uncertain piece is the **additive
   read on the closed `apps/signals` app** (DESIGN §5.1) — it is the OQ-DD-4 resolution, the only
   cross-app touch into a closed feature, and it carries the design's headline integrity invariant
   (`impression_breakdown(app,w).total == app_funnel(app,w).impressions`, §4.2) plus the zero-fill
   (AC4) and time-bucket-bounded (AC9/M6) guarantees. It lands at **T-01** and is unit-tested at the
   ORM level — including the equality invariant and a constant-query-count assertion — **before any
   dashboard module exists**, so a surprise in the signals corpus surfaces as early as possible. Every
   `apps.signals` test stays green in its DoD (regression on the closed app).
3. **Each task leaves the system working and releasable.** T-01 adds inert, un-called selectors to a
   closed app (no existing consumer changes). T-02/T-03/T-04 add pure, un-routed modules to a new app
   that is **not yet in `INSTALLED_APPS` and not routed** — unreachable over HTTP, discovered only by
   the test runner. The surface becomes reachable **only at T-05** — the single `config/urls` include
   (+ the `INSTALLED_APPS` line) is the entire activation switch; removing them is the entire rollback
   (DESIGN §8/§12), with **zero data migration** (the app owns no schema). T-06 is docs only.

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/signals/selectors.py` — **T-01** only (`TrendGranularity` + the three new reads + their DTOs);
  the existing `app_funnel`/`funnel_for_apps`/`category_impressions`/`has_impression` are **unchanged**.
- `apps/signals/tests/` — **T-01** only (the new-reads test module + the invariant/regression checks).
- `apps/dashboard/windows.py` — **T-02** only (new). Imports `TrendGranularity` from `signals.selectors`.
- `apps/dashboard/charts.py` — **T-03** only (new; stdlib only, no project imports).
- `apps/dashboard/reception.py` — **T-04** only (new; the composition DTOs + the two `build_*` funcs).
- `apps/dashboard/views.py` / `urls.py` / `templates/dashboard/*.html` — **T-05** only (new).
- `apps/core/observability.py` — **T-05** only (the six `DASHBOARD_*` counters).
- `config/urls.py` and `config/settings.py` `INSTALLED_APPS` — **T-05** only (the one `dashboard/`
  include + the `"apps.dashboard"` line = the activation switch, DESIGN §12).
- `apps/dashboard/` package scaffold (`__init__.py`, `apps.py`, `tests/__init__.py`) — created in
  **T-02** (the first task to add a module there); subsequent tasks add files, never re-edit these.
- **No new `apps/core/config.py` entry** — the window set lives in `apps/dashboard/windows.py` (a closed
  code-fixed vocabulary, DESIGN §4.3), and the funnel/review labels reuse the **existing**
  `config.return_window_short_days()/_long_days()` and `config.reviews_display_limit()` (DESIGN §1/§8).

---

## T-01 — Signals additive reads: `TrendGranularity` + `impression_breakdown[_for_apps]` + `impression_trend` (the OQ-DD-4 resolution; the risk centerpiece)

- **Description.** Add the surface-aware and time-bucketed reads to `apps/signals/selectors.py` exactly
  per DESIGN §5.1 (DD-DESIGN-2) — the **only** D-7-permitted reader of `signals_*` for these aggregates
  (R4). **Additive and neutral**: new functions + one new enum; the existing `AppFunnel` reads are
  untouched, and signals **never** decides which surface "means" curation (that stays
  `ratings.gate.CURATED_SURFACES`, composed by the dashboard at T-04). **No model, no migration, no new
  index** — every read is a `GROUP BY` aggregate over the existing `signals_impression` table, filtered
  by `app_id + occurred_at` and backed by the **existing** `signals_imp_app_time_idx (app_id,
  occurred_at)` (A7).
  - `TrendGranularity(models.TextChoices)` — `DAY="day"`, `WEEK="week"`, `MONTH="month"`; maps to
    `TruncDate`/`TruncWeek`/`TruncMonth` in **UTC** (matching the existing returns-derivation date math,
    §5.1). This enum is the import `apps/dashboard/windows.py` (T-02) depends on.
  - `ImpressionBreakdown` (`@dataclass(frozen=True)`): `app_id: UUID`, `total: int`,
    `by_surface: dict[str, int]` — **every `Surface.values` key present, zero-filled** (a surface with no
    impressions reads `0`, AC4; a `Surface` added later appears automatically with no caller change,
    AC3 extensibility).
  - `ImpressionBucket` (`@dataclass(frozen=True)`): `bucket_start: datetime` (the truncated UTC bucket
    key), `total: int`, `by_surface: dict[str, int]` (every `Surface` value, zero-filled, for that
    bucket).
  - `impression_breakdown(app_id, *, start, end) -> ImpressionBreakdown` — per-`Surface` counts over
    `[start, end]` in **one** grouped query; `by_surface` enumerates `Surface.values` (zero-filled);
    `total` = the sum.
  - `impression_breakdown_for_apps(app_ids, *, start, end) -> dict[UUID, ImpressionBreakdown]` — the
    bulk variant in **one** grouped query regardless of K apps (no N+1, AC9); apps with no impressions
    present with an all-zero breakdown; keyed by `app_id`. (Mirrors the `funnel_for_apps` bulk pattern.)
  - `impression_trend(app_id, *, start, end, granularity) -> list[ImpressionBucket]` — impressions
    bucketed by `granularity`, split per `Surface`, in **one** grouped query; returns only buckets with
    ≥1 impression (**sparse** on the time axis — the caller densifies at T-04), **ascending** by
    `bucket_start`. `Trunc` is UTC.
  - **No ordering/score/weight** anywhere (raw counts only, the D-7 raw-only guarantee, AC8/§5.1).
- **Dependencies.** none (foundational — T-02 imports `TrendGranularity`; T-04 calls all three reads).
- **Definition of done.** ORM-level tests (seed real `Impression` rows across surfaces and time;
  no HTTP, no mocking):
  - **breakdown + zero-fill (AC3/AC4):** 5 `DIGEST` + 20 `APP_PAGE` in-window → `total == 25` and
    `by_surface == {"digest": 5, "app_page": 20}`; an app with **no** `DIGEST` → `by_surface["digest"]
    == 0` (present, not omitted). **Enumeration test:** `by_surface.keys() == set(Surface.values)` so a
    surface added later appears with no signature change.
  - **the headline invariant (§4.2):** for random fixtures and several windows,
    `impression_breakdown(app, start=s, end=e).total == app_funnel(app, start=s, end=e).impressions`
    (both count `Impression` rows in the same window) — the reach section can never silently disagree
    with the funnel section.
  - **trend (AC10):** impressions spread across a window → sparse `ImpressionBucket` list ascending by
    `bucket_start`, each with `total` and a per-`Surface` split; an empty window → `[]`; bucket keys
    truncate correctly per `DAY`/`WEEK`/`MONTH` (UTC). A bucket's `total` equals the sum of its
    `by_surface`.
  - **window bounds (AC7):** events outside `[start, end]` are excluded from both reads; an `all`-style
    very-early `start` includes every event.
  - **bounded reads (AC9):** `impression_breakdown` is one query; `impression_breakdown_for_apps` is a
    **constant** query count at K=2 vs K=20 apps (`assertNumQueries`); `impression_trend` is one query.
  - **Regression:** the full existing `apps.signals` suite stays green (the additive functions change no
    existing read); `app_funnel`/`funnel_for_apps`/`has_impression`/`category_impressions` behaviour
    unchanged. `makemigrations --check` clean (no model change); `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/signals/selectors.py` (`TrendGranularity` + `ImpressionBreakdown` +
  `ImpressionBucket` + the three reads; `TruncWeek`/`TruncMonth` imports added alongside the existing
  `TruncDate`), `apps/signals/tests/` (a new test module for the three reads + the invariant).

## T-02 — `apps/dashboard/windows.py`: the 8 reporting windows + per-window granularity + `resolve_window`

- **Description.** Create the new model-less app's **reporting-window vocabulary** exactly per DESIGN
  §4.3 (DD-DESIGN-3) — a **code-fixed declarative table** (the change-cheap place: add/remove a window =
  edit one tuple), modelled on how `ratings.gate.CURATED_SURFACES` lives in its feature app rather than
  in env config. Also scaffolds the new package (`__init__.py`, `apps.py` with
  `AppConfig(name="apps.dashboard", label="dashboard")`, `tests/__init__.py`) mirroring
  `apps/discovery/apps.py` — **but does not register it in `INSTALLED_APPS` and adds no route** (that is
  the T-05 activation switch; the package is import-only here, discovered by the test runner).
  - `ReportingWindow` (`@dataclass(frozen=True)`): `key: str`, `label: str`, `duration: timedelta | None`
    (`None` ⇒ all-time), `granularity: TrendGranularity` (imported from `signals.selectors`, T-01).
  - `REPORTING_WINDOWS: tuple[ReportingWindow, ...]` — the **8 windows in selector display order**
    exactly as DESIGN §4.3: `1w`/`2w`/`1m` (`DAY`), `3m`/`6m` (`WEEK`), `1y`/`3y`/`all` (`MONTH`).
    Granularity per window keeps bucket counts bounded (the M6/AC9 lever): DAY ≤31 pts, WEEK ≤26, MONTH
    ≤12·years (all-time bounded by data age **because** it is monthly).
  - `DEFAULT_WINDOW_KEY = "1m"`; `ALL_TIME_START = datetime(1970, 1, 1, tzinfo=UTC)` (predates any
    event, so all-time reuses the range-based reads unchanged — not a special code path).
  - `resolve_window(key, *, now) -> ResolvedWindow(window, start, end, granularity)`: unknown/blank key
    → `DEFAULT_WINDOW_KEY` (**fail-safe, never raises** — a bad bookmark must not 500, §7); `end = now`;
    `start = now - duration`, or `ALL_TIME_START` for all-time. (`ResolvedWindow` carries the chosen
    `ReportingWindow` so the view can highlight the active selection and pass `granularity` to
    `impression_trend`.)
- **Dependencies.** T-01 (`TrendGranularity`).
- **Definition of done.** Unit tests (pure, no DB):
  - `REPORTING_WINDOWS` has exactly the **8** keys in the DESIGN §4.3 order with the specified
    label/duration/granularity per window; `DEFAULT_WINDOW_KEY` is one of them.
  - `resolve_window("3m", now=T)` → `start == T - 90d`, `end == T`, `granularity == WEEK`;
    `resolve_window("all", now=T)` → `start == ALL_TIME_START`, `end == T`, `granularity == MONTH`.
  - `resolve_window(unknown_or_blank, now=T)` → the **default** window resolved (no exception) — the
    AC7 fail-safe.
  - The package imports cleanly and the test runner discovers `apps/dashboard/tests/`.
  - `ruff` clean; full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/dashboard/__init__.py` (new), `apps/dashboard/apps.py` (new),
  `apps/dashboard/windows.py` (new), `apps/dashboard/tests/__init__.py` (new),
  `apps/dashboard/tests/test_windows.py` (new).

## T-03 — `apps/dashboard/charts.py`: the pure inline-SVG sparkline helper (+ table-fallback data)

- **Description.** Add the **pure function** chart helper exactly per DESIGN §3/§5.2/§6 (DD-DESIGN-5,
  alt 4) — a dense trend series → inline-SVG polyline points for the **total** line + the distinguished
  **curated** line, plus the same series exposed for a `<table>` fallback. **stdlib only, no I/O, no
  project imports, no JS dependency** (the D-4 server-rendered default — alternative 4 rejected the JS
  charting library).
  - `build_sparkline(buckets) -> SparklineSvg | None` where the input is the dense `list[TrendBucket]`
    (the T-04 DTO: `label`, `total`, `curated`). Returns `None` for an empty/all-zero window (the view
    renders "no impressions in this window" — AC4/AC10, never a degenerate chart).
  - `SparklineSvg` (`@dataclass(frozen=True)`): the SVG geometry the template needs — e.g. viewBox
    dimensions, the `total` polyline points string, the `curated` polyline points string. Coordinate
    math (scale to the max value, x-step over the bucket count) is the only logic; it lives **here**, not
    in the template.
  - The `<table>` fallback carries the **exact per-bucket numbers** (`label`/`total`/`curated`) — this
    is what AC10 is asserted against (exact values testable without parsing SVG; accessibility).
- **Dependencies.** none. (The `TrendBucket` shape it consumes is finalized in T-04; this task may
  define `build_sparkline` against the documented field names — `label`/`total`/`curated` — and T-04
  produces matching DTOs. To avoid an import cycle, `charts.py` accepts a sequence of objects/namedtuples
  with those attributes, or T-04 owns `TrendBucket` and `charts` imports it; pick the boring option that
  keeps `charts` dependency-free — see the DoD.)
- **Definition of done.** Unit tests (pure, no DB):
  - a multi-bucket series with a curated subset → a `SparklineSvg` whose two polylines have one point
    per bucket, scaled so the max value maps to the chart extent; the curated points are distinct from
    the total points.
  - an all-zero / empty series → `None` (no chart).
  - a single-bucket series renders without divide-by-zero (degenerate-axis guard).
  - `charts.py` imports **nothing** from `apps.*` (or imports **only** the `TrendBucket` DTO from
    `reception` if that is the chosen seam) — assert it has no DB/selector dependency. `ruff` clean;
    full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/dashboard/charts.py` (new), `apps/dashboard/tests/test_charts.py` (new).

## T-04 — `apps/dashboard/reception.py`: the composition layer (`build_my_apps_summaries` + `build_app_reception`)

- **Description.** Add the **one place that assembles reception** exactly per DESIGN §3/§5.2 — calls the
  four read surfaces, orders surfaces **curated-first** via `ratings.gate.CURATED_SURFACES` (the single
  D-8 source, reused — never re-defined; alt 2 rejected), densifies the sparse trend onto a continuous
  axis, and projects to frozen view-model DTOs. Holds **no ORM access**; the dashboard's only business
  logic is this composition + ordering.
  - **DTOs (DESIGN §5.2), all `@dataclass(frozen=True)`:** `SurfaceReach` (`surface`, `label`, `count`,
    `is_curated`), `ReachView` (`total`, `surfaces` **curated-first**, `trend`), `TrendBucket` (`label`,
    `total`, `curated`), `TrendView` (`granularity_label`, dense `buckets`, `sparkline`, `is_empty`),
    `FunnelView` (a presentation projection of `AppFunnel` — no new numbers; `off_platform_proxy` a
    **separate** field, never folded into `click_throughs`, AC5; the short/long return labels carry the
    configured day counts from `config.return_window_short_days()/_long_days()`), `ReviewsView`
    (`available` — `False` ⇒ degraded; `total_count`; raw `distribution`; capped `reviews`; **no
    average**, AC6), `ReceptionSummary` (one my-apps row: `app_id`, `app_name`, `total_impressions`,
    `curated_impressions`, `click_throughs`), `AppReception` (`app_id`, `app_name`, `window`,
    `available_windows`, `reach`, `funnel`, `reviews`).
  - `build_my_apps_summaries(owner, *, window) -> list[ReceptionSummary]` (S1, AC1/AC2/AC9): owned,
    **ACCEPTED-only** (filter `catalog.list_owned_apps(owner)` to `status == ACCEPTED`). **Bounded:** one
    `signals.funnel_for_apps` (2 queries) + one `signals.impression_breakdown_for_apps` (1 query) for
    **all** K apps — total query count **independent of K** (the AC9 N+1 trap; no per-app funnel).
    `curated_impressions = Σ by_surface over CURATED_SURFACES`. Empty/own-nothing owner ⇒ `[]` (AC2).
    **RAISES** on a signals DB error (fail loud — §7/DD-DESIGN-4; a fake-empty list would lie about H2).
  - `build_app_reception(owner, app_id, *, window) -> AppReception | None` (S2–S5, AC1–AC10):
    - **owner-scope (AC8/R3):** `None` when `catalog.get_owned_app(owner, app_id)` is `None` **or** the
      app's status `!= ACCEPTED` — a non-owner's id is **indistinguishable** from not-found (the view
      404s; no enumeration).
    - **reach (AC3/AC4/AC10):** `impression_breakdown` → `ReachView` with `surfaces` **curated-first**
      (DIGEST highlighted), each `SurfaceReach.is_curated = surface in CURATED_SURFACES`, each labelled
      via `Surface(...).label`; `impression_trend(..., granularity=window.granularity)` **densified** to
      a continuous axis (every bucket in the window present, zero-filled — the selector returns sparse),
      `curated = Σ over CURATED_SURFACES` per bucket, then `charts.build_sparkline(...)` for the
      `TrendView` (`is_empty`/`sparkline=None` on an empty window).
    - **funnel (AC5):** `app_funnel(app_id, window)` → `FunnelView`; **RAISES** loud on a DB error
      (core reception read — §7).
    - **reviews (AC6) — fail soft (§7/DD-DESIGN-4):** `reviews_for_app(app_id,
      limit=config.reviews_display_limit())` wrapped in try/except; on error → `ReviewsView(available=
      False, …)` (the slot degrades; the rest of the view still renders), the **only** soft path.
  - **Densify helper:** map the sparse `impression_trend` buckets onto the full ordered bucket axis the
    window/granularity implies (the inverse of the selector's sparseness) — the one place trend gaps
    become explicit zeros (AC10 "dense buckets, zero-filled").
- **Dependencies.** T-01 (the three signals reads + `TrendGranularity`), T-02 (`ReportingWindow`/
  `resolve_window` shape), T-03 (`build_sparkline`).
- **Definition of done.** Tests at the composition level (real selectors + seeded fixtures; the reviews
  fail-soft path exercised by patching `reviews_for_app` to raise):
  - **AC1/AC2 owner-scope:** a dev with 2 accepted apps (+ a 3rd owned by another dev) →
    `build_my_apps_summaries` returns exactly the 2; `build_app_reception(owner, other_devs_id)` →
    `None`; an owned **non-accepted** app id → `None`; an owner with no accepted apps → `[]`.
  - **AC3/AC4 reach:** 5 DIGEST + 20 APP_PAGE → `ReachView.total == 25`, `surfaces` lists DIGEST(5,
    `is_curated=True`) **first**, then APP_PAGE(20, `is_curated=False`); a 0-DIGEST app → a DIGEST
    `SurfaceReach` with `count == 0` (present, the honest zero).
  - **AC10 trend:** impressions across the window → **dense** `TrendView.buckets` (zero-filled gaps)
    with a `total` and a distinct `curated` per bucket; empty window → `is_empty=True`, `sparkline=None`.
  - **AC5 funnel:** every `FunnelView` count equals the matching `app_funnel` field for the same window;
    `off_platform_proxy` is its own field, never summed into `click_throughs`.
  - **AC6 reviews:** total + raw distribution + capped list present; **no** average/score/rank/
    eligibility field anywhere on `ReviewsView`/its rows.
  - **AC9 bounded:** `build_my_apps_summaries` is a **constant** query count at K=2 vs K=20 accepted apps
    (`assertNumQueries`); `build_app_reception` is a fixed query count.
  - **fail loud / fail soft (§7):** a patched `app_funnel`/`impression_breakdown` raise propagates out of
    `build_app_reception` (loud); a patched `reviews_for_app` raise yields `ReviewsView.available=False`
    with the rest of the view intact (soft).
  - `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/dashboard/reception.py` (new), `apps/dashboard/tests/test_reception.py`
  (new).

## T-05 — `apps/dashboard/` HTTP: the two views + templates + observability + the `config/urls` include (the activation switch)

- **Description.** Add the two thin GET views, their URLs, the three templates, the six observability
  counters, then wire the **activation switch** — `path("dashboard/", include("apps.dashboard.urls"))`
  in `config/urls.py` **and** `"apps.dashboard"` in `INSTALLED_APPS` (DESIGN §12; removing both = the
  entire rollback, zero data migration). The views hold **no ORM and no business logic** beyond calling
  `reception`/`windows` + gating + rendering — the `apps/discovery` house rule. The app **imports
  nothing from `signals.capture`** (AC8 structural).
  - **Routes (DESIGN §5.3):** `app_name="dashboard"`; `path("", views.my_apps, name="my-apps")`
    (`GET /dashboard/`) and `path("apps/<uuid:app_id>/", views.app_reception, name="app")`
    (`GET /dashboard/apps/<uuid>/`).
  - **Both views:** `@require_http_methods(["GET"])` + `@login_required` + `@require_role(roles.DEVELOPER)`
    (GET-only ⇒ no mutation, AC8; role gate → 403 on a non-developer; owner-scope is enforced *inside*
    `reception` per task T-04 — defence in depth, §8). `?window=<key>` coerced via
    `windows.resolve_window` (unknown/blank → default, never an error — AC7).
  - **`my_apps(request)` (DESIGN §5.3/§6 Screen A):** `build_my_apps_summaries(request.user,
    window=resolved)`; render `my_apps.html` (incl. the **own-nothing** empty state → **200**, AC2);
    increment `DASHBOARD_MY_APPS_VIEWED`. A signals read raising propagates to a loud **500** (count
    `DASHBOARD_RECEPTION_DEGRADED` around the raise, then re-raise — never a fake-empty list, §7/R1).
  - **`app_reception(request, app_id)` (DESIGN §5.3/§6 Screen B):** `build_app_reception(request.user,
    app_id, window=resolved)`; `None` → **404** (`Http404`, indistinguishable from a real not-found,
    AC8/R3) + `DASHBOARD_ACCESS_DENIED`; otherwise render `app_reception.html` + increment
    `DASHBOARD_RECEPTION_VIEWED` (tag: `window`) and `DASHBOARD_NONEMPTY_RECEPTION` **only** when the
    funnel is non-zero (M3). Core reception (signals) read raising → loud **500** +
    `DASHBOARD_RECEPTION_DEGRADED`. The reviews-slot degradation **never** changes the status code (200
    with a "reviews unavailable right now" affordance; `DASHBOARD_REVIEWS_DEGRADED` is counted in
    `reception` at T-04 — confirm it is incremented on that path).
  - **Templates (DESIGN §6) — server-rendered, no JS, all text auto-escaped (no `|safe`):**
    `templates/dashboard/base.html` (mirrors `discovery/base.html`); `my_apps.html` (the app cards:
    name → link to `dashboard:app`, "Reach: N shown (C curated)", "Click-throughs: X", the window
    selector applying to the whole list; the own-nothing empty panel + a submit link); `app_reception.html`
    (the 5 sections top-to-bottom: header + 8-window selector with the active key highlighted; **Reach**
    total + per-source breakdown **curated DIGEST first/highlighted** with a "no curated shows yet"
    affordance for an empty DIGEST; **Reach trend** the inline SVG total+curated lines with the `<table>`
    fallback carrying exact per-bucket numbers, or "no impressions in this window" when empty; **Funnel**
    with the off-platform proxy shown **separately**; **Reviews** count + raw distribution + recent list,
    no average, with the degraded affordance). Keyboard-navigable links/controls.
  - **No `signals.capture` import (AC8 structural):** add an AST import-absence test mirroring
    `apps/discovery/tests/test_imports.py` — assert no `apps.dashboard` module (excluding `tests`)
    imports anything matching `signals.capture`. (The dashboard *does* import `signals.selectors` — the
    test forbids the **capture** emitter specifically, so viewing records no D-7 impression.)
  - **Observability (DESIGN §8) — add to `apps/core/observability.py`:** `DASHBOARD_MY_APPS_VIEWED`,
    `DASHBOARD_RECEPTION_VIEWED`, `DASHBOARD_ACCESS_DENIED`, `DASHBOARD_RECEPTION_DEGRADED` (**the one
    actionable alert**), `DASHBOARD_REVIEWS_DEGRADED`, `DASHBOARD_NONEMPTY_RECEPTION`.
- **Dependencies.** T-02 (`windows`), T-04 (`reception`). (T-03 is reached transitively via T-04.)
- **Definition of done.** Integration tests (Django test client, project URLconf with the `dashboard/`
  include):
  - **AC1 list:** a developer with 2 accepted apps (3rd owned by another dev) → `/dashboard/` shows
    exactly the 2, never the 3rd or its data.
  - **AC2 access:** a non-developer → **403** on both routes; a developer owning nothing → **200**
    own-nothing state; another dev's app id → **404** (indistinguishable from a missing app).
  - **AC3/AC4 reach:** `/dashboard/apps/<id>/` shows the total + per-source breakdown with DIGEST
    first/highlighted and an explicit `0` + "no curated shows yet" affordance when DIGEST is empty.
  - **AC10 trend:** the SVG + `<table>` fallback render with the exact per-bucket total/curated numbers;
    an empty window shows "no impressions in this window" (no chart).
  - **AC5 funnel:** the displayed counts equal `app_funnel` for the window; the proxy renders in its own
    line.
  - **AC6 reviews:** count + distribution + list render; **no** average/score/eligibility anywhere.
  - **AC7 window:** events in/out of each of the 8 windows recompute to in-window only; `all` counts
    every event; a bad `?window=` falls back to the default (no 500).
  - **AC8 read-only:** `POST` to either route → **405**; the AST test confirms no `signals.capture`
    import; a GET writes **no** `Impression`/`EngagementEvent` row.
  - **AC9 bounded:** the my-apps list is a constant query count at K=2 vs K=20 (`assertNumQueries`);
    the per-app view is a fixed query count.
  - **failure split (§7):** `impression_breakdown`/`app_funnel` patched to raise → **500** (not a masked
    empty page) + `DASHBOARD_RECEPTION_DEGRADED`; `reviews_for_app` patched to raise → **200** with the
    reviews slot degraded + `DASHBOARD_REVIEWS_DEGRADED`.
  - the six `DASHBOARD_*` counters exist and fire on their paths (`DASHBOARD_NONEMPTY_RECEPTION` only on
    a non-zero funnel). `manage.py check` clean; `makemigrations --check` clean (the app owns no model);
    `ruff`/template lint clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/dashboard/views.py` (new), `apps/dashboard/urls.py` (new),
  `apps/dashboard/templates/dashboard/{base,my_apps,app_reception}.html` (new),
  `apps/dashboard/tests/test_views.py` + `tests/test_imports.py` (new), `apps/core/observability.py`
  (the six `DASHBOARD_*` counters), `config/urls.py` (the `dashboard/` include),
  `config/settings.py` (`INSTALLED_APPS` += `"apps.dashboard"`).

## T-06 — README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: docs + the shared-code index — no behavioural change (DESIGN §12).
  - `apps/dashboard/README.md` — the app's single responsibility (a pure read orchestrator over the
    D-3/D-6/D-7/D-8 surfaces; **owns no model**; **never imports `signals.capture`**, so viewing emits no
    D-7 impression), the two routes (`dashboard:my-apps` at `/dashboard/`, `dashboard:app` at
    `/dashboard/apps/<id>/`), the loud-core/soft-reviews failure split (the one alert =
    `DASHBOARD_RECEPTION_DEGRADED`), and the **rollback** (remove the `config/urls` `dashboard/` include
    + the `INSTALLED_APPS` line; the two additive signals selectors are then inert and harmless to leave
    — **not** an emergency step, DESIGN §8/§12).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: the additive D-7 reads
    `signals.selectors.impression_breakdown` / `impression_breakdown_for_apps` / `impression_trend` (+
    `TrendGranularity` + the `ImpressionBreakdown`/`ImpressionBucket` DTOs); the new
    `apps/dashboard/` consumer (its two routes, `reception` composition layer, `windows`
    vocabulary, `charts` helper); the six `DASHBOARD_*` observability constants. Note that the window set
    is a code-fixed table in `apps/dashboard/windows.py` (no `config` entry) and that the curated split
    reuses `ratings.gate.CURATED_SURFACES`.
  - [features/developer-dashboard/DECISIONS.md](DECISIONS.md) — mark **DD-DESIGN-1…5** as **built**.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit artifact,
    produced alongside the build, **not** in this task.
- **Dependencies.** T-01…T-05.
- **Definition of done.** `apps/dashboard/README.md` matches the shipped routes/rollback; `CODEMAP.md`
  lists every new shared surface above; `DECISIONS.md` marks DD-DESIGN-1…5 built; `makemigrations
  --check` clean; **full suite green, `ruff` clean, no drift** (the close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/dashboard/README.md` (new), [CODEMAP.md](../../CODEMAP.md),
  `features/developer-dashboard/DECISIONS.md`.

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §5.1 `TrendGranularity` + `impression_breakdown[_for_apps]` + `impression_trend` additive signals reads (DD-DESIGN-2, resolves OQ-DD-4) | **T-01** |
| §4.2 invariant `impression_breakdown(app,w).total == app_funnel(app,w).impressions` | **T-01** (asserted) |
| §4.2/§5.1 zero-fill every `Surface` (AC4) + new-surface auto-appears (AC3 extensibility) | **T-01** |
| §4.2/§5.1/§8 bounded reads — one grouped query each; bulk breakdown no N+1 (AC9/M6) | **T-01** (+ T-04 bulk usage) |
| §4.3 the 8 reporting windows + per-window granularity + `resolve_window` + all-time epoch (DD-DESIGN-3, AC7) | **T-02** |
| §3/§5.2/§6 pure inline-SVG sparkline (total + curated) + `<table>` fallback, no JS (DD-DESIGN-5) | **T-03** (+ T-05 template render) |
| §3/§5.2 reception composition: curated-first ordering via `CURATED_SURFACES`, trend densify, the view-model DTOs | **T-04** |
| §5.2 `build_my_apps_summaries` bounded my-apps list (AC1/AC2/AC9) | **T-04** (+ T-05 view) |
| §5.2 `build_app_reception` owner-scope → `None` (AC8/R3); reach/funnel/reviews assembly | **T-04** (+ T-05 view) |
| §5.3/§6 the two GET views + routes; role gate + GET-only + `?window=` coercion (AC7/AC8) | **T-05** |
| §6 the templates (Screen A own-nothing 200; Screen B 5 sections; curated-first; honest-zero affordance) | **T-05** |
| §5.3/§8 AC8 structural — no `signals.capture` import (viewing emits no D-7) | **T-05** (AST import-absence test) |
| §7/DD-DESIGN-4 failure split — core read fails **loud** (500 + `DASHBOARD_RECEPTION_DEGRADED`); reviews fail **soft**; owner-scope ⇒ 404 | **T-04** (raise/soft in composition) + **T-05** (500/404/200 status mapping) |
| §8 observability — the six `DASHBOARD_*` counters (the one alert = `DASHBOARD_RECEPTION_DEGRADED`); M3 `DASHBOARD_NONEMPTY_RECEPTION` | **T-05** |
| §8/§12 activation/rollback = one `config/urls` include + `INSTALLED_APPS` line; design-for-deletion; zero data migration | **T-05** (wire) + **T-06** (rollback note) |
| §12 docs/CODEMAP + DD-DESIGN-1…5 built | **T-06** |
| §9 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-04+T-05; AC2 → T-04+T-05; AC3 → T-01+T-04+T-05; AC4 → T-01+T-04+T-05;
AC5 → T-04+T-05; AC6 → T-04+T-05; AC7 → T-02+T-05; AC8 → T-05; AC9 → T-01+T-04+T-05;
AC10 → T-01+T-03+T-04+T-05. **M1/M2** → T-05 (view counters); **M3** → T-05 (`DASHBOARD_NONEMPTY_RECEPTION`);
**M4** → T-04 (curated split, expected thin until a DIGEST emitter — honest, not a bug);
**M5** (leak = 0) → T-04+T-05 (the owner-scope tests are the guard); **M6** → T-01 (bounded reads) +
T-05 (request timing). All ten acceptance criteria are covered; **no `L` tasks** (all S/M); every task
has a checkable definition of done and declared files; every task leaves the system green and
releasable (the surface goes live only at the T-05 `config/urls` include + `INSTALLED_APPS` line).
