# OPEN_QUESTIONS.md — interface-cleanup

All stages append here. Carries the verbatim origin (the UX/UI walkthrough), the open questions the
Product Analyst deliberately left to Stage 2 (architecture), and any later escalations.

---

## Origin — the full-app UX/UI walkthrough (2026-06-30)

The user asked for a full UX walkthrough of the app in its current state (UI/UX focus, not logic),
using the Experience-Designer lens, then asked to **consolidate the findings into one feature**,
`interface-cleanup`, "since these are a lot of changes and it would be better to address them in one
go." Scope was bounded by [IC-D-1](DECISIONS.md) (cleanup layer only — the distinctive rebrand stays
the held `ui-modernization` bet) and routed to the Feature Track by [IC-D-2](DECISIONS.md).

### Findings the brief is built from (grouped)

**A — system-wide**
- **A1 (silent design-system defects).** `btn--sm` used in 12 templates, **undefined** in
  [app.css](../../apps/core/static/core/app.css) → "small" buttons render full size.
  `--space-0.5/1.5/2.5` (~15 spots) and `--font-size-md` (dashboard) **undefined** → spacing/size
  silently collapses. `.app-page-sidebar form button` overrides `.btn--primary` (specificity 0,2,1 >
  0,1,0) → the app-page **Follow primary button renders grey/secondary**.
- **A2 (design system bypassed).** ~621 inline `style="` attributes; recurring presentational intent
  is re-tuned per file instead of expressed once as a class — the root cause of drift and of A1
  propagating.
