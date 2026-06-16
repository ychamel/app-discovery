# TASKS — identity-accounts

*Stage 3 artifact (Planner / Tech Lead). Status: **complete — ready for Stage 4 (Senior
Engineer)**. Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md), [DESIGN.md](DESIGN.md). Every
task references the exact DESIGN.md section(s) and the acceptance criteria it satisfies,
per the traceability rule (CLAUDE.md §6.3). Produced by
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

---

## How to read this list

- Tasks are in **execution order**. Each is sized for one focused session and leaves the
  system **working and releasable** (vertical slices over horizontal layers).
- **Sequencing** follows DESIGN: scaffold → shared core → schema → core logic →
  API+UI slices → ops/security → telemetry → docs. Risk is front-loaded (the magic-link
  token logic, T-07, is the sharpest correctness edge and lands early).
- **Every `L` has been split** — no `L` tasks remain (Planner exit criterion).
- **Files/areas touched** are declared so parallel agents do not collide. Paths follow
  the layout fixed in [DESIGN.md §2](DESIGN.md) (shared-code root `apps/`, recorded in
  [CODEMAP.md](../../CODEMAP.md)).
- **Standards apply to every task** (CLAUDE.md §5): one function/one job, fail-loud,
  config over hardcoding, and **shared code must be registered in CODEMAP.md as part of
  definition-of-done** — a shared helper added without a CODEMAP entry is an incomplete
  task.

---

## Dependency overview

```
T-01 scaffold
 ├─ T-02 core.config ── T-04 rate-limit ─┐
 ├─ T-03 core.email ─────────────────────┤
 └─ T-05 data model ── T-06 role gate ───┤
                       └ T-07 magic-link ─┤ (needs T-03,T-05)
                                          ▼
                       T-08 register (needs T-04,T-06,T-07)
                          └ T-09 sign-in/verify/session
                               ├ T-10 sign-out
                               └ T-11 profile
                                    ├ T-12 developer self-serve (needs T-06)
                                    ├ T-13 account deletion
                                    └ T-14 admin grant/revoke (needs T-06)
                       T-15 mgmt commands (needs T-06,T-07)
                       T-16 security settings (needs T-08,T-09)
                       T-17 observability (needs T-08..T-15)
                       T-18 docs & deploy runbook (needs all)
```

---

## T-01 — Project scaffold & stack baseline
- **Description.** Stand up the Django project exactly as specified in
  [DESIGN.md §2](DESIGN.md): `config/` project (settings, root urls, asgi/wsgi), the
  `apps/` shared-code root with empty `core` and `accounts` apps registered, `pyproject.toml`
  (Python 3.12+, Django 5.x, DRF, psycopg, a linter/formatter), PostgreSQL connection via
  env, DRF + Django server-side sessions wired in settings, and `manage.py`. No domain
  models yet.
- **Dependencies.** none.
- **Definition of done.**
  - `python manage.py check` passes; the dev server boots with the console email backend.
  - `settings` reads DB + secrets from env (no secrets in code); DRF and the session
    middleware are installed and the `accounts`/`core` apps are in `INSTALLED_APPS`.
  - Linter/formatter configured and clean on the scaffold.
  - A README stub documents how to run locally (expanded in T-18).
- **Estimated size.** M.
- **Files/areas touched.** `config/`, `apps/core/__init__.py`, `apps/accounts/__init__.py`,
  `pyproject.toml`, `manage.py`, `README.md`.

## T-02 — Shared config tunables (`core.config`)
- **Description.** Implement `apps/core/config.py` providing **typed** access to the
  tunables DESIGN requires to be config-driven, never hardcoded
  ([DESIGN.md §5](DESIGN.md), §10): `LOGIN_TOKEN_TTL` (default 15 min), rate limits
  (default 5/email/hr, 20/IP/hr). Values resolve from Django settings/env with documented
  defaults.
