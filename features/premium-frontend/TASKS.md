# TASKS — premium-frontend

_Stage 3 (Planner / Tech Lead) artifact. **Status: READY FOR BUILD.**_
_Upstream: the APPROVED [DESIGN.md](DESIGN.md) (PF-DESIGN-1…7 RATIFIED; global ADR
[D-13](../../DECISIONS.md) — Option A, no build step) + the APPROVED
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) (US-1…6, AC-1…7, M1–M7, C1–C7)._

This is a **presentation-only** feature: no schema, no migration, no new model, no build step,
no new endpoint **except the one landing route**. Every task below is additive and leaves the
suite green (≥975) and the system releasable. The order follows DESIGN §13 (smallest-useful-first):
**CSS substrate → shell → landing → app page → discover → HTMX → TEST_PLAN**, risk-aware (the CSS
substrate everything depends on first; the load-bearing app page before discover; the
drop-if-risky HTMX layer last but one).

All sizes are **S or M** — no `L` remains (planner exit criterion).

---

## Standing guardrails — apply to EVERY task (not re-stated per task)

These are the invariants the design preserves by construction. Each is a hard part of every
task's definition of done, and each has an explicit test in **T-08**:

- **G1 — Suite green, no drift.** `python manage.py test` ≥ **975** green and
  `python manage.py makemigrations --check` reports **no drift** after the task (AC-6 / M4).
- **G2 — Widget firewall held (M5=0).** `apps/widget/templates/**` references **neither**
  `core/app.css` **nor** `core/base.html` and is **byte-unchanged** by this feature (AC-6).
  The widget is excluded from the design system *by construction* — **never** add a `<link>`,
  `{% extends %}`, or shared class to it. This is an **explicit non-change.**
- **G3 — One source of truth (AC-5).** All colour/size/space literals live **only** in the
  `:root` token block of `app.css`; in-scope templates carry **no** inline `style=` / `<style>`
  and **no** per-page stylesheet; every surface links **exactly one** stylesheet (`core/app.css`).
- **G4 — No-JS path is the source of truth (AC-1).** Every interactive control is a real
  `<a href>` / `<form action>` that works with JavaScript disabled. HTMX (T-07) only *intercepts*
  this path; nothing depends on it.
- **G5 — No view / selector / URL / schema contract change** on the restyle tasks (T-03, T-05,
  T-06). Only the landing task (T-04) adds a route + view; only the HTMX task (T-07) adds a
  vendored static asset. Closed-feature inclusion tags (reviews, follow, share, widget-reach) are
  **untouched**.
- **G6 — Existing class names kept working.** Restyling extends/aliases existing classes
  (`.card`, `.button`, `.messages`, `.site-*`); `.button` and the new `.btn` are aliased. **No
  rename** that could break a non-in-scope child template (DESIGN §5.1 evolution rule).

---

## T-01 — Design-system foundation in `app.css`: tokens, reset/base, layout primitives

- **Description.** Deepen [`apps/core/static/core/app.css`](../../apps/core/static/core/app.css)
  sections **1–3** per DESIGN §5.1: (1) the full **token system** in `:root` — the 12-name palette
  with states + elevation, the modular **type scale** (`--font-size-xs…3xl`, weights, line-heights,
  refined system `--font-sans`), the **spacing scale** (`--space-1…8`, with the existing `--space`
  **aliasing** `--space-4`), `--radius`/`--radius-lg`/`--shadow-sm`/`--shadow-md`/`--container-max`,
  and the single `--transition` motion token; (2) **reset/base** — box-sizing, document/body,
  headings driven by the type scale, links, media, and a `:focus-visible` ring; (3) **layout
  primitives** — `.container`, `.stack`, `.cluster`, `.grid`. Keep every existing token and rule
  working (extend, do not rename — G6).
- **Dependencies.** None. (First task; the substrate everything else composes from.)
- **Definition of done.**
  - The token table in DESIGN §5.1 is fully present in `:root`; `--space` resolves to `--space-4`.
  - Every palette foreground/background pair used as text meets **WCAG AA** contrast (AC-7).
  - All motion rules are wrapped in `@media (prefers-reduced-motion: no-preference)`.
  - `collectstatic` succeeds; the file is valid CSS; G1, G3 hold.
- **Estimated size.** M
- **Files/areas touched.** `apps/core/static/core/app.css` (only).

