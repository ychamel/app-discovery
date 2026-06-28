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

## Brief — _pending_ (Maintenance Planner)

## Root-cause design — _pending_ (Maintenance Planner)

## Tasks — _pending_ (Maintenance Planner; ordered, T-01 = red-first regression test)
