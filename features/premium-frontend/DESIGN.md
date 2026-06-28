# DESIGN — premium-frontend

_Stage 2 (Software Architect) artifact. **Status: APPROVED** (DN-PF-DESIGN resolved 2026-06-28 — user
chose **Option A / no build step** "for now," Option B kept as an outcome-gated reversible fallback;
PF-DESIGN-1…7 RATIFIED; recorded as global ADR **[D-13](../../DECISIONS.md)**)._
_Upstream: the APPROVED [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (US-1…6, AC-1…7, M1–M7, C1–C7) +
[D-4](../../DECISIONS.md) (server-rendered Django templates) + [D-10](../../DECISIONS.md)
(app-page = the developer's marketing landing page) + [D-12](../../DECISIONS.md) (the
WhiteNoise serving model + the consolidated `core/base.html` shell this builds on)._

This feature ships **no new product capability** — its architecture is **a CSS design system,
the restyle of three already-rendered surfaces, one new static landing page, and a bounded,
fully-degradable HTMX enhancement.** Every change is presentation-layer and additive; there is
no schema, no migration, no new model, and (in the recommended option) no build step.

---

## 0. The one pivotal decision (PF-2 / C3) — read this first

The brief named the user's intended direction as "HTMX + Tailwind + Django templates" and
**explicitly deferred the Tailwind-vs-alternatives + build-step call to this stage** (brief C3,
Out-of-scope item, OQ **PF-2**). After surveying the code I am **recommending against adopting
Tailwind's toolchain**, and instead **deepening the existing hand-authored stylesheet into a real
design system with no build step.** This both meets the brief and *eliminates* its #1 risk (R1).

Because that diverges from a technology the user named **and** it is a global-ADR-level call (it
settles D-12's build-free posture for every future surface), I do **not** self-ratify it. It is
raised as gate **DN-PF-DESIGN** and recorded as proposed global ADR **D-13**. The full rationale,
the genuine alternative (Tailwind **standalone CLI**, fully specified so it is buildable if you
overrule me), and what each sacrifices are in §10 + §11. **Everything below §1 assumes the
recommended no-build option (A); the Option-B contingency is specified in §11 so the design is
complete either way.**

---

## 1. Reasoning trace (14-step protocol — condensed)

1. **SCOPE.** Make the three public wedge surfaces (app page, discover/browse) + a new `/`
   landing read as a polished, premium product on phone/desktop, from one design system, with
   **zero** regression to behaviour, the no-JS path, SEO, first-paint, or the widget firewall.
   OUT: SPA, new product capabilities, authed-surface content restyle, the widget, admin, the
   live deploy. Lifespan = **platform** (the design system is the durable styling substrate every
   later surface inherits) → effort matches.
2. **REQUIREMENTS.** Functional: AC-1…AC-7. Non-functional: first-paint **no regression** (M2);
   one served, hashable stylesheet (C3/D-12); accessibility floor no worse than today (AC-7);
   widget bytes unchanged (M5=0). Hard constraints C1–C7. Assumptions A1 (975 green baseline,
   verified last session), A2 (user signs off premium), A3 (current first-paint = the reference,
   **measured at Stage 4**). The only **unverified** input is A3 → handled by recording the
   baseline before/after in Stage 4 (M2 is a measured pass/fail, not a guess).
3. **CONTEXT.** Reuse-first: the consolidated [`core/base.html`](../../apps/core/templates/core/base.html)
   shell + single [`core/app.css`](../../apps/core/static/core/app.css) (D-12, ~199 lines: tokens,
   nav, forms, tables, cards, two breakpoints) already **is** a small hand-authored design system —
   it is simply shallow. The six per-app `base.html` are thin `{% extends "core/base.html" %}`
   stubs (C7). The widget is isolated by absence (extends nothing, links nothing — verified). The
   serving model: WhiteNoise `CompressedManifestStaticFilesStorage`, `collectstatic` at build,
   pure-Python `buildCommand` in [render.yaml](../../render.yaml). `/` 404s (PS-OQ-1 / PF-CARRY-1).
4. **MODULES** → §3. Five components: the **design-system stylesheet** (one source of truth), the
   **shell** (shared chrome), the **landing surface** (new), the **two restyled wedge templates**,
   and the **HTMX enhancement layer** (optional, removable). Low coupling: each is independently
   replaceable; the stylesheet is the only shared dependency and is consumed by `<link>`, not import.
5. **INTERFACES** → §5. Contracts: the **CSS class/token API** (the named, documented surface every
   template draws from), the **landing view/route**, the **`{% block %}` contract** of the shell
   (unchanged, additive), and the **HTMX attribute contract** (degrades to plain HTML).
6. **DATA & STATE** → §4. **None.** No model, no migration, no persisted state. The landing view is
   stateless. (C5 honoured; any schema change would be a scope smell to escalate.)
7. **FAILURE** → §8. The only runtime code is the landing view (trivially safe — static render) and
   the HTMX layer (degrades to full-page nav on any JS/network failure). CSS cannot "fail" at
   runtime beyond a cache miss (WhiteNoise-hashed, immutable). No new trust boundary, no new input.
8. **CHANGE** → §10. Most-likely-to-change = the visual tokens (colour/type/spacing) → all live in
   **one `:root` token block** so a re-theme is a token edit, not a component rewrite. Irreversible-ish
   = the build-step decision (touches the global deploy contract) → §0/§10, extra rigor, ratified.
9. **TRADE-OFFS** → §11. ≥2 genuinely different options: **A) no-build hand-authored CSS**
   (recommended), **B) Tailwind via the standalone CLI** (build step, no Node), plus the rejected
   Tailwind-Node and Tailwind-CDN. Compared against the Step-2 requirements, not taste.