## T-02 — Design-system components, utilities & breakpoints in `app.css`

- **Description.** Add sections **4–6** per DESIGN §5.1 on top of T-01: (4) the refined
  **component set** — `.site-header`/`.site-nav`/`.site-footer`, `.btn` (+ `--primary`/`--secondary`/
  `--ghost`/`--lg`) **aliased to the existing `.button`** (G6), `.card`, `.form-field`, `.table-wrap`,
  `.badge`, `.empty-state`, `.hero`, `.app-grid`, and the `.app-page-*` layout classes; (5) the
  **small** named utility set (`.visually-hidden`, `.skip-link`, spacing helpers — utilities are the
  exception, components the rule, AC-5); (6) the **three** mobile-first breakpoints (~360px base /
  ~600px / ~900px) widening the container/grids and laying out the nav. Components reference **only
  tokens**, never literals (G3).
- **Dependencies.** T-01 (consumes its tokens/scales).
- **Definition of done.**
  - Every component named in DESIGN §3/§5.1 exists and uses only `:root` tokens.
  - `.btn` and `.button` are aliased (both render identically); existing class names still resolve.
  - No token/literal leak outside `:root` (AC-5 grep clean); G1, G3 hold.
- **Estimated size.** M
- **Files/areas touched.** `apps/core/static/core/app.css` (only).

## T-03 — Restyle the shared shell `core/base.html`

- **Description.** Restyle the chrome in
  [`apps/core/templates/core/base.html`](../../apps/core/templates/core/base.html) using the new
  component classes (DESIGN §3 C2, §5.3): premium `.site-header`/`.site-nav`/`.site-footer`, the
  messages block, and a **skip-to-content link** (`.skip-link` → `#main`, with the matching `id` on
  `<main>`) for AC-7. Add the optional **`{% block body_class %}`** (default empty) to `<body>`.
  Preserve `{% block title %}`/`{% block head %}`/`{% block content %}` **verbatim** (additive-only,
  G5/G6). Do **not** add the HTMX script here — that is T-07.
- **Dependencies.** T-02 (uses the component classes).
- **Definition of done.**
  - **Render-every-surface check** (the platform-staging pattern): every surface that extends the
    shell — the 6 per-app bases + landing once it exists — renders without error.
  - The skip-link is present and targets the main landmark; `body_class` block exists and defaults
    to empty; the three original blocks are unchanged.
  - G1, G3, G5, G6 hold.
- **Estimated size.** S
- **Files/areas touched.** `apps/core/templates/core/base.html` (only).

## T-04 — New static landing page: route + view + template (closes PF-CARRY-1 / AC-3)

