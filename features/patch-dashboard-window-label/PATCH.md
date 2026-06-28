# PATCH — `patch-dashboard-window-label`

**Source issue:** [`BUG-003`](../../issues/BUG-003.md) (Medium) — selected reporting
period renders literal `{{ w.label }}` in the developer dashboard.

**Stage:** `P-plan` — _pending Maintenance Planner._

---

## Source & triage (Coordinator, 2026-06-28)

Triaged against live code. **Root cause is certain and template-only.**

- [`apps/dashboard/templates/dashboard/my_apps.html:32-33`](../../apps/dashboard/templates/dashboard/my_apps.html#L32-L33)
  splits the active-window `{{ w.label }}` variable tag across two lines.
- Django's `tag_re` (`django/template/base.py`) is compiled **without** `re.DOTALL`,
  so a `{{ … }}` tag spanning a newline is not tokenized and is emitted as literal
  text. Verified on Django 5.2.15.
- Only the selected window uses the multiline form; the non-selected branch
  ([:36](../../apps/dashboard/templates/dashboard/my_apps.html#L36)) is single-line and
  renders fine — matching the reported symptom (only the *selected* period is wrong).

## Patch Track scope gate

PASS — presentation-layer template fix only. **No** migration, **no** API change, **no**
global ADR. No-Schema Assertion holds (to be re-confirmed by `makemigrations --check`
at build).

## Proposed fix (for the Planner to finalize)

1. Join the variable tag onto one line:
   `…>{{ w.label }}</span>` at [my_apps.html:32-33](../../apps/dashboard/templates/dashboard/my_apps.html#L32-L33).
2. Sweep the other dashboard / shared templates for the same multiline `{{ … }}` /
   `{% … %}` pattern (cheap insurance) and fix any found.
3. Red-first regression test: render the dashboard "My apps" view and assert the
   selected window's label appears and the literal string `{{ w.label }}` does **not**.

_Planner: replace this section with the ordered task list (T-01 = red-first test)._
