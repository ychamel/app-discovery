# TASKS.md — interface-cleanup

*Stage 3 (Planner / Tech Lead). Inputs read: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (approved,
DN-IC-BRIEF; AC-1…AC-9, US-1…7, C1–C6), [DESIGN.md](DESIGN.md) (the eight workstreams W1–W8 +
the §4 contracts), [EXPERIENCE.md](EXPERIENCE.md) (binding feel spec S1–S5 / X1–X4 + the §4
sign-off checklist), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) (OQ-IC-8), [DECISIONS.md](DECISIONS.md)
(IC-D-1…3, IC-DESIGN-1…9, IC-EXP-1…5), and [CODEMAP.md](../../CODEMAP.md).*

> **How this list was decomposed.** The design's eight workstreams (W1–W8) are the spine; each is
> split where one agent-session + one releasable state demands it (no `L` survives). Per the
> Planner sequencing rules: **W1 tokens first** (prerequisite — nothing styles correctly until the
> design system is whole), **the W8 enumeration guard lands immediately with W1** (so the
> silent-defect class is closed before any new CSS is written), **shared artifacts get their own
> task before their consumers** (the `{% icon %}` tag before the emoji replacement; the W2
> component layer before the worst-offender migration; the `_dev_tabs` partial inside its only
> consumer-pair), and the **EXPERIENCE feel spec is carried into the definition-of-done of every
> UI task** — the build implements the intended feel, not a default one. Each task leaves the
> suite green and the system releasable (presentation-only; no migration, ever).

> **Envelope reminder (C2/C4, every task).** No schema/migration, no new URL/view, no public-API
> or business-logic change, no global ADR. The **one** deliberate exception is the OQ-IC-8 picker
> view-context touch, confined to **T-10** and gated there. The widget templates are **never**
> edited (C6). `makemigrations --check` must report **no drift** at every task boundary.

---

## Dependency graph

```
T-01 (W1 tokens+defects, app.css)  ──┬─> T-02 (W8 enumeration guard)        [guard lands with W1]
                                     ├─> T-03 (W2 component layer, app.css) ─> T-04 (W2 migrate worst offenders)
                                     ├─> T-07 (W4 app-page reflow/facet/share)
                                     └─> T-08 (W5 developer hub)
T-05 (W3 {% icon %} tag + SVG set) ───> T-06 (W3 replace decorative emoji)
T-03 ──> T-09 (W6 discover caption)
T-03 ──> T-10 (W7 picker dedupe / no-JS)            [confirms OQ-IC-8]
T-03 ──> T-11 (W7 form-field idiom + submit grouping)
ALL  ──> T-12 (W8 final gate: suite + render-every-surface + no-drift + AC-8 sign-off carry)
```

T-01 is the sole hard prerequisite (tokens + the defect repairs the others build on). T-05 (the
icon tag) is independent of T-01 and can run any time before T-06. T-02 must follow T-01 and then
**stays green through every later task** (each UI task that adds a token/class defines it before
referencing it). T-12 is the gate and depends on all.

---

## Task summary

| ID | Title | WS | Dep | Size |
|----|-------|----|-----|------|
| T-01 | Define missing tokens + `btn--sm`; remove the Follow/Share specificity demotion | W1 | — | M |
| T-02 | Enumeration guard test `test_design_system.py` (+ CODEMAP) | W8 | T-01 | M |
| T-03 | Add the bounded component/utility layer to `app.css` | W2 | T-01 | M |
| T-04 | Migrate the three worst-offender templates + fix the B7 legend swatch | W2 | T-03 | M |
| T-05 | Create the `{% icon %}` inline-SVG tag + the hand-authored set (+ CODEMAP) | W3 | — | M |
| T-06 | Replace decorative emoji with `{% icon %}` across non-widget templates | W3 | T-05 | M |
| T-07 | App page: mobile Try reflow + facet legibility + Share copy affordance | W4 | T-01 | M |
| T-08 | Developer hub: `_dev_tabs` partial + nav active-state + relabel both homes | W5 | T-01 | M |
| T-09 | Discover: ordering-basis caption (informational, not a control) | W6 | T-03 | S |
| T-10 | Interests picker: dedupe → no-JS consistency (confirm OQ-IC-8) | W7 | T-03 | M |
| T-11 | Form-field idiom (auth/submit) + submit required/optional grouping | W7 | T-03 | M |
| T-12 | Final gate: full suite + render-every-surface + no-drift + AC-8 sign-off carry | W8 | all | S |

