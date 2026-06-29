# TEST_PLAN — `patch-dashboard-window-label`

Maps the [`BUG-003`](../../issues/BUG-003.md) reproduction to the passing regression test.

## Regression test

**Test:** `MyAppsListTests.test_template_tags_render_no_literal_braces`
in [`apps/dashboard/tests/test_views.py`](../../apps/dashboard/tests/test_views.py).

| Reproduction (PATCH §1) | Assertion | Why it catches the bug |
|---|---|---|
| Selected window renders literal `{{ w.label }}` | `assertContains(response, "Last month")` | The default window (`1m`) is selected on first load; its label only appears if the multiline `{{ w.label }}` tag tokenizes. |
| Card renders literal `{{ summary.curated_impressions }}` (sibling found by the sweep) | `assertContains(response, "(1 curated)")` | A `DIGEST` (curated, D-8) impression is seeded, so the curated count renders only if that tag tokenizes. |
| Any template expression leaking to output | `assertNotContains(response, "{{")` | One broad guard covering both instances **and** any future multiline tag in this view. |

**Red-first evidence:** on the unpatched template the test failed at the first
assertion, and the captured response body showed both literal tags
(`{{\n w.label }}` and `({{\n summary.curated_impressions }}`). After the fix all three
assertions pass.

## Verification run

- `python manage.py test` → **999 tests, OK** (was 998; +1 regression test).
- `ruff check apps/dashboard/` → clean.
- `python manage.py check` → no issues.
- `python manage.py makemigrations --check --dry-run` → **No changes detected** (No-Schema
  Assertion confirmed).
- Repo-wide multiline-tag sweep (regex over every `*.html` for `{{…}}`/`{%…%}` spanning a
  newline) → **0 matches** remaining.
