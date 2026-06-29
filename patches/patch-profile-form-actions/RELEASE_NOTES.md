# RELEASE_NOTES.md — `patch-profile-form-actions`

> Stage `P-build` change summary + rehearsed rollback. Source: [`BUG-002`](../../issues/BUG-002.md).
> Maintenance Engineer, 2026-06-28. Released local/dev (no prod target yet — D-11 staging pending).

## What changed

Resolves [`BUG-002`](../../issues/BUG-002.md) (High): on `/profile`, both the **Edit display
name** and **Delete my account** forms plain-`POST`ed to the JSON `/me` API
([`MeView`](../../apps/accounts/views.py#L200) answers only `GET`/`PATCH`/`DELETE` — no
`post()`), so the browser got a **405 Method Not Allowed** that `hx-boost` silently swallowed.
The page idled with no feedback; the display name never updated and the account never deleted.
The `data-method="patch"`/`"delete"` attributes were **dead markup** (no project JS reads them).

The fix stops routing human-flow form submissions through the JSON API and gives each action
its own server-rendered §9 handler — the established Post/Redirect/Get + Django messages
house pattern (interests / ratings / updates).

1. **Two new §9 views** ([`apps/accounts/views.py`](../../apps/accounts/views.py)):
   - `update_display_name` — `@login_required @require_POST`; validates with the existing
     [`DisplayNameForm`](../../apps/accounts/forms.py#L23) (same 1–80 char bound as the
     serializer), saves `display_name`, and redirects to the profile with a success/error
     message either way (the silent-idle symptom is gone).
   - `delete_my_account` — `@login_required @require_POST`; guarded on the hidden `confirm`
     field, it deletes via the one existing [`delete_account`](../../apps/accounts/services.py#L58)
     service, flushes the session, and lands on `home`. (Named `delete_my_account` so it does
     not shadow the imported `delete_account` service; `MeView` left byte-unchanged.)
2. **Two new §9 routes** ([`apps/accounts/urls.py`](../../apps/accounts/urls.py)):
   `profile/display-name` (`accounts:profile-display-name`) and `profile/delete`
   (`accounts:profile-delete`), in the server-rendered block — **not** the §5 API block.
3. **Re-pointed both forms** ([`accounts/profile.html`](../../apps/accounts/templates/accounts/profile.html)):
   each `action` now targets its new route; the dead `data-method` attributes are removed; the
   delete form keeps its `onsubmit` JS confirm and the hidden `confirm` input.

Reuses only existing code (`DisplayNameForm`, `delete_account`, `messages` + PRG) — **no new
shared helper, no [CODEMAP.md](../../CODEMAP.md) entry**.

## Who is affected

- **Signed-in users:** editing the display name now works and shows a confirmation/validation
  message; **Delete my account** works (confirm → delete → sign out → home). No more silent 405.
- **Downstream consumers of the JSON `/me` API:** **no change** — `MeView` (`GET`/`PATCH`/`DELETE`)
  is byte-for-byte unchanged; the §5 contract is untouched.

## Scope / safety

- **No schema, no migration, no new public API endpoint, no global ADR** — the two new URLs are
  server-rendered §9 human-flow routes, not §5 JSON contracts. `makemigrations --check` reports
  no drift. The [PATCH.md](PATCH.md) §2 No-Schema Assertion holds; stayed on the Patch Track.
- The delete view increments the same `DELETION_FULFILMENT` metric as the §5 API path, so the
  deletion count stays path-independent (no undercount now that humans delete via this route).

## Verification

- **997 tests green** (988 baseline + 9 new), 0 skipped · `ruff` clean · `manage.py check`
  clean · `makemigrations --check` = no drift. Mapping in [TEST_PLAN.md](TEST_PLAN.md).

## Rollback (rehearsed, DU-REL-1)

This patch adds no migration and no irreversible state, so revert is a clean code-only undo.

**Rehearsed:** the four changed files (`views.py`, `urls.py`, `profile.html`,
`tests/test_profile.py`) were stashed off the working tree; on the reverted tree
`manage.py check` was clean, `makemigrations --check` reported no drift, and the 91 baseline
accounts tests were green; the patch was then restored intact. Once committed, the production
rollback is `git revert` of the build commit — the forms revert to posting `/me` (back to the
known 405, no worse than pre-patch), and no data migration is needed.