10. **SECURITY** → §8.4. Threat surface is near-zero (presentation only, no new input, no PII, no
    auth change). The one note: no third-party CDN/web-font (supply-chain + privacy + offline) —
    HTMX is **vendored** and self-hosted; the firewall (AC-6) is preserved structurally.
11. **OPERATIONS** → §7/§8. Rollback = revert the CSS + templates + the one landing route (no data).
    Observability: existing request logs; the landing view emits one metric; no new alert needed.
12. **TESTS** → §9. Every AC maps to a concrete check; each component is testable in isolation
    (the landing view as a view test; the no-JS/SEO guarantees as response-content tests; the
    firewall + "one source of truth" as static-grep assertions; premium feel as the M7 sign-off).
13. **SELF-CRITIQUE** → §12. Attacked the design; ran a simplification pass (dropped a web font, an
    optional landing DB strip, and a discovery-fragment view change — all named as deferred
    extension points, none built); re-checked the assumption ledger (A3 the only open item, handled).
14. **DELIVER** → §3–§13 + the proposed ADR **D-13** + the smallest-useful-first increment plan (§13).

---

## 2. Current-state summary (what exists, diffable)

| Area | Today | This feature changes it to |
|------|-------|----------------------------|
| Stylesheet | One ~199-line `core/app.css`: a handful of flat tokens, system font, no type/spacing scale, a thin component set, 2 breakpoints. | A **full design system** in the same one file: a complete token system (palette + states + elevation + a modular type scale + a spacing scale + motion), a refined component set, 3 breakpoints. Same `<link>`, same WhiteNoise hashing. |
| Shell `core/base.html` | Functional header/nav/footer, messages, viewport, the `{% block title/head/content %}` contract. | **Restyled chrome** (premium header, refined nav, footer, a skip-to-content link for AC-7) using the new component classes. The `{% block %}` contract is **unchanged + additive** (a new optional `{% block body_class %}`). Vendored HTMX loaded `defer`. |
| App page `pages/app_page.html` | Six uniform slots in semantic HTML, almost no styling. | Same slots, same order, same content (AC-2/AC-3 uniformity intact) — wrapped in design-system layout/components. Follow/Share/Try **stay no-JS POST/anchor** (closed-feature inclusion tags untouched). |
| Discover `discovery/catalogue.html` | Search form, facet sidebar, result list, 5 states — minimal styling. | Same markup/states, restyled into a responsive card grid + sidebar; defined empty state (AC-4). |
| Landing `/` | **404** (no route; `accounts.urls` mounted at `""` publishes no bare view). | **200** — a new static `core/landing.html` via `core.views.landing`, routed at `path("", …)` before the accounts include (AC-3 / PF-CARRY-1). |
| Widget `apps/widget/templates/` | Self-contained inline `<style>`, links nothing, extends nothing. | **Byte-unchanged.** Excluded from the design system by construction (AC-6 / M5=0). |
| Serving / deploy | WhiteNoise + `collectstatic` at build; pure-Python `buildCommand`. | **Unchanged (Option A).** No build step added; D-12 serving model intact. |
| Schema / migrations | — | **None.** (C5.) |

