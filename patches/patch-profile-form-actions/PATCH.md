# PATCH.md — `patch-profile-form-actions`

> **Stage P-plan artifact.** Consolidated brief + root-cause design + task list.
> The **Coordinator** seeded the *Source & triage* section below; the rest is
> **_pending_** — to be written by the **Maintenance Planner** ([../../process/personas/patch-1-planner.md](../../process/personas/patch-1-planner.md)).

## Source & triage (Coordinator, 2026-06-28)

- **Source issue:** [`BUG-002`](../../issues/BUG-002.md) — *Profile display name update fails with 405 Method Not Allowed and idles* (Severity: **High**).
- **Confirmed against live code:**
  - The server-rendered profile page [`accounts/profile.html`](../../apps/accounts/templates/accounts/profile.html) wires **two** plain HTML `<form method="post">` controls at the JSON API endpoint `accounts:me`:
    - the **Edit display name** form ([profile.html:37](../../apps/accounts/templates/accounts/profile.html#L37), `data-method="patch"`), and
    - the **Delete my account** form ([profile.html:81](../../apps/accounts/templates/accounts/profile.html#L81), `data-method="delete"`).
  - `data-method` is **dead markup**: a repo-wide search finds it only on these two forms, and there is **no project JavaScript at all** (the only script asset is the vendored `core/vendor/htmx.min.js`). `hx-boost` does **not** read `data-method` — it submits with the form's real `method` (POST).
  - The target [`MeView`](../../apps/accounts/views.py#L200) is a DRF `APIView` exposing only `get`/`patch`/`delete` — **no `post()`** → Django/DRF returns **405**. Because `hx-boost` does not swap error responses, the page idles with **no feedback**.
  - **Same root cause affects both forms** (edit *and* delete), so this patch must fix both.
- **Scope-gate decision → Patch Track.** `Account.display_name` and the [`delete_account`](../../apps/accounts/services.py) service already exist → **no migration / no schema**. The intended fix is dedicated **server-rendered POST handler(s)** in the accounts §9 human-flow style (where `register`/`signin`/`logout` already live), leaving the §5 JSON `/me` API contract that downstream features consume **untouched** → no public-API-contract change, no global ADR. The Patch Track scope gate ([CLAUDE.md](../../CLAUDE.md) §2) holds. *(If the Planner finds the clean fix cannot avoid changing the `/me` contract or a migration, escalate and re-route to Feature Track.)*

## 1. Problem Statement

### Reproduction Steps
1. Log in and navigate to `/profile` ([`accounts/profile.html`](../../apps/accounts/templates/accounts/profile.html)).
2. Under **Account Information → Edit display name**, type a new name and click **Save**.
3. The page idles: no refresh, no success/error message. Server logs show
   `"POST /me HTTP/1.1" 405 40` / `Method Not Allowed: /me`.
4. The same failure occurs for **Delete my account** (the form at
   [profile.html:81](../../apps/accounts/templates/accounts/profile.html#L81)): a `POST /me`
   that 405s and is swallowed.

### Root Cause Analysis
Two plain HTML forms post to the **JSON API** endpoint, which has no POST handler:

- [profile.html:37](../../apps/accounts/templates/accounts/profile.html#L37) — the edit form is
  `<form method="post" action="{% url 'accounts:me' %}" data-method="patch">`.
- [profile.html:81](../../apps/accounts/templates/accounts/profile.html#L81) — the delete form is
  `<form method="post" action="{% url 'accounts:me' %}" data-method="delete">`.
- `accounts:me` resolves ([urls.py:24](../../apps/accounts/urls.py#L24)) to
  [`MeView`](../../apps/accounts/views.py#L200), a DRF `APIView` implementing only
  `get` / `patch` / `delete` (views.py [203](../../apps/accounts/views.py#L203) /
  [206](../../apps/accounts/views.py#L206) / [213](../../apps/accounts/views.py#L213)) — **no
  `post()`**. An HTML form can only emit GET or POST, so the browser sends `POST /me` → DRF
  returns **405 Method Not Allowed**.
- `data-method` is **dead markup**. A repo-wide search finds it on only these two forms, and the
  repo ships **no project JavaScript** — the sole script asset is vendored
  [`core/vendor/htmx.min.js`](../../apps/core/static/core/vendor/htmx.min.js). `hx-boost` (set on
  `<main>` in [`core/base.html`](../../apps/core/templates/core/base.html#L47)) submits the form's
  *real* method (POST) and **does not read `data-method`**, nor does it swap non-2xx responses — so
  the 405 is discarded with no UI feedback (the "idles silently" symptom).

**One root cause, both forms:** each posts a non-POST-able verb at the JSON API. The clean fix is to
stop routing human-flow form submissions through the `/me` API at all.

## 2. Proposed Fix / Change

### Code-level Design
Give each profile action its own **server-rendered §9 handler** (the style `register` / `signin` /
`logout` already use), using **Post/Redirect/Get + the Django messages framework** — the exact
convention already followed by `interests`, `ratings`, `subscriptions`, and `updates` views. The
JSON `/me` API ([`MeView`](../../apps/accounts/views.py#L200)) is left **byte-unchanged**, so every
downstream consumer of the §5 contract is unaffected.

Two new thin views in [`apps/accounts/views.py`](../../apps/accounts/views.py), in the §9 block:

- **`update_display_name(request)`** — `@login_required` + `@require_POST`. Validate with the
  **already-existing** [`DisplayNameForm`](../../apps/accounts/forms.py#L23) (same bounds as the
  serializer: 1–80 chars, stripped). On valid: set `request.user.display_name` and
  `save(update_fields=["display_name"])`, `messages.success(...)`, `redirect("accounts:profile")`.
  On invalid: `messages.error(...)`, `redirect("accounts:profile")`. (PRG — the user sees feedback,
  fixing the silent-idle symptom too.)
- **`delete_account(request)`** *(view; distinct from the service)* — `@login_required` +
  `@require_POST`. Guard on the existing hidden `confirm` field (`request.POST.get("confirm") ==
  "true"`); on confirm, call the **already-existing** service
  [`services.delete_account(request.user)`](../../apps/accounts/services.py#L58), then `auth_logout`,
  then `redirect("home")` (the landing route, [config/urls.py:55](../../config/urls.py#L55)). A flash
  message is **not** used here because `auth_logout` flushes the session, so it could not survive the
  redirect — the landing page is the confirmation. On missing/false confirm:
  `messages.error(...)`, `redirect("accounts:profile")` (account untouched).
  > To avoid shadowing the imported service, import it as `from apps.accounts import services` and
  > call `services.delete_account(...)`, or alias the view name — the Engineer picks one and keeps it
  > readable (prime directive).

Two new routes in [`apps/accounts/urls.py`](../../apps/accounts/urls.py), in the **server-rendered
(§9)** block (not the §5 API block):

- `path("profile/display-name", views.update_display_name, name="profile-display-name")`
- `path("profile/delete", views.delete_account, name="profile-delete")`

Re-point the two forms in [`profile.html`](../../apps/accounts/templates/accounts/profile.html):

- edit form `action` → `{% url 'accounts:profile-display-name' %}`; **drop** the dead
  `data-method="patch"`.
- delete form `action` → `{% url 'accounts:profile-delete' %}`; **drop** the dead
  `data-method="delete"`; **keep** `onsubmit="return confirm(...)"` and the hidden `confirm` input.

Reuse only: `DisplayNameForm` (exists), `services.delete_account` (exists), `messages` + PRG
(established pattern). **No new shared helper → no [CODEMAP.md](../../CODEMAP.md) entry.**

### No-Schema Assertion
*This patch contains no schema changes, no new public API endpoints, and no global ADR updates.* The
two new URLs are **server-rendered §9 human-flow routes**, not §5 JSON API contracts; the public
`/me` API consumed by downstream features is untouched. No model field is added or altered
(`display_name` and the `delete_account` service already exist) → `makemigrations --check` must
report **no drift**. The Patch Track scope gate ([CLAUDE.md](../../CLAUDE.md) §2) holds.

## 3. Task List

> Sizes S/M only. **T-01 is red-first** (written and failing before any fix code). Each task states
> its Definition of Done (DoD) and Files Touched.

- **T-01 — Red-first regression tests (S).**
  Add a `ProfileFormActionTests` class to
  [`apps/accounts/tests/test_profile.py`](../../apps/accounts/tests/test_profile.py) asserting the
  **fixed** behaviour, so it fails against today's code (routes/views absent):
  - authed `POST accounts:profile-display-name` with a valid name → `302` to `accounts:profile`,
    `display_name` updated in the DB, a success message present;
  - empty/whitespace name → `302` to profile, name **unchanged**, an error message, no `500`;
  - authed `POST accounts:profile-delete` with `confirm=true` → account row deleted, session
    logged out (a follow-up `GET accounts:profile` redirects to sign-in), `302` to `home`;
  - `POST accounts:profile-delete` **without** `confirm` → account **not** deleted, redirected with
    an error;
  - both new routes are POST-only (`GET` → `405`) and login-required (anonymous → redirect to
    sign-in);
  - `GET accounts:profile` HTML now points the two forms at the new routes (`assertContains` the new
    `action` URLs; the page no longer posts the forms to `accounts:me`).
  **DoD:** tests added and **failing** for the right reason (route reverse / 405), suite otherwise
  green. **Files:** `apps/accounts/tests/test_profile.py`.

- **T-02 — Add the two server-rendered §9 views (S).**
  Implement `update_display_name` and the delete view in the §9 block of
  [`apps/accounts/views.py`](../../apps/accounts/views.py) per the design (PRG + `messages`; reuse
  `DisplayNameForm` and `services.delete_account`; resolve the service/view name clash readably).
  **DoD:** both views implemented; no change to `MeView`. **Files:** `apps/accounts/views.py`.

- **T-03 — Add the two §9 routes (S).**
  Add `profile-display-name` and `profile-delete` to the server-rendered block of
  [`apps/accounts/urls.py`](../../apps/accounts/urls.py); leave the §5 API routes unchanged.
  **DoD:** both routes reverse; `manage.py check` clean. **Files:** `apps/accounts/urls.py`.

- **T-04 — Re-point the two forms + remove dead markup (S).**
  In [`profile.html`](../../apps/accounts/templates/accounts/profile.html) set each form's `action`
  to its new route and delete the now-meaningless `data-method` attributes; keep `csrf_token`, the
  delete `onsubmit` confirm, and the hidden `confirm` input.
  **DoD:** T-01 tests pass; the page renders with no `accounts:me` form action. **Files:**
  `apps/accounts/templates/accounts/profile.html`.

- **T-05 — Verify + no-schema gate (S).**
  Run the full suite (must be green, no skips), `ruff`, `manage.py check`, and **`makemigrations
  --check` (expect no drift — proves the No-Schema Assertion)**. Rehearse rollback (DU-REL-1: stash
  the patch → `check`/no-drift/accounts tests green on the reverted tree → restore). Write
  [`TEST_PLAN.md`](TEST_PLAN.md) (map each AC/repro step to a test) and
  [`RELEASE_NOTES.md`](RELEASE_NOTES.md).
  **DoD:** suite green, lint/check clean, **no migration drift**, rollback rehearsed, both artifacts
  written. **Files:** `features/patch-profile-form-actions/TEST_PLAN.md`,
  `features/patch-profile-form-actions/RELEASE_NOTES.md`.