- **Dependencies.** T-01.
- **Definition of done.**
  - Typed getters return the configured value or the documented default; an invalid value
    fails loudly at startup, not silently at use.
  - Unit tests cover default and override paths.
  - Registered in [CODEMAP.md](../../CODEMAP.md) (shared surface).
- **Estimated size.** S.
- **Files/areas touched.** `apps/core/config.py`, `apps/core/tests/test_config.py`, CODEMAP.

## T-03 — Shared email interface (`core.email` / EmailSender)
- **Description.** Implement the pluggable `EmailSender` from [DESIGN.md §6](DESIGN.md):
  the `Protocol` and a default implementation wrapping Django's email backend, with the
  concrete transport selected by `EMAIL_BACKEND` env config (console in dev). Send failures
  **fail loudly** (raise), never swallowed — this is the substrate AC2 relies on.
- **Dependencies.** T-01.
- **Definition of done.**
  - `EmailSender.send(to, template, context)` delivers via the configured backend; a
    backend failure propagates as a raised exception (verified by test with a failing backend).
  - Transport is env-selected, not hardcoded; console backend works in dev.
  - Unit tests: successful send invokes the backend; failure raises.
  - Registered in [CODEMAP.md](../../CODEMAP.md) (shared surface; the digest reuses it).
- **Estimated size.** S.
- **Files/areas touched.** `apps/core/email.py`, `apps/core/templates/` (email templates),
  `apps/core/tests/test_email.py`, settings (`EMAIL_BACKEND`), CODEMAP.

