# apps/dashboard — the developer-dashboard

A **read-only** view of an owned, accepted app's *reception* for the developer who owns it
(Phase-3 core developer value; H2). It is a pure read **orchestrator** over the existing
read surfaces — accounts (**D-3**), catalog (**D-6**), signals (**D-7**), ratings (**D-8**) —
and **owns no model, migration, table, or index**. It mirrors the model-less consumer house
pattern of [`apps/pages/`](../pages/) and [`apps/discovery/`](../discovery/).

## What it shows

- **Screen A — my apps** (`GET /dashboard/`, name `dashboard:my-apps`): the developer's
  *accepted* apps, each with a bounded reception summary (total reach, curated reach,
  click-throughs) over a selected window. An owner with no accepted apps gets a 200
  own-nothing state.
- **Screen B — app reception** (`GET /dashboard/apps/<uuid>/`, name `dashboard:app`):
  one app's **reach** (combined total + per-source `Surface` breakdown, **curated `DIGEST`
  first/highlighted**, + an impressions-over-time trend with a distinguished curated line),
  **engagement funnel** (off-platform proxy shown separately), and incoming **reviews**
  (count + raw distribution + recent list, no average).

## Design guarantees

- **Read-only / no self-inflation (AC8).** Both views are `GET`-only, `login_required` +
  `require_role(developer)`, owner-scoped inside `reception`. The app **never imports
  `signals.capture`** — viewing a dashboard emits no D-7 impression. This is enforced
  structurally by [`tests/test_imports.py`](tests/test_imports.py). (It *does* read
  `signals.selectors` — that is its job.)
- **Owner-scope = 404 indistinguishable (R3).** A non-owner's / non-accepted app id is a 404,
  identical to a genuine not-found — no enumeration.
- **Failure split (§7).** The **core reception read** (signals) **fails loud** — a DB error
  increments `DASHBOARD_RECEPTION_DEGRADED` (the one actionable alert) and 500s, never a
  fake-empty page that would lie about H2 / corrupt M1/M3/M4. The **reviews slot fails soft**
  (`DASHBOARD_REVIEWS_DEGRADED`, status stays 200).
- **Curated is one source of truth.** "Which surface is curated" is *not* defined here — it is
  reused from `ratings.gate.CURATED_SURFACES` (the D-8 definition). Signals stays neutral.

## Modules

| File | Responsibility |
|---|---|
| `views.py` | The two thin GET views: gate, parse `?window=`, call `reception`, render. No ORM, no business logic. |
| `reception.py` | The one composition layer: calls the read surfaces, orders surfaces curated-first, densifies the trend, projects to frozen view-model DTOs. |
| `windows.py` | The fixed 8 reporting windows + per-window bucket granularity (a code-fixed table) + `resolve_window` (fail-safe). |
| `charts.py` | Pure inline-SVG sparkline geometry (total + curated line). stdlib only, no app imports, no JS. |

The two additive signals reads it depends on — `signals.selectors.impression_breakdown` /
`impression_breakdown_for_apps` / `impression_trend` (+ `TrendGranularity`) — live in the
closed signals app per D-7, not here.

## Activation & rollback

Activation = **one `config/urls` `dashboard/` include + the `"apps.dashboard"`
`INSTALLED_APPS` line**. Rollback = remove both — **zero data migration** (the app owns no
schema). The two additive `signals.selectors` reads ship alongside but are inert when unused
and harmless to leave; removing them is *not* part of an emergency rollback.
