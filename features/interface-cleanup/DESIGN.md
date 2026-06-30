# DESIGN.md — interface-cleanup

*Stage 2 (Software Architect). Inputs read: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (approved,
DN-IC-BRIEF), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md), [DECISIONS.md](DECISIONS.md)
(IC-D-1/2/3), the live design system [`core/app.css`](../../apps/core/static/core/app.css)
+ shell [`core/base.html`](../../apps/core/templates/core/base.html), the 33 templates audited,
the app-page invariants ([test_template.py](../../apps/pages/tests/test_template.py),
[test_redesign_invariants.py](../../apps/catalog/tests/test_redesign_invariants.py)),
[CODEMAP.md](../../CODEMAP.md), and the global [DECISIONS.md](../../DECISIONS.md) (D-4 / D-13).*

> **`2b-ux` routing gate: USER-FACING.** Every workstream below changes a screen a person
> sees. After this stage the feature routes to the **Experience Designer (`2b-ux`)** to own the
> *feel* of the reflowed app page, the developer hub tabs, and the consolidated component set,
> then to the Planner. See **Hand-off**.

---

## 0. Protocol trace (14-step, condensed)

1. **SCOPE.** Make the existing design system the actual single source of truth and clean up
   accumulated UI/UX inconsistency, silent defects, and per-surface rough edges across every
   non-widget surface — *presentation only*, no schema/API/business-logic/ADR change. Lifespan:
   **platform** (the design system is inherited by every future feature). OUT: the distinctive
   rebrand (`ui-modernization`, IC-D-1); dark mode; any new product behaviour.
2. **REQUIREMENTS.** Functional = AC-1…AC-9. Non-functional = no-build server-rendered CSS
   (D-4/D-13), no-JS path is the source of truth, a11y is first-class, the app-page
   uniformity/firewall invariants stay green, full suite green + no migration drift. **All brief
   findings verified against live code this session** (see §1) — the assumption ledger is now
   evidence, not claim.
3. **CONTEXT.** One stylesheet ([`core/app.css`](../../apps/core/static/core/app.css), 825 lines,
   token-driven) inherited by 6 app `base.html` via the shared shell. 33 templates (2 are the
   firewalled widget — untouched). The `{% is_developer %}` role tag
   ([account_roles](../../apps/accounts/templatetags/account_roles.py)) is the established
   no-build template-tag precedent to mirror for the new `{% icon %}` tag. Reuse-first throughout.
4–14. Modules §3; interfaces §4–§6; data/state — **none changes** (this feature owns no model,
   no migration); failure modes §7; change/irreversibility §8; trade-offs/alternatives §9;
   security §10; operations/rollback §11; tests §12; self-critique §13; deliver/decisions §14
   (recorded as IC-DESIGN-1…9 in [DECISIONS.md](DECISIONS.md)).

---

## 1. Current-state summary (verified this session)

