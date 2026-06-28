# FEATURE_BRIEF — premium-frontend

_Stage 1 (Product Analyst) artifact. **Status: APPROVED** (user, 2026-06-28 — gate **DN-PF-BRIEF**
answered with the three recommended defaults: **Q1 = wedge surfaces first**, **Q2 = light progressive
enhancement only**, **Q3 = real platform landing**). No architecture/schema/UI design here; that is
Stage 2._

**Resolved scope (from DN-PF-BRIEF):**
- **Q1 → wedge surfaces first.** This feature restyles **landing + app page + discover/browse**; authed
  surfaces inherit the design system as a cheap follow-on later (not in this feature).
- **Q2 → light progressive enhancement only.** HTMX is used only for polish that never breaks the no-JS
  path (AC-1 no-JS pass stands).
- **Q3 → real platform landing.** `/` is a genuine front door (value prop + entry points for users and
  developers), resolving **PF-CARRY-1** (US-3 / AC-3); not a redirect.

---

## Upstream (why this feature exists)

- **Decision (user, 2026-06-28** — [CONTROL.md](../../CONTROL.md) *Decisions Made* + Activity Log):
  resolve the [D-11](../../DECISIONS.md) frontend evidence-gate **inside the [D-4](../../DECISIONS.md)
  envelope** — build a **premium server-rendered frontend** (polish, interactivity, premium feel),
  **NOT** a dedicated SPA. The user named the intended direction as **HTMX + Tailwind + Django
  templates**; the *how* (and Tailwind's build step) is a Stage-2 architecture call, not decided here.
- **Why it is load-bearing:** the developer's **app page is their marketing landing page** (the
  bring-your-own-audience thesis, [D-10](../../DECISIONS.md)). A developer brings their own audience to
  that page, so its look *is* the platform's first impression and the developer's growth surface. It
  must also stay **SEO-friendly + fast-first-paint** — an SPA would relocate the cost and regress both.
- **Evidence the gap is *design*, not architecture:** the live UI is barebone — one ~199-line
  [`app.css`](../../apps/core/static/core/app.css) (system fonts, a handful of tokens, no type scale,
  no component library), rendered through the shared [`core/base.html`](../../apps/core/templates/core/base.html)
  shell that `platform-staging` consolidated the 7 per-app `base.html` into. The structure is sound and
  uniform; it simply looks unfinished.
- **Carry-in:** **PS-OQ-1** — the bare domain `/` has **no route → 404** (confirmed: [config/urls.py](../../config/urls.py)
  mounts `accounts.urls` at `""` but accounts publishes no `/` view). There is no home/landing surface.
  Resolved here as **PF-CARRY-1**, with a real landing surface (not a throwaway redirect).

---

## Glossary (no undefined terms downstream)

- **Premium feel** — a *measurable* visual-quality bar, defined for this feature as: (a) a coherent
  **design system** is applied consistently across the in-scope surfaces, and (b) the user signs off the
  result as "looks like a polished product, not a prototype" (human-judgment AC, mirroring the
  `platform-staging` PS-3 sign-off pattern). It is **not** "subjectively pretty with no checklist."
- **Design system** — the shared, named set of visual primitives every in-scope surface draws from: a
  type scale, a spacing scale, a colour palette with states, and a small set of styled components
  (buttons, cards, forms, nav, tables, badges/empty-states). One source of truth, no per-page ad-hoc styling.
- **In-scope surface** — a rendered page selected (per **DN-PF-BRIEF Q1**) to receive the premium
  treatment in *this* feature. Surfaces not selected keep working unchanged and inherit the design
  system incrementally later.
- **First paint** — first contentful paint: how quickly meaningful content appears on a cold load. The
  server-rendered posture ([D-4](../../DECISIONS.md)) makes this fast; the bar is "no regression."
- **Wedge surfaces** — the public, anonymous-reachable pages that carry the bring-your-own-audience
  funnel: the **landing page** (`/`, new), the **app page** ([`pages/app_page.html`](../../apps/pages/templates/pages/app_page.html)),
  and the **discover/browse** surface ([`discovery/catalogue.html`](../../apps/discovery/templates/discovery/catalogue.html)).

---

## Problem statement