---

## 3. Proposed architecture (components + responsibilities)

```
                         core/app.css  (THE DESIGN SYSTEM — one source of truth, §5.1)
                           ▲        ▲         ▲              ▲
           <link> (hashed) │        │         │              │  (NOT linked — firewall, AC-6)
        ┌──────────────────┴──┐   ┌─┴──────┐ ┌┴────────────┐ │
        │ core/base.html      │   │landing │ │app_page +   │ │   apps/widget/templates/*
        │ (shell: chrome,     │   │.html   │ │catalogue    │ │   (self-contained inline
        │  HTMX defer, AC-7)  │   │(new,   │ │.html        │ │    <style>; untouched)
        └─────────▲───────────┘   │ AC-3)  │ │(restyled)   │ │
                  │ extends        └───▲────┘ └─────▲───────┘ │
        ┌─────────┴──────────┐         │            │         │
        │ 6 per-app base.html│      core.views   pages/      apps/widget/views
        │ (thin stubs, C7)   │      .landing     discovery
        └────────────────────┘                   views (unchanged)
```

**C1 — Design-system stylesheet** (`apps/core/static/core/app.css`, extended in place).
*Owns:* every visual primitive — the token system, the type/spacing scales, and the styled
component classes. *Exposes:* a **named, documented CSS class + token API** (§5.1) that every
in-scope template composes from. *Hides:* all colour/size/spacing literals (they live only in
`:root`). **One source of truth for the look** (AC-5/M1). Replaceable: swapping it re-themes the
whole platform with no template edit. Served exactly as today (one hashed `<link>`).

**C2 — The shared shell** (`apps/core/templates/core/base.html`, restyled).
*Owns:* the chrome shared by all surfaces (header/nav/footer/messages/skip-link) and the
document head (viewport, the one stylesheet link, the deferred HTMX `<script>`). *Exposes:* the
**unchanged** `{% block title/head/content %}` contract **plus** a new optional
`{% block body_class %}` (default empty) so a surface can opt into a theme variant without forking
the shell. *Hides:* nav auth-state logic (already present). Restyling the shell lifts **all**
surfaces' chrome consistently (US-5) — that is consistency, not a behaviour change to the
non-in-scope surfaces (their *content* is untouched).

**C3 — The landing surface** (new: `core.views.landing` + `core/landing.html`).
*Owns:* the `/` front door. *Exposes:* `GET /` → **200**, AllowAny, a static value-prop page with
explicit entry points (Discover, Register, Sign in, a developer "list your app" CTA). *Hides:*
nothing — it reads **no model and no DB** (fastest possible first paint; it cannot fail; §8.2). A
"recently added apps" strip is a **named deferred extension point** (§12), not built (avoids
coupling the front door to the catalogue).

**C4 — The two restyled wedge templates** (`pages/app_page.html`, `discovery/catalogue.html`).
*Own:* their page structure. *Change:* presentation only — design-system classes + responsive
layout wrappers around the **same content, same slots, same order, same server-rendered HTML
strings** for title/canonical/name/description/category (AC-2). No view, selector, or URL change.

