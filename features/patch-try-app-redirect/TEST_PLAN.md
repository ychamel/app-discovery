# TEST_PLAN.md — patch-try-app-redirect

**Source:** [`BUG-004`](../../issues/BUG-004.md) — "Try App" button stuck on platform URL.
**Build verified:** 2026-06-29 · Maintenance Engineer.

---

## Regression test

| ID | Test | File | Class | Result |
|----|------|------|-------|--------|
| RT-01 | `test_try_app_anchor_bypasses_htmx_boost` — asserts `hx-boost="false"`, `target="_blank"`, `rel="noopener noreferrer"` present in rendered `app_page.html`. **Red-first:** failed on unpatched template. **Green after:** T-02 fix applied. | `apps/pages/tests/test_template.py` | `FullyPopulatedTests` | PASS |

## Full suite

| Metric | Value |
|--------|-------|
| Tests run | 1 000 |
| Failures | 0 |
| Errors | 0 |
| Test count delta | +1 (RT-01) |

## Static analysis

| Check | Result |
|-------|--------|
| `ruff check .` | Clean |
| `python manage.py check` | Clean |
| `python manage.py makemigrations --check` | No drift (No-Schema Assertion held — template-only change) |

## Rollback rehearsal (DU-REL-1)

- `git stash` applied; reverted tree ran `manage.py check` (clean) + `makemigrations --check` (no drift) + `apps.pages` tests (42 tests, OK).
- `git stash pop` restored the patch intact.
- No migration → nothing irreversible; rollback = `git revert` of the build commit.
