# EXPERIENCE.md — interface-cleanup

*Stage 2b (Experience Designer). Inputs read: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (approved,
DN-IC-BRIEF; AC-1…AC-9, the AC-8 human-judgment gate), [DESIGN.md](DESIGN.md) (the eight workstreams
= my canvas), [DECISIONS.md](DECISIONS.md) (IC-D-1…3, IC-DESIGN-1…9), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
(OQ-IC-8), and the live design system [`core/app.css`](../../apps/core/static/core/app.css) — my
visual CODEMAP.*

> **What this stage owns.** The Architect fixed the *mechanisms* (invariant-safe `order:` reflow, the
> hub IA, the consolidated component layer, the `{% icon %}` tag). I own the *feel*: focal order,
> grouping, wayfinding, affordance legibility, motion purpose, tone — turned into a sign-off checklist
> a reviewer answers yes/no against the built screen. **Zero implementation here** (no CSS, no class
> names, no hex) — intent and named relationships only, the mirror of the Architect's "no TBD."
>
> **Boundary I hold (IC-D-1).** This pass *quiets and aligns* the existing visual language; it does
> **not** introduce a distinctive palette, stylized/animated nav, or decorative motion. Those stay the
> held `ui-modernization` bet. An "improvement" that crosses into them is out of scope here.

---

## 1. Surface inventory (from DESIGN.md — my canvas, not added to)

DESIGN changes presentation on screens a person sees; it introduces **no new screen, state, or data**
(DESIGN §5). I write a full per-screen block for the surfaces whose *feel* genuinely changes, and
gather the system-wide layers (icons, component grammar, wayfinding, defect-repair) into cross-surface
notes so each decision is stated once.

| ID | Surface (workstream) | Why it earns a feel decision |
|----|----------------------|------------------------------|
| **S1** | App page — mobile action panel + facet legibility + Share feedback (W4) | New composition: Try/Follow/Share rise above the hero on mobile; facet category becomes visible; Share gains feedback |
| **S2** | Developer hub — Manage \| Analytics tabs (W5) | New IA/wayfinding element replacing two confusable "My Apps" homes |
| **S3** | Discover — ordering-basis caption (W6) | New visible informational element on the merit surface |
| **S4** | Interests picker — dedupe + form idiom (W7) | Composition changes (one control per tag); no-JS consistency |
| **S5** | Submit form — required/optional grouping (W7/B3) | New scannable structure on a long form |
| **X1–X4** | Cross-surface system layers | Iconography, component grammar, wayfinding/active-state, defect-repair — applied across all of the above |

Empty/loading/error states belong to the surfaces above and are designed in-block (no state left to
build-time default). No surface I wished existed is missing — nothing is escalated to OPEN_QUESTIONS.

---

## 2. Per-screen experience spec

### S1 — App page: mobile action panel, facet legibility, Share feedback (W4)

Canvas (DESIGN §4.4–§4.5): on viewports below the 900px breakpoint the page is single-column and the
sidebar action cluster (**Try / Follow / Share**, plus the compact curated-rating read) is lifted by
`order:` to the **top**, the reviews stay last, and the hero (app name + tagline + fact strip) sits
between. Source DOM order is unchanged (the invariant). Facet category becomes visible text; Share
gains a copy affordance with a confirmation. **The action-panel feel is the question DESIGN handed me.**