- **A3 (generic palette / no brand) + A4 (no top-end type hierarchy, no display face, no "you are
  here" nav, no stylized/animated nav).** → **DEFERRED to `ui-modernization`** ([IC-D-1](DECISIONS.md)),
  not this feature.
- **A5 (emoji as iconography).** Inconsistent per-OS, informal, not `aria-hidden`.
- **A6 (global nav has no active state / mobile priority).** The *active-state* part is a small
  presentational fix (in scope); the *stylized/animated nav* part is A4 → deferred.

**B — per-surface**
- **B1 (app page):** primary **Try** buried ~5–6 sections down on mobile; uniformity invariant means
  new apps show a stack of near-empty cards (experiential cost — noted, not necessarily "fixed");
  facet category only in hover `title`; **Share** POSTs then silently reloads, no copy affordance.
- **B2 (discover):** strong surface; but **no statement of how results are ordered** (the
  "ranked by merit" basis is invisible). A *sort control* would change behavior → out of scope.
- **B3 (submit):** very long single-column form; required-vs-optional grouping is thin;
  `demo_clip_alt` required-if-clip only signalled in placeholder.
- **B4 (IA):** two developer homes both named around "My Apps" (`catalog:my-apps` = submissions,
  `dashboard:my-apps` = analytics) — ambiguous naming despite the reciprocal links.
- **B6 (auth):** signin/register render fields via the Django widget; submit hand-rolls inputs — two
  form idioms.
- **B7 (dashboard):** strong; minor — the sparkline legend swatch uses a non-property
  (`background-dasharray`) so the dashed swatch won't render; leans on the A1 undefined tokens.
- **interests picker:** duplicate-tag checkboxes synced **only via JS** → no-JS users can submit
  inconsistent state.

> The full prioritized report (P0/P1/P2 + the "what the persona catches vs misses" note) was
> delivered in the originating session; the actionable substance is captured above and in the brief's
> In/Out-of-scope.

---

## Open questions for Stage 2 (Architect) — deliberately left by the Product Analyst

The brief defines the **capability/outcome**; the **mechanism** is the Architect's call.

- **OQ-IC-1 (consolidation depth).** How aggressive is the A2 inline-style → design-system
  consolidation? Full extraction across all ~30 templates, or a bounded prioritized subset (define
  the missing tokens + a small utility/component set covering the top recurring patterns, migrate the
  worst offenders, leave genuinely one-off styles)? Sets the M2 target. *Recommend bounded-first to
  hold R1.*
- **OQ-IC-2 (icon mechanism).** What replaces decorative emoji — inline SVG, a small vendored sprite,
  CSS-drawn glyphs? Must be consistent, brand-neutral (no rebrand — IC-D-1), no build step (D-13),
  and accessible (decorative = not announced). The Architect picks; the brief only requires the
  outcome (AC-6a).
- **OQ-IC-3 (mobile CTA reflow).** How to surface the app-page **Try** action near the top on small
  viewports **without** changing the DOM slot order (so the uniform-slot-order fingerprint test stays
  green — C1/AC-4)? Pure layout/responsive technique only.
- **OQ-IC-4 (developer-home names).** Final labels for the two surfaces (e.g. "Submissions" vs.
  "Analytics", or one "Developer" hub with two tabs). Has a product-naming flavour — may warrant a
  quick user confirmation if the Architect can't settle it cleanly.
- **OQ-IC-5 (Share feedback without behavior change).** Can the Share control give feedback + a
  copyable link **without** changing what the server-side Share action does (C4)? E.g. a visible,
  already-present readable link + a no-JS-safe confirmation, with copy-to-clipboard as pure PE. If
  any option requires new behavior, it's deferred/escalated.
- **OQ-IC-6 (ordering visibility scope).** AC-7 is a presentational **label** of the existing order
  only. Confirm no sort **control** (which would touch the catalog primitive = behavior, out of
  scope) sneaks in.
- **OQ-IC-7 (form idiom).** Standardize auth-vs-submit field rendering — is unifying the idiom purely
  presentational, or does it touch form/validation behavior? If the latter, scope carefully (C4).

*(No open questions block Stage 1. The brief is complete and internally consistent; these are
hand-offs to the Architect.)*

---

## Stage-2 resolution (Software Architect, 2026-06-30)

OQ-IC-1…7 are **resolved in [DESIGN.md](DESIGN.md)** (digested in [DECISIONS.md](DECISIONS.md)
IC-DESIGN-1…9): OQ-IC-1 → bounded-first (IC-DESIGN-1/2); OQ-IC-2 → `{% icon %}` inline-SVG
(IC-DESIGN-3) + picker dedupe (IC-DESIGN-9); OQ-IC-3 → CSS `order:` reflow (IC-DESIGN-4); **OQ-IC-4 →
the user chose a single "Developer" hub with Manage|Analytics tabs** (AskUserQuestion; IC-DESIGN-5);
OQ-IC-5 → copy-link PE, no server change (IC-DESIGN-7); OQ-IC-6 → label only, no control
(IC-DESIGN-8); OQ-IC-7 → presentational form-field idiom only (DESIGN §4.8).

### OQ-IC-8 (NEW, Architect → Planner) — does the picker no-JS fix touch the view context?

The AC-6c "consistent without JavaScript" outcome cannot be met by CSS (it can't sync two
checkboxes), so the clean fix is to **render each interest tag at most once** and delete the JS sync
`<script>`. Whether that de-duplication can be done by **regrouping data already in the template
context** (purely presentational, fully in-envelope) or needs a **minimal reshape of the view's
`clusters` context** (a single endpoint/schema-neutral view-layer touch) is a Stage-3/4 call.

**Resolution path:** the Planner/Engineer confirms at task time. If template-only → in-envelope, do
it. If it needs the view-context touch → that touch is **acceptable as the single deliberate
view-layer change** *provided* it changes no URL, no saved-state contract, and no schema (it does
not); otherwise the **fallback** (keep the JS sync; document that the saved state is already
no-JS-correct because the server recomputes `item.checked` from declared tags on reload) is taken and
the picker item is noted as partially-addressed. **Not a user block** — recorded so the C2 envelope
gate is honoured explicitly, not crossed silently.
