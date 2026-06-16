# RELEASE_NOTES — identity-accounts

*Stage 5 artifact (Release Engineer). Status: **ready to ship** — build verified green and
rollback rehearsed (2026-06-17).* Sources: verified Stage-4 build,
[DESIGN.md §12](DESIGN.md) (rollout), [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (success
metrics / error conditions), and the operator [deploy runbook](../../docs/deploy-identity-accounts.md).

---

## 1. What this release is

The platform's **identity foundation**: one email-based account per person, a single
passwordless sign-in for every role, an extensible role model (**user** / **developer** /
**admin**), and the account lifecycle (register, sign in/out, profile, self-serve
developer role, admin grant/revoke, account deletion). This is the first feature shipped
and the **stable cross-feature identity contract** every later feature keys off
(global [D-3](../../DECISIONS.md)).

It satisfies all ten acceptance criteria AC1–AC10 (mapping in
[TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since "no platform existed")

- **Auth & sessions** — passwordless **magic-link** sign-in (hash-only storage,
  single-use, atomic consume; [DL-3](DECISIONS.md)). Surfaces: `/auth/register`,
  `/auth/signin`, `/auth/verify`, `/auth/logout`.
- **Roles & authorization** — Django Groups as roles seeded by migration 0001
  (`user`/`developer`/`admin`), a single **fail-closed** role gate (`HasRole` /
  `require_role`), and **audited** grant/revoke recording a `RoleGrant` row
  ([DL-4](DECISIONS.md)).
- **Profile** — view/edit display name (`/profile`, JSON `/me`).
- **Self-serve developer role** — `POST /me/roles/developer`.
- **Admin grant/revoke** — `/admin/accounts/...` (admin-gated; never self-assignable).
- **Account deletion** — hard-delete of identity/credential/role/profile data.
- **Operability** — `GET /health` (DB + email reachability), structured logs keyed by
  `request_id` + `account_id` (UUID, never raw email), operational metrics, and the
  `create_admin` / `purge_expired_tokens` management commands.

## 3. Who is affected

- **End users / developers** — can now create an account and sign in; developers can
  self-serve the developer role on the same identity.
- **Operators / editors** — authenticate through the *same* sign-in; privileged work is
  gated on a granted **admin** role (the admin *tooling* itself ships later in
  `editorial-curation-tools`).
- **Downstream feature teams** — may now build against the account + role contract.
  **Action required of them:** any feature that owns data referencing an account must
  define its own deletion behavior (cascade/reassign) for AC8's hard-delete — this
  feature deletes only identity data (see Known limitations and
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).

## 4. How to use it (operators)

Deploy strictly per the [deploy runbook](../../docs/deploy-identity-accounts.md), which
implements [DESIGN.md §12](DESIGN.md):

1. `python manage.py migrate` (schema + `citext` + seed the three role groups).
2. `python manage.py create_admin you@example.com` (cold-start first admin; idempotent).
3. Configure `EMAIL_BACKEND` + `PUBLIC_BASE_URL`; verify with `curl -fsS https://<host>/health`
   (must report `email: true`).
4. Route public traffic to the auth surfaces.
5. Schedule `python manage.py purge_expired_tokens` (e.g. hourly cron).

**Required prod env** (see [`.env.example`](../../.env.example)): `DJANGO_DEBUG=false`, a
strong `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`, a real `EMAIL_BACKEND`, and a
**shared** `CACHES` backend (e.g. Redis) so rate-limit counters hold across workers.

## 5. Rollout strategy

> **Current deployment target: local / development only** (the platform is still
> mid-development — decided 2026-06-17). The feature is verified locally — migrations
> apply on a local Postgres, `/health` is green, 108 tests pass. **Production promotion
> (a live host, a real `EMAIL_BACKEND`, a shared `CACHES`) and the live-metrics
> monitoring window are deferred** until the platform approaches launch; the gate table
> and §4 procedure below are the plan for that future promotion, not something executed
> now.

This is the **first** feature — there is no pre-existing behavior to protect, so no phased
percentage flag applies. Safety comes from a **reversible migration** + the **ordered
procedure** above rather than a kill switch (an honest deviation from the generic
internal→%→full template, justified by "nothing to ramp against").

Promotion is therefore gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate` applied; `/health` → `200` (DB + email both reachable). |
| Internal smoke | Operator completes a real magic-link sign-in; `create_admin` admits them to `/django-admin/`. |
| Open to users | `auth_error` rate near zero on legitimate traffic; no `email_send_failure` spikes for the first hour. |
| Stable at target | Above holds for the monitoring window with no Sev-1/Sev-2 (see §7). |

## 6. Rollback (rehearsed)

**One action: revert the deploy to the previous release.** If the schema must also be
undone (only safe on a fresh/empty deployment — reverting destroys identity data):

```bash
python manage.py migrate accounts zero
```

**Rehearsed 2026-06-17** on a throwaway PostgreSQL database: migration 0001 applied
(5 `accounts_*` tables + `citext` extension + `user`/`developer`/`admin` groups), then
`migrate accounts zero` reversed it cleanly to **0 tables, 0 groups**. The initial
migration is confirmed reversible. **Who can trigger:** any operator with deploy access
and the DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

`GET /health` → `200` only when DB **and** email are reachable, `503` otherwise. Metrics
are emitted via `apps.core.observability.increment`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| Registration completion rate | `registration_completion` | drop-off / sustained zero after traffic. |
| Sign-in success / auth-error rate | `signin_success`, `auth_error` | **auth-error spikes**. |
| Unexpected-logout rate | `signout` vs. session expiry | anomalous logout rate. |
| Developer-role adoption | `developer_role_adoption` | trend only (not paged). |
| Role-gate correctness | `role_gate_decisions{result}` | unexpected `denied`/`allowed` skew (leakage ~0). |
| Deletion fulfilment | `deletion_fulfilment` | failed deletions. |
| Error conditions (DESIGN §11) | `email_send_failure`, `auth_error`, `admin_role_change` | sustained `email_send_failure`; **any `admin_role_change`** (privilege change is always reviewed — brief R6). |

## 8. Verification at release (2026-06-17)

- **108 automated tests pass** (incl. a real 2-thread token double-spend race).
- `ruff check` clean; `manage.py check` clean; `makemigrations --check` reports no model
  drift (model ↔ migration in sync).
- Rollback **rehearsed** on a scratch DB (§6).
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC10.

## 9. Known limitations

- **Magic-link only** — no OAuth/SSO/MFA (post-MVP; an account that can't receive email
  has no product value since the digest *is* email — [DESIGN §13](DESIGN.md)).
- **Registration enumeration** — the duplicate-email message is observable; integrity
  controls are deliberately deferred to the future integrity system.
- **Rate-limit counters** under-count across workers unless `CACHES` is a shared backend
  (Redis) — called out in the runbook prerequisites.
- **Email transport is ops-configured** — no provider is hardcoded; `EMAIL_BACKEND` must
  be set per environment and verified via `/health` before opening traffic.
- **Cross-feature deletion cascade** — downstream features owning account-referencing data
  must implement their own AC8 deletion behavior (handed downstream;
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).

## 10. Stakeholder notification

On promotion to "open to users": notify downstream feature owners that the account + role
contract is live and buildable against, and remind them of the deletion-cascade obligation
in §3 / §9. Notify support that auth is **passwordless** — the recovery path is "request a
new magic link," not a password reset.
