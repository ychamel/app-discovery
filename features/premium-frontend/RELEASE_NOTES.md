# RELEASE_NOTES.md — premium-frontend

_Stage 5 (Release Engineer) artifact. **Status: RELEASED to local/dev — build verified.**
Live deploy still follows this feature (the parked [DN-PS-DEPLOY](../../CONTROL.md)). One
human-judgment gate is outstanding: the **M7 premium visual sign-off** is the user's to give
(it is an unfalsifiable-by-an-agent AC, the PS-3 pattern)._

---

## What this is

A **presentation-only** feature: it deepens the platform's look into a coherent, token-driven
**design system** and applies it to the three public **wedge surfaces** — a new landing page,
the app page, and discover/browse — plus the shared shell. It adds **no product capability, no
model, no migration, and no new endpoint** beyond the static `/` landing. It exists so the
platform debuts on a polished UI *before* the live staging deploy ([D-10](../../DECISIONS.md):
the developer's app page is their marketing landing page).

Design choices that shaped the release (see [DECISIONS.md](DECISIONS.md), global
[D-13](../../DECISIONS.md)):

- **No build step.** The design system is one hand-authored, WhiteNoise-hashable
  [`core/app.css`](../../apps/core/static/core/app.css) (token-driven `:root`); Tailwind's
  Node/CLI toolchain was rejected — this kept the just-stabilised [D-12](../../DECISIONS.md)
  serving model intact and eliminated the brief's #1 risk (R1).
- **Light progressive enhancement only.** HTMX is **vendored** (`core/vendor/htmx.min.js`, no
  CDN), loaded `defer`, and used only for `hx-boost`. Every surface is fully usable with
  JavaScript disabled.

## What changed

- **New design system** in [`apps/core/static/core/app.css`](../../apps/core/static/core/app.css):
  a token-only `:root` (palette + states, type & spacing scales, elevation, motion, focus ring),
  reset/base, layout primitives, a styled component set (buttons, cards, forms, nav, tables,
  badges, empty-states), and 3 responsive breakpoints.
- **New landing page at `/`** — [`core.views.landing`](../../apps/core/views.py) +
  `core/landing.html`, routed `path("", …, name="home")` **before** the accounts include, with
  **zero DB reads**. Closes the long-standing **PF-CARRY-1 / PS-OQ-1** (the bare domain used to
  404). Emits a `landing_rendered` metric; `POST /` → 405.
- **Restyled shared shell** [`core/base.html`](../../apps/core/templates/core/base.html) —
  additive `{% block body_class %}` + a skip-link; existing blocks verbatim.
- **Restyled, presentation-only**, the app page
  ([`pages/app_page.html`](../../apps/pages/templates/pages/app_page.html)) and discover/browse
  ([`discovery/catalogue.html`](../../apps/discovery/templates/discovery/catalogue.html)) — same
  slots, order, states, and server-rendered content/SEO strings; no view/selector/URL change.

## Who is affected

- **Developers (audience owners)** and **first-time visitors** — the app page now reads as a
  premium product (US-1/US-2), the load-bearing bring-your-own-audience surface.
- **Anyone hitting the bare domain** — `/` is now a real front door, not a 404 (US-3).
- **Browsing users** — discover/browse is responsive with a defined empty state (US-4).
- **The widget's third-party embedders** — **unaffected**: the widget firewall is held
  (templates byte-unchanged; the premium stylesheet does not leak in).

## How to use it

Nothing to enable. The styling is served from the existing static pipeline; the landing page is
live at `/`. On a live deploy, `collectstatic` produces the hashed, gzipped `app.css` and
`htmx.min.js` WhiteNoise serves (verified below).

---

## Verification (independently re-run this session, against live local PG)

| Gate | Result |
|------|--------|
| Full test suite (`manage.py test`) | **980 passed** (M4: ≥975 baseline, +5 from the landing tests) |
| Migration drift (`makemigrations --check`) | **No changes detected** — no schema/migration (C5) |
| `ruff check .` | **All checks passed** — *5 trivial lint defects fixed this session; see Honesty note* |
| `manage.py check` | **0 issues** |
| `collectstatic` (DEBUG=false, manifest) | **156 copied / 450 post-processed**; `app.<hash>.css(.gz)` + `htmx.min.<hash>.js(.gz)` produced → WhiteNoise serving model intact (R1 mitigated) |
| Widget firewall (G2 / M5=0) | **Held** — `apps/widget/` structurally untouched by the feature; templates reference no `app.css`/`base.html` |
| Landing route (AC-3 / M6) | `path("", landing, name="home")` mounted **before** accounts; `/` → 200, 0 DB queries, 405 on POST |
| Vendored HTMX (PF-DESIGN-6) | `core/vendor/htmx.min.js` present (47 KB), no CDN reference |

### Acceptance-criteria status

- **Agent-verifiable — all PASS:** AC-2 (no-JS SEO strings present), AC-3 (`/` 200 real landing),
  AC-6 (suite green + no drift + widget firewall), AC-7 (skip-link, `:focus-visible`, alt text,
  AA-contrast tokens), and the agent-verifiable halves of AC-1/AC-4/AC-5 (renders at the three
  breakpoints; styling sourced from the one shared design system).
- **Human-judgment — OUTSTANDING (the user's, per PS-3):** the visual halves of **AC-1, AC-3,
  AC-4, AC-5** = the **M7 premium sign-off**. Use the checklist in
  [TEST_PLAN.md](TEST_PLAN.md) §4 (three breakpoints × landing / app page / discover, plus
  anon/auth nav states). This is the one gate an agent cannot certify.

### M2 — first-paint baseline (local dev-server, no-regression reference)

Recorded on the load-bearing app page: 0 inline stylesheets, 0 blocking JS (HTMX is `defer`),
TTFB ~12 ms unchanged, DOMContentLoaded ~45 ms → ~48 ms (no meaningful regression). These are
**local dev-server** numbers; the authoritative baseline is re-recorded against the live deploy
(DN-PS-DEPLOY).

---

## Rollback — documented & **rehearsed** this session

- **Nothing irreversible.** The feature adds **no migration** (verified: empty migration diff
  since the platform-staging close), so rollback is a pure code/template/CSS revert.
- **One action:** `git revert 6a01436 b14b238 8be0a51` (the two `premium-frontend` code commits
  + the CSS-consistency commit). The new `name="home"` route has **no external `reverse()`
  dependents** (only its own definition), so removing it breaks nothing.
- **Rehearsed:** `git revert --no-commit` of those three commits was run this session.
  `manage.py check` stayed **clean mid-revert** (no dangling references after the feature code is
  removed). The **only** conflict was in [CONTROL.md](../../CONTROL.md) — a prose tracking file,
  reconciled by hand, never code. Aborted cleanly; HEAD restored.
- **Who can trigger:** any maintainer; no DB step, no coordination required.

## Known limitations / deferred

- **M7 premium visual sign-off is outstanding** (above) — the headline "premium" gate is the
  user's human judgment; surfaced in [CONTROL.md](../../CONTROL.md) as **DN-PF-SIGNOFF**.
- **Authed surfaces not yet restyled** — by design (DN-PF-BRIEF Q1 = wedge surfaces first); they
  keep working and inherit the design system as a cheap follow-on later.
- **HTMX discovery-search fragment** is a deferred extension point (PF-DESIGN-6), not built.
- **Live deploy not performed** — this feature was deliberately sequenced *before* the live
  staging deploy so staging debuts polished. The parked
  [DN-PS-DEPLOY](../../CONTROL.md) runbook is the next bet; the M2 first-paint baseline and the
  agent-run AC1/AC5 checks finalise against that live URL.

## Honesty note (release-time findings)

During independent re-verification I found **5 ruff lint defects** the build handoff had missed
(an unused `observability` import in `test_landing.py`, three trailing-whitespace lines, and an
unsorted import block in `core/views.py`). All are pure hygiene with **no behaviour change**
(the `observability` import was genuinely dead; `views.py` only needed import re-ordering). I
applied `ruff --fix` to restore the standing ruff-clean gate; the suite remains 980 green. These
two files (`apps/core/tests/test_landing.py`, `apps/core/views.py`) are uncommitted working-tree
changes pending the release commit.

Separately, a small **`app.css` consistency pass** (badge colours aligned to the
`--color-success/warning/error` token hues for AA contrast, a hardcoded focus shadow replaced
with `var(--focus-ring)`, and a **fix for a broken `var(--space-1.5)` reference** that is
undefined in `:root` → `var(--space-2)`) was committed by the user concurrently as
`8be0a51 "minor css changes for consistancy"`. It is in-scope (PF-DESIGN-2/5/7: token-only
`:root`, AC-5 consistency, AC-7 a11y) and is included in the verified build above.