**Who:** developers who bring their own audience to their app page (the [D-10](../../DECISIONS.md) wedge),
and the visitors/prospective users who land on it — plus anyone who hits the bare domain.

**What problem:** the platform's structure and behaviour are complete and uniform, but the surface looks
like an unstyled prototype. The app page — which is the developer's *marketing landing page* and the
platform's first impression — does not read as a premium product, which directly undercuts the
bring-your-own-audience thesis (a developer is reluctant to send their audience to a page that looks
unfinished). Separately, the bare domain `/` 404s, so there is no coherent front door at all.

**Why now:** the wedge is code-complete and `platform-staging` is build-verified, but the user
deliberately **re-sequenced the live deploy to land *after* this feature** so staging debuts on a
polished UI ([DN-PS-DEPLOY](../../CONTROL.md) parked). The look is the last gap between "built" and
"presentable to a real developer."

## Goal

**One sentence:** every in-scope surface — above all the app page and a new landing page — reads as a
polished, premium product on phone and desktop, while staying fast-first-paint, SEO-friendly, and
accessible, with no loss of existing behaviour.

---

## User stories (roles → capability → benefit)

- **US-1 — Developer (audience owner).** As a developer, I want my **app page** to look like a premium
  product, so that I can confidently send my own audience there as my marketing landing page.
- **US-2 — Visitor / prospective user.** As a first-time visitor arriving at an app page from a
  developer's link, I want the page to look trustworthy and load instantly, so that I take the app
  seriously and try it.
- **US-3 — Anyone hitting the bare domain.** As someone who opens the root URL, I want a real **landing
  page** that explains the platform and routes me onward, so that I am not met with a 404 (**PF-CARRY-1**).
- **US-4 — User browsing.** As a user on the **discover/browse** surface, I want a clean, consistent,
  mobile-friendly layout, so that scanning curated apps feels effortless and credible.
- **US-5 — Returning authenticated user/developer.** As a signed-in user moving between auth, profile,
  dashboard, and submission surfaces, I want a **consistent** look and navigation, so that the product
  feels like one coherent whole rather than stitched-together pages.
- **US-6 — Maintainer (us, later).** As the team, I want the premium look to come from **one design
  system**, so that future surfaces inherit it cheaply and nothing drifts into per-page styling.

---

## Acceptance criteria (Given / When / Then)

Each is tagged **[agent-verifiable]** (checkable mechanically) or **[human-judgment]** (the user signs
off, per the PS-3 pattern). Premium *feel* is anchored to the design system + a sign-off so it is not
unfalsifiable.

**AC-1 (US-1, US-2) — App page is premium & fast.**
- **Given** an accepted app's page, **When** it is loaded on phone and desktop, **Then** it renders the
  design system (type scale, spacing, styled components) with no broken/overflowing layout at the
  ~360px, ~600px, and ~900px+ widths **[agent-verifiable: renders at each width]** **and** the user
  signs it off as premium **[human-judgment]**.
- **Given** the app page, **When** it loads cold, **Then** first-contentful-paint shows no regression
  vs. the current server-rendered baseline, and the page remains usable with **JavaScript disabled**
  (all six slots present, Try-it / Share / Follow still function) **[agent-verifiable]**.

**AC-2 (US-2) — App page stays SEO-friendly.**
- **Given** the app page, **When** its HTML is fetched (no JS execution), **Then** the title, the
  canonical link, and the app's name/description/category content are present in the server response,
  unchanged from today's SEO posture **[agent-verifiable]**.

**AC-3 (US-3, PF-CARRY-1) — Real landing page at `/`.**
- **Given** the bare domain `/`, **When** it is requested, **Then** it returns **200** with a real
  landing surface (platform value proposition + clear entry points for both users and developers), not a
  404 and not a bare redirect **[agent-verifiable]**, and the user signs off its look **[human-judgment]**.

**AC-4 (US-4) — Discover/browse is premium & responsive.**
- **Given** the discover/browse surface with results, **When** loaded on phone and desktop, **Then** it
  renders the design system, lists apps cleanly, and has a defined empty state when there are no results
  **[agent-verifiable: renders + empty state]** **and** reads as polished **[human-judgment]**.

