# FEATURE_BRIEF.md — interface-cleanup

*Stage 1 (Product Analyst) — **DRAFT, awaiting approval** (DN-IC-BRIEF).*

> Upstream inputs read: the user's request to consolidate a full-app UX/UI walkthrough into one
> feature (this session); the walkthrough findings + scope decisions in
> [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) and [DECISIONS.md](DECISIONS.md) ([IC-D-1](DECISIONS.md) scope =
> cleanup layer only; [IC-D-2](DECISIONS.md) Feature Track); the shared design system
> ([../../apps/core/static/core/app.css](../../apps/core/static/core/app.css)) and the shared shell
> ([../../apps/core/templates/core/base.html](../../apps/core/templates/core/base.html)); the live
> surfaces audited (landing, discover, app page, submit, the two developer homes, dashboard, profile,
> auth flow, interests, following); the vision (§4 integrity, §5.4 the developer wedge, §6 app pages)
> and the engineering standards ([../../CLAUDE.md](../../CLAUDE.md) §5.1/§5.3); the global build-free /
> server-rendered posture ([D-4](../../DECISIONS.md) / [D-13](../../DECISIONS.md)).

---

## Problem statement

**Who.** Every user of the platform — visitors browsing and trying apps, developers presenting and
managing their apps — and the maintainers who read and extend this codebase (§5.1).

**What problem.** The UI was built feature-by-feature across ~13 features, each adding its own
surface. A holistic walkthrough (this session) found three classes of accumulated debt:

1. **Silent, live design-system defects.** The design system is referenced by names that **don't
   exist**, so the intended styling silently doesn't apply:
   - `btn--sm` is used in **12 templates** but is **not defined** in [app.css](../../apps/core/static/core/app.css) —
     every "small" button renders at full size.
   - The custom properties `--space-0.5`, `--space-1.5`, `--space-2.5` (used across ~15 spots) and
     `--font-size-md` (dashboard headings) are **not defined** in `:root`, so `gap`/`font-size` set
     with them collapse to a fallback — spacing the templates intend is simply absent.
   - A CSS specificity conflict (`.app-page-sidebar form button` over `.btn--primary`) **silently
     demotes the app page's primary Follow button to a grey/secondary appearance** — the most
     important relationship CTA looks inert.
2. **Systemic inconsistency from bypassing the design system.** There are **~621 inline `style="`
   attributes** across the templates. The token set exists, but presentational intent (a section
   heading, a muted caption, a card sub-section) is hand-tuned inline per file rather than expressed
   once as a reusable class — so the same meaning drifts screen to screen, and the defects above
   propagate because there is no single component to fix.
3. **Per-surface experiential rough edges.** The app page's primary **Try** action is buried ~5–6
   sections down on mobile; **two distinct developer homes** are both named around "My Apps"
   (confusing wayfinding); facet badges convey their category only via a hover `title` (invisible to
   touch/keyboard); the **Share** control records a signal then silently reloads with no feedback and
   no copy affordance; **Discover never states how results are ordered** (on the one surface whose
   pitch is "ranked by merit"); decorative **emoji** are used as iconography (inconsistent per-OS,
   informal, not marked decorative for screen readers); the interests picker keeps duplicate-tag
   checkboxes in sync **only with JavaScript**.

**Why now.** The developer's app page and the surrounding surfaces are the platform's **marketing
face and the bring-your-own-audience wedge** (§5.4; [D-10](../../DECISIONS.md)), and the live staging
deploy is sequenced to debut on a polished UI ([D-11](../../DECISIONS.md)/[D-13](../../DECISIONS.md)).
A product that reads competent-but-inconsistent — with visibly half-applied styling — undersells
every developer recruited onto it. These are not one bug; they are a connected layer (one root cause:
the design system is not the single source of truth), so fixing them **piecemeal as patches would be
inefficient and would not address the root cause**. The user chose to address them in one coordinated
pass.

## Goal

**One sentence:** Make the existing design system the **actual single source of truth** and clean up
the accumulated UI/UX inconsistencies, silent defects, and experiential rough edges across **every
surface** — so the product is consistent, correct, and polished — **without** a distinctive rebrand
(palette, stylized/animated navigation, and premium motion remain the separate, held
[`ui-modernization`](../README.md) bet — [IC-D-1](DECISIONS.md)).

## Domain terms

- **Design system** — the shared token set + component classes in
  [`core/app.css`](../../apps/core/static/core/app.css), inherited by every surface via
  [`core/base.html`](../../apps/core/templates/core/base.html). The intended single source of truth
  for presentation.
- **Silent defect** — a template referencing a token/class/treatment that the design system does not
  actually provide, so the intended styling never applies and nothing errors.
