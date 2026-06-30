# TEST_PLAN.md — interface-cleanup

*Stage 4 (Senior Engineer) — In Progress.*

## 1. Unit & Integration Tests

### T-02: Design System Alignment Guard
- **File:** [test_design_system.py](file:///home/ychamel/Desktop/Apps/app-discovery/apps/core/tests/test_design_system.py)
- **Tests implemented:**
  1. `test_design_system_definitions`:
     - Verifies that regression anchors added in T-01 (`--font-size-md`, `--font-size-4xl`, `--space-0.5`, `--space-1.5`, `--space-2.5`, `--space-3.5`, `.btn--sm`) are present in `app.css`.
  2. `test_design_system_tokens_alignment`:
     - Parses `app.css` for all defined tokens (`--name:`).
     - Scans `app.css` and all non-widget HTML templates (excluding `apps/widget/`) for references to custom properties via `var(--name)`.
     - Asserts `referenced_tokens ⊆ defined_tokens`.
  3. `test_design_system_classes_alignment`:
     - Parses `app.css` for all defined class names.
     - Scans all non-widget HTML templates for references to component/utility classes of interest (e.g., matching known prefixes like `btn--`, `badge--`, `legend-swatch--`, or exact component names).
     - Asserts `referenced_classes ⊆ defined_classes`.

---

## 2. Regression Checklist

- [x] Run Django test suite to verify no existing tests are broken by token definitions or sidebar button layout alterations:
  - Command: `.venv/bin/python manage.py test`
  - Result: 1095 tests passed.
- [x] Check that `makemigrations --check` reports no database schema drift (presentation-only workstream):
  - Result: Verified (no changes to database models).
- [x] Verify design system guard fails on missing definitions:
  - Action during dev: Removed token `--space-3.5` from `app.css` and saw `test_design_system_tokens_alignment` fail with the expected error.
  - Action during dev: Restored `--space-3.5` and saw test suite run clean.

---

## 3. Acceptance Self-Check (Non-binding)

| Verification / Story | Status | Notes |
|---|---|---|
| AC-1 / M1: Tokens & small button defined | Pass | `--font-size-md`, `--space-0.5`, `--space-1.5`, `--space-2.5`, `--space-3.5`, `--font-size-4xl` defined. `.btn--sm` defined. |
| AC-2: Specificity override gone | Pass | Override block deleted. Layout now driven by `.app-page-sidebar form` and `.app-page-sidebar .btn`. |
| AC-6c / T-10: Picker no-JS / dedupe | Pass | Verified by view-context duplicate filter and deleting the JS sync script. `test_duplicate_tags_are_deduplicated_in_render` checks that tags are only rendered once. |
| AC-3 / T-11: Form-field idiom & grouping | Pass | Form fields styled consistently. Required and optional fields visually separated using card-layout fieldsets with descriptive legends. `demo_clip_alt` hint promoted to a persistent visible note. |