**AC-5 (US-5, US-6) — Consistency from one design system.**
- **Given** any in-scope surface, **When** it renders, **Then** its colours, type, spacing, buttons,
  forms, and nav come from the shared design system (no per-page ad-hoc styling), so the in-scope
  surfaces are visually consistent with one another **[agent-verifiable: shared source]** **and** the
  user confirms cross-surface consistency **[human-judgment]**.

**AC-6 (US-1, US-6) — No behaviour or firewall regression.**
- **Given** the full test suite (currently **975** green), **When** the feature is built, **Then** all
  existing tests still pass and there is no schema/migration drift **[agent-verifiable]**.
- **Given** the embeddable widget ([`apps/widget`](../../apps/widget/)), **When** the feature ships,
  **Then** its templates remain **isolated and unrestyled by the platform stylesheet** (the AC3.3 /
  D-12 third-party-iframe firewall is preserved — premium styling must not leak into the widget)
  **[agent-verifiable: widget templates unchanged by this feature]**.

**AC-7 (US-2, US-4) — Accessibility floor.**
- **Given** any in-scope surface, **When** evaluated, **Then** it meets a baseline accessibility bar
  (focus-visible states, sufficient colour contrast, labelled controls, image alt text preserved), no
  worse than today **[agent-verifiable: checklist]**.

---

## Success metrics (measurable signals)

- **M1 — Surface coverage:** 100% of the surfaces selected in **DN-PF-BRIEF Q1** render the design
  system on phone + desktop with no broken layout at the three breakpoints.