| Pillar | Decision (intent only — verifiable) |
|--------|-------------------------------------|
| 1. Scanning & hierarchy | **Exactly one dominant focal point: the `Try` action.** Try is the conversion goal (US-3, the wedge funnel) and wins by size + position + fill. Within the panel the order of emphasis is **Try (dominant) › Follow (clearly actionable, restored to primary — never the grey/demoted look AC-2 forbids) › Share (quiet/tertiary)**. Try and Follow are differentiated by *prominence* (size/position), **not** by demoting Follow's colour. On mobile the panel is first, then the hero identity, then content — see pillar 12. |
| 2. Gestalt & grouping | The action cluster reads as **one bounded action region** (common region) distinct from the identity hero below it. The curated-rating read groups *with* the actions (it is decision support for "should I try this"), kept compact. Reviews are a separate region, visually last. |
| 3. Layout & breathing room | On mobile the action region is **compact (a deliberate action bar), not a tall stack of full-width cards** — so it occupies roughly one band and the app identity surfaces immediately after it, not five sections down. Density: compact for the action band, balanced for the rest. Single alignment spine down the column. |
| 4. IA & navigation | Leaf page; back/wayfinding via the existing header (unchanged). The action panel adds no navigation. The user is never dead-ended (Try opens the app; Follow/Share act in place). |
| 5. Affordances & signifiers | Try = dominant button: default / hover / focus / active (the existing subtle press feedback) — never inert-looking. Follow = primary form button with full default→hover→focus→active→**loading**(post-submit)→disabled-if-not-actionable states, restored from the specificity demotion (AC-2). Share's copy control is unmistakably a button with hover/focus/active. The facet category is **static text, not interactive** (it must not look clickable). |
| 6. Feedback & responsiveness | Try (external link) → standard navigation away. Follow → POST then reload reflecting the "Following" state (existing; acceptable acknowledgment). **Share copy → an immediate, visible, polite confirmation ("Copied!")** announced to assistive tech; the readable link is always present so the no-JS path needs no confirmation. No spinner introduced. |
| 7. Progressive disclosure | First screen = identity + the action band; reviews are deferred to the bottom (their natural depth, existing). Screenshots stay in the horizontal scroll gallery. Facet **categories now shown** (no longer hidden behind hover). Nothing newly hidden. |
| 8. Motion & transition | No new layout animation (the reflow is static). The only new motion is the "Copied!" confirmation, whose **meaning must not depend on motion** (text change + a polite live announcement carry it; any fade is decorative and reduced-motion-gated). Honors the system's reduced-motion-first model. |
| 9. Consistency & reuse | Buttons reuse the existing button variants; the facet category reuses the badge typography (a semibold category caption preceding the value, replacing the hover `title`); the copy confirmation reuses the existing polite-message idiom. The compact mobile action-bar arrangement is a layout reuse of existing primitives, not a new component. |
| 10. Accessibility | Try/Follow/Share meet a comfortable minimum touch-target size. Facet category is **conveyed as real visible text** → reachable by touch, keyboard, and screen reader without hover (AC-6b). Copy button is keyboard-focusable with a live-region confirmation. **Known trade-off, accepted & signed off (IC-EXP-2):** `order:` moves *visual* order only; keyboard/screen-reader order stays DOM order (identity → actions → reviews). That sequence is itself logical, so it does not create a meaning-changing visual/DOM contradiction — but the sign-off explicitly verifies focus order stays coherent. Status colours never signal alone (paired with text). |
| 11. Emotional tone & voice | **Confident, focused, trustworthy, polished.** Confident/focused ← one unmistakable dominant Try. Trustworthy ← visible facet categories + a restored (not greyed) primary. Polished ← no oversized/mis-coloured buttons. Voice: action verbs only — `Try`, `Follow`/`Following`, `Copy link` → `Copied!`. |
| 12. Responsive behavior | **≥900px:** two columns, content + a sticky action sidebar visible alongside — Try already in view, no reflow needed. **<900px:** single column; the compact action band lifts to the top, the hero identity follows immediately, reviews stay last. Preserved at every width: all slots/content and DOM order. Collapses: 2-col→1-col; the action sidebar→a compact top band; sticky→static. |
| 13. Error prevention & recovery | Share copy on a browser without clipboard support → the readable link stays selectable (no error path, the no-JS truth). Follow POST failure → the existing page-level message framework. No new error state is introduced. |

### S2 — Developer hub: Manage | Analytics tabs (W5)

Canvas (DESIGN §3.3/§4.6): one header entry "Developer" → the **Manage** surface (`catalog:my-apps`);
a shared two-tab bar (**Manage** ↔ **Analytics** = `dashboard:my-apps`) on both surfaces; the active
tab carries the current-page semantics; the dashboard's old inline sub-nav is replaced by the partial.