**C5 — The HTMX enhancement layer** (vendored `core/vendor/htmx.min.js`, `hx-boost`).
*Owns:* the single, bounded progressive enhancement (snappy in-page navigation via `hx-boost`).
*Exposes:* nothing server-side — it is attribute-driven HTML that **degrades to ordinary
navigation with JS off** (AC-1). *Hides:* nothing. Removable in one line (design-for-deletion).
Touches **no** closed-feature view. The discovery live-search/pagination **fragment** is a
documented deferred extension point (§12), explicitly **not** built this feature.

**Coupling check:** the only shared dependency is C1 (consumed by `<link>`, the loosest possible
coupling). C2–C5 are each independently testable and independently removable. Dependencies point
toward the most stable thing (the token/class API). High cohesion: each component has one job.

---

## 4. Data design

**None.** No new or changed model, table, field, index, or migration. No persisted or session
state is added. `makemigrations --check` must report **no drift** (AC-6 / M4). This honours C5;
any DB change here would be a scope violation to escalate via `OPEN_QUESTIONS.md`.

---

## 5. Interface contracts (no TBD)

### 5.1 The design-system CSS API (the contract every template depends on)

One source of truth: `apps/core/static/core/app.css`, organised into **clearly-labelled layered
sections in one served file** (no build → partitioning is by section, not by file; a single file
is also one request = best first-paint and trivially WhiteNoise-hashable). Section order:

```
1. TOKENS        :root custom properties — the ONLY place colour/size/space literals live
2. RESET/BASE    box-sizing, document/body, headings via the type scale, links, media, focus
3. LAYOUT        .container, .stack, .cluster, .grid (the reusable layout primitives)
4. COMPONENTS    .site-header/.site-nav/.site-footer, .btn (+ --primary/--secondary/--ghost/--lg),
                 .card, .form-field, .table-wrap, .badge, .empty-state, .hero, .app-grid, .app-page-*
5. UTILITIES     a SMALL, named set (.visually-hidden, .skip-link, spacing helpers) — not a utility
                 framework; utilities are the exception, components are the rule (AC-5)
6. BREAKPOINTS   mobile-first; ~600px and ~900px widen the container/grid and lay out the nav
```

**Token contract (the cheapest place to change — §10).** All in `:root`:

| Group | Tokens (names are the contract) |
|-------|---------------------------------|
| Palette | `--color-bg`, `--color-surface`, `--color-surface-2`, `--color-text`, `--color-muted`, `--color-border`, `--color-accent`, `--color-accent-hover`, `--color-accent-contrast`, `--color-success`, `--color-warning`, `--color-error` — all foreground/background pairs meet **WCAG AA** contrast (AC-7) |
| Type scale | `--font-size-xs/sm/base/lg/xl/2xl/3xl` (a modular scale), `--font-weight-normal/medium/bold`, `--line-tight/base`, `--font-sans` (refined **system** stack — no web-font fetch, so first-paint stays instant, M2) |
| Spacing | `--space-1 … --space-8` (a `0.25rem`-based scale; the existing `--space` aliases `--space-4`) |
| Form | `--radius`, `--radius-lg`, `--shadow-sm`, `--shadow-md` (elevation), `--container-max` |
| Motion | `--transition` (a single shared duration/easing; **all** transition rules are wrapped in `@media (prefers-reduced-motion: no-preference)`) |

**Evolution rule:** components reference **only** tokens, never literals; new components are added
as new sections; renaming a token is a single-file find/replace. Existing class names already in
templates (`.card`, `.button`, `.messages`, `.site-*`, `.app-list`, `.discovery-layout`) are
**kept working** (extended, not renamed) so the restyle is non-breaking; `.button` and a new
`.btn` are aliased.

### 5.2 The landing route/view contract

- **Route:** `path("", core_views.landing, name="home")` in [`config/urls.py`](../../config/urls.py),
  placed **before** `path("", include("apps.accounts.urls"))`. Django matches the exact empty path
  to `landing`; every existing accounts/other route is unaffected (accounts publishes no bare `""`).
- **View:** `core.views.landing(request) -> HttpResponse` — GET, **AllowAny**, renders
  `core/landing.html`. No DB read, no auth requirement, no query params consumed. Non-GET → Django's
  default 405 (consistent with the other simple GET views). Emits one `LANDING_RENDERED` metric.
