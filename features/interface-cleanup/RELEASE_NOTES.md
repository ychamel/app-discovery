# RELEASE_NOTES.md — interface-cleanup

*Stage 4-build (Senior Engineer) — T-12 final gate*

---

## Summary

A presentation-only, cross-cutting consistency and defect-repair pass. No schema, no migration,
no new URL/view/API, no ADR promoted. Everything is reversible with a `git revert`.

**Changes shipped (T-01…T-11):**

| Task | What changed |
|------|-------------|
| T-01 | Defined 4 missing CSS tokens + `.btn--sm`; deleted the specificity demotion of the app-page Follow/Share buttons |
| T-02 | Added `test_design_system.py` — the enumeration guard that makes "undefined token/class" a failing test |
| T-03 | Added bounded utility/component layer to `app.css` (`.text-muted`, `.text-error`, `.card-heading`, `.metric-value`, `.toolbar`, `.legend-swatch--dashed`, and more) |
| T-04 | Migrated inline styles from 22 templates; inline-`style` count: **621 → 388** (M2 floor ≤ 400) |
| T-05 | `{% icon "name" %}` inline-SVG inclusion tag + 16-icon hand-authored set (search / package / photo / tag / newspaper / upload / megaphone / chart / mail / gear / check / warning / arrow-left / arrow-right / arrow-up-right / star) |
| T-06 | Replaced all decorative emoji across non-widget templates with `{% icon %}` (0 emoji remain) |
| T-07 | App page: mobile Try/Follow/Share compact action bar via CSS `order:` (DOM order unchanged); facet category visible text; Share copy-link PE button + "Copied!" `aria-live` confirmation |
| T-08 | Developer hub: `_dev_tabs.html` partial (Manage / Analytics with `aria-current`); single "Developer" header entry; both surfaces updated |
| T-09 | Discover: static "Ranked by merit, never by spend" ordering caption (informational, not a control; suppressed on zero results) |
| T-10 | Interests picker: per-tag deduplication in `_cluster_rows()` (the single OQ-IC-8 view-layer touch); JS sync `<script>` removed; no-JS path inherently consistent |
| T-11 | `.form-field` idiom unified across auth/submit/picker; submit form required/optional fieldset grouping; `demo_clip_alt` hint promoted from placeholder to visible note |

---

## T-12 Gate Results

| Check | Result |
|-------|--------|
| Full test suite | **1104 tests — OK** (up from 1103 pre-feature) |
| `makemigrations --check` | **No drift** |
| Inline-`style` count (M2 floor) | **388** (≤ 400 ✅) |
| App-page uniformity invariants | **Green** (slot fingerprint unchanged) |
| M5=0 firewall invariants | **Green** (ranking + devlog firewalls held) |
| Design system enumeration guard | **Green** (no undefined token or class reference) |
| Emoji grep (non-widget templates) | **0 matches** (M4) |
| `ruff check` | **Clean** |

### AC-9 attestation — no view / URL / model / serializer / ADR change (beyond the gated OQ-IC-8 touch)

Non-test Python files changed in this feature:

- `apps/core/templatetags/__init__.py` — package file for the new templatetag module
- `apps/core/templatetags/icons.py` — the `{% icon %}` tag (T-05, explicitly allowed)
- `apps/interests/views.py` — `_cluster_rows()` deduplication (T-10, the **single deliberate OQ-IC-8 view-layer touch**, confirmed in-envelope: no URL, schema, or saved-state contract changed; recorded in DECISIONS.md)

No model, migration, URL conf, serializer, API endpoint, or global ADR was touched. ✅

---

## Rollback

No migration → rollback is `git revert <build-commit>` + static file re-collect. No DB state to undo.

---

## AC-8 Human sign-off checklist (from EXPERIENCE.md §4)

> **This gate is the user's to sign.** Review on web and mobile (phone viewport). For each
> item answer **yes** (✅) or **no** (with a note). AC-8 is not self-signed by the agent.

### Consistency & polish (AC-3, AC-2, AC-8)

- [ ] A section heading, a muted caption, and a header action-row look the **same** on Discover, the profile, Submit, and the developer hub — not subtly different per page.
- [ ] No surface shows an **oversized "small" button**, collapsed/cramped spacing, or a primary action that reads **grey/inert** (AC-2: Follow button on the app page).
- [ ] Icons read as **one consistent family** (same weight, same optical size, brand-neutral) — **no per-OS emoji** anywhere a person looks.
- [ ] Every **empty state** (incl. empty Manage tab, empty Analytics tab) shares one look: consistent icon + title + description rhythm.

### App page on mobile (AC-4)

- [ ] On a phone, **Try is visible within the first screen / one short scroll** — not buried below the whole page.
- [ ] The Try/Follow/Share panel reads as **one deliberate compact action bar** — Try clearly dominant, Follow clearly actionable (not grey), Share quiet — **not** a tall stack that pushes the app identity far down.
- [ ] The app **identity (name + tagline) is reached immediately after** the action bar — it doesn't feel like buttons without context.
- [ ] Facet **categories are readable without hovering**, on touch and with a screen reader.
- [ ] Sharing gives a **visible "Copied!" confirmation**, and the link is obtainable with JavaScript off.

### Developer hub (AC-5)

- [ ] The header shows **exactly one "Developer" entry**, and the hub shows two tabs (**Manage / Analytics**) with the current one **unmistakably indicated** (more than colour: weight + accent + `aria-current`).
- [ ] On either tab you can tell which one you're on and switch to the other — never two confusable "My Apps".

### Discover (AC-7)

- [ ] Discover **plainly states results are ranked by merit**, as an informational caption — **not** a clickable control implying a sort that doesn't exist.

### Accessibility & robustness (AC-6, US-7)

- [ ] With **reduced-motion** on, every surface is fully usable and nothing essential relies on animation.
- [ ] With **JavaScript off**, the interests picker stays consistent and the Share link is still obtainable.
- [ ] Active nav/tab state is signalled by **more than colour alone** (weight + current-page semantics).
- [ ] On the app page, **keyboard/screen-reader focus order stays logical** (identity → actions → reviews) despite the mobile visual reflow (IC-EXP-2).

### Overall (AC-8) & scope boundary (AC-9)

- [ ] End to end on **web and mobile**, the product reads as **one coherent, polished, trustworthy product** — not surfaces assembled from parts.
- [ ] **Nothing in this pass introduced a new palette, stylized/animated nav, or decorative motion** (that stays the separate `ui-modernization` bet — IC-D-1).