- **Presentational consolidation** — moving a recurring presentational intent out of repeated inline
  `style="…"` and into a named, reusable design-system pattern. (How aggressively, and via what
  mechanism, is a Stage-2 architecture call — see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).)
- **Cleanup envelope** — this feature changes **presentation only**: no DB schema/migration, no
  public API change, no business-logic/view/URL change, no global ADR. (If a fix needs any of those,
  it is out of scope and escalates — see Constraints C2/C4.)
- **Distinctive rebrand** — a new brand palette, stylized/animated navigation, and premium motion
  language. **Explicitly out of scope here** ([`ui-modernization`](../README.md), [IC-D-1](DECISIONS.md)).

## User stories

1. **US-1 (consistency).** As a user, across every screen the same kind of element looks and is
   spaced the same way, so the product feels coherent and trustworthy rather than assembled from
   parts.
2. **US-2 (nothing half-finished).** As a user, buttons, spacing, and icons render as intended on
   every page and operating system — no oversized "small" buttons, no collapsed spacing, no
   primary action that looks greyed-out, no platform-dependent emoji — so nothing looks unfinished.
3. **US-3 (reachable primary action).** As a visitor on a phone, the app page's primary **Try**
   action is reachable without scrolling past the entire page.
4. **US-4 (wayfinding).** As a developer, I can tell my two homes apart (submissions vs. analytics)
   and always know which one I'm on, so I never get lost or dead-ended.
5. **US-5 (legible details).** As a visitor, I can read an app's facet categories without hovering,
   I get clear feedback when I share, and I can see how Discover results are ordered — so the small
   interactions are clear, not mysterious.
6. **US-6 (maintainability).** As a developer of this codebase, presentational intent lives in the
   design system, not scattered across hundreds of inline styles, so the same visual change is made
   once and cannot silently drift (§5.1/§5.3).
7. **US-7 (accessibility holds).** As a user relying on a screen reader, keyboard, or no JavaScript,
   decorative icons are not announced as content, facet groupings are conveyed without hover, and no
   surface depends on JavaScript to stay in a consistent state.

## Acceptance criteria

Each criterion is tagged **[agent-verifiable]** (checkable by an automated test / inspection) or
**[human-judgment]** (a person's eye, signed off like [premium-frontend](../premium-frontend/)'s PS-3).

- **AC-1 (US-2, defined references).** **[agent-verifiable]** *Given* the template set and the design
  system, *When* a check enumerates every design-system token (`--…`) and component class
  (e.g. `btn--*`) referenced by a template, *Then* **every referenced token and class is defined** in
  the design system — specifically `btn--sm`, `--space-0.5`, `--space-1.5`, `--space-2.5`, and
  `--font-size-md` are no longer referenced-but-undefined (either defined, or the references removed).
- **AC-2 (US-2, no silent demotion).** **[agent-verifiable]** *Given* the app page, *When* it renders,
  *Then* the element intended as the page's primary action in the sidebar (Follow when actionable)
  carries the primary treatment and is **not** overridden to a secondary appearance by a CSS
  specificity conflict; *And* each button's rendered prominence matches its intent across surfaces.
- **AC-3 (US-1/US-6, consolidation).** **[agent-verifiable + human-judgment]** *Given* the templates,
  *When* the cleanup is complete, *Then* **recurring presentational intent** (the patterns that
  repeat across surfaces — section headings, muted captions, card sub-sections, status colours, etc.)
  is expressed through **named, reusable design-system patterns rather than duplicated inline
  styles**; the inline-`style` count is **materially reduced from the recorded baseline of ~621**
  (the exact target is set in Stage 2/3), and remaining inline styles are genuinely one-off. *(Scope
  depth — full extraction vs. a bounded prioritized subset — is a Stage-2 call, [OQ-IC-1](OPEN_QUESTIONS.md).)*
- **AC-4 (US-3, mobile CTA).** **[agent-verifiable + human-judgment]** *Given* the app page on a
  small viewport, *When* it renders, *Then* the primary **Try** action is reachable near the top
  (the visitor does not scroll the entire page to find it); *And* this is achieved as a **uniform,
  presentational** change — the app-page **uniformity invariant from [app-page-redesign](../app-page-redesign/)
  (same slots, same DOM slot order for every app) and the M5=0 firewall invariant still pass
  unchanged** (C1).
- **AC-5 (US-4, naming).** **[agent-verifiable]** *Given* the two developer surfaces
  ([`catalog:my-apps`](../../apps/catalog/templates/catalog/my_apps.html) and
  [`dashboard:my-apps`](../../apps/dashboard/templates/dashboard/my_apps.html)), *When* a user
  navigates from the header, landing, profile, and the cross-links, *Then* the two surfaces have
  **distinct, consistent names used everywhere**, and the current surface is indicated. *(Final
  labels — [OQ-IC-4](OPEN_QUESTIONS.md).)*
