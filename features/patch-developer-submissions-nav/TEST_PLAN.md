# TEST_PLAN.md — `patch-developer-submissions-nav`

> Stage `P-build` regression test mapping. Source: [`UX-003`](../../issues/UX-003.md).
> Maintenance Engineer, 2026-06-28. All tests written **red-first** (T-01) before the fix.

## How the bug reproduces → which test guards it

The defect (UX-003) was pure **reachability**: the submissions surfaces exist and work,
but nothing in the UI linked to them, so a developer's pending/withdrawn/rejected apps
were unreachable once they navigated away. Each gap below now has a test that fails on
pre-patch `main` and passes after the fix.

| # | Reproduction (from [PATCH.md](PATCH.md) §1) | Regression test | Pre-patch | Post-patch |
|---|---------------------------------------------|-----------------|-----------|------------|
| 1 | Header shows no link to the submissions list for a developer | [`test_header_nav.py::HeaderSubmissionsLinkTests::test_present_for_developer`](../../apps/core/tests/test_header_nav.py) | **FAIL** (no link) | PASS |
| 2 | The new link must NOT leak to a plain authenticated user | `…::test_absent_for_plain_user` | PASS | PASS |
| 3 | The new link must NOT show to an anonymous visitor | `…::test_absent_for_anonymous` | PASS | PASS |
| 4 | Dashboard empty state dead-ends with only "Submit" | [`test_views.py::MyAppsListTests::test_empty_state_links_to_submissions`](../../apps/dashboard/tests/test_views.py) | **FAIL** (no submissions link) | PASS |
| 5 | No template-side way to detect the developer role | [`test_role_tags.py::IsDeveloperTagTests`](../../apps/accounts/tests/test_role_tags.py) (3 cases: dev/user/anon) | **FAIL** (`account_roles` library absent → `TemplateSyntaxError` at collection) | PASS |
| 6 | Submissions list has no path back to the analytics dashboard | [`test_pages_developer.py::DeveloperPagesTests::test_my_apps_links_to_dashboard`](../../apps/catalog/tests/test_pages_developer.py) | **FAIL** (no dashboard link) | PASS |

The negative cases (2, 3) were already green pre-patch and **stay** green — they prove the
developer-gated link mirrors the view's `@require_role(developer)` gate and never shows to
an account that would receive a 403 on click.

## Red-first evidence

Before any fix code, the suite was run with only the T-01 tests present. The `is_developer`
tag library did not exist, so `{% load account_roles %}` raised
`TemplateSyntaxError: 'account_roles' is not a registered tag library` — the reachability
cases failed exactly as the defect predicts. After T-02–T-05, all cases pass.

## Verification gate (Stage `P-build` exit)

Run from the repo root in the project venv:

```
python manage.py test            # 988 passed (980 baseline + 8 new), no skips
ruff check apps/ config/         # All checks passed
python manage.py check           # no issues
python manage.py makemigrations --check --dry-run   # No changes detected (No-Schema Assertion holds)
```

- **988 tests green**, 0 skipped (8 new: 3 tag + 3 header + 1 dashboard + 1 catalog).
- **`ruff` clean · `check` clean · `makemigrations --check` = no drift** — proves the patch
  is presentation-only (no migration), confirming the [PATCH.md](PATCH.md) §2 No-Schema
  Assertion and that the work correctly stayed on the Patch Track.

## Manual check (matches PATCH.md verification summary)

As a `developer`: header → **My submissions** reaches all statuses; the dashboard empty
state and sub-nav reach the submissions list; the submissions list → **View analytics**
reaches the dashboard. Anonymous and plain-`user` headers render unchanged.