- **M2 — First paint:** app-page first-contentful-paint shows **no regression** vs. the current baseline
  (target: within +0 ms of today's server-rendered render; record the baseline at Stage 4).
- **M3 — SEO integrity:** title + canonical + app content present in the **no-JS** server response on the
  app page (binary pass/fail).
- **M4 — Zero behaviour regression:** existing test count stays green (≥975) with no migration drift.
- **M5 — Firewall held:** widget templates carry **zero** premium-stylesheet bytes (binary; mirrors the
  embeddable-widget M5=0 firewall guardrail).
- **M6 — Landing front door:** `/` returns 200 (binary; closes PF-CARRY-1).
- **M7 — Premium sign-off:** the user signs off app page + landing + discover as "premium / not a
  prototype" (human-judgment, per PS-3).

---

## In scope

- A **design system** (tokens + type/spacing scales + a small styled-component set) as the single source
  of the premium look, applied through the existing shared shell.
- Premium restyle of the surfaces selected in **DN-PF-BRIEF Q1** (default recommendation: the three
  **wedge surfaces** — landing, app page, discover/browse — first).
- A **real landing page** at `/` (US-3 / PF-CARRY-1).
- **HTMX interactivity** only to the extent agreed in **DN-PF-BRIEF Q2** (default: light progressive
  enhancement that never breaks the no-JS path).
- Responsive behaviour across the three breakpoints and the accessibility floor (AC-7).
- Preserving every existing behaviour, the no-JS path, SEO posture, and the widget firewall.

## Out of scope

- Any **dedicated SPA / client-side-rendered** rewrite (explicitly excluded by the upstream decision;
  would re-open [D-11](../../DECISIONS.md)/[D-4](../../DECISIONS.md)).
- New **product capabilities** — no new features, models, or endpoints beyond the landing page. This is a
  presentation feature.
- Restyling the **embeddable widget** (firewalled — AC-6) and the **Django admin**.
- The **live staging deploy** ([DN-PS-DEPLOY](../../CONTROL.md), parked) — it follows this feature.
- The Stage-2 **architecture choices** themselves: the Tailwind-vs-alternatives call and the build-step /
  [D-12](../../DECISIONS.md)-revision ADR (named here as a constraint, decided at Stage 2).
- Any change that lets money buy visual prominence or ranking position (see Vision alignment).

---

## Constraints & assumptions

**Constraints**
- **C1 — Server-rendered envelope ([D-4](../../DECISIONS.md)).** Output stays Django-template,
  server-rendered HTML; no SPA. *(verified — repo is Django templates throughout.)*
- **C2 — SEO + fast-first-paint are non-negotiable** on the wedge surfaces (the app page is a marketing
  landing page). *(verified rationale — D-10 thesis.)*
- **C3 — Build step revises [D-12](../../DECISIONS.md).** The upstream-named Tailwind direction
  introduces a build step, a deliberate revision of D-12's build-free stylesheet posture. The *decision*
  is Stage 2 (likely a new global ADR); this brief only flags that it must be resolved there.
  *(unverified — Stage-2 call.)*
- **C4 — Widget firewall preserved.** The embeddable-widget templates must remain isolated from the
  platform stylesheet (AC3.3 / D-12). *(verified — widget is self-contained today.)*
- **C5 — No schema change expected.** A presentation feature; any DB change would be a scope smell to
  escalate. *(verified — no model work implied.)*
- **C6 — Accessibility floor** (focus-visible, contrast, labels, alt text) no worse than today.
  *(verified — current `app.css` already sets focus outlines and forms carry labels.)*
- **C7 — Reuse the consolidated shell.** Build on the existing [`core/base.html`](../../apps/core/templates/core/base.html)
  + `app.css` from `platform-staging`; do not re-fork per-app base templates. *(verified — 7 bases
  already consolidated to one shell.)*

**Assumptions**
- **A1 — The 975-test baseline is green and the build is unchanged since `platform-staging` closed.**
  *(verified by last session's re-verification; Stage 4 re-confirms.)*
- **A2 — "Premium" can be judged by the user** at Stage 4/5 via sign-off (PS-3 pattern), so the
  human-judgment ACs are answerable. *(verified — same owner signed off platform-staging.)*
- **A3 — The current first-paint baseline is acceptable as the no-regression reference;** it will be
  recorded at Stage 4. *(unverified until measured.)*

---

## Risks (top 5 — likelihood × impact × mitigation)

| # | Risk | L | I | Mitigation |
|---|------|---|---|------------|
| R1 | Tailwind's build step adds deploy/dev complexity that destabilises the parked staging deploy. | M | H | Treat the build-step as a Stage-2 ADR (C3); require a build that produces a static, hash-able stylesheet WhiteNoise can serve, keeping the [D-12](../../DECISIONS.md) serving model intact. |
| R2 | "Premium" stays subjective → the feature can't be called done. | M | H | Anchor to a concrete design system + the M7 sign-off + per-breakpoint render checks (AC-1/AC-5); no open-ended "make it nice." |
| R3 | Restyle accidentally breaks the no-JS path or SEO on the app page (the load-bearing surface). | M | H | AC-1/AC-2 make no-JS + no-JS-SEO explicit pass/fails; keep progressive-enhancement-only (DN-PF-BRIEF Q2). |
| R4 | Premium styles leak into the embeddable widget, breaking the third-party firewall. | L | H | AC-6 / M5=0 firewall guardrail; widget templates excluded from the design system, asserted mechanically. |
| R5 | Scope creep — "premium" silently expands to every surface + heavy interactivity, blowing the estimate. | M | M | DN-PF-BRIEF Q1/Q2 fix the surface set + interactivity appetite up front; the design system makes later surfaces cheap without re-scoping now. |

---

## Vision alignment

Serves the **§1 vision** ("a fair launchpad … Marketing becomes something the platform does *for* you")
and the [D-10](../../DECISIONS.md) bring-your-own-audience wedge: a premium app page is the developer's
marketing landing surface, directly supporting the **§8 one-line test** (a great app by an unknown solo
dev finds its audience here). It touches **presentation only** — it adds no path for money to buy visual
prominence or ranking position, so the *money-buys-tools-never-position* principle is untouched.

---

## Decisions needed from you (gate DN-PF-BRIEF) — RESOLVED 2026-06-28

All three answered by the user with the recommended defaults (see *Resolved scope* at the top):

1. **Q1 — Surface prioritisation → wedge surfaces first** (landing + app page + discover/browse).
2. **Q2 — HTMX interactivity appetite → light progressive enhancement only.**
3. **Q3 — Landing page (`/`) intent → real platform landing** (resolves PF-CARRY-1).

Open for Stage 2 (not a Stage-1 call): **PF-2** — the Tailwind build step revises [D-12](../../DECISIONS.md)'s
build-free posture (brief constraint **C3**), to be decided by the Software Architect as a likely new
global ADR.