- **Invariant:** returns **200** for an anonymous request with JS disabled, carrying the value prop
  + the entry-point links in the server HTML (AC-3 / M6). It is **not** a redirect (Q3).
- **Rollback:** delete the route line + the view + the template → `/` returns to 404, nothing else
  moves. (Design-for-deletion.)

### 5.3 The shell `{% block %}` contract (unchanged + additive)

`{% block title %}` (default "App Discovery"), `{% block head %}`, `{% block content %}` — **all
preserved verbatim** so every existing child template keeps working. **Added:** an optional
`{% block body_class %}` on `<body>` (default empty) for opt-in per-surface theming. Additive-only:
no existing block is removed or repurposed (consumers cannot break).

### 5.4 The HTMX attribute contract (progressive enhancement, degradable)

- The library is **vendored** at `apps/core/static/core/vendor/htmx.min.js` (a pinned version,
  served + hashed by WhiteNoise; **no CDN**) and loaded once in the shell via
  `<script defer src="{% static 'core/vendor/htmx.min.js' %}"></script>`. `defer` ⇒ never blocks
  first paint (M2). Inert on any surface that uses no `hx-*` attribute (so non-in-scope/authed
  surfaces are unaffected in behaviour).
- **Use:** `hx-boost="true"` on the in-scope content region so internal links/forms swap without a
  full reload. **Contract:** every boosted element is a real `<a href>` / `<form action>` that
  works identically when HTMX is absent — **the no-JS path is the source of truth; HTMX only
  intercepts it** (AC-1). No server view returns HTMX-specific output in this feature (the
  fragment path is deferred, §12), so there is **no new endpoint or response shape** (brief
  out-of-scope honoured).

---

## 6. UX flow (screens + states)

**Landing `/` (new).** Single state: a hero (headline value prop + sub), primary CTAs
("Discover apps" → `discovery:browse`, "List your app" → register/dashboard), a short "how it
works / why curated" band, and a footer. No empty/loading/error states (static, no fetch). Renders
identically signed-in or out except the nav chrome (from the shell).

**App page (restyled).** States are unchanged from today: the six uniform slots always render
(media slot shows its placeholder when empty; reviews/follow slots fail soft via their existing
inclusion tags). The restyle adds: a page header band, a screenshot gallery layout, a prominent
"Try it" primary button, and card framing — **same slots, same order** (AC-2 uniformity).

**Discover (restyled).** The five existing states all keep working, now styled: results (a
responsive `.app-grid` of `.card`s), **zero-results** (a defined `.empty-state`), empty-catalogue
(`.empty-state`), facet-degraded (sidebar message), error (the loud 500, never a fake empty). The
search form + facets + pagination keep their exact GET semantics (no-JS, AC-1/AC-4).

Breakpoints (all three surfaces): **~360px** single column; **~600px** two-column grids / horizontal
nav; **~900px+** the max-width container + multi-column grid. No horizontal overflow at any width.

---

## 7. Non-functional handling

- **Performance / first paint (M2).** One render-blocking `<link>` to a small hashed CSS file (the
  design system stays well under the size where a single CSS file matters); **system fonts** (no
  web-font request, no FOUT); HTMX `defer` (non-blocking); no CDN, no client framework. Target:
  first-contentful-paint **≤ the current baseline**, recorded before/after at Stage 4 (A3).
- **SEO (AC-2).** Server-rendered HTML is unchanged in content; title + canonical + name +
  description + category remain in the no-JS response on the app page. The landing page adds a
  `<title>` + meta description in the server HTML.
- **Accessibility (AC-7).** `:focus-visible` rings on all interactives (keyboard rings without
  mouse-click rings — an improvement); AA contrast on every token pair; preserved labels + alt
  text; a **skip-to-content** link; `prefers-reduced-motion` gating all motion; semantic landmarks
  kept. Bar: **no worse than today**, and measurably better on focus + skip-link.
