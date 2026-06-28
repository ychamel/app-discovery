# TEST_PLAN.md — patch-my-apps-status-display

## Regression Tests

All four new tests live in
`apps/catalog/tests/test_pages_developer.DeveloperPagesTests`.

| Test | Assertion | Fails without patch |
|------|-----------|---------------------|
| `test_my_apps_heading_says_my_apps` | `assertContains "My Apps"` + `assertNotContains "My submissions"` | Yes — H1 + nav link both said "My submissions" |
| `test_my_apps_status_grouping_shows_group_headers` | `assertContains "Active"` + `assertContains "Awaiting Review"` | Yes — flat list, no section headings |
| `test_my_apps_accepted_app_has_live_page_link` | `assertContains pages:app-page URL` | Yes — no live-page link anywhere on card |
| `test_my_apps_pending_app_has_no_live_page_link` | `assertNotContains pages:app-page URL` | No (correctly absent pre-patch; continues correct post-patch) |

## Verification Run

```
python manage.py test
Ran 1004 tests in 27s — OK   (+4 vs. 1000 baseline)
ruff check .                  — All checks passed
manage.py check               — No issues (0 silenced)
manage.py makemigrations --check — No changes detected
```

## Rollback Rehearsal (DU-REL-1)

`git stash` → `manage.py check` clean + `makemigrations --check` no drift +
170 catalog tests green on reverted tree → `git stash pop` intact.

No migration exists, so the rollback is a pure `git revert` with no irreversible
database step.