## T-04 — Shared rate-limit decorator (`core`)
- **Description.** Implement a config-driven request limiter used by the auth-request
  endpoints to satisfy the `429` contract and the email/link-bombing mitigation
  ([DESIGN.md §5](DESIGN.md) #1/#2, §10). Limits read from `core.config` (T-02):
  per-email and per-IP windows.
- **Dependencies.** T-02.
- **Definition of done.**
  - Decorator enforces the configured per-email and per-IP limits and returns `429` when
    exceeded; under the limit it is a no-op.
  - Unit tests cover under-limit pass, over-limit `429`, and window reset.
  - Registered in [CODEMAP.md](../../CODEMAP.md) (shared surface).
- **Estimated size.** S.
- **Files/areas touched.** `apps/core/ratelimit.py`, `apps/core/tests/test_ratelimit.py`,
  CODEMAP.

## T-05 — Data model & initial migration
- **Description.** Implement the three models and the seeding migration from
  [DESIGN.md §4](DESIGN.md): `Account` (custom `AbstractBaseUser` + `PermissionsMixin`,
  `USERNAME_FIELD=email`, UUID PK, `citext` unique email, `display_name`,
  `email_confirmed_at` nullable, `is_active`, **no password** via `set_unusable_password`,
  plus its manager), `LoginToken` (UUID PK, FK→account CASCADE, unique `token_hash`,
  `expires_at`, `consumed_at`), and `RoleGrant` (UUID PK, `target_account`/`granted_by`
  FKs **`on_delete=SET_NULL`**, `role`, `action` enum, immutable `created_at`). The
  migration enables the `citext` extension, creates the schema, and **seeds the
  `user`/`developer`/`admin` groups** ([DESIGN.md §4](DESIGN.md), §12 step 1).
- **Dependencies.** T-01.
- **Definition of done.**
  - Migration applies cleanly on a fresh PostgreSQL DB and seeds exactly the three groups;
    `citext` extension enabled.
  - Tests: account creation has **no usable password**; email uniqueness is
    case-insensitive; the required indexes exist (unique email, unique token_hash, FK
    indexes); `RoleGrant.granted_by` is nullable and a deleted account sets it NULL rather
    than blocking deletion.
  - `Account` registered in [CODEMAP.md](../../CODEMAP.md) (cross-feature identity key).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/models.py`, `apps/accounts/managers.py`,
  `apps/accounts/migrations/0001_*.py`, `apps/accounts/tests/test_models.py`,
  settings (`AUTH_USER_MODEL`), CODEMAP.

## T-06 — Role service & the single enforcement gate
- **Description.** Implement [DESIGN.md §3/§5](DESIGN.md): `apps/accounts/roles.py`
  (`USER`/`DEVELOPER`/`ADMIN` constants), `apps/accounts/permissions.py`
  (`HasRole(role)` DRF permission + `require_role(role)` view decorator, **fail-closed** on
  unknown role / lookup error), and `grant_role()/revoke_role()` services that write an
  immutable `RoleGrant` audit row. This is the one authorization point downstream features
  depend on.
- **Dependencies.** T-05.
- **Definition of done.**
  - `HasRole`/`require_role` allow only when the account holds the role; unknown role or
    any lookup error **denies** (closed) — verified by test.
  - `grant_role`/`revoke_role` append a `RoleGrant` row with the correct `action`; never
    update/delete existing audit rows.
  - The invariant "self-serve is limited to `developer`; no code path adds a privileged
    role except the admin endpoint" holds — there is no general self-grant function.
  - `roles.py` and `permissions.py` registered in [CODEMAP.md](../../CODEMAP.md).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/roles.py`, `apps/accounts/permissions.py`,
  `apps/accounts/services.py` (grant/revoke), `apps/accounts/tests/test_roles.py`, CODEMAP.

## T-07 — Magic-link issue & verify (risk-first)
- **Description.** Implement `apps/accounts/auth_backend.py` per [DESIGN.md §8](DESIGN.md)
  and the §4 concurrency rules: `issue_login_link(email, purpose)` (32-byte random token,
  stored **only** as SHA-256 hash, `expires_at = now + LOGIN_TOKEN_TTL`, delivered via
  `EmailSender`) and `verify_token(raw) -> Account` (atomic single-use consumption via
  `UPDATE ... WHERE id=? AND consumed_at IS NULL`, TTL check). This is the sharpest
  correctness edge, so it is built and tested in isolation before any endpoint wires it.
- **Dependencies.** T-03, T-05.
- **Definition of done.**
  - Raw token is never persisted (only its hash); verify enforces TTL and single-use.
  - Tests: happy path; **expired → rejected**; **already-consumed → rejected**; forged/
    unknown hash → rejected; **concurrent double-spend → exactly one succeeds** (the
    atomic-consume invariant, [DESIGN.md §4](DESIGN.md)).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/auth_backend.py`,
  `apps/accounts/tests/test_auth_backend.py`.

## T-08 — Registration flow (endpoint #1 + pages) — AC1, AC2
- **Description.** Implement endpoint **#1 `POST /auth/register`** and the **register** +
  **check-email** server-rendered pages ([DESIGN.md §5](DESIGN.md) #1, §9). Account is
  created in **one transaction** that also assigns the base `user` role (T-06); the
  magic-link is issued (T-07). Apply the rate-limit decorator (T-04). Errors per contract:
  `400` invalid, `409` email already registered (clear message + sign-in link), `429`,
  `503` email send failed — on `503` the account stays **unconfirmed** (never marked
  digest-eligible), per AC2.
- **Dependencies.** T-04, T-06, T-07.
- **Definition of done.**
  - Contract #1 statuses all returned; `user` role assigned in the creation transaction
    (no account ever lacks it); duplicate email → `409`; send failure → `503` with retry
    CTA and the account remains unconfirmed.
  - Register/check-email pages render the specified states (idle→submitting→check-email;
    email-taken / send-failed / invalid).
  - Tests cover AC1 (incl. duplicate refusal) and AC2 (send-failure surfaced, account not
    digest-eligible).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  `apps/accounts/templates/accounts/register.html`, `.../check_email.html`,
  `apps/accounts/tests/test_register.py`.

## T-09 — Sign-in, verify landing & session (endpoints #2, #3) — AC3, AC4
- **Description.** Implement **#2 `POST /auth/login`** (with the **generic "if an account
  exists, we sent a link"** response to avoid enumeration, [DESIGN.md §10](DESIGN.md)) and
  **#3 `GET /auth/verify`** (consume token via T-07, create the Django session, set
  `email_confirmed_at` on first verify, redirect to profile; `410` on expired/consumed/
  invalid with a resend CTA). Plus the **sign-in** and **verify-landing** pages
  ([DESIGN.md §9](DESIGN.md)). Rate-limit #2 (T-04).
- **Dependencies.** T-07, T-08.
- **Definition of done.**
  - #2 returns the generic `202` regardless of account existence; #3 creates a session and
    sets `email_confirmed_at` on first successful verify; `410` path shows resend CTA.
  - Tests cover AC3 (valid auth establishes session; invalid/expired denies, no session)
    and AC4 (re-authenticating via email returns the **same account with the same roles**).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  `apps/accounts/templates/accounts/signin.html`, `.../verify.html`,
  `apps/accounts/tests/test_signin.py`.

## T-10 — Sign-out (endpoint #4) — AC5
- **Description.** Implement **#4 `POST /auth/logout`** ([DESIGN.md §5](DESIGN.md) #4):
  flush the session, return `204`; expose a sign-out control in the UI.
- **Dependencies.** T-09.
- **Definition of done.**
  - `204` on logout; session fully flushed; a protected action afterward requires
    re-authentication.
  - Test covers AC5.
- **Estimated size.** S.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  profile template (sign-out control), `apps/accounts/tests/test_logout.py`.

## T-11 — Profile view/edit (endpoints #5, #6 + page) — AC7
- **Description.** Implement **#5 `GET /me`** (`{id,email,display_name,roles[],
  email_confirmed}`) and **#6 `PATCH /me`** (`{display_name}`, validated non-empty), plus
  the **Profile** page (view→editing→saved, error inline; shows roles held)
  ([DESIGN.md §5](DESIGN.md) #5/#6, §9). Both require a session (`401` otherwise).
- **Dependencies.** T-09.
- **Definition of done.**
  - #5/#6 contracts honored; `display_name` validation rejects empty/oversized with `400`;
    unauthenticated → `401`.
  - Profile page renders all specified states.
  - Test covers AC7 (name change saved and reflected by `GET /me`).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  `apps/accounts/serializers.py`, `apps/accounts/templates/accounts/profile.html`,
  `apps/accounts/tests/test_profile.py`.

## T-12 — Self-serve developer role (endpoint #8 + button) — AC6
- **Description.** Implement **#8 `POST /me/roles/developer`** ([DESIGN.md §5](DESIGN.md)
  #8): add the `developer` role to the **calling** account via `grant_role` (T-06), and a
  **"Become a developer"** button on the profile page. This is the only self-serve role.
- **Dependencies.** T-06, T-11.
- **Definition of done.**
  - `200` adds `developer` to self on the same account; `401` unauthenticated; a
    `RoleGrant` row is recorded.
  - Test covers AC6 (a `user` account takes `developer` and a developer action then
    succeeds on the **same** account, no second login).
- **Estimated size.** S.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  profile template (button), `apps/accounts/tests/test_developer_role.py`.

## T-13 — Account deletion (endpoint #7 + confirm) — AC8
- **Description.** Implement **#7 `DELETE /me`** with `{confirm:true}`
  ([DESIGN.md §5](DESIGN.md) #7, §4 lifecycle): in one transaction **hard-delete** the
  account, its tokens (CASCADE) and group memberships, then end the session. `RoleGrant`
  audit rows survive via `SET_NULL` (T-05). Add the confirm dialog on the profile page.
  `400` if confirm missing.
- **Dependencies.** T-11.
- **Definition of done.**
  - `204` deletes account+tokens+role memberships in one transaction and ends the session;
    missing confirm → `400`; deleted account can no longer sign in.
  - `RoleGrant` rows referencing the deleted account survive (no FK block).
  - Test covers AC8 (identity/credential/role/profile removed; tokens cascade-deleted;
    audit preserved).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  `apps/accounts/services.py` (deletion), profile template (confirm dialog),
  `apps/accounts/tests/test_deletion.py`.

## T-14 — Admin grant/revoke API + audit (endpoints #9, #10) — AC9
- **Description.** Implement **#9 `POST /admin/accounts/{id}/roles`** and **#10
  `DELETE /admin/accounts/{id}/roles/{role}`** ([DESIGN.md §5](DESIGN.md) #9/#10, §10),
  gated by `HasRole(ADMIN)` (T-06). Each grant/revoke records a `RoleGrant`. There is **no
  self-grant path**. Cold-start grants use Django's built-in admin site (staff only); this
  task supplies the API the future `editorial-curation-tools` calls.
- **Dependencies.** T-06, T-11.
- **Definition of done.**
  - #9: `200` + `RoleGrant` on success; `403` non-admin; `404` unknown target; `400`
    unknown role. #10: `204` + `RoleGrant`; same error set. Nothing mutated on the error
    paths ([DESIGN.md §11](DESIGN.md)).
  - Register the models on the Django admin site for cold-start grants.
  - Test covers AC9 (non-admin refused; self-grant impossible; granted admin succeeds via
    the same sign-in).
- **Estimated size.** M.
- **Files/areas touched.** `apps/accounts/views.py`, `apps/accounts/urls.py`,
  `apps/accounts/admin.py`, `apps/accounts/tests/test_admin_roles.py`.

## T-15 — Management commands (bootstrap + token purge)
- **Description.** Implement `manage.py create_admin <email>` (first-admin bootstrap — grant
  `admin`, record a `RoleGrant` with `granted_by = NULL`, [DESIGN.md §10](DESIGN.md), §12
  step 2) and `manage.py purge_expired_tokens` ([DESIGN.md §2](DESIGN.md), §12 step 5).
- **Dependencies.** T-06, T-07.
- **Definition of done.**
  - `create_admin` grants `admin` to an existing or newly-created account and writes the
    bootstrap audit row (`granted_by` NULL); idempotent on re-run.
  - `purge_expired_tokens` deletes expired/consumed tokens and reports the count.
  - Tests for both commands.
- **Estimated size.** S.
- **Files/areas touched.** `apps/accounts/management/commands/create_admin.py`,
  `.../purge_expired_tokens.py`, `apps/accounts/tests/test_commands.py`.

## T-16 — Security settings & transport hardening
- **Description.** Apply the [DESIGN.md §10](DESIGN.md) security posture in settings:
  session cookies `HttpOnly` + `Secure` + `SameSite=Lax`, CSRF enforced on all
  form posts (Django built-in), HTTPS enforced (`SECURE_*` settings), and confirm logs
  carry the account **UUID, never the raw email**.
- **Dependencies.** T-08, T-09.
- **Definition of done.**
  - Cookie flags and HTTPS/CSRF settings are set and verified by test where feasible
    (e.g. cookie flags, CSRF rejection of a form post without token).
  - No log line emits a raw email (review + a targeted test/assertion).
- **Estimated size.** S.
- **Files/areas touched.** `config/settings*.py`, `apps/accounts/tests/test_security.py`.

## T-17 — Observability (metrics, structured logs, health)
- **Description.** Implement [DESIGN.md §10](DESIGN.md) observability: structured logs with
  a request id + account UUID; metrics mapping 1:1 to the brief's success metrics —
  `registration_completion`, `signin_success_rate`/`auth_error_rate`,
  `unexpected_logout_rate`, `developer_role_adoption`,
  `role_gate_decisions{result=allow|deny}`, `email_send_failure`, `deletion_fulfilment`;
  a health endpoint checking DB + email reachability; and actionable alerts (auth-error
  spike, email-send-failure rate, **any** admin grant/revoke).
- **Dependencies.** T-08, T-09, T-10, T-11, T-12, T-13, T-14, T-15.
- **Definition of done.**
  - Each metric is emitted at the correct point (registration completion at confirm,
    role-gate decisions in the gate, etc.); the health endpoint returns DB + email status.
  - Structured logs carry request id + account UUID and never the raw email.
  - Tests for the health endpoint and at least one representative metric emission.
- **Estimated size.** M.
- **Files/areas touched.** `apps/core/observability.py` (or settings logging config),
  `apps/accounts/views.py` (metric hooks), health endpoint in `config/urls.py`,
  `apps/core/tests/test_health.py`, CODEMAP (if the observability helper is shared).

## T-18 — Docs & deploy runbook
- **Description.** Finalize operator + developer docs: README run instructions,
  `.env.example` listing **every** tunable (`EMAIL_BACKEND`, `LOGIN_TOKEN_TTL`, rate
  limits, DB/secret vars), and a deploy runbook following the exact order in
  [DESIGN.md §12](DESIGN.md) (apply migrations → `create_admin` → configure `EMAIL_BACKEND`
  + verify via health → enable registration/sign-in → schedule `purge_expired_tokens`),
  including the rollback path (revert deploy + last migration). Reconcile
  [CODEMAP.md](../../CODEMAP.md) so its entries match the shipped shared surface.
- **Dependencies.** all prior tasks.
- **Definition of done.**
  - Runbook reproduces the §12 deploy order and the rollback path; `.env.example` covers
    every tunable used in code; README lets a new dev run the app and tests.
  - CODEMAP reflects exactly the shared code that exists (no stale/missing entries).
- **Estimated size.** S.
- **Files/areas touched.** `README.md`, `.env.example`, `docs/deploy-identity-accounts.md`,
  CODEMAP.

---

## Coverage check (Planner exit criterion — every design element appears in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §2 stack & project layout | T-01 |
| §3 Account model | T-05 | 
| §3 Role service + gate | T-06 |
| §3 Magic-link auth | T-07 |
| §3 Session lifecycle | T-09 (create), T-10 (end), T-16 (cookies) |
| §3 Profile | T-11 |
| §3 Account deletion | T-13 |
| §3 EmailSender | T-03 |
| §3 Admin grant path | T-14 |
| §4 data model + groups seed + citext + on_delete | T-05 |
| §4 audit-row writes | T-06, T-14, T-15 |
| §5 #1 register | T-08 |
| §5 #2 login / #3 verify | T-09 |
| §5 #4 logout | T-10 |
| §5 #5/#6 profile | T-11 |
| §5 #7 delete | T-13 |
| §5 #8 developer self-serve | T-12 |
| §5 #9/#10 admin roles | T-14 |
| §6 email failure handling | T-03 (interface), T-08 (503) |
| §8 auth flow | T-07, T-08, T-09 |
| §9 UX pages | T-08, T-09, T-11, T-12, T-13 |
| §10 perf (indexes) | T-05 |
| §10 rate limiting | T-04, T-08, T-09 |
| §10 enumeration (generic login) | T-09 |
| §10 security cookies/CSRF/HTTPS/PII | T-16 |
| §10 first-admin bootstrap | T-15 |
| §10 observability + health + alerts | T-17 |
| §11 failure modes | distributed across endpoint DoDs; health T-17 |
| §12 rollout order (migrate→bootstrap→email→enable→purge) | T-05, T-15, T-18 |
| §14 all 10 ACs | AC1/AC2 T-08 · AC3/AC4 T-09 · AC5 T-10 · AC6 T-12 · AC7 T-11 · AC8 T-13 · AC9 T-14 · AC10 T-06+T-09 (one gate, one access method) |

All design elements are covered; all tasks have a definition of done; no `L` tasks remain.

> **Note for Stage 4 (Senior Engineer):** the `TEST_PLAN.md` you produce must show every
> acceptance criterion (AC1–AC10) is exercised by the tests in these tasks — the
> AC→task column above is the starting map.