- **Security (§8.4).** No new input, trust boundary, PII, or auth path. No third-party origin
  (vendored HTMX, system fonts). The widget firewall (AC-6) is preserved by construction.
- **Observability / rollback.** One new metric (`LANDING_RENDERED`); existing request logs cover
  the rest; no new alert is warranted (no new failure mode). Rollback is a plain `git revert` of
  the build commit — CSS, templates, the landing route, and the vendored JS come out together with
  **no data migration** (mirrors the standing DU-REL-1 single-revert pattern).

---

## 8. Failure modes (per component — detection → response, never silent)

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| C1 stylesheet | CSS fails to load (cache miss / bad hash) | Browser | Page is **fully usable unstyled** (semantic HTML); WhiteNoise serves an immutable hashed asset so this is near-impossible. No JS dependency on CSS. |
| C2 shell | Template syntax error | Test suite + `manage.py check` at build | Caught pre-deploy (CI/build); never reaches users. |
| C3 landing | View raises | It does nothing that can raise (static render, no DB) | N/A by construction; if a template error slips in, the test suite (§9) catches it. Stateless ⇒ safe on restart. |
| C4 wedge templates | Restyle drops content / breaks a slot | The no-JS + SEO + uniformity tests (§9) | A failing AC-1/AC-2 test blocks the build (M4 gate). |
| C5 HTMX | JS disabled, fails to load, errors, or network drops mid-boost | Absent attribute behaviour | **Degrades to ordinary full-page navigation** — the no-JS path is the source of truth (AC-1). No functionality depends on HTMX. |
| Widget firewall | Premium CSS leaks into the widget | Static assertion (§9, M5=0) | The widget links/extends nothing from core; a leak would fail the firewall test and block the build. |

### 8.4 Threat model (brief §SECURITY)
Presentation-only; no new input parsing, no new endpoint accepting data (landing consumes no
params), no privilege or PII flow. Injection: all app/tag text already renders through Django
auto-escaping (no `|safe` added). Supply chain: **no CDN/web-font** — HTMX is vendored + pinned +
self-hosted, so there is no third-party runtime origin. The firewall guarantees premium styling
cannot reach a third-party iframe (AC-6).

---

## 9. Tests — every AC mapped to a concrete verification

| AC | Verification | Type |
|----|--------------|------|
| AC-1 (premium + fast + no-JS) | Render app page at 360/600/900 (template renders without error per width section); **no-JS response** still contains all six slots + working Try/Share/Follow controls (assert the anchors/forms present in raw HTML); first-paint baseline recorded Stage 4 | agent + **M7 sign-off** |
| AC-2 (SEO) | Fetch app-page HTML (no JS): assert `<title>`, `<link rel=canonical>`, name, description, category strings present and unchanged from today's snapshot | agent |
| AC-3 (landing) | `GET /` → 200; assert value-prop text + the entry-point links (`discovery:browse`, `accounts:register`, `accounts:signin`) in the body; assert it is not a 3xx | agent + **M7 sign-off** |
| AC-4 (discover) | Render discover with results, zero-results, and empty-catalogue: assert the `.app-grid`/`.empty-state` structures; renders at all three widths | agent + **M7 sign-off** |
| AC-5 (one design system) | **Static grep:** in-scope templates carry no inline `style=`/`<style>` and no per-page stylesheet; all surfaces link exactly the one `core/app.css`; token literals live only in `:root` | agent |
| AC-6 (no regression + firewall) | Full suite green (≥975) + `makemigrations --check` no drift; **firewall grep:** `apps/widget/templates/**` references neither `app.css` nor `core/base.html` and is byte-unchanged by this feature (M5=0) | agent |
| AC-7 (a11y floor) | Checklist test: `:focus-visible` present, skip-link present, every form control labelled, every `<img>` has alt, AA contrast on token pairs, motion gated by `prefers-reduced-motion` | agent |

