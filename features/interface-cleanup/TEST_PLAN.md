# TEST_PLAN.md — interface-cleanup

*Stage 4 (Senior Engineer) — T-12 gate reached.*

---

## 1. Unit & Integration Tests

### T-02 — Design system enumeration guard

**File:** `apps/core/tests/test_design_system.py`

- `test_design_system_definitions` — asserts T-01 regression anchors (`--font-size-md`, `--space-0.5`, `--space-1.5`, `--space-2.5`, `.btn--sm`) are defined in `app.css`.
- `test_design_system_tokens_alignment` — parses `app.css` for defined tokens and all non-widget templates for referenced tokens; asserts `referenced ⊆ defined`. Excludes widget templates (C6).
- `test_design_system_classes_alignment` — same scan for component/utility classes; asserts `referenced ⊆ defined`.
- `test_inline_styles_count` — grep over non-widget templates; asserts count ≤ 400 (M2 floor).

Verified: guard fails correctly when a definition is removed; passes green post-T-01.

### T-05 — `{% icon %}` template tag

**File:** `apps/core/tests/test_icons.py`

- `test_render_known_icon` — `{% icon "search" %}` renders `<svg class="icon"` with `aria-hidden="true"`.
- `test_render_unknown_icon_raises_error` — unknown name raises `TemplateDoesNotExist` (fail loud in dev).

### T-09 — Discover ordering caption

**File:** `apps/discovery/tests/test_views.py`

- `test_ranking_caption_browse` — results state contains "Ranked by merit, never by spend"; no `<select>` sort control added.
- `test_ranking_caption_search` — caption still present in search-results state.
- `test_ordering_caption_absent_on_zero_results` — caption absent when query yields no results.

### T-10 — Interests picker dedupe (OQ-IC-8)

**File:** `apps/interests/tests/test_views.py`

- `test_duplicate_tags_are_deduplicated_in_render` (added in build) — each tag appears at most once in the rendered picker; no duplicate checkbox for the same tag id.

### T-11 — Form-field idiom + submit grouping

Covered by existing `apps/catalog/tests/` form and submit tests: no form/validation/view behaviour changed; the `.form-field` idiom is additive CSS only; fieldset grouping is template-only.

### T-07 — App page mobile reflow + facet + Share

**File:** `apps/pages/tests/test_template.py`

- `StructuralUniformityTests.test_two_wildly_different_apps_render_identical_slots` — DOM slot fingerprint (`_ALWAYS_SLOTS`) unchanged despite mobile reflow (proves DOM order intact, IC-D-3/AC-4/M5/C1).
- `FacetTests.test_facets_render_in_fact_strip` — facet category label rendered as visible text (not only a `title` attribute).
- `PressKitAndAccessibilityTests.test_canonical_url_present_and_copyable` — Share link readable + `readonly` input present.

Dedicated CSS presence checks run via `test_design_system.py` (media query block present in `app.css`).

### T-08 — Developer hub

**File:** `apps/core/tests/test_header_nav.py` + `apps/catalog/tests/test_pages_developer.py`

Existing developer-nav tests updated to the "Developer" label and verified the active-state/`aria-current` treatment; `_dev_tabs.html` inclusion on both surfaces.

---

## 2. Regression Checklist

- [x] Full suite: **1104 tests — OK** (pre-feature baseline 1103; +1 new test T-09 zero-results caption absence).
- [x] `makemigrations --check` — **no drift** (presentation-only, no model touched).
- [x] `ruff check` — clean.
- [x] Design system enumeration guard — green on every task boundary (each new class defined before first reference).
- [x] Inline-`style` count — **388** (M2 floor ≤ 400 ✅, baseline 621).
- [x] Emoji grep across non-widget templates — **0 matches** (M4).
- [x] App-page `StructuralUniformityTests` + `test_redesign_invariants` — green unchanged (DOM order + firewall invariants held).
- [x] OQ-IC-8 confirmation: `_cluster_rows()` view-context touch confirmed in-envelope; URL/schema/saved-state contract unchanged; logged in DECISIONS.md.

---

## 3. Acceptance Self-Check (non-binding — binding gate = user's AC-8 checklist in RELEASE_NOTES.md)

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1 (token/class guard) | ✅ | `test_design_system.py` green; no undefined reference |
| AC-2 (Follow primary restored) | ✅ | Specificity demotion block deleted; `.app-page-sidebar .btn` rules deliver full-width via class-scoped layout |
| AC-3 (consolidation / component grammar) | ✅ | Inline-style count 621 → 388; named classes apply consistently |
| AC-4 (mobile Try reachability) | ✅ | `order: -1` on `.app-page-sidebar` below 899.98px; DOM order fingerprint unchanged |
| AC-5 (Developer hub / naming) | ✅ | One "Developer" nav entry; `_dev_tabs.html` on both surfaces with `aria-current` |
| AC-6a (icons not announced) | ✅ | `aria-hidden="true"` on every SVG; 0 emoji in non-widget templates |
| AC-6b (facet category no-hover) | ✅ | `.facet__cat` visible text replaces `title` attribute |
| AC-6c (picker no-JS consistency) | ✅ | JS sync script removed; deduped tags inherently consistent without JS |
| AC-6d (Share feedback) | ✅ | `navigator.clipboard` PE copy button + `aria-live` "Copied!"; readable link present with JS off |
| AC-7 (ordering visibility) | ✅ | Static "Ranked by merit, never by spend" caption; no sort control; suppressed on zero results |
| AC-8 (overall polish) | ⬜ | **User's gate** — EXPERIENCE §4 checklist carried into RELEASE_NOTES.md |
| AC-9 (no regression / in-envelope) | ✅ | Suite green; no model/URL/ADR change; only gated OQ-IC-8 view-layer touch |
| M1 (guard) | ✅ | `test_design_system.py` green |
| M2 (inline-style ≤ 400) | ✅ | 388 |
| M3 (render-every-surface) | ✅ | All surface tests pass |
| M4 (emoji = 0) | ✅ | 0 emoji in non-widget templates |
| M5 (widget firewall) | ✅ | Widget templates untouched (C6); firewall invariant green |
| M6 (AC-8 checklist staged) | ✅ | RELEASE_NOTES.md §AC-8 |