No `L` tasks. Every DESIGN workstream (W1–W8) and every EXPERIENCE surface (S1–S5) + system layer
(X1–X4) appears in ≥1 task (coverage map at the foot of this file).

---

## Tasks

### T-01 — Define missing tokens + `btn--sm`; remove the Follow/Share specificity demotion
- **Workstream / source:** W1 — DESIGN §3.1, §4.1, §4.2. EXPERIENCE **X4** (defect-repair feel),
  **S1** pillar 5 (Follow restored to primary). Serves **AC-1**, **AC-2**, **M1**.
- **Description:** In [`apps/core/static/core/app.css`](../../apps/core/static/core/app.css):
  1. Add to `:root` the four undefined tokens with the values fixed in DESIGN §4.1 —
     `--font-size-md: 1rem;`, `--space-0.5: 0.125rem;`, `--space-1.5: 0.375rem;`,
     `--space-2.5: 0.625rem;` (the **dotted names defined as-written**, IC-DESIGN-1a — zero
     template churn).
  2. Add the missing small-button variant: `.btn--sm { padding: var(--space-1) var(--space-3);
     font-size: var(--font-size-xs); }` (DESIGN §4.1).
  3. **Delete** the `.app-page-sidebar form button { … }` override block ([app.css:772-790](../../apps/core/static/core/app.css#L772))
     and replace its full-width intent with class-scoped layout rules (DESIGN §4.2):
     `.app-page-sidebar form { width: 100%; }` and `.app-page-sidebar .btn { width: 100%; }`. The
     sidebar **Follow** button then renders **primary** (not grey); the Share submit keeps its
     intended treatment. No template markup is edited in this task.
- **Dependencies:** none (prerequisite for T-02/T-03/T-04/T-07/T-08).
- **Files/areas:** `apps/core/static/core/app.css` only.
- **Definition of done:**
  - `--font-size-md`, `--space-0.5`, `--space-1.5`, `--space-2.5` resolve as defined custom
    properties; `.btn--sm` is defined as a peer of `.btn--lg`.
  - The `.app-page-sidebar form button` override is gone; the app page's Follow (when actionable)
    carries `btn--primary` and renders primary, full-width via the new layout rules.
  - Full suite green; `makemigrations --check` → no drift (no model touched).
  - **Feel (X4):** no "small" button renders full-size; intended dotted-token spacing now applies;
    the primary Follow is no longer inert/grey (verified at AC-8, structurally here).

### T-02 — Enumeration guard test `test_design_system.py`
- **Workstream / source:** W8 — DESIGN §3.4, §7, §12 (AC-1 row). Serves **AC-1**, **M1**. The
  app-page-redesign invariant-test precedent.
- **Description:** Add `apps/core/tests/test_design_system.py` (DESIGN §3.4): parse `app.css` for
  the **defined** set — every `--…:` declaration (union across the whole file, *not* only `:root`,
  per the §7 scope note) and every defined component class (`btn--*` and the known component
  classes); parse all **non-widget** templates + `app.css` for the **referenced** set — every
  `var(--…)` and every `btn--*` / known-component class — and **assert referenced ⊆ defined**.
  Make the silent-defect class unrepresentable going forward: a future template referencing an
  undefined token/class fails this test loudly. Index it in [CODEMAP.md](../../CODEMAP.md).
- **Dependencies:** T-01 (the test must pass, which requires the tokens/`btn--sm` to exist).
- **Files/areas:** `apps/core/tests/test_design_system.py` (new); `CODEMAP.md` (one line).
- **Definition of done:**
  - The test asserts `btn--sm`, `--space-0.5`, `--space-1.5`, `--space-2.5`, `--font-size-md` are
    now defined (regression anchors for T-01).
  - The test is **green** post-T-01, and is written so it **fails** if any referenced token/class
    is undefined (verify by a temporary undefined reference during development, then remove it).
  - Excludes the two firewalled widget templates from its scan (C6).
  - CODEMAP records the guard under `apps/core` shared/test surface.
  - Full suite green; no migration drift.

### T-03 — Add the bounded component/utility layer to `app.css`
- **Workstream / source:** W2 — DESIGN §3.1, §4.3 (IC-DESIGN-2, bounded-first). EXPERIENCE **X2**
  (component grammar) + system tone *Coherent*. Serves **AC-3**, **M2**.
- **Description:** Add to `app.css` the small, named utility/component layer for the patterns the
  audit shows actually repeat across surfaces (DESIGN §4.3.1): `.text-muted`, `.text-error`,
  `.page-header` (the `<h1>` + muted-lede block), `.m-0`, `.full-width`, `.toolbar` (the cluster +
  `space-between` header action-row), and the **muted-caption** treatment X2/S3 reuse. Add the
  real `.legend-swatch--dashed` class (the B7 repair target — DESIGN §4.3.2; the swatch itself is
  applied in T-04). Each class is **one documented declaration block** naming the intent it
  expresses (comment the *why* — §5.3). This task **adds the classes only**; template migration is
  T-04/T-09/T-11.
- **Dependencies:** T-01 (the classes consume the now-defined tokens).
- **Files/areas:** `apps/core/static/core/app.css` only.
- **Definition of done:**
  - Each named class exists, is token-driven, and carries an intent comment.
  - `test_design_system.py` (T-02) stays green (every new class is in the defined set; if the
    guard's known-component list is extended, that extension is part of this task).
  - **Feel (X2):** a section heading / muted caption / toolbar are now expressible once — the
    coherence backbone for AC-3. No template renders differently yet (additive CSS).
  - Full suite green; no migration drift.

### T-04 — Migrate the three worst-offender templates + fix the B7 legend swatch
- **Workstream / source:** W2 — DESIGN §4.3.2/.3. EXPERIENCE **X2** (same meaning → same
  treatment) + the B7 dashed-swatch a11y gain (S2 note). Serves **AC-3**, **M2**.
- **Description:** Migrate the recurring inline `style="…"` patterns in the three non-form worst
  offenders to the T-03 classes: **`app_reception.html`** (117 — the heaviest, includes the B7
  defect), **`app_detail.html`** (71), **`review_detail.html`** (38). In `app_reception.html`
  replace the invalid `background-dasharray` legend swatch ([app_reception.html:68](../../apps/dashboard/templates/dashboard/app_reception.html#L68))
  with the real `.legend-swatch--dashed` class so the dashed series renders (B7 → pattern + colour,
  not colour alone). Leave **genuinely one-off** inline styles and the sanctioned
  `style="--gap: …"` token idiom in place (DESIGN §4.3.3). *(submit.html's inline-style migration
  is folded into T-11 so that file is touched by exactly one task — see T-11.)*
- **Dependencies:** T-03 (classes must exist).
- **Files/areas:** `apps/dashboard/templates/dashboard/app_reception.html`,
  `app_detail.html`, `review_detail.html` (resolve exact app dirs at build), plus the
  `.legend-swatch--dashed` application. **No** view/model edits.
- **Definition of done:**
  - The three files use the T-03 classes for their recurring intents; the B7 legend swatch
    renders as a real dashed swatch.
  - Inline-`style` count across the non-widget templates drops by ≈230 from these three files,
    measured by the same grep that set the 621 baseline (final M2 ≤ 400 floor is asserted at T-12
    after T-11 also lands — DESIGN §4.3 M2 contract).
  - `test_design_system.py` green; full suite green (update any presentational assertion that
    pinned an inline style on these files); no migration drift.
  - **Feel (X2):** headings/captions/action-rows on these surfaces read identically to their peers.

### T-05 — Create the `{% icon %}` inline-SVG tag + the hand-authored set
- **Workstream / source:** W3 (shared artifact) — DESIGN §3.2, §7. EXPERIENCE **X1** (one quiet,
  brand-neutral set). Serves **AC-6a**, **M4**.
- **Description:** Add the reusable inclusion tag at `apps/core/templatetags/icons.py` and the
  hand-authored SVG partials under `apps/core/templates/core/icons/`, **mirroring the established
  `account_roles` template-tag pattern** (no-build, template-side, reusable — DESIGN §3.2, not a
  private helper). `{% icon "<name>" %}` renders `<svg aria-hidden="true" focusable="false">…</svg>`.
  Author the set covering the 16 decorative glyphs the audit found (empty-state `🔍 📦 📸 🏷️ 📰 📤
  📢 📈 ✉ ⚙`, status `✅ ⚠`, arrows `← → ↗`, rating `★`) as **brand-neutral, uniform-stroke,
  uniform-optical-size** SVGs (X1 — *quiet*, muted role; **not** the distinctive `ui-modernization`
  style, IC-D-1). Unknown name → `TemplateDoesNotExist` (fail loud in dev, DESIGN §7). Index the
  tag in [CODEMAP.md](../../CODEMAP.md).
- **Dependencies:** none (independent of T-01).
- **Files/areas:** `apps/core/templatetags/icons.py` (new), `apps/core/templates/core/icons/*.svg`
  (new set), `CODEMAP.md` (one line). No template *consumers* edited here.
- **Definition of done:**
  - `{% icon "search" %}` (and each named icon) renders an `aria-hidden="true" focusable="false"`
    inline SVG; an unknown name raises `TemplateDoesNotExist` (a small unit test asserts both).
  - The set is visually one family (uniform weight/optical size), brand-neutral (no rebrand).
  - CODEMAP records the tag; full suite green; no migration drift.
  - **Feel (X1):** icons are decorative (not announced); the adjacent visible text still carries
    the meaning.

### T-06 — Replace decorative emoji with `{% icon %}` across non-widget templates
- **Workstream / source:** W3 — DESIGN §2 (W3), §12 (AC-6 row). EXPERIENCE **X1**. Serves
  **AC-6a**, **M4**.
- **Description:** Replace the decorative emoji across the ~14 non-widget templates (empty states,
  status indicators, arrows, the rating star) with the matching `{% icon %}` call. The adjacent
  visible text already carries the meaning, so removing the glyph loses no information (DESIGN
  §3.2). **Status icons must remain paired with semantic colour *and* text** (never icon/colour
  alone — X1). Do **not** touch the two widget templates (C6).
- **Dependencies:** T-05 (the tag + set must exist).
- **Files/areas:** the ~14 non-widget templates carrying decorative emoji (empty-state/status/arrow/
  star). Resolve the exact list by the audit grep. No view/model edits.
- **Definition of done:**
  - A grep for the decorative emoji set across non-widget templates returns **0** (AC-6a / M4).
  - Every replaced icon renders `aria-hidden` (via the tag); status indicators still pair icon +
    colour + text.
  - `test_design_system.py` green; full suite green; no migration drift.
  - **Feel (X1):** every empty state shares one icon look (consistent weight/optical size); no
    per-OS emoji remains where a person looks.

### T-07 — App page: mobile Try reflow + facet legibility + Share copy affordance
- **Workstream / source:** W4 — DESIGN §1 (the source-order invariant), §4.4, §4.5 (IC-DESIGN-7).
  EXPERIENCE **S1** (full 13-pillar block) + **X4**. Serves **AC-4**, **AC-6b**, **AC-6d**,
  **M5**; carries the **IC-EXP-2** focus-order trade-off.
- **Description:** Three presentational changes on the app page:
  1. **Mobile Try reflow (AC-4):** in `app.css`, make `.app-page` a flex column below the 900px
     breakpoint and reorder its three direct children by **CSS `order:` only** (DESIGN §4.4):
     `@media (max-width: 899.98px) { .app-page { display:flex; flex-direction:column; }
     .app-page-sidebar { order:-1; } .app-page-reviews { order:1; } }`. **Source DOM order is
     untouched** — the `_slots()` fingerprint + firewall invariants stay byte-identical (the gate).
     Style the lifted action region per **S1**: a **compact action bar** (one band, not a tall
     stack of full-width cards), one dominant focal point = **Try**, emphasis order **Try › Follow
     (restored primary, never grey) › Share (quiet)**, the curated-rating read kept compact with
     the actions, identity hero immediately after. ≥900px keeps the two-column sticky-sidebar
     layout (S1 pillar 12).
  2. **Facet legibility (AC-6b):** in [`app_page.html`](../../apps/pages/templates/pages/app_page.html#L42)
     replace `title="{{ facet.label }}"` with a **visible** category caption
     `<span class="facet__cat">{{ facet.label }}</span> {{ value.label }}` + a `.facet__cat` rule
     (DESIGN §4.5). The category is **static text, must not look interactive** (S1 pillar 5).
  3. **Share feedback (AC-6d, no server change — C4):** reframe the slot so the already-present
     readonly link input is the primary "Copy link" affordance, with a **pure-PE** copy button
     (`navigator.clipboard`, small inline script) and an `aria-live` "**Copied!**" confirmation
     whose meaning does not depend on motion (S1 pillars 6/8). **No-JS path:** the link stays
     selectable/readable and the existing Share POST is byte-unchanged (DESIGN §4.5 / IC-DESIGN-7).
  Update the app-page-redesign **FacetTests** value-string assertions (e.g. `assertIn(">Free<")`)
  to the new facet markup (DESIGN §4.5 / §12) — a presentational test update only.
- **Dependencies:** T-01 (Follow primary fix + tokens).
- **Files/areas:** `apps/core/static/core/app.css` (reflow block, `.facet__cat`, action-bar
  layout), `apps/pages/templates/pages/app_page.html` (facet markup, Share slot + PE script). The
  FacetTests file in the app-page test suite. **No** view/URL/model edit (the Share POST is
  untouched).
- **Definition of done:**
  - `pages/tests/test_template.py` fingerprint + `catalog/tests/test_redesign_invariants.py` stay
    **green unchanged** (proves DOM source order intact — AC-4/M5/C1).
  - A CSS-presence assertion for the `max-width:899.98px` reflow block exists.
  - Facet category renders as visible text (not `title`); a test asserts the category string is in
    the rendered body without hover. Updated FacetTests pass.
  - Share: the readable link is present and selectable with **JS off**; the copy button + `aria-live`
    "Copied!" appear only when `navigator.clipboard` exists; the server Share action is unchanged.
  - `test_design_system.py` green; full suite green; no migration drift.
  - **Feel (S1 sign-off items, verified at AC-8):** Try visible within the first screen/one short
    scroll; the panel reads as one compact action bar with Try dominant + Follow actionable (not
    grey) + Share quiet; identity reached immediately after; facet categories readable without
    hover; visible "Copied!" confirmation. **Keyboard/SR focus order stays logical** (identity →
    actions → reviews) despite the visual reflow (IC-EXP-2).

### T-08 — Developer hub: `_dev_tabs` partial + nav active-state + relabel both homes
- **Workstream / source:** W5 — DESIGN §3.3, §4.6. EXPERIENCE **S2** (full block) + **X3**
  (wayfinding/active-state). Serves **AC-5**; resolves the two-"My Apps" confusion.
- **Description:**
  1. Add `apps/core/templates/core/_dev_tabs.html` (DESIGN §3.3): a two-tab bar **Manage** →
     `{% url 'catalog:my-apps' %}`, **Analytics** → `{% url 'dashboard:my-apps' %}`; the including
     page passes `active_tab="manage"|"analytics"`; the active tab gets `aria-current="page"` +
     `.active`. Add a `.tab` / `.tab.active` pair to `app.css` **reusing the existing
     `.sidebar-link.active` accent treatment family** (X3/S2 pillar 5/9 — reuse, not a new accent).
  2. `{% include %}` the partial in `catalog/my_apps.html` (**Manage**, `active_tab="manage"`) and
     `dashboard/my_apps.html` (**Analytics**, `active_tab="analytics"`), **replacing** the
     dashboard's ad-hoc inline `Analytics/Submissions` sub-nav. Align each page's `<h1>`/title to
     "Manage" / "Analytics".
  3. In `base.html`, change the developer-gated entry label **"My Apps" → "Developer"**, pointing
     at the Manage tab (`catalog:my-apps`) as the hub default — **one** entry, not two — and add
     the global-nav current-section active state (`aria-current` + the accent treatment) called for
     by A6/X3. The entry stays behind the existing `{% is_developer %}` gate (presentation mirror,
     not the security boundary — DESIGN §6).
- **Dependencies:** T-01 (the `.tab` rules use tokens).
- **Files/areas:** `apps/core/templates/core/_dev_tabs.html` (new), `apps/core/static/core/app.css`
  (`.tab` pair + nav active state), `apps/core/templates/core/base.html`,
  `apps/catalog/templates/catalog/my_apps.html`, `apps/dashboard/templates/dashboard/my_apps.html`.
  **No** new route/view — tabs are `<a>` to the two existing URLs.
- **Definition of done:**
  - Both surfaces render `_dev_tabs.html`; the active tab carries `aria-current="page"` + `.active`;
    the inactive tab is a link to the other existing URL.
  - The header shows **exactly one** "Developer" entry (no second "My Apps"); the current nav
    section shows an active state.
  - Existing developer-nav tests are updated to the new label and pass; full suite green; no
    migration drift; `test_design_system.py` green.
  - Empty Manage / empty Analytics use the shared empty-state treatment (icon + title + next-action
    — S2 pillar 13 / X1).
  - **Feel (S2/X3 sign-off, verified at AC-8):** the two tabs read as one segmented control with
    the current one unmistakably indicated; "active" signalled by **more than colour** (semantics +
    weight + accent tint); the tab bar stays horizontal and visible on mobile.

### T-09 — Discover: ordering-basis caption
- **Workstream / source:** W6 — DESIGN §4.7 (IC-DESIGN-8). EXPERIENCE **S3** (full block). Serves
  **AC-7**.
- **Description:** In `discovery/templates/discovery/catalogue.html` add a presentational
  `.text-muted` caption by the results count stating the basis — **"Ranked by merit, never by
  spend"** (matches the footer/vision voice). **No sort control, no query param, no change to
  `search_catalogue`** (AC-7 / C4 — the catalog primitive is untouched). The caption is **static
  informational text and must not look interactive** (S3 pillar 5). **Suppress it on the
  zero-results state** (S3 pillar 13 — nothing to order; the empty state carries the message).
- **Dependencies:** T-03 (reuses the muted-caption treatment).
- **Files/areas:** `apps/discovery/templates/discovery/catalogue.html` only.
- **Definition of done:**
  - The results state contains the ordering-basis caption; **no** sort control/param is added (a
    test asserts the caption text is present and that the rendered page has no new `<select>`/sort
    form).
  - The caption is **absent** on the zero-results render.
  - `test_design_system.py` green; full suite green; no migration drift.
  - **Feel (S3 sign-off, AC-8):** Discover plainly states results are ranked by merit as an
    informational line — not a clickable control implying a sort that doesn't exist.

### T-10 — Interests picker: dedupe → no-JS consistency (confirm OQ-IC-8)
- **Workstream / source:** W7 — DESIGN §4.8 (IC-DESIGN-9), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
  **OQ-IC-8**. EXPERIENCE **S4** (full block). Serves **AC-6c**, **US-7**.
- **Description:** Make the picker consistent **without JavaScript** by rendering **each interest
  tag at most once** and **deleting** the JS sync `<script>` ([picker.html:86-99](../../apps/interests/templates/interests/picker.html#L86)).
  **Confirm OQ-IC-8 first (the C2 gate):**
  - If the dedupe can be done by **regrouping data already in the template context**, it is purely
    presentational → do it (in-envelope).
  - If it needs a **minimal reshape of the view's `clusters` context**, that is the **single
    deliberate view-layer touch** of this feature — **permitted only** if it changes **no URL, no
    saved-state contract, and no schema** (it does not). Record the confirmation in
    [DECISIONS.md](DECISIONS.md) (close OQ-IC-8) and note the touch in the session status.
  - **Fallback** (if the view touch is judged out-of-envelope at build): keep the JS sync and
    document that the *saved* state is already no-JS-correct (the server recomputes `item.checked`
    from declared tags on reload); mark the picker item partially-addressed. No regression either
    way.
- **Dependencies:** T-03 (the `.form-field` idiom — applied to the picker's controls in T-11's
  shared rule; the dedupe itself is independent but sequenced after the layer exists).
- **Files/areas:** `apps/interests/templates/interests/picker.html` (dedupe + delete `<script>`);
  **only if OQ-IC-8 is confirmed in-envelope:** the interests view's `clusters` context shaping
  (no URL/schema/saved-state change). No model/migration.
- **Definition of done:**
  - The rendered picker contains **no duplicate control for the same tag id** and **no `<script>`
    sync** (a test asserts both) — **or** the documented fallback is in place with a note.
  - **No-JS path:** with JS off, selecting/saving keeps state consistent; the server recompute of
    `item.checked` is preserved.
  - OQ-IC-8 is **explicitly resolved** in DECISIONS.md (which branch was taken + why); no URL/
    schema/saved-state contract changed; `makemigrations --check` → no drift.
  - `test_design_system.py` green; full suite green.
  - **Feel (S4 sign-off, AC-8/US-7):** with JS off the picker stays consistent; each tag is one
    labelled control; selected vs unselected distinct by more than colour.

### T-11 — Form-field idiom (auth/submit) + submit required/optional grouping
- **Workstream / source:** W7 — DESIGN §4.8 (OQ-IC-7 resolution, B3). EXPERIENCE **S5** (full
  block) + **X2**. Serves **AC-3** (submit's share of M2), **US-1**, and the long-form B3 intent.
- **Description:**
  1. **Form-field idiom (presentational only — C4):** add a shared `.form-field` structure/spacing
     class to `app.css` (the X2 form grammar) and apply it so the auth pages (Django-widget
     rendered) and `submit.html` (hand-rolled inputs) share **one** field idiom (DESIGN §4.8). **No
     form/validation/field change** — if unifying would alter a widget's behaviour, that field is
     left as-is.
  2. **Submit grouping (B3 / S5):** in `submit.html` add a lighter-touch **required-vs-optional**
     visual grouping (a `<fieldset>` / section heading + the existing `.card` rhythm) so the long
     form reads as chunks; **promote `demo_clip_alt`'s "required-if-clip" hint from a placeholder to
     a persistent visible field note** (S5 pillar 5 — a placeholder is the wrong affordance for a
     conditional requirement). Required vs optional signalled **in text/markup, not colour alone**.
  3. **Fold in submit.html's inline-style migration** (the 43 inline styles, the fourth worst
     offender — DESIGN §4.3.2) here, since this is the only task touching `submit.html` (avoids a
     two-task collision on one file). Migrate its recurring inline intents to the T-03 + `.form-field`
     classes; leave genuinely one-off styles.
- **Dependencies:** T-03 (component layer; `.form-field` is added here as the form-grammar member).
- **Files/areas:** `apps/core/static/core/app.css` (`.form-field` + any submit-section rhythm
  class), the auth templates (signin/register), `submit.html` (resolve exact app dir). **No** form
  class / validation / view edit.
- **Definition of done:**
  - Auth + submit share the `.form-field` idiom (same structure/spacing); no form/field/validation
    behaviour changed (the form classes and view are untouched — assert no diff there).
  - Submit shows a required group then an optional group via headings + card rhythm; the
    `demo_clip_alt` note is a **persistent visible field note** (not a placeholder).
  - submit.html's inline-`style` count is materially reduced; **combined with T-04 the non-widget
    inline-`style` total is ≤ 400** (the M2 floor — asserted at T-12).
  - `test_design_system.py` green; full suite green; no migration drift.
  - **Feel (S5 sign-off, AC-8):** the form reads as scannable chunks (required first, optional set
    apart); the clip-alt requirement is visible before submit.

### T-12 — Final gate: full suite + render-every-surface + no-drift + AC-8 sign-off carry
- **Workstream / source:** W8 — DESIGN §11, §12 (AC-8/AC-9 rows). EXPERIENCE **§4 sign-off
  checklist**. Serves **AC-3 (M2 floor)**, **AC-8**, **AC-9**, **M3/M5/M6**.
- **Description:** The release-readiness gate after T-01…T-11. Run and record:
  - Full suite **green**; the platform-staging **render-every-surface** check (M3) — every
    non-widget surface still renders.
  - `makemigrations --check` → **no drift**; an audit that **no `views.py` / `urls.py` / model /
    serializer changed** except the single OQ-IC-8 picker-context touch **if** it was confirmed in
    T-10 (AC-9 / C2/C4).
  - The **M2 floor**: a grep over non-widget templates shows inline-`style` ≤ **400** (from 621).
  - The app-page **uniformity + M5=0 firewall** invariants green unchanged (M5).
  - **Carry the EXPERIENCE §4 yes/no sign-off checklist into RELEASE_NOTES** as the AC-8 human gate
    (web + mobile), the premium-frontend PS-3 precedent — this stage does **not** self-sign AC-8;
    it stages the checklist for the user.
- **Dependencies:** all of T-01…T-11.
- **Files/areas:** no production code; `RELEASE_NOTES.md` (stage the AC-8 checklist + the
  no-drift/no-API-change attestation). CI/test invocation only.
- **Definition of done:**
  - Suite green; render-every-surface passes; `makemigrations --check` clean; inline-`style` ≤ 400;
    app-page invariants green.
  - The AC-9 attestation (no view/URL/model/ADR change beyond the gated OQ-IC-8 touch) is written.
  - The EXPERIENCE §4 sign-off checklist is carried into RELEASE_NOTES for the user's AC-8 web +
    mobile review (M6). **AC-8 is not marked done by the agent** — it is the release gate handed to
    the user.

---

## Coverage map (every DESIGN element + EXPERIENCE surface → ≥1 task)

| DESIGN / EXPERIENCE element | Task(s) |
|---|---|
| W1 tokens + `btn--sm` + Follow/Share demotion (AC-1/AC-2) | T-01 |
| W2 component/utility layer (AC-3) | T-03 (add) + T-04, T-11 (migrate) |
| W3 `{% icon %}` tag + emoji replacement (AC-6a) | T-05 (tag) + T-06 (replace) |
| W4 app-page reflow / facet / Share (AC-4/AC-6b/AC-6d/M5) | T-07 |
| W5 developer hub (AC-5) | T-08 |
| W6 discover ordering caption (AC-7) | T-09 |
| W7 picker no-JS (AC-6c) + form idiom + submit grouping (OQ-IC-8) | T-10 (picker) + T-11 (forms) |
| W8 enumeration guard (AC-1/M1) | T-02 |
| W8 render-every-surface / no-drift / suite / AC-8 carry (AC-9/M3/M6) | T-12 |
| EXPERIENCE S1 (app-page action bar) | T-07 |
| EXPERIENCE S2 (developer hub tabs) | T-08 |
| EXPERIENCE S3 (discover caption) | T-09 |
| EXPERIENCE S4 (picker dedupe) | T-10 |
| EXPERIENCE S5 (submit grouping) | T-11 |
| EXPERIENCE X1 (iconography) | T-05, T-06 |
| EXPERIENCE X2 (component grammar) | T-03, T-04, T-11 |
| EXPERIENCE X3 (wayfinding/active-state) | T-08 |
| EXPERIENCE X4 (defect-repair feel) | T-01, T-07 |
| EXPERIENCE §4 AC-8 sign-off checklist | carried by every UI task; staged at T-12 |
| IC-EXP-2 focus-order trade-off | T-07 (DoD) |
| OQ-IC-8 picker view-context confirmation | T-10 (gated) |

**Exit-criteria check:** ✅ every DESIGN element + EXPERIENCE surface maps to ≥1 task. ✅ no task
lacks a concrete definition of done. ✅ no `L` task remains (all S/M). ✅ shared artifacts (icon
tag T-05, component layer T-03, `_dev_tabs` T-08, enumeration guard T-02, `.form-field` T-11) get
their own placement before/with their consumers — none folded into a consumer as an in-file helper.

---

## Hand-off
Task list complete and covering DESIGN + EXPERIENCE. Set `Stage: 4-build`, persona = **Senior
Engineer** ([phase-4-engineer.md](../../process/personas/phase-4-engineer.md)). Build in ID order;
T-01 first (prerequisite), T-02 immediately after (the guard closes the defect class before new CSS
lands), T-12 last (the gate). The OQ-IC-8 confirmation is the engineer's call at T-10 under the C2
gate — record the branch taken in [DECISIONS.md](DECISIONS.md). AC-8 is the **user's** release gate
(EXPERIENCE §4 checklist, web + mobile) — never self-signed.
