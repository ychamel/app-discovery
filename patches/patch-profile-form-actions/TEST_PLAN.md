# TEST_PLAN.md — `patch-profile-form-actions`

> Stage `P-build` regression test mapping. Source: [`BUG-002`](../../issues/BUG-002.md).
> Maintenance Engineer, 2026-06-28. All tests written **red-first** (T-01) before the fix.

## How the bug reproduces → which test guards it

BUG-002 (High): both profile forms plain-`POST` to the JSON `/me` API ([`MeView`](../../apps/accounts/views.py#L200)
has no `post()`) → **405**, swallowed by `hx-boost` → the page idles with no feedback. The fix
re-points each form at a dedicated server-rendered §9 handler (PRG + Django messages). Every
case below fails on pre-patch `main` (the `profile-display-name` / `profile-delete` routes do
not exist → `NoReverseMatch`) and passes after the fix.

All cases live in [`apps/accounts/tests/test_profile.py::ProfileFormActionTests`](../../apps/accounts/tests/test_profile.py).

| # | Reproduction (from [PATCH.md](PATCH.md) §1) | Regression test | Pre-patch | Post-patch |
|---|---------------------------------------------|-----------------|-----------|------------|
| 1 | Saving a valid display name 405s + idles | `test_valid_display_name_update_redirects_and_persists` | **FAIL** (route absent) | PASS — 302→profile, name persisted, success message |
| 2 | Empty/whitespace name must not change the name or 500 | `test_blank_display_name_is_rejected_without_changing_the_name` | **FAIL** | PASS — name unchanged, error message, 200 (no 500) |
| 3 | Display-name route is POST-only | `test_display_name_route_is_post_only` | **FAIL** | PASS — `GET` → 405 |
| 4 | Display-name route is login-required | `test_display_name_route_requires_login` | **FAIL** | PASS — anon → redirect to sign-in |
| 5 | Confirmed delete 405s instead of deleting | `test_confirmed_delete_removes_account_and_logs_out` | **FAIL** | PASS — account row gone, session flushed, 302→home |
| 6 | A delete without confirm must leave the account intact | `test_unconfirmed_delete_keeps_the_account` | **FAIL** | PASS — account untouched, error message |
| 7 | Delete route is POST-only | `test_delete_route_is_post_only` | **FAIL** | PASS — `GET` → 405 |
| 8 | Delete route is login-required | `test_delete_route_requires_login` | **FAIL** | PASS — anon → redirect to sign-in, account untouched |
| 9 | The page must wire both forms to the new routes, not `/me` | `test_profile_page_posts_forms_to_the_new_routes_not_the_api` | **FAIL** | PASS — both `action`s point at the new routes; no `accounts:me` form action remains |

The pre-existing `MeApiTests` (the §5 JSON `/me` contract) stay green **unchanged** — the
patch left `MeView` byte-for-byte intact, so every downstream consumer of `/me` is unaffected.

## Red-first evidence

Before any fix code, the suite was run with only the T-01 tests present. The
`profile-display-name` / `profile-delete` routes did not exist, so
`reverse("accounts:profile-display-name")` raised
`NoReverseMatch: Reverse for 'profile-display-name' not found` — all 9 cases failed exactly
as the defect predicts (the forms had nowhere correct to post). After T-02–T-04, all 9 pass.

## Verification gate (Stage `P-build` exit)

Run from the repo root in the project venv:

```
python manage.py test            # 997 passed (988 baseline + 9 new), no skips
ruff check apps/accounts         # All checks passed
python manage.py check           # no issues
python manage.py makemigrations --check --dry-run   # No changes detected (No-Schema Assertion holds)
```

- **997 tests green**, 0 skipped (9 new in `ProfileFormActionTests`).
- **`ruff` clean · `check` clean · `makemigrations --check` = no drift** — proves the patch
  touched no model (`display_name` and the `delete_account` service already existed),
  confirming the [PATCH.md](PATCH.md) §2 No-Schema Assertion and that the work correctly
  stayed on the Patch Track.

## Manual check (matches PATCH.md reproduction)

As a signed-in user at `/profile`: editing the display name now refreshes with a success/error
message (no silent idle, no 405). **Delete my account** (after the JS confirm) removes the
account, signs out, and lands on the home page. Both server logs show `302`, not `405 /me`.
