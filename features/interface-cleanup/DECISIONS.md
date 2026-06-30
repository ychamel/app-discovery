# DECISIONS.md — interface-cleanup

Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide decisions live in the
global [../../DECISIONS.md](../../DECISIONS.md).

---

## IC-D-1 — Scope = cleanup layer only; the distinctive rebrand stays `ui-modernization`

**Date:** 2026-06-30 · **Decided by:** user (Coordinator-surfaced via AskUserQuestion) · **Status:** ratified

**Decision.** `interface-cleanup` covers the **consistency / silent-defect / experiential-fix** layer
(walkthrough findings A1, A2, A5, the active-state part of A6, and the B-level per-surface fixes). The
**distinctive rebrand** — new brand palette, stylized/animated navigation, and premium motion language
(findings A3/A4) — is **explicitly excluded** and remains the separate, held **`ui-modernization`**
Feature-Track bet, activated by a future user decision.

**Why.** The held `ui-modernization` bet (recorded at premium-frontend close-out and in standing
memory) is a deliberate, separately-decided strategic feature needing its own Stage-1→2 design.
Folding it into a cleanup pass would (a) balloon scope, (b) blur a clean strategic boundary, and
(c) couple low-risk presentation fixes to a high-judgment redesign. Keeping cleanup boring and
shippable is the higher-value sequencing.

**Rejected:** "Absorb the rebrand too" (one mega-feature superseding `ui-modernization`) — rejected by
the user in favour of the clean boundary.

---

## IC-D-2 — Runs on the Feature Track (not a single patch), within the patch *envelope*

**Date:** 2026-06-30 · **Decided by:** user + Coordinator · **Status:** ratified

**Decision.** This work runs on the **Feature Track** (Stages 1→5), even though, taken individually,
it introduces **no schema/migration, no public-API change, and no global-ADR change** — i.e. it stays
inside what the Patch Track *scope gate* ([../../CLAUDE.md](../../CLAUDE.md) §2) would permit.

**Why.** It is a **large, cross-cutting, coordinated** change (a design-system consolidation touching
~30 templates plus a connected set of experiential fixes) that the user chose to "address in one go."
That benefits from explicit **Design** (consolidation depth, icon mechanism, mobile-reflow technique)
and **Plan** stages and a per-surface sign-off — more than a single patch can carry. The patch
*envelope* (no schema/API/ADR — brief C2) is retained as a **constraint** so the feature stays
low-risk and reversible; any finding that breaks that envelope is pulled out and re-routed, not forced
through.

**Rejected:** splitting into many independent patches — rejected as inefficient and because it
wouldn't address the shared root cause (the design system not being the single source of truth), which
needs one coordinated design.

---

## IC-D-3 — Preserve the app-page-redesign invariants while moving the mobile CTA

**Date:** 2026-06-30 · **Decided by:** Product Analyst · **Status:** ratified (brief constraint C1/AC-4)

**Decision.** The app-page mobile **Try**-reachability fix is delivered as a **purely presentational,
uniform responsive reflow** that keeps the DOM **slot order/fingerprint unchanged**, so the
[app-page-redesign](../app-page-redesign/) **uniform-slot-order** and **M5=0 firewall** invariants
continue to pass as the gate.

**Why.** app-page-redesign's uniformity guarantee (vision §4 integrity) is load-bearing and tested; a
cleanup must not erode it. Reordering layout for small viewports is fairness-neutral (applied
identically to every app) as long as the structural slot order is untouched.

---

## IC-DESIGN-1…9 — Stage-2 architecture calls (Software Architect, 2026-06-30)

**Date:** 2026-06-30 · **Decided by:** Software Architect (Stage 2) · **Status:** ratified in
[DESIGN.md](DESIGN.md). Full rationale + rejected alternatives live in DESIGN §4/§9; digested here.