- **AC-6 (US-5/US-7, legibility + a11y).** **[agent-verifiable]** *Given* the surfaces, *When* they
  render, *Then* (a) decorative icons are not announced as content to a screen reader (emoji either
  replaced with a consistent icon treatment or marked decorative — mechanism is [OQ-IC-2](OPEN_QUESTIONS.md));
  (b) an app's facet **category** is conveyed **without relying on hover/`title`**; (c) the interests
  picker keeps duplicate-tag selections consistent **without JavaScript** (or the duplication is
  removed); (d) the Share control gives the user **feedback** and a way to obtain the link.
- **AC-7 (US-5, ordering visibility).** **[agent-verifiable]** *Given* the Discover surface, *When*
  results render, *Then* the surface **states how results are ordered** (the "ranked by merit, never
  spend" basis is surfaced in the UI). *(A re-ordering/sort **control** that changes the catalog
  primitive is out of scope — see [OQ-IC-6](OPEN_QUESTIONS.md); this AC is a presentational label only.)*
- **AC-8 (overall polish — human sign-off).** **[human-judgment]** *Given* the cleaned-up surfaces on
  **web and mobile**, *When* the user reviews them, *Then* they sign off that the product reads as
  **consistent and polished** end-to-end (the premium-frontend PS-3 / app-page-redesign AC-8
  precedent). This is the gate that makes "cleaner" verifiable rather than a vibe.
- **AC-9 (no regression / stays in the cleanup envelope).** **[agent-verifiable]** *Given* the
  changes, *When* the suite and a render-every-surface check run, *Then* the **full test suite is
  green**, every surface still renders, there is **no migration drift**, and **no public API, view,
  URL, business-logic, or global ADR has changed** (presentation-only — C2/C4). Any fix that would
  require one is escalated, not smuggled in.

## Success metrics

Structural metrics are checkable now; the qualitative gate is at release. No prod data is required —
consistent with the standing closed-out pattern.

- **M1 (structural, now).** **Zero** referenced-but-undefined design-system tokens/classes
  (AC-1) — measured by the enumeration check.
- **M2 (structural, now).** Inline-`style` usage reduced from the **~621 baseline** to the Stage-2/3
  target, with recurring patterns componentized (AC-3).
- **M3 (structural, now).** Full suite green; every surface renders (the platform-staging
  render-every-surface check); no migration drift; no API/view/URL/ADR change (AC-9).
- **M4 (a11y, now).** Decorative icons not announced; facet category conveyed without hover; no
  surface depends on JS to stay consistent (AC-6) — measured by inspection/test.
- **M5 (structural, now).** The [app-page-redesign](../app-page-redesign/) uniformity + M5=0 firewall
  invariants still pass after the mobile-CTA change (AC-4 / C1).
- **M6 (qualitative, at release).** User sign-off on AC-8 (consistent + polished, web + mobile).

## In scope

- **A1 — the silent design-system defects:** define (or remove references to) `btn--sm`,
  `--space-0.5/1.5/2.5`, `--font-size-md`; resolve the Follow/Share primary-button specificity
  demotion.
- **A2 — presentational consolidation:** make the design system the single source of truth for
  recurring patterns; reduce inline-style sprawl (depth is a Stage-2 call).
- **A5 — consistent, accessible iconography** in place of decorative emoji.
- **Per-surface experiential fixes:** app-page mobile **Try** reachability (B1); the **two
  developer-home** naming/wayfinding (B4); facet-category legibility without hover (B1); **Share**
  feedback + link affordance (B1); Discover **ordering-basis** label (B2); a lighter touch on the
  long **Submit** form's required-vs-optional grouping (B3); interests-picker no-JS consistency.
- Form-rendering idiom consistency across auth/submit where it is purely presentational.
- Responsive, server-rendered, no-build presentation consistent with [D-4](../../DECISIONS.md) /
  [D-13](../../DECISIONS.md).

## Out of scope

- **The distinctive rebrand — new brand palette, stylized/animated navigation, premium motion
  language** (walkthrough findings A3/A4). This stays the separate, held **`ui-modernization`**
  Feature-Track bet, activated by a future user decision ([IC-D-1](DECISIONS.md); the standing memory
  note). *This is the headline boundary: `interface-cleanup` tightens the existing design; it does
  not reinvent the look.*
- **Dark mode / theming.**
- **Any new product behavior:** changing the ranking/sort algorithm or adding a sort control that
  alters the catalog primitive; new share targets/integrations requiring backend work; new screens,
  states, or data.