Each component is testable in isolation: the landing view as a view test; the no-JS/SEO/uniformity
guarantees as raw-response-content tests; "one source of truth" + firewall as static-grep tests;
premium *feel* as the M7 user sign-off (PS-3 pattern). Edge cases enumerated: empty media, empty
catalogue, zero search results, JS-off, CSS-miss, signed-in vs anonymous nav, 360px overflow.

---

## 10. Tech / build decision — proposed global ADR **D-13** (the PF-2 resolution)

**Proposed decision:** the platform's frontend stays **build-free**. The premium look is delivered
by **deepening the hand-authored `core/app.css` into a full design system**; **no Tailwind, no
Node/npm toolchain, and no CSS build step are introduced.** HTMX is added as a **vendored,
self-hosted** static asset (no CDN, no build). This **affirms and extends [D-12](../../DECISIONS.md)**
(its build-free, WhiteNoise-served stylesheet posture is preserved, not revised) and keeps
[D-4](../../DECISIONS.md)'s single-language (Python) repo intact.

**Why (against the user's named "Tailwind"):**
1. **The gap is design depth, not tooling.** The repo already has a working hand-authored design
   system (tokens + components); it is shallow, not mis-architected. Tailwind does not *give* a
   premium look — you still design the tokens/scale; it changes *how* you apply them (utility
   classes in markup). The premium feel is achievable without it.
2. **It eliminates the brief's #1 risk (R1).** R1 is "Tailwind's build step destabilises the parked
   staging deploy." No build step ⇒ R1 cannot occur; the `render.yaml` `buildCommand`, the WhiteNoise
   serving model, and `collectstatic` are **unchanged**.
3. **Standards (CLAUDE.md §5.5).** Simplicity-first / boring-and-well-understood / no speculative
   abstraction / match-existing-conventions all point at extending the existing CSS over adding a
   second language + a build step to a deliberately single-language, just-stabilised deploy.
4. **AC-5 alignment.** "One design system, no per-page ad-hoc styling, one source of truth" is most
   directly served by a component stylesheet; a utility-class framework pushes styling decisions
   into every template's markup (the opposite axis), and needs the build step purely to tree-shake
   the utilities it generates.

**What it sacrifices (stated honestly):** the utility-class authoring velocity and the large ready-made
default scale Tailwind gives; we hand-author the scale instead (a one-time design cost, paid once,
then reused). If future surface velocity proves this wrong, Option B (§11) is a clean, additive
upgrade — the design system's tokens map directly onto a Tailwind config.

→ **Recorded as proposed global ADR D-13**, ratified via **DN-PF-DESIGN** (because it diverges from
a user-named technology and settles the global build posture — the architect does not self-ratify a
global decision; this mirrors DN-PS-DESIGN → D-12).

## 11. Alternatives considered

- **Option B — Tailwind via the standalone CLI (the contingency, fully specified).** If you prefer
  Tailwind: use the **standalone CLI binary** (no Node/npm). Build = `tailwindcss -i
  apps/core/static/core/src.css -o apps/core/static/core/app.css --minify`, run **before**
  `collectstatic` in `render.yaml`'s `buildCommand`; the binary is fetched in the build step (a
  pinned release URL) or vendored. Output is one static, hashable `app.css` WhiteNoise serves exactly
  as today, so the serving model and firewall hold; the `content` glob scans `apps/**/templates/**`
  to tree-shake. **Sacrifices:** a real build step (reopens R1 at lower severity — a binary fetch can
  fail a deploy), a vendored/fetched binary to pin and update, utility classes in template markup,
  and a heavier template churn. This is a complete, buildable fallback if DN-PF-DESIGN overrules me —
  it would itself become the D-13 text.
- **Tailwind via the full Node/npm toolchain — rejected.** Adds `package.json` + `node_modules` + a
  Node runtime to a pure-Python repo (D-4) and the heaviest build step into a just-stabilised deploy
  (R1 at full severity). Most power, worst fit for this repo's constraints.
- **Tailwind Play CDN — rejected.** A runtime browser JIT (`<script src=cdn.tailwindcss.com>`) makes
  the entire stylesheet depend on JS + an external origin → breaks no-JS (AC-1), regresses first
  paint (M2), adds a supply-chain/privacy dependency, and is explicitly not for production.