- **Description.** Add the `/` front door (DESIGN §3 C3, §5.2, §6): a **`core.views.landing`** view
  (GET, AllowAny, **reads no model / no DB**, renders `core/landing.html`, non-GET → default 405,
  emits one `LANDING_RENDERED` metric **via the existing observability/logging facility** —
  [`apps/core/observability.py`](../../apps/core/observability.py); if no lightweight hook fits
  cleanly, log it in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) rather than inventing a metrics system);
  the route `path("", core_views.landing, name="home")` in
  [`config/urls.py`](../../config/urls.py) placed **before** `path("", include("apps.accounts.urls"))`;
  and a new `apps/core/templates/core/landing.html` (a `.hero` with the value-prop headline + sub,
  primary CTAs to `discovery:browse` and a developer "list your app" path, a short "how it works /
  why curated" band, using the shell). No empty/loading/error states (static, unfailable).
- **Dependencies.** T-03 (uses the restyled shell + components).
- **Definition of done.**
  - `GET /` → **200** (asserted **not** 3xx); the value-prop text and the entry-point links
    (`discovery:browse`, `accounts:register`, `accounts:signin`, the developer CTA) are present in
    the **no-JS** server body (AC-3 / M6).
  - A view test asserts the view issues **no DB query** (e.g. `assertNumQueries(0)`).
  - Rollback is the single route line + view + template (design-for-deletion); G1, G3, G5 hold.
- **Estimated size.** S
- **Files/areas touched.** `apps/core/views.py`, `config/urls.py`,
  `apps/core/templates/core/landing.html` (new). (Possibly `apps/core/observability.py` for the metric.)

## T-05 — Restyle the app page `pages/app_page.html` (the load-bearing wedge surface)

- **Description.** **Presentation-only** restyle of
  [`apps/pages/templates/pages/app_page.html`](../../apps/pages/templates/pages/app_page.html)
  (DESIGN §2, §3 C4, §6): wrap the **same six uniform slots, in the same order, with the same
  server-rendered HTML strings** (title, `<link rel=canonical>`, name, description, category) in
  design-system layout/components — a page-header band, a screenshot gallery layout, a prominent
  **Try-it `.btn--primary`**, and `.card` framing. Follow / Share / Try stay **no-JS POST/anchor**;
  the closed-feature inclusion tags (reviews, follow) are **untouched** (G5). No view/selector/URL
  change.
- **Dependencies.** T-02 (components). _(Independent of T-03/T-04; ordered after them per §13.)_
- **Definition of done.**
  - The **no-JS response** still contains **all six slots** and working Try / Share / Follow
    controls (assert the anchors/forms are present in raw HTML) — AC-1.
  - **SEO unchanged (AC-2):** `<title>`, canonical link, and name/description/category strings match
    today's snapshot in the no-JS response.
  - Renders without error at the **360 / 600 / 900** width sections (AC-1).
  - G1, G3, G4, G5, G6 hold.
- **Estimated size.** M
- **Files/areas touched.** `apps/pages/templates/pages/app_page.html` (only).

## T-06 — Restyle discover `discovery/catalogue.html` (grid + states + responsiveness)

- **Description.** **Presentation-only** restyle of
  [`apps/discovery/templates/discovery/catalogue.html`](../../apps/discovery/templates/discovery/catalogue.html)
  (DESIGN §3 C4, §6): the search form + facet sidebar + result list become a responsive **`.app-grid`
  of `.card`s** with a styled sidebar; **all five existing states** keep working — results,
  **zero-results** (a defined `.empty-state`, AC-4), empty-catalogue (`.empty-state`), facet-degraded
  (sidebar message), error (the loud 500, never a fake empty). The search/facets/pagination keep
  their **exact GET semantics** (no-JS, G4). No view/selector/URL change.
- **Dependencies.** T-02 (components). _(Ordered after T-05 per §13.)_
- **Definition of done.**
  - Renders the **results**, **zero-results**, and **empty-catalogue** states; the `.app-grid` /
    `.empty-state` structures are asserted present (AC-4).
  - Renders without error at **360 / 600 / 900**; no horizontal overflow.
  - GET form/facet/pagination semantics unchanged; G1, G3, G4, G5 hold.
- **Estimated size.** M
- **Files/areas touched.** `apps/discovery/templates/discovery/catalogue.html` (only).

## T-07 — Vendored HTMX + `hx-boost` (light, fully degradable enhancement)

- **Description.** Add the single bounded progressive enhancement (DESIGN §3 C5, §5.4, §8.4):
  **vendor** a pinned `htmx.min.js` at `apps/core/static/core/vendor/htmx.min.js` (**no CDN**,
  served + hashed by WhiteNoise), loaded **once** in the shell via
  `<script defer src="{% static 'core/vendor/htmx.min.js' %}"></script>` (defer ⇒ never blocks first
  paint, M2); apply **`hx-boost="true"`** on the in-scope content region so internal links/forms swap
  without a full reload. **No** server view returns HTMX-specific output — the discovery
  live-search/pagination **fragment is a deferred extension point (DESIGN §12), explicitly NOT built**;
  no new endpoint or response shape. Removable in one line (design-for-deletion).
- **Dependencies.** T-03 (shell holds the script tag), T-05, T-06 (the boosted surfaces exist).
- **Definition of done.**
  - The vendored file is present + pinned (version recorded in a comment); the shell loads it
    `defer`; HTMX is **inert** on any surface using no `hx-*` attribute.
  - Every boosted element is a real `<a href>` / `<form action>` — the no-JS tests from T-04/T-05/T-06
    **still pass** (G4 / AC-1); no new endpoint added.
  - G1, G2 (firewall — the widget gets none of this), G3 hold.
- **Estimated size.** S
- **Files/areas touched.** `apps/core/static/core/vendor/htmx.min.js` (new),
  `apps/core/templates/core/base.html`, plus `hx-boost` attributes on the in-scope content regions.

## T-08 — `TEST_PLAN.md` + the M7 premium sign-off package

- **Description.** Author [`TEST_PLAN.md`](TEST_PLAN.md) mapping **every AC-1…AC-7** to its concrete
  check from DESIGN §9 (the table below), including the **static-grep** tests (AC-5 one-source-of-truth;
  AC-6 / **M5=0 firewall**: `apps/widget/templates/**` references neither `app.css` nor `core/base.html`
  and is byte-unchanged) and the enumerated edge cases (empty media, empty catalogue, zero results,
  JS-off, CSS-miss, signed-in vs anonymous nav, 360px overflow). Record the **M2 first-paint baseline**:
  capture the current app-page first-contentful-paint **before T-05** and re-measure after (A3 — M2 is
  a measured pass/fail). Define and hand the user the **M7 sign-off package**: the app page + landing +
  discover viewed at **360 / 600 / 900** widths, signed-in and anonymous, to confirm "premium / not a
  prototype" + cross-surface consistency (the PS-3 human-judgment pattern).
- **Dependencies.** T-01…T-07 (covers the whole feature).
- **Definition of done.**
  - `TEST_PLAN.md` has a row for **every** AC-1…7 with a concrete, runnable check (planner/architect
    exit gate: every AC covered).
  - The firewall (M5=0), no-JS (AC-1), SEO (AC-2), and a11y (AC-7) checks are listed and green.
  - The M2 baseline (before/after) is recorded; the M7 sign-off package is written for the user.
- **Estimated size.** S
- **Files/areas touched.** `features/premium-frontend/TEST_PLAN.md` (new).

---

## AC → task coverage map (every acceptance criterion lands in ≥1 task)

| AC | What it requires | Built in | Verified in |
|----|------------------|----------|-------------|
| **AC-1** App page premium + fast + no-JS | restyle + responsive + degradable PE | T-02, T-05, T-07 | T-05 (no-JS slots/controls, 3 widths), T-08 (M2 baseline + M7) |
| **AC-2** App page SEO unchanged | content/slots/strings preserved | T-05 | T-05 (title/canonical/name/desc/category snapshot), T-08 |
| **AC-3** Real landing at `/` (PF-CARRY-1, M6) | new route + view + template | T-04 | T-04 (200 not 3xx, entry-point links), T-08 (M7) |
| **AC-4** Discover premium + responsive + empty state | grid + 5 states | T-02, T-06 | T-06 (grid/empty-state, 3 widths), T-08 (M7) |
| **AC-5** One design system (M1) | tokens-only literals, shared source | T-01, T-02, T-03, T-05, T-06 | T-08 (static grep: one stylesheet, no inline style, literals only in `:root`) |
| **AC-6** No regression + widget firewall (M4/M5) | additive-only; widget untouched | all (G1) + non-change G2 | T-08 (suite ≥975, no drift, firewall grep M5=0) |
| **AC-7** Accessibility floor | focus-visible, contrast, labels, alt, skip-link, reduced-motion | T-01 (focus/contrast/motion), T-02 (utilities), T-03 (skip-link) | T-08 (a11y checklist test) |

## Design-element coverage (PF-DESIGN-1…7 all land)

- **PF-DESIGN-1/2** (no-build token-driven design system, one served sectioned `app.css`) → **T-01, T-02**
- **PF-DESIGN-3** (restyled shell, additive `{% block body_class %}` + skip-link) → **T-03**
- **PF-DESIGN-4** (static `/` landing via `core.views.landing`) → **T-04**
- **PF-DESIGN-5** (app-page + discover restyle, content/slots/SEO unchanged) → **T-05, T-06**
- **PF-DESIGN-6** (vendored HTMX + `hx-boost`, fully degradable) → **T-07**
- **PF-DESIGN-7** (firewall + no-JS + SEO + a11y preserved by construction) → **G1–G6 + T-08**

## Verification gates (the M4 build gate, in order)

1. No migration drift (`makemigrations --check`) — every task.
2. ≥ **975** tests green — every task.
3. Widget firewall **M5=0** — G2 + T-08.
4. No-JS (AC-1) + SEO (AC-2) pass — T-05, T-08.
5. M2 first-paint baseline recorded, no regression — T-08.
6. The user's **M7** premium sign-off (the human-judgment ACs: AC-1, AC-3, AC-4, AC-5) — T-08 hands
   the package; the user signs off at Stage 4/5.

---

_Build order: **T-01 → T-02 → T-03 → T-04 → T-05 → T-06 → T-07 → T-08.** Each task is one focused
session and leaves the suite green and the system releasable. No `L` tasks remain._
