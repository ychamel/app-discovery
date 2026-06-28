# RELEASE_NOTES — `patch-dashboard-window-label`

**Issue:** [`BUG-003`](../../issues/BUG-003.md) (Medium) · **Track:** Patch · **Stage:** closed-out

## What changed

The developer dashboard "My apps" view had two Django variable tags split across a
newline. Django's template lexer (`tag_re`) is compiled without `re.DOTALL`, so a
`{{ … }}` tag spanning two lines is never tokenized and leaks to the page as literal
text. Both tags were joined onto a single line — no markup, attributes, classes, or
copy changed.

- [`apps/dashboard/templates/dashboard/my_apps.html`](../../apps/dashboard/templates/dashboard/my_apps.html)
  - L32 — the **selected** reporting-period button: `{{ w.label }}` (the reported symptom).
  - L57-58 — the app card's curated count: `{{ summary.curated_impressions }}` (an
    unreported sibling with the same root cause, surfaced by a repo-wide sweep; it leaked
    `{{ summary.curated_impressions }}` whenever a developer had curated impressions).
- [`apps/dashboard/tests/test_views.py`](../../apps/dashboard/tests/test_views.py) — added
  `test_template_tags_render_no_literal_braces` (red-first regression test).

## Who is affected

Any developer viewing their dashboard. Before the fix the active reporting period showed
`{{ w.label }}` instead of its label, and (for developers with curated impressions) the
reach line showed `{{ summary.curated_impressions }}`. After the fix both render their
values. No data, schema, or API change — presentation only.

## Verification

999 tests green (+1); `ruff check`, `manage.py check`, and `makemigrations --check`
(no drift) all clean; the multiline-tag sweep now returns zero matches across all
templates.

## Rehearsed rollback (DU-REL-1)

The patch touches only one template and one test file, with no migration. Rollback is a
plain `git revert` of the patch commit. **Rehearsed:** stashing both changed files
returned the tree to a clean state — `manage.py check` and `makemigrations --check`
clean, all 60 `apps.dashboard` tests green — then the patch was restored intact. Nothing
in this patch is irreversible.
