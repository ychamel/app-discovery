# PATCH — `patch-dashboard-window-label`

**Source issue:** [`BUG-003`](../../issues/BUG-003.md) (Medium) — selected reporting
period renders literal `{{ w.label }}` in the developer dashboard.

**Stage:** `P-plan` — _Maintenance Planner: plan complete, pending user approval._

---

## 1. Problem Statement

### Reproduction Steps

1. Sign in as a developer who owns at least one accepted app.
2. Open the developer dashboard "My apps" view (`dashboard:my-apps`).
3. Look at the **Reporting Period** selector. The currently-selected window renders the
   literal text `{{ w.label }}` instead of its human label (e.g. "Last month"). The
   non-selected windows render correctly.
4. (Second, unreported instance — found by the sweep below.) If that developer has any
   **curated** impressions in the active window, each app card's *On-platform Reach* row
   renders the literal text `{{ summary.curated_impressions }}` in place of the curated
   count.

### Root Cause Analysis

Django's template lexer compiles its `tag_re` (`django/template/base.py`) **without**
`re.DOTALL`, so a `{{ … }}` (or `{% … %}`) tag that spans a newline is never tokenized —
it is emitted verbatim as literal text. Verified empirically on Django 5.2.15
(`tag_re.findall` returns no match for a multiline variable tag).

A repo-wide sweep of every `*.html` template (regex for `{{…}}`/`{%…%}` spans containing a
newline) finds **exactly two** offending tags, **both in the same file**:

- [`apps/dashboard/templates/dashboard/my_apps.html:32-33`](../../apps/dashboard/templates/dashboard/my_apps.html#L32-L33)
  — the **selected** window's `{{ w.label }}` is split across two lines. Only the selected
  branch uses the multiline form; the non-selected branch
  ([:36](../../apps/dashboard/templates/dashboard/my_apps.html#L36)) is single-line and
  renders fine. This is the reported `BUG-003` symptom.
- [`apps/dashboard/templates/dashboard/my_apps.html:58-59`](../../apps/dashboard/templates/dashboard/my_apps.html#L58-L59)
  — `{{ summary.curated_impressions }}` is split across two lines inside the curated-count
  `<span>`. Not yet reported because it only renders when a developer has accepted apps
  with curated impressions, but it is the **same defect** and is fixed here as cheap
  insurance (the sweep is the whole point — fixing only the reported line would leave a
  known sibling bug live).

No other template in the repo contains a multiline tag.

## 2. Proposed Fix / Change

### Code-level Design

Join each offending variable tag back onto a single line so the lexer tokenizes it. No
markup, attributes, classes, or surrounding text change — only the line break inside the
`{{ … }}` is removed.

- `my_apps.html:32-33` → `…var(--font-weight-semibold));">{{ w.label }}</span>` on one line.
- `my_apps.html:58-59` → `…color: var(--color-success);">({{ summary.curated_impressions }} curated)</span>` on one line.

This is purely a whitespace fix inside two template expressions. Surrounding HTML
indentation/wrapping for the static markup is unaffected.

### No-Schema Assertion

*This patch contains no schema changes, new public API endpoints, or global ADR updates.*
(Re-confirmed at build via `makemigrations --check`.) Template-only → Patch Track holds.

## 3. Task List

### T-01 — Red-first regression test (S)

Add a regression test to [`apps/dashboard/tests/test_views.py`](../../apps/dashboard/tests/test_views.py)
(in `MyAppsListTests`, which already drives `dashboard:my-apps` via the test client) that
fails on the current template and passes after T-02. It must cover **both** instances:

- Seed an accepted app for `self.dev` with at least one **curated** impression so the
  summaries card renders (use the `_impress` helper with `Surface.DIGEST`, the curated
  surface), then `GET` the My-apps view.
- Assert the rendered page contains the active window's human label (the default window's
  `.label`, e.g. "Last month") — proving the selected-window tag rendered.
- Assert the rendered page contains the literal curated-count value (e.g. the integer as a
  string) — proving the curated-count tag rendered.
- Assert `assertNotContains(response, "{{")` — a single broad guard that no template
  expression leaked to output (catches both instances and any future multiline tag).

- **DoD:** New test fails on the unpatched template for the right reason (literal `{{`
  present), and the existing dashboard suite is otherwise green.
- **Files Touched:** [`apps/dashboard/tests/test_views.py`](../../apps/dashboard/tests/test_views.py).

### T-02 — Join both multiline tags onto one line (S)

Fix both offending tags in
[`apps/dashboard/templates/dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html):
lines 32-33 (`{{ w.label }}`) and lines 58-59 (`{{ summary.curated_impressions }}`).

- **DoD:** T-01 passes; no other markup/attribute/class changes; the selector and the
  curated-count both render their values in a manual or test render.
- **Files Touched:** [`apps/dashboard/templates/dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html).

### T-03 — Verify, sweep-confirm, and write release artifacts (S)

- Run the full test suite — **must be green, no skips** (CLAUDE.md §6.6).
- `ruff check` clean; `manage.py check` clean.
- `makemigrations --check` → **no drift** (confirms the No-Schema Assertion).
- Re-run the multiline-tag sweep (regex over `*.html` for `{{…}}`/`{%…%}` spanning a
  newline) → **zero** matches remain.
- Rehearse rollback (DU-REL-1): `git revert` / stash the patch, confirm `check` + a slice
  of dashboard tests stay green on the reverted tree, restore.
- Write [`TEST_PLAN.md`](TEST_PLAN.md) (regression mapping) and
  [`RELEASE_NOTES.md`](RELEASE_NOTES.md) (change summary + rehearsed rollback).

- **DoD:** All checks pass; sweep returns zero multiline tags; both release artifacts
  written; BUG-003 ready to close in [`INDEX.md`](../INDEX.md) and
  [`issues/README.md`](../../issues/README.md).
- **Files Touched:** [`TEST_PLAN.md`](TEST_PLAN.md), [`RELEASE_NOTES.md`](RELEASE_NOTES.md)
  (+ no source beyond T-01/T-02).

---

## Source & triage (Coordinator, 2026-06-28)

_Preserved from triage; superseded by §1–§3 above where they overlap._ Root cause certain
and template-only; Patch Track scope gate **PASS** (no migration, no API, no global ADR).
The Planner's sweep upgraded the triage's "cheap insurance" step to a **confirmed second
instance** (line 58-59), now folded into T-02.