- **IC-DESIGN-1 — Missing tokens are *defined*, not renamed (resolves OQ-IC-1's token half).**
  Add `--font-size-md: 1rem` and the **dotted** custom-property names `--space-0.5: 0.125rem`,
  `--space-1.5: 0.375rem`, `--space-2.5: 0.625rem` to `:root`, plus `.btn--sm`. A `.` is a legal
  char in a CSS custom-property name, so the ~37 existing `var(--space-1.5)` references start working
  with **zero template churn**. *Rejected:* renaming every reference to dot-free names (more churn,
  more regression surface).
- **IC-DESIGN-2 — Consolidation depth = bounded-first (resolves OQ-IC-1).** Add a small named
  utility/component layer (`.text-muted`, `.text-error`, `.page-header`, `.toolbar`, `.full-width`,
  a real `.legend-swatch--dashed` replacing the B7 `background-dasharray`), migrate the **four
  worst-offender files** (~270 of 621 inline styles), leave genuinely one-off styles + the sanctioned
  `style="--gap:…"` idiom. **M2 target: inline `style=` 621 → ≤ 400.** *Rejected:* full extraction
  across all 31 templates (brief R1 — balloons, regression risk, diminishing returns).
- **IC-DESIGN-3 — Icon mechanism = inline-SVG `{% icon %}` tag (resolves OQ-IC-2).** A new reusable
  `apps/core/templatetags/icons.py` + hand-authored SVG set, mirroring the `account_roles` tag;
  renders `aria-hidden="true"`. No build (D-13), brand-neutral (no rebrand, IC-D-1), accessible.
  *Rejected:* icon font / CDN sprite (build/asset dependency, a11y regression, breaks vendored-only).
- **IC-DESIGN-4 — Mobile Try reflow = CSS `order:` only (resolves OQ-IC-3; upholds IC-D-3/C1).**
  Below 900px, reorder `.app-page`'s three direct children by `order:` so the action panel rises to
  the top; **source DOM order unchanged → the fingerprint/firewall invariants stay green**.
  *Rejected:* DOM reorder (breaks the invariant — the whole point of IC-D-3).
- **IC-DESIGN-5 — Developer hub = one "Developer" header entry + a shared `_dev_tabs.html`
  (Manage|Analytics) — the user's chosen IA (AskUserQuestion, OQ-IC-4).** No new route/view; the
  tabs link the two existing URLs; the dashboard's inline sub-nav is replaced by the shared partial.
  *Rejected:* keep two header entries / a plain rename (the user chose the unified hub).
- **IC-DESIGN-6 — Follow/Share demotion fix = delete the `.app-page-sidebar form button` override**,
  deliver full-width via a class-scoped layout rule so `.btn--primary` wins by treatment (AC-2).
- **IC-DESIGN-7 — Share feedback stays in-envelope (resolves OQ-IC-5).** The server Share action is
  byte-unchanged (C4); feedback comes from a **pure-PE copy-link button** + the already-present
  readable link (no-JS still works). Flashing the POST itself would need a view change → **not done**.
- **IC-DESIGN-8 — Discover ordering = a presentational label only (resolves OQ-IC-6).** "Ranked by
  merit, never by spend" caption; **no sort control/param**, `search_catalogue` untouched (C4).
- **IC-DESIGN-9 — Picker no-JS = de-duplicate the rendered tags (resolves OQ-IC-2/AC-6c).** Render
  each tag once → delete the JS sync `<script>` → no-JS path inherently consistent. **C4 nuance:**
  if the dedupe needs reshaping the view's `clusters` context (vs. regrouping data already in the
  template), it is the single, endpoint/schema-neutral view-layer touch — **surfaced for Planner/
  build confirmation under the C2 gate ([OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-IC-8)**, with a
  no-regression fallback (keep the JS sync; the *saved* state is already no-JS-correct).

**No global ADR.** All choices are presentation-only within D-4/D-13 (DESIGN §14); nothing is
promoted to the global [DECISIONS.md](../../DECISIONS.md) (confirms IC-D-2).

---

## IC-EXP-1…5 — Stage-2b experience calls (Experience Designer, 2026-06-30)

**Date:** 2026-06-30 · **Decided by:** Experience Designer (Stage 2b) · **Status:** ratified in
[EXPERIENCE.md](EXPERIENCE.md) (intent-only; no implementation). These set the *feel* the Architect's
mechanisms (IC-DESIGN-1…9) deliver, and feed the AC-8 sign-off checklist (EXPERIENCE §4).

- **IC-EXP-1 — App-page mobile action panel = a compact action bar with one dominant focal point.**
  Try/Follow/Share render as **one bounded, compact action region** (not a tall full-width stack), so
  the app identity surfaces immediately after it. Focal order **Try (dominant) › Follow (primary,
  restored from the AC-2 grey demotion) › Share (quiet)**; Try and Follow are differentiated by
  *prominence* (size/position), never by demoting Follow's colour. Resolves the "two primaries"
  tension (Try = dominant conversion link; Follow = primary relationship form-button, below Try) and
  the DESIGN §4.4 "compact bar or not" question → **compact bar**. (EXPERIENCE S1.)
- **IC-EXP-2 — Mobile reflow focus-order trade-off accepted (not escalated).** CSS `order:` moves
  *visual* order only; keyboard/screen-reader order stays DOM order (identity → actions → reviews).
  That sequence is itself logical → no meaning-changing visual/DOM contradiction (no WCAG 1.3.2
  failure), so this is **documented as an accepted trade-off + a §4 sign-off item** rather than routed
  back to the Architect. Upholds IC-D-3 (source order is the invariant). (EXPERIENCE S1-10.)
- **IC-EXP-3 — Developer-hub "home" tab = Manage; active-tab treatment reuses the existing accent
  "you are here" pattern.** Managing/submitting is the developer's primary job → the header "Developer"
  entry lands on **Manage**; Analytics is the reflective second. The active indicator reuses the
  Discover sidebar active-link pattern (no new pattern) + current-page semantics so "active" is
  signalled by more than colour. The horizontal tab bar is the one new *arrangement*, justified by the
  new hub IA. (EXPERIENCE S2.)
- **IC-EXP-4 — Discover ordering caption must read as informational, never as a control, and is
  suppressed on zero results.** A merit caption styled like a button/dropdown would imply a sort
  control that AC-7 explicitly excludes; it reads unmistakably as a statement. On the empty state it is
  hidden (nothing to order). (EXPERIENCE S3.)
- **IC-EXP-5 — System scope guard: this pass *quiets and aligns*, it does not embellish.** No new
  palette, stylized/animated nav, or decorative motion (those stay `ui-modernization`, IC-D-1); the
  only new feedback motion is the reduced-motion-safe Share "Copied!" confirmation. "Calm" is a tone
  target tied to restrained accent use + reduced-motion-first. (EXPERIENCE §3.)