| Finding | Evidence (live) | Status |
|---|---|---|
| `btn--sm` undefined | used in **12 files**; **not defined** in `app.css` — "small" buttons render full size | confirmed |
| `--space-0.5` (3), `--space-1.5` (29), `--space-2.5` (5) undefined | referenced across templates; **absent from `:root`** (scale is `--space-1…8`) → `gap`/`padding` collapse to the CSS-invalid-value fallback | confirmed |
| `--font-size-md` (4) undefined | dashboard headings; **absent from `:root`** (scale has no `-md`) | confirmed |
| Follow/Share primary demotion | [`app.css:772`](../../apps/core/static/core/app.css#L772) `.app-page-sidebar form button` (specificity 0,2,1) overrides `.btn--primary` (0,1,0) → the sidebar **Follow** primary button renders grey/secondary; the **Share** submit is forced full-width grey | confirmed |
| ~621 inline `style="`; worst offenders | 621 total across 31 non-widget templates; top: `app_reception.html` (117), `app_detail.html` (71), `submit.html` (43), `review_detail.html` (38) | confirmed |
| Decorative emoji as iconography | **16 distinct glyphs** across ~14 templates (empty-state `🔍 📦 📸 🏷️ 📰 📤 📢 📈 ✉ ⚙`, status `✅ ⚠`, arrows `← → ↗`, rating `★`); none `aria-hidden` | confirmed |
| App-page **Try** buried on mobile | sidebar (slot 6) renders after main slots 1–5 in source; single-column mobile → Try ~5–6 sections down | confirmed |
| Two developer homes both "My Apps" | header → `catalog:my-apps` labelled "My Apps"; `dashboard:my-apps` is analytics with an inline "Analytics/Submissions" sub-nav | confirmed |
| Facet category only in hover `title` | [`app_page.html:42`](../../apps/pages/templates/pages/app_page.html#L42) `<li class="badge facet" title="{{ facet.label }}">` | confirmed |
| Share = POST then silent reload | [`app_page.html:133-145`](../../apps/pages/templates/pages/app_page.html#L133) — POST to `pages:share`, no feedback; a **readonly link input already exists** (the "way to obtain the link" half is present) | confirmed |
| Discover never states ordering | [`catalogue.html`](../../apps/discovery/templates/discovery/catalogue.html) shows "N results" with no ordering basis | confirmed |
| Picker syncs duplicate tags via JS only | [`picker.html:86-99`](../../apps/interests/templates/interests/picker.html#L86) `<script>` syncs same-value checkboxes; no-JS users see unsynced pre-submit state | confirmed |
| `background-dasharray` non-property | [`app_reception.html:68`](../../apps/dashboard/templates/dashboard/app_reception.html#L68) — invalid CSS prop; legend swatch silently blank | confirmed |
| Nav has no active state | [`base.html:17-46`](../../apps/core/templates/core/base.html#L17) — no `aria-current`/`.active` on the current link | confirmed |

**Load-bearing invariant to preserve.** [`pages/tests/test_template.py:77-79`](../../apps/pages/tests/test_template.py#L77)
computes the fingerprint by regex over the rendered HTML **source order** of `data-slot="…"`.
**CSS `order:`/visual reflow does not change source order → the fingerprint test stays green.**
This is the mechanism that lets W4 move the Try CTA without touching uniformity (IC-D-3/C1).

---

## 2. Architecture overview — eight workstreams, one envelope

The feature is **presentation-only** and owns **no data model, no migration, no new URL, no new
view, no public-API change** (C2/C4; confirms IC-D-2's "patch envelope as a constraint"). It adds
exactly **two reusable code artifacts** — the `{% icon %}` tag and the design-system enumeration
guard — and otherwise edits CSS + templates. Work is decomposed into eight independently-shippable
workstreams so the build stays releasable after each (mirrors the app-page-redesign task model).

```
W1  Token & defect repair (app.css)         → AC-1, AC-2, M1     [system-wide, no template edits except defect removal]
W2  Bounded presentational consolidation     → AC-3, M2           [app.css component/utility layer + worst-offender migration]
W3  Iconography: {% icon %} inline-SVG set    → AC-6a, M4          [new reusable tag + sprite; replace decorative emoji]
W4  App-page: mobile-Try reflow, facet
    legibility, Share feedback                → AC-4, AC-6b/d      [app.css order reflow + app_page.html presentational]
W5  Developer hub (Manage|Analytics tabs)     → AC-5              [shared tab partial + base.html nav + active state, A6]
W6  Discover ordering-basis label             → AC-7              [catalogue.html presentational label]
W7  Picker no-JS + form-idiom + submit group  → AC-6c            [picker dedupe, field idiom, submit grouping]
W8  Guardrails: enumeration check + render-
    every-surface + invariants + no-drift     → AC-1, AC-9, M3/M5 [new test_design_system.py + CI of existing suites]
```

Coupling is low: W1 is a prerequisite for the others (tokens must exist before consolidation), but
W2–W7 are mutually independent template edits; W8 is the gate. Each is replaceable/deletable in
isolation (design-for-deletion: revert a workstream's CSS block + its template edits; nothing else
depends on it).

---

## 3. Modules / components (what each owns, exposes, hides)

### 3.1 `core/app.css` — the design system (modified, not replaced)
- **Owns:** every token (`:root`), component class (`btn--*`, `.card`, `.badge`, …), utility,
  breakpoint. **Single source of truth for presentation** (the whole point — §5.1/§5.3).
- **W1 adds** the missing tokens and `btn--sm`; **removes** the `.app-page-sidebar form button`
  override (replaced by a layout class — §4.2).
- **W2 adds** a bounded utility/component layer (§4.3) covering the top recurring inline patterns.
- **W4 adds** the mobile app-page `order:` reflow + a `.facet` category-label rule.
- Hides: nothing — CSS is declarative and inspectable; that is the point.

### 3.2 `{% icon "<name>" %}` — new reusable inclusion tag (W3)
- **Home:** `apps/core/templatetags/icons.py` + a hand-authored SVG set in
  `apps/core/templates/core/icons/`. **Indexed in [CODEMAP.md](../../CODEMAP.md).**
- **Mirrors** the established `account_roles` tag pattern (no-build, template-side, reusable) —
  not a private helper inside one consumer (§5.3 "a home, not a host file").
- **Owns:** the canonical inline-SVG for each named icon; renders `<svg aria-hidden="true"
  focusable="false">…</svg>`. **Exposes:** `{% icon "search" %}` → consistent, brand-neutral,
  cross-OS-stable, accessible (decorative → not announced). **Hides:** the SVG path data.
- Replaces decorative emoji; the **adjacent visible text already carries the meaning** in every
  empty-state, so removing the emoji loses no information.

### 3.3 `core/_dev_tabs.html` — shared developer-hub tab bar (new partial, W5)
- **Home:** `apps/core/templates/core/_dev_tabs.html`, `{% include %}`d by both developer
  surfaces (`catalog/my_apps.html` = **Manage**, `dashboard/my_apps.html` = **Analytics**).
- **Owns:** the two-tab nav (`Manage` ↔ `Analytics`) and the current-tab indicator
  (`aria-current="page"` + `.active`). **Takes** one context flag (`active_tab`) the including
  template sets. No new route, no view logic — the tabs are two `<a>` to the **existing** URLs.
- Single source of truth for the hub IA — replaces today's ad-hoc inline sub-nav in
  `dashboard/my_apps.html`.

### 3.4 `apps/core/tests/test_design_system.py` — the enumeration guard (new, W8)
- **Owns** the structural proof of AC-1/M1: parse `app.css` for every defined token (`--…`) and
  component class, parse all templates for every referenced token (`var(--…)`) and `btn--*`/known
  component class, and **assert referenced ⊆ defined**. Makes the silent-defect class
  **unrepresentable going forward** (the app-page-redesign invariant-test precedent). Indexed in
  CODEMAP. Failure mode: a future template that references an undefined token fails CI loudly.

No other module is created. W2/W4/W6/W7 are template + CSS edits to existing files.

---

## 4. Interface contracts (no "TBD")

### 4.1 W1 — token additions (`:root`)
Add, with values chosen to fit the existing scale (`--space-1`=0.25rem … `--space-8`=3rem):
```
--font-size-md: 1rem;   /* sits between -base and -lg; matches dashboard heading intent */
--space-0.5: 0.125rem;  --space-1.5: 0.375rem;  --space-2.5: 0.625rem;
```
**Naming decision (IC-DESIGN-1a).** The templates already *use* `--space-1.5` etc. Two options,
resolved in favour of (b):
- **(a)** rename every reference to a dot-free name (`--space-1-5`) — touches ~37 reference sites.
- **(b) define the dotted names** in `:root`. A `.` is a legal character in a CSS custom-property
  name, so `var(--space-1.5)` resolves exactly as written today. **Chosen:** zero template churn,
  the templates' existing intent simply starts working. The enumeration guard (§3.4) then treats
  them as first-class defined tokens.

`btn--sm` definition (the missing small variant, peer of the existing `.btn--lg`):
```
.btn--sm { padding: var(--space-1) var(--space-3); font-size: var(--font-size-xs); }
```

### 4.2 W1 — Follow/Share specificity fix (the demotion)
Delete the `.app-page-sidebar form button { … }` block ([app.css:772-790](../../apps/core/static/core/app.css#L772)).
It exists only to make sidebar form buttons full-width grey — a goal now better served by the
buttons' **own** classes. Contract after the fix:
- The sidebar **Follow** button keeps `class="btn btn--primary"` → renders **primary** (no longer
  overridden). Full-width is delivered by a layout rule on the slot, not a button override:
  `.app-page-sidebar form { width: 100%; } .app-page-sidebar .btn { width: 100%; }` (class-scoped,
  wins by treatment, not by re-colouring).
- **Share** submit keeps its intended treatment (`btn--secondary`, §4.5).
- **Invariant:** `_follow_slot.html` / `_reviews_slot.html` / `app_page.html` markup is unchanged
  except where W4 touches Share — so the ratings/subscriptions slot tests stay green.

### 4.3 W2 — bounded consolidation contract (resolves OQ-IC-1)
**IC-DESIGN-2: bounded-first, not full extraction** (holds R1; the brief's recommended path).
The build does **not** rewrite all 31 templates. It:
1. Adds a small, named **utility/component layer** to `app.css` for the patterns that actually
   repeat across surfaces (evidence-driven from the audit): `.text-muted`, `.text-error`,
   `.page-header` (the `<h1>` + muted lede block seen on discover/picker/profile/submit/my-apps),
   `.m-0` / `.full-width`, and a `.toolbar` (the `cluster` + `justify-content: space-between`
   header row). Each is one declaration block, documented with the intent it names.
2. **Migrates the four worst-offender files** (`app_reception.html` 117, `app_detail.html` 71,
   `submit.html` 43, `review_detail.html` 38 = ~270 of 621) plus any inline style that is a
   *defect carrier* (e.g. the `background-dasharray` swatch → a real `.legend-swatch--dashed`
   class, fixing B7).
3. Leaves **genuinely one-off** inline styles (a single bespoke `margin`, the `style="--gap: …"`
   idiom — which *is* the sanctioned design-system mechanism, not a violation) in place.
- **M2 target (contract):** reduce inline `style="` from **621 to ≤ 400** (a ≥ 35% cut concentrated
  in the worst offenders), measured by the same grep that set the baseline. The remainder is
  reviewed as "genuinely one-off" at AC-3 sign-off. The Planner may tighten the number; it must not
  loosen below this floor.

### 4.4 W4 — app-page mobile Try reflow (resolves OQ-IC-3; preserves C1/AC-4)
- **Mechanism:** make `.app-page` a flex container whose **three direct children** (`.app-page-main`,
  `.app-page-sidebar`, `.app-page-reviews`) are reordered **by CSS `order:` only**, below the
  `900px` breakpoint:
  ```
  @media (max-width: 899.98px) {
    .app-page { display: flex; flex-direction: column; }
    .app-page-sidebar  { order: -1; }   /* Try + Follow + Share rise to the top */
    .app-page-reviews  { order: 1; }    /* reviews stay last */
  }
  ```
- **Source DOM order is unchanged** → `_slots()` (regex over source) is byte-identical → the
  uniformity fingerprint + firewall invariants stay green (the gate). Applied **identically to
  every app** → fairness-neutral (IC-D-3).
- **Tradeoff (recorded):** the whole action panel (Try/Follow/Share) rises above the hero on
  mobile, rather than hero-then-Try. This is the only pure-CSS option that preserves source order
  (the hero lives inside `.app-page-main`; `order:` cannot interleave across containers). **The
  exact visual treatment of this action panel is handed to the Experience Designer (`2b-ux`)** —
  this design fixes the *mechanism* (Try reachable near the top, invariant preserved); the *feel*
  is theirs.

### 4.5 W4 — facet legibility + Share feedback
- **Facet category without hover (AC-6b):** replace `title="{{ facet.label }}"` with a **visible**
  category caption inside the badge: `<li class="badge facet"><span class="facet__cat">{{ facet.label }}</span> {{ value.label }}</li>`,
  with `.facet__cat { font-weight: var(--font-weight-semibold); margin-right: var(--space-1); }`.
  The category is now conveyed to touch/keyboard/screen-reader. *(This changes the facet markup, so
  the app-page-redesign `FacetTests` value-string assertions `assertIn(">Free<")` get updated to the
  new markup — a presentational test update; the uniformity/firewall invariants untouched; §12.)*
- **Share feedback without behaviour change (AC-6d; resolves OQ-IC-5 within C4):** the server-side
  Share action is **byte-unchanged** (no view edit). The slot is reframed so the **already-present
  readonly link input** is the primary "obtain the link" affordance, labelled "Copy link", with a
  **pure progressive-enhancement copy button** (`navigator.clipboard`, small inline script, an
  `aria-live` "Copied!" confirmation). **No-JS path:** the link is selectable/readable exactly as
  today; the existing "Share" POST keeps recording its signal and reloading. **Decision
  (IC-DESIGN-7):** giving the *POST itself* a flash confirmation would require a view change → out
  of envelope (C4) → **not done**; the copy affordance supplies the feedback instead.

### 4.6 W5 — developer hub contract (the user's chosen IA)
- **`core/_dev_tabs.html`** renders: `Manage` → `{% url 'catalog:my-apps' %}`, `Analytics` →
  `{% url 'dashboard:my-apps' %}`; the including page passes `active_tab="manage"|"analytics"`;
  the active one gets `aria-current="page"` + `.active` (a new `.tab`/`.tab.active` pair in
  `app.css`, reusing the `.sidebar-link.active` treatment family).
- **Header (`base.html`):** the developer-gated entry changes label **"My Apps" → "Developer"** and
  points at the Manage tab (`catalog:my-apps`) as the hub's default. One entry, not two.
- **No new route/view** — the tabs are links to the two existing URLs; `dashboard/my_apps.html`'s
  current inline `Analytics/Submissions` sub-nav is **replaced** by the shared partial (relabelled
  Submissions→Manage). Page `<h1>`s/titles align to "Manage" / "Analytics".

### 4.7 W6 — Discover ordering label (resolves OQ-IC-6 = label only, no control)
Add a presentational caption by the results count: a `.text-muted` line stating the basis —
**"Ranked by merit, never by spend"** (matches the footer/vision copy). **No sort control, no query
param, no change to `search_catalogue`** — the catalog primitive is untouched (C4; the template's
"never reorders" property stays true). Rendered on the results state.

### 4.8 W7 — picker no-JS, form idiom, submit grouping
- **Picker (AC-6c; IC-DESIGN-9):** render **each tag at most once**, removing the duplicate
  checkboxes entirely → the JS sync `<script>` is **deleted**, and the no-JS path is inherently
  consistent. **C4 boundary, surfaced honestly:** pure CSS cannot sync two checkboxes, so the
  correct fix de-duplicates the rendered rows; if that can be done by re-grouping data **already in
  the template context** it is presentational; if it needs reshaping the view's `clusters` context
  it is a **minimal, endpoint/schema-neutral view-context touch** — the single deliberate
  view-layer change in this feature, **flagged for Planner/build confirmation under the C2 gate**
  (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-IC-8). If confirmation is withheld, the fallback is
  to keep the JS sync and document that the *saved* state is already no-JS-correct (the server
  recomputes `item.checked` from declared tags on reload) — but the recommended, clean fix is the
  dedupe.
- **Form idiom (resolves OQ-IC-7):** unify the **purely presentational** wrapper — auth pages use
  Django widget rendering, `submit.html` hand-rolls inputs; both get the same `.form-field`
  structure/spacing. **No form/validation/field change** (C4) — if unifying would touch a widget's
  behaviour, that field is left as-is.
- **Submit grouping (B3):** a lighter-touch required-vs-optional visual grouping (a `<fieldset>`/
  section heading + the existing `.card` rhythm) — presentational only; `demo_clip_alt`'s
  "required-if-clip" hint promoted from placeholder to a visible field note.

---

## 5. UX flows / states touched (for the Experience Designer)
Every surface keeps its existing states (empty / loading / error); this feature changes only
*presentation* of them. The `2b-ux` owner should focus on: (1) the mobile app-page **action panel**
(W4) — does Try/Follow/Share-above-hero feel right, or should the panel be styled as a compact bar;
(2) the **developer hub** tab treatment + which tab is "home"; (3) the consolidated component layer
(W2) — section headings, captions, toolbars reading consistently across surfaces; (4) the **icon**
set's visual weight (brand-neutral, no rebrand — IC-D-1). No new screen or state is introduced.

---

## 6. Non-functional handling
- **Performance:** strictly neutral-to-positive — fewer inline styles, one cached hashed stylesheet,
  inline SVGs are tiny and not network requests. No new queries (no view/selector data change,
  modulo the W7 dedupe which is bounded and read-only).
- **Security/PII (§10):** none touched — no new endpoint, no new data, no auth change. The
  developer-hub header entry stays behind the existing `{% is_developer %}` gate (presentation
  mirror of `@require_role`, never the security boundary). The copy-link PE reads only the public
  page URL already on the page. Widget firewall untouched (C6 — no widget template edited).
- **Observability/rollback (§11):** see §11.

---

## 7. Failure modes (per component)
- **`{% icon %}` with an unknown name:** fail **loud in dev** — the tag raises `TemplateDoesNotExist`
  (a missing SVG partial) so a typo is caught at render in CI's render-every-surface check, never a
  silent blank. (No production fallback glyph — a missing icon is a build defect, surfaced.)
- **Enumeration guard scope:** the "defined" set is the union of **all** `--…:` declarations in
  `app.css` (not only `:root`), so it cannot mis-flag a validly-defined token; the "referenced" set
  is every `var(--…)` and `btn--*`/known-component class across templates + `app.css`.
- **Copy-link PE on a browser without `navigator.clipboard`:** the button is added by JS only when
  the API exists; without it, the readonly link (selectable) is the no-JS path. No error path.
- **W4 reflow on an unsupported old browser:** `order:`/flex degrade to source order (Try lower) —
  the *content* is fully present and reachable, only the ordering enhancement is absent. Graceful.
- **W7 picker dedupe:** if the view-context confirmation is withheld, the documented fallback keeps
  today's behaviour (no regression). No data path changes either way.

---

## 8. Change & irreversibility
- **Most-likely-to-change** (kept cheap): token values, the consolidation depth/target (M2 is a
  number in one place), the icon set (add an SVG file + a CODEMAP line). All config-like, isolated.
- **Irreversible decisions: none.** No schema, no migration, no public-API shape, no global ADR
  (confirms IC-D-2: the patch envelope is retained as a constraint). Every workstream is a
  `git revert` of its commit. This is by design (design-for-deletion §5.4).

---

## 9. Alternatives considered (≥2 genuinely different; what we sacrifice)
- **A2 consolidation — full extraction of all 621 inline styles across 31 templates** (rejected,
  IC-DESIGN-2). Sacrifice accepted: some inline styles remain. Rejected because it balloons into a
  template rewrite fighting the pipeline (brief R1), risks visual regressions on surfaces not
  individually reviewed (R3), and yields diminishing returns past the worst offenders. Bounded-first
  addresses the **root cause** (design system = source of truth for *recurring* intent) without the
  blast radius.
- **Icon mechanism — a vendored icon font or an external sprite CDN** (rejected). Sacrifice: a font
  would be one fewer set of inline SVGs. Rejected: a font is a build/asset dependency and announces
  glyphs to some screen readers (a11y regression); a CDN violates the vendored-only posture
  (premium-frontend D-13). Inline SVG via a template tag is no-build, accessible, and reuses the
  established tag pattern.
- **Mobile Try — actually reordering the DOM** (rejected). Sacrifice: hero-then-Try would read more
  naturally. Rejected: it breaks the source-order fingerprint invariant (C1/IC-D-3) — the entire
  point is to preserve it. CSS `order:` is the boring, correct, invariant-safe tool.
- **Developer homes — keep two separate header entries** (rejected by the **user**, who chose the
  unified hub). Sacrifice: the hub is a slightly larger nav/IA change than a rename. Accepted per the
  user's decision; kept in-envelope via a shared partial + existing URLs (no new route).

---

## 10. Security model
No attack surface added. No new input is trusted (the copy-link reads the server-rendered public
URL; no user input is reflected unescaped — all template output stays Django auto-escaped). No
privilege change. No PII flow. The widget firewall (C6) is preserved by never editing a widget
template.

## 11. Operations / rollback
- **How we know it works:** the **W8 enumeration guard** (M1), the existing **render-every-surface**
  check (M3, platform-staging), the **app-page invariants** (M5), `makemigrations --check`
  (no-drift, M3), and the full suite green (AC-9). The qualitative gate is the **AC-8 human sign-off
  on web + mobile** (M6, the premium-frontend PS-3 precedent).
- **Rollback:** no migration → nothing irreversible; `git revert` of any workstream commit restores
  the prior presentation with zero data impact. Rehearsed at release (DU-REL-1 pattern).
- **Alerts:** none — presentation has no runtime alarms; defects surface in CI, not production.

## 12. Tests (map every AC to a verification)
| AC | Verification |
|---|---|
| AC-1 / M1 | **NEW** `core/tests/test_design_system.py` enumeration guard: referenced tokens/classes ⊆ defined. Asserts `btn--sm`, `--space-0.5/1.5/2.5`, `--font-size-md` now defined. |
| AC-2 | A test (or the guard's class-coverage) asserting the `.app-page-sidebar form button` override is gone and the Follow slot button carries `btn--primary`; manual prominence check at AC-8. |
| AC-3 / M2 | Inline-`style` count grep ≤ 400 (from 621); the new component/utility classes exist; `2b-ux`/AC-8 reader review for "genuinely one-off." |
| AC-4 / M5 | `pages/tests/test_template.py` fingerprint + `catalog/tests/test_redesign_invariants.py` **stay green unchanged** (source order untouched); a CSS-presence test for the `max-width:899.98px` reflow block. |
| AC-5 | `core/_dev_tabs.html` rendered on both surfaces; header shows one "Developer" entry; `aria-current` on the active tab; existing developer-nav tests updated to the new label. |
| AC-6 | a/ no decorative emoji remain in non-widget templates (grep = 0) + `{% icon %}` renders `aria-hidden`; b/ facet category is visible text (not `title`); c/ picker renders no duplicate tag id + no `<script>` sync (or documented fallback); d/ copy-link PE present + readable link in no-JS. |
| AC-7 | `catalogue.html` results state contains the ordering-basis label; **no** sort control/param added. |
| AC-8 / M6 | Human sign-off, web + mobile (release gate). |
| AC-9 / M3 | Full suite green; render-every-surface; `makemigrations --check` no drift; a check (or reviewer) that no `views.py`/`urls.py`/model/serializer changed except the **single flagged** W7 picker-context touch if confirmed. |

## 13. Self-critique
- *"Is the W7 picker dedupe smuggling a view change past C4?"* — No: it is **surfaced**, not smuggled
  (OQ-IC-8, flagged for confirmation; a no-regression fallback exists). That is the honest handling
  the brief's C2 gate demands.
- *"Does defining dotted custom-property names invite confusion?"* — They are valid CSS and already
  used as-written; the alternative (renaming 37 sites) is more churn and more regression risk. The
  enumeration guard documents them as first-class.
- *"Could W4's action-panel-above-hero feel wrong?"* — Possibly; that is precisely why the *feel* is
  routed to the Experience Designer while the design fixes only the invariant-safe *mechanism*.
- *Simplification pass:* dropped any idea of a CSS framework, a theming layer, or a component-library
  abstraction — none tied to a requirement (§5.5). The feature stays edits-to-existing + two small
  reusable artifacts.

## 14. Tech-stack decision
**No stack change; no global ADR.** This feature works entirely within D-4 (server-rendered Django
templates) and D-13 (no-build token CSS). It introduces no language, framework, storage, or
build-step decision that constrains later features — so, per IC-D-2, nothing is promoted to the
global [DECISIONS.md](../../DECISIONS.md). All choices are feature-local (IC-DESIGN-1…9, recorded in
the feature [DECISIONS.md](DECISIONS.md)). The two new reusable artifacts (`{% icon %}` tag, the
enumeration guard) are **shared code → indexed in [CODEMAP.md](../../CODEMAP.md)** at build time.

---

## Rollout strategy
No flag, no phased data rollout (presentation-only, no migration). Ship the eight workstreams as
ordered, independently-releasable commits (W1 first — tokens are the prerequisite; W8's guard lands
with W1 so the defect class stays closed). Backward-compatible by construction. Release = the
standing local/dev close-out with the AC-8 human sign-off on web + mobile.

## Exit criteria check
- ✅ Every AC (1–9) maps to ≥1 design element (§12 table).
- ✅ All interfaces specified — no "TBD" (§4); the one open boundary (W7 view-context) is an
  explicit, recorded escalation, not an undefined contract.
- ✅ Every component's failure behaviour documented (§7).
- ✅ Honors CLAUDE.md §5 (design system as single source of truth; bounded, no speculative
  abstraction; fail-loud icon/guard; design-for-deletion) — §13 simplification pass run.

---

## Hand-off
**Route: `2b-ux` (user-facing).** Create [EXPERIENCE.md](EXPERIENCE.md) (heading + _pending_), set
`Stage: 2b-ux`, persona = **Experience Designer**. They own the *feel* of: the mobile action panel
(W4), the developer-hub tabs (W5), the consolidated component layer + icon weight (W2/W3). The
Planner runs after them. The decision ledger (IC-DESIGN-1…9) is in [DECISIONS.md](DECISIONS.md); the
one open boundary (OQ-IC-8, the W7 picker view-context touch) is in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
for the Planner to confirm under the C2 gate.
