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