- **A self-hosted web font — rejected (deferred extension point).** Adds a render-blocking/FOUT
  request that risks M2; a refined system-font stack delivers the premium feel at zero first-paint
  cost. Revisit only if the M7 sign-off says typography specifically falls short.

## 12. Deferred extension points (named, **not** built — anti-speculation, §5.5)

- A "recently added apps" strip on the landing page (would couple `/` to the catalogue + a DB read;
  keep the front door static + unfailable for now).
- HTMX **fragment** enhancement of discovery search/pagination (debounced `hx-get` returning just the
  results region on `HX-Request`) — a real but additive view change; **out of this feature's "light"
  appetite** (Q2). Sequence it as a separate later increment only if cheap + the no-JS test stays green.
- A self-hosted variable web font (see §11).
- Inheriting the design system into the authed surfaces (Q1 follow-on — cheap once the system exists).

## 13. Rollout strategy

- **Flag/toggle.** No feature flag needed — it is additive and reversible. The landing route is its
  own toggle (the one route line); the restyle ships in the CSS + templates.
- **Backward compatibility.** Existing class names are kept/extended, never renamed; the shell block
  contract is additive; no view/selector/URL/schema contract changes. All 975 tests stay green (M4).
- **Increment order (smallest-useful-first, for the Planner):**
  1. **Design-system tokens + base/components in `app.css`** (the substrate everything else needs).
  2. **Restyle the shell** `core/base.html` (chrome + skip-link + `body_class` block) — lifts every
     surface's chrome; verify every surface still renders (the platform-staging render-every-surface
     check).
  3. **New landing** route + view + `core/landing.html` (closes PF-CARRY-1; independently testable).
  4. **Restyle the app page** (the load-bearing wedge surface; no-JS + SEO + uniformity tests).
  5. **Restyle discover** (grid + states + responsiveness).
  6. **Vendored HTMX + `hx-boost`** (last; pure enhancement, drop-if-risky).
  7. **TEST_PLAN.md** mapping every AC + the M7 sign-off package for the user.
- **Verification gates:** no migration drift; ≥975 green; firewall M5=0; no-JS + SEO pass; then the
  user's M7 premium sign-off (the human-judgment ACs).

---

## 14. Exit-criteria self-check

- ✅ Every AC (AC-1…AC-7) maps to ≥1 design element (§3) + a concrete verification (§9).
- ✅ All interfaces fully specified, no "TBD" (§5: the CSS API, the landing route/view, the block
  contract, the HTMX contract — and Option B is specified to buildable detail).
- ✅ Every component's failure behaviour documented (§8).
- ✅ Honours CLAUDE.md §5: scalable (a hashed CSS file is fine at 100×), readable/partitioned (layered
  sections + a token API), fail-loud (build/test gates), one source of truth (C1), design-for-deletion
  (single-revert rollback, route toggle), and **adds no speculative abstraction** (§12 defers, not builds).
- ✅ **DN-PF-DESIGN resolved** — user chose **Option A (no build step)** "for now," with Option B
  (Tailwind standalone CLI) kept as an outcome-gated reversible fallback; PF-DESIGN-1…7 RATIFIED;
  recorded as global ADR **[D-13](../../DECISIONS.md)**. Cleared for Stage 3 (Planner).

---

_Proposed design elements: **PF-DESIGN-1** (no-build hand-authored design system = D-13), **PF-DESIGN-2**
(one served, sectioned, token-driven `app.css`), **PF-DESIGN-3** (restyled shared shell, additive block
contract), **PF-DESIGN-4** (new static `/` landing via `core.views.landing`), **PF-DESIGN-5** (app-page +
discover restyle, content/slots/SEO unchanged), **PF-DESIGN-6** (vendored HTMX + `hx-boost`, fully
degradable), **PF-DESIGN-7** (firewall + no-JS + SEO + a11y preserved by construction). All **RATIFIED**
2026-06-28 (DN-PF-DESIGN, Option A → global [D-13](../../DECISIONS.md))._