- **Any DB schema/migration, public API change, or global ADR change.** A fix that needs one does
  not belong in this feature (it would re-route to its own Feature Track item) — see C2/C4.
- Ranking, Quality Score, or impression-allocation logic of any kind.

## Constraints & assumptions

- **C1 — Preserve the app-page invariants (load-bearing).** The mobile-CTA change (AC-4) must keep
  the [app-page-redesign](../app-page-redesign/) **uniform-slot-order** invariant and the **M5=0**
  firewall invariant passing — a responsive reflow is presentational and applied uniformly to every
  app; the DOM slot order/fingerprint must not change. **[verified]** the invariants exist as tests.
- **C2 — Cleanup envelope / no schema-API-ADR.** Presentation-only: no DB schema/migration, no public
  API endpoint added/changed, no global ADR modified. (This keeps the change within what the Patch
  Track *gate* permits even though it runs on the Feature Track for coordination — [IC-D-2](DECISIONS.md).)
  **[verified]** as a requirement; if a finding can't be fixed within it, escalate via OPEN_QUESTIONS.
- **C3 — Stack.** Server-rendered Django templates ([D-4](../../DECISIONS.md)), no-build token CSS
  ([D-13](../../DECISIONS.md)), responsive shell, HTMX as light progressive enhancement only; the
  **no-JS path is the source of truth**. **[verified]**
- **C4 — Presentation-only / no behavior change.** No view, URL, or business-logic change (mirror of
  premium-frontend's G5). Share "feedback" (AC-6d) must be achievable without changing what the Share
  action *does* on the server; if it requires new behavior, it is deferred/escalated. **[unverified]**
  — the cheapest no-behavior-change treatment is a Stage-2 call ([OQ-IC-5](OPEN_QUESTIONS.md)).
- **C5 — Accessibility is a requirement, not a retrofit.** Contrast, focus order, non-color
  signaling, decorative-vs-content semantics, and the no-JS path are first-class (AC-6). **[verified]**
- **C6 — Widget firewall untouched.** The embeddable widget is intentionally unstyled by the shared
  system and must stay isolated (AC-6/M5=0 of the widget features) — no cleanup touches it. **[verified]**
- **A1 — Assumption.** Consolidating into the design system will reduce, not increase, total
  presentational code and future drift. **[unverified]** — validated by M2 + the reader's-eye review.
- **A2 — Assumption.** The accumulated rough edges are individually small enough that none hides a
  required schema/API change. **[unverified]** — tested as each is scoped in Stage 2 (C2 gate).

## Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | The A2 consolidation balloons into a "rewrite every template" mega-task that fights the pipeline. | High / High | Stage 2/3 picks a **bounded, prioritized** target (define tokens + fix defects + extract the top recurring patterns first); the rest is iterative. [OQ-IC-1](OPEN_QUESTIONS.md) sets the depth; M2 target is explicit, not "all of it." |
| R2 | Reordering the app-page CTA for mobile breaks the uniform-slot-order fingerprint test (AC-7 of app-page-redesign). | Med / High | C1: keep DOM slot order, reflow via layout only; the invariant test stays green and is the gate (AC-4). |
| R3 | Touching ~30 templates causes visual regressions on surfaces not individually eyeballed. | Med / Med | The platform-staging **render-every-surface** check + the per-surface human sign-off (AC-8) on web + mobile. |
| R4 | A "cleanup" fix quietly adds behavior (e.g. a Share copy-button as new JS, a sort control touching the catalog primitive). | Med / Med | C4 presentation-only line; AC-7/AC-6 are scoped to labels/feedback **without** behavior change; anything more escalates to OPEN_QUESTIONS / a separate feature. |
| R5 | Scope blurs into the deferred `ui-modernization` (someone "improves" the palette/nav while in here). | Med / Med | [IC-D-1](DECISIONS.md) line is explicit and is the out-of-scope **headline**; reviewers reject palette/nav/motion changes in this feature. |
| R6 | A finding turns out to need a schema/API change once designed, violating the cleanup envelope. | Low / Med | C2 gate at Stage 2: any such finding is pulled out of this feature and re-routed, not forced through. |

## Vision alignment

Serves the **engineering prime directive** (§5.1 — optimize for the reader; make the design system
the single source of truth, §5.3 readability/reuse), **§5.4 / [D-10](../../DECISIONS.md)** (the wedge's
surfaces are the developer's marketing face — they must read polished and consistent before the live
deploy), and **§4 integrity** (the cleanup explicitly *preserves* the app-page uniformity guarantee
rather than eroding it — C1). It deliberately stops short of the distinctive rebrand so that strategic
bet ([`ui-modernization`](../README.md)) stays a clean, separately-decided feature.