| Pillar | Decision (intent only — verifiable) |
|--------|-------------------------------------|
| 1. Scanning & hierarchy | Focal order: (1) the page `H1` + the tab bar answering **"where am I,"** (2) the tab's primary content (the app list on Manage; the metrics on Analytics), (3) secondary actions. Dominant focal point = the content; the tab bar is a persistent, immediately-legible wayfinding strip above it, with the **active tab as the dominant nav signal**. |
| 2. Gestalt & grouping | The two tabs read as **one segmented control** (proximity + common region), not two stray links. The active tab is visually bonded to the content region directly below it (it "owns" what's shown). |
| 3. Layout & breathing room | Balanced density. The tab bar is a full-width strip above the content, aligned to the content's left spine. Clear separation between the nav strip and the content beneath. |
| 4. IA & navigation | **The core decision.** Nav model = a flat **two-item tab bar**, depth 1, two peers. **"Home" tab = Manage** — managing/submitting apps is the developer's primary job; Analytics is the reflective second read — so the header "Developer" entry lands on Manage. You always know which tab you're on (active indicator) and can always reach the other (never dead-ended). This collapses the two confusable "My Apps" homes into one oriented hub. |
| 5. Affordances & signifiers | Tabs look like tabs: default / hover / **active(current page)** / focus. The active tab uses the **same accent-tinted "you are here" treatment the Discover sidebar's active link already uses** (reuse, pillar 9) + heavier weight; inactive tabs are clearly clickable but quieter. The active tab is the current page (not a link to nowhere); inactive tabs are links. |
| 6. Feedback & responsiveness | Clicking an inactive tab navigates (server-rendered page load); **arrival is confirmed by the destination's active-tab state**. The active-state change is the acknowledgment; no spinner. (If `hx-boost` smooths the swap it is light PE and must not break the no-JS truth.) |
| 7. Progressive disclosure | Manage and Analytics are **peers, not nested** — each tab discloses its own domain. Within Analytics, per-app deep metrics remain a drill-in (existing). Nothing newly hidden. |
| 8. Motion & transition | Tab switching is page navigation — **no required animation**. The active indicator needs no motion beyond the existing link transition. Reduced-motion safe by construction. |
| 9. Consistency & reuse | The active-tab indicator **reuses the existing accent active-link pattern** (same meaning "current location" → same pattern). The *horizontal* tab bar is the one genuinely-new arrangement (the existing active-link pattern is a vertical sidebar nav); justified because no existing pattern is a top-of-page section nav, and the new hub IA needs one. |
| 10. Accessibility | The tab strip is a labelled navigation region; the active tab carries current-page semantics so **"active" is signalled by more than colour** (semantics + weight + tint). Comfortable touch targets; tabs in logical focus order with the existing visible focus ring. |
| 11. Emotional tone & voice | **Organized, oriented, professional, calm.** Organized ← one hub, not two homes. Oriented ← always-visible active tab. Professional/calm ← a restrained accent indicator reusing the system pattern, no novelty. Voice: tab labels `Manage` / `Analytics`; header entry `Developer`. |
| 12. Responsive behavior | The tab bar **stays horizontal and fully visible on mobile** — two short labels fit; wayfinding is never collapsed into a menu (two items don't warrant it). Content below reflows per its own surface rules. |
| 13. Error prevention & recovery | No error state for the tabs. **Empty Manage** (no apps yet) and **empty Analytics** (no data yet) each get the shared empty-state treatment (X1): consistent icon + a title + a description that points to the next action. Designed, not defaulted. |

> The Analytics tab includes the reception view whose legend swatch was the B7 defect. With the
> `background-dasharray` fixed (DESIGN §3.1/§4.3), the dashed-series swatch now actually renders →
> the chart legend distinguishes series by **pattern + colour, not colour alone** (an a11y gain). See X2.

### S3 — Discover: ordering-basis caption (W6)

Canvas (DESIGN §4.7): a presentational caption by the results count stating the basis — *"Ranked by
merit, never by spend"* — **no sort control, no query param, no change to the catalog primitive** (AC-7).

| Pillar | Decision (intent only — verifiable) |
|--------|-------------------------------------|
| 1. Scanning & hierarchy | The results grid stays dominant. The ordering caption is a **quiet secondary line** beside the result count — it informs without competing. Focal order: search → result count + basis caption → cards. |
| 2. Gestalt & grouping | The caption groups with the result count as one "results meta" line (proximity). |
| 3. Layout & breathing room | A single compact muted line; no extra structure. |
| 4. IA & navigation | N/A: no navigation change. |
| 5. Affordances & signifiers | **Critical: the caption is static informational text and must NOT look interactive.** A merit caption styled like a button or dropdown would imply a sort control that does not exist (AC-7). It reads unmistakably as a statement, not an affordance. |
| 6. Feedback & responsiveness | N/A: static label, no user action. |
| 7. Progressive disclosure | N/A: the basis is stated plainly, nothing deferred. |
| 8. Motion & transition | N/A: no motion. |
| 9. Consistency & reuse | Reuses the muted-caption treatment from the consolidated component layer (X2). The copy matches the footer/vision voice ("merit, never spend") — voice consistency. |
| 10. Accessibility | Real text, screen-reader reachable, AA contrast on its surface, associated with the results region. |
| 11. Emotional tone & voice | **Transparent, principled, confident.** Stating the ranking basis openly on the one surface whose pitch is merit. Voice = the merit line, plain and unhedged. |
| 12. Responsive behavior | The caption wraps with the count on mobile; preserved at all widths (it is short). |
| 13. Error prevention & recovery | **Zero-results state:** the ordering caption is **suppressed** (nothing to order); the existing empty state carries the message instead. Verifiable. |

### S4 — Interests picker: dedupe + no-JS + form idiom (W7)

Canvas (DESIGN §4.8 / IC-DESIGN-9): render each interest tag **at most once**, delete the JS sync
`<script>` → the no-JS path is inherently consistent (AC-6c). The form-field idiom is unified with the
rest of the product (presentational only). (OQ-IC-8 is the Planner's view-context confirmation — not a
feel question.)

| Pillar | Decision (intent only — verifiable) |
|--------|-------------------------------------|
| 1. Scanning & hierarchy | Focal order: the page header ("pick your interests" + lede) → the tag groups (clusters) → the save action. Dominant = the tag-selection grid. |
| 2. Gestalt & grouping | Tags grouped by cluster (labelled common region); within a cluster the controls read as a set. **Dedupe removes duplicate controls** → each tag appears once → no confusing repeated checkboxes for the same tag. |
| 3. Layout & breathing room | Balanced; clusters as labelled groups with breathing room between them so the groups are visually distinct. |
| 4. IA & navigation | A single-screen form; save returns to the profile (existing). No nav change. |
| 5. Affordances & signifiers | Checkboxes look checkable; selected vs. unselected is clearly distinct via the native control + label, **not colour alone**. After dedupe there are no duplicate same-tag controls to fall out of sync. |
| 6. Feedback & responsiveness | Selection is immediate (native control). Save → the existing confirmation message. **No-JS:** the server recomputes the checked state from declared tags on reload → consistent without JavaScript (AC-6c/US-7). |
| 7. Progressive disclosure | All clusters shown (existing); nothing newly deferred. N/A new disclosure. |
| 8. Motion & transition | None new; reduced-motion safe. |
| 9. Consistency & reuse | Form fields reuse the **unified `.form-field` idiom** (W7) shared with auth/submit — same structure and spacing. Checkbox/label treatment consistent with the product. |
| 10. Accessibility | Each tag = one labelled control (no duplicate controls to confuse assistive tech); keyboard-navigable; the no-JS path keeps state consistent; comfortable targets. |
| 11. Emotional tone & voice | **Clear, effortless, robust.** Clear ← one control per tag. Effortless/robust ← no JS dependence to stay consistent. Voice: cluster headings, `Save`. |
| 12. Responsive behavior | Clusters reflow to a single column on mobile; tag controls wrap. Preserved: every tag reachable. |
| 13. Error prevention & recovery | On validation re-render the server preserves the user's selections (existing); no new error state. Dedupe removes the *class* of "inconsistent duplicate state" error (error prevention). |

### S5 — Submit form: required/optional grouping (W7 / B3)

Canvas (DESIGN §4.8): a lighter-touch required-vs-optional visual grouping (section heading + the
existing card rhythm), and `demo_clip_alt`'s "required-if-clip" hint promoted from a placeholder to a
visible field note. Presentational only — no form/validation/field change.

| Pillar | Decision (intent only — verifiable) |
|--------|-------------------------------------|
| 1. Scanning & hierarchy | Focal order: the page header (what am I submitting) → the form sections in order → the submit action. Dominant = the section/field in focus. The required/optional grouping gives the long form a **scannable chunked structure** instead of one wall of inputs. |
| 2. Gestalt & grouping | Fields grouped into labelled sections (**required group**, then **optional group**) via section headings + the card rhythm → the eye reads a few chunks, not a single list. |
| 3. Layout & breathing room | Balanced→generous; clear section breaks; single-column (forms read top-down). |
| 4. IA & navigation | Single-screen form; submit → app created (existing). No nav change. |
| 5. Affordances & signifiers | Inputs look editable (existing focus ring). Required vs. optional is signalled **in text/markup, not colour alone**. The `demo_clip_alt` note is a **persistent visible field note** (a placeholder vanishes on input → the wrong affordance for a conditional requirement). Submit = primary button, grouped at the end. |
| 6. Feedback & responsiveness | Field focus state (existing); submit → success/redirect or inline validation errors (existing). No new feedback mechanism. |
| 7. Progressive disclosure | **Required fields grouped first/prominent; optional fields in their own lighter-emphasis group** — the user completes the essential set and treats optional as clearly-deferred-but-present. This is the B3 intent. |
| 8. Motion & transition | None new. |
| 9. Consistency & reuse | The `.form-field` idiom is unified across auth/submit/picker; section headings reuse the heading scale; submit reuses the primary button. No new pattern. |
| 10. Accessibility | Labels associated; required state conveyed in text/markup not colour; the promoted note is persistent and programmatically associated (vs. a vanishing placeholder); logical focus order; comfortable targets. |
| 11. Emotional tone & voice | **Structured, guiding, unintimidating.** Structured/guiding ← required/optional grouping. Unintimidating ← visible field notes replacing vanishing placeholders, optional clearly set apart. Voice: section headings (e.g. `Required` / `Optional`), the promoted clip-alt note, the submit verb. |
| 12. Responsive behavior | Single column at all widths; sections stack; submit reachable. Preserved. |
| 13. Error prevention & recovery | Validation errors shown inline per field in **text + the error colour (not colour alone)**; entered values preserved on re-render (existing); the required-if-clip rule surfaced **before** submit as a note (error prevention). Recovery = fix the flagged field. |

---

## 3. Cross-surface system notes (stated once)

### X1 — Iconography (W3): one quiet, brand-neutral set

Decorative emoji become a single consistent icon set across empty states, status indicators, arrows,
and the rating star. **Intent:** uniform stroke weight, uniform optical size, consistent metaphors,
**brand-neutral** (no distinctive/illustrative style — that is `ui-modernization`, IC-D-1). Icons read
**quiet** — muted by default, never louder than the text they support (they keep the existing
empty-state icon's large-but-muted role). Decorative icons are semantically decorative: **the adjacent
visible text already carries the meaning**, so they are not announced (AC-6a). Status icons always pair
with the semantic colour **and** text — never icon/colour alone. Verifiable: no per-OS emoji remains
where a person looks; icons read as one family.

### X2 — Component grammar (W2): same meaning → same treatment, everywhere

The recurring presentational intents become named, consistent patterns: the **page header** (title +
muted lede), the **muted caption**, the **toolbar** (header action row), **status colours**, card
sub-sections. **Intent:** a section heading on Discover looks identical to one on the profile, submit,
and the hub; a muted caption is the same everywhere. This is the coherence backbone of AC-3/AC-8 — the
thing that makes the product read as *one product* rather than surfaces assembled from parts. The B7
legend defect is repaired into a real dashed swatch (series distinguished by pattern + colour).
Verifiable: pick any heading / caption / action-row and it matches its peers across surfaces.

### X3 — Wayfinding & active state (W5 + base.html): always know where you are

The global nav now marks the current section with current-page semantics + the accent "you are here"
treatment (reusing the Discover active-link pattern), and the developer entry is **one "Developer"
item** (not two "My Apps"). **Intent:** in the top nav and in the hub tabs, the user can always answer
"where am I" — signalled by more than colour (semantics + weight). Verifiable per surface.

### X4 — Defect-repair feel (W1): nothing half-finished

Invisible-when-right repairs that the eye reads as polish: "small" buttons render small (correct
rhythm), intended spacing applies (the dotted-space tokens resolve), and the app-page **Follow** primary
is restored from grey to its primary treatment (AC-2). **Intent:** no button looks oversized or
mis-coloured, no spacing looks collapsed, no primary action looks inert. Verifiable as the absence of
these defects on every surface.

### System tone (5 adjectives — each tied to a verifiable choice)

| Adjective | Tied to (verifiable) |
|-----------|----------------------|
| **Coherent** | Same meaning renders the same everywhere (X2 component grammar; one icon family X1) |
| **Polished** | No silent defects — correct button sizes, applied spacing, restored primary, real icons not emoji (X4, X1) |
| **Trustworthy** | Visible facet categories (S1), the stated ranking basis (S3), the restored primary CTA (S1/X4), accessibility by default |
| **Legible** | Non-hover facet categories, real text labels, AA contrast, scannable hierarchy (S1, S5, X2) |
| **Calm** | Restrained accent use, reduced-motion-first, no decorative noise — the pass *quiets* rather than embellishes (deliberately **not** `ui-modernization`) |

### System motion language

Motion stays **functional-only and reduced-motion-first** — every transition already lives behind
`prefers-reduced-motion: no-preference`, and this feature **adds no new decorative motion** (branded
motion is the held `ui-modernization` bet). The single new feedback motion is the Share "Copied!"
confirmation, whose meaning must survive with motion disabled (text + a polite live announcement carry
it). Verifiable: with reduced-motion on, every surface is fully usable and nothing essential depends on
animation.

---

## 4. The "compelling feel" sign-off checklist (AC-8 class → yes/no)

Convert the human-judgment criteria — **AC-3** (consolidation, human half), **AC-4** (mobile CTA, human
half), **AC-2** (rendered prominence), and **AC-8** (overall polish) — into items a reviewer answers
**yes/no looking at the built screen, on web and on mobile**. This is the release gate (M6, the
premium-frontend PS-3 precedent).

**Consistency & polish (AC-3, AC-2, AC-8)**
- [ ] A section heading, a muted caption, and a header action-row look the **same** on Discover, the profile, Submit, and the developer hub — not subtly different per page.
- [ ] No surface shows an **oversized "small" button**, collapsed/cramped spacing, or a primary action that reads **grey/inert** (AC-2).
- [ ] Icons read as **one consistent family** (same weight, same optical size, brand-neutral) — **no per-OS emoji** anywhere a person looks.
- [ ] Every **empty state** (incl. empty Manage, empty Analytics) shares one look: consistent icon + title + description rhythm.

**App page on mobile (AC-4)**
- [ ] On a phone, **Try is visible within the first screen / one short scroll** — not buried below the whole page.
- [ ] The Try/Follow/Share panel reads as **one deliberate compact action bar** — Try clearly dominant, Follow clearly actionable (not grey), Share quiet — **not** a tall stack that pushes the app identity far down.
- [ ] The app **identity (name + tagline) is reached immediately after** the action bar — it doesn't feel like buttons without context.
- [ ] Facet **categories are readable without hovering**, on touch and with a screen reader.
- [ ] Sharing gives a **visible "Copied!" confirmation**, and the link is obtainable with JavaScript off.

**Developer hub (AC-5)**
- [ ] The header shows **exactly one "Developer" entry**, and the hub shows two tabs (**Manage / Analytics**) with the current one **unmistakably indicated**.
- [ ] On either tab you can tell which one you're on and switch to the other — never two confusable "My Apps".

**Discover (AC-7)**
- [ ] Discover **plainly states results are ranked by merit**, as an informational caption — **not** a clickable control implying a sort that doesn't exist.

**Accessibility & robustness (AC-6, US-7)**
- [ ] With **reduced-motion** on, every surface is fully usable and nothing essential relies on animation.
- [ ] With **JavaScript off**, the interests picker stays consistent and the Share link is still obtainable.
- [ ] Active nav/tab state is signalled by **more than colour alone** (weight + current-page semantics).
- [ ] On the app page, **keyboard/screen-reader focus order stays logical** (identity → actions → reviews) despite the mobile visual reflow (IC-EXP-2).

**Overall (AC-8) & scope boundary (AC-9)**
- [ ] End to end on **web and mobile**, the product reads as **one coherent, polished, trustworthy product** — not surfaces assembled from parts.
- [ ] **Nothing in this pass introduced a new palette, stylized/animated nav, or decorative motion** (that stays the separate `ui-modernization` bet — IC-D-1).

---

## 5. Traceability map (every user-facing AC → experience spec)

| AC | Type | Served by |
|----|------|-----------|
| **AC-1** (defined refs) | agent-verifiable | The *feel* it enables = **X4** (defect-repair: spacing/sizing actually apply). Structural proof is the W8 guard. |
| **AC-2** (no silent demotion) | agent + human | **S1** (Follow restored to primary, focal order Try›Follow›Share) + **X4**; checklist §4 "polish". |
| **AC-3** (consolidation) | agent + human | **X2** (component grammar) + system tone (Coherent); checklist §4 "consistency". |
| **AC-4** (mobile CTA) | agent + human | **S1** (compact action bar, Try dominant, identity-immediately-after); checklist §4 "app page on mobile". |
| **AC-5** (developer naming) | agent | **S2** (the hub + tabs) + **X3** (one "Developer" entry, active state). |
| **AC-6a** (icons not announced) | agent | **X1**. |
| **AC-6b** (facet category no hover) | agent | **S1** (visible category caption). |
| **AC-6c** (picker no-JS) | agent | **S4** (dedupe → inherently consistent). |
| **AC-6d** (Share feedback + link) | agent | **S1** (copy affordance + "Copied!" + readable link). |
| **AC-7** (ordering visibility) | agent | **S3** (informational caption, not a control). |
| **AC-8** (overall polish) | human | All surfaces + system tone/motion; the **§4 sign-off checklist** is the gate. |
| **AC-9** (no regression / in envelope) | agent | Structural (suite/render/no-drift). Its experiential half — **no new palette/nav/motion** — is held by the system-motion/tone notes + the §4 boundary item. |

Every user-facing AC maps to ≥1 experience spec; every human-judgment AC (the AC-8 class) has a yes/no
item in §4. No criterion was unmappable — no finding to surface to the Architect.

---

## 6. Exit-criteria self-check
- ✅ Every feel-changing screen in DESIGN has a complete 13-pillar block (S1–S5); system-wide layers in X1–X4. Pillars marked **N/A** carry a reason.
- ✅ Every user-facing AC maps to ≥1 spec (§5); every AC-8-class criterion is a yes/no item (§4).
- ✅ Tone = 5 concrete adjectives, each tied to a verifiable choice (§3).
- ✅ Every empty/error/boundary state named by the design has a designed treatment (empty hub tabs S2-13, zero-results S3-13, no-JS/no-clipboard S1-13/S4-6, validation S5-13) — none left to build-time default.
- ✅ **Zero implementation**: no CSS, no class/component names, no framework, no hex/pixel values — intent and named relationships only.

---

## Hand-off
**Route: `3-plan` (Planner / Tech Lead).** No design gap found → not routed back to the Architect. The
feel of the mobile action panel (S1), the developer-hub tabs (S2), and the consolidated component +
icon layer (X1/X2) is specified as intent + a verifiable §4 sign-off checklist feeding AC-8. Experience
decisions IC-EXP-1…5 are logged in [DECISIONS.md](DECISIONS.md). The one open envelope boundary
([OQ-IC-8](OPEN_QUESTIONS.md), the W7 picker view-context touch) remains the Planner's to confirm under
the C2 gate — it is a mechanism question, untouched by this stage.
