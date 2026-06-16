# TEST_PLAN — identity-accounts

*Stage 4 artifact (Senior Engineer). Companion to the code. Proves every acceptance
criterion (AC1–AC10) in [FEATURE_BRIEF.md](FEATURE_BRIEF.md) is exercised by automated
tests, lists the edge cases covered, and gives the regression checklist for the areas
this feature touches.*

## How to run

```bash
. .venv/bin/activate
python manage.py test        # 108 tests, requires PostgreSQL (see README)
ruff check .                 # lint
```

All 108 tests pass; lint is clean; `manage.py check` reports no issues.

## Acceptance-criterion coverage

| AC | What it requires | Automated test(s) |
|----|------------------|-------------------|
| **AC1** Register; no duplicates | account created + base `user` role; signed in after confirm; duplicate email refused | `test_register.py::RegisterTests::test_valid_registration_creates_unconfirmed_user_and_emails_link`, `::test_every_account_has_the_user_role`, `::test_duplicate_email_is_refused`; confirm→signed-in in `test_signin.py::SignInFlowTests::test_valid_auth_establishes_session`; DB-level uniqueness in `test_models.py::AccountModelTests::test_email_uniqueness_is_case_insensitive` |
| **AC2** Email deliverability surfaced | send failure surfaced; account not digest-eligible | `test_register.py::RegisterSendFailureTests::test_send_failure_returns_503_and_account_stays_unconfirmed`; interface fail-loud in `apps/core/tests/test_email.py::FailLoudTests` |
| **AC3** Sign in / deny invalid | valid auth → session; invalid/expired → denied, no session | `test_signin.py::SignInFlowTests::test_valid_auth_establishes_session`, `::test_invalid_token_denies_and_creates_no_session`, `::test_expired_or_reused_token_denied`; token logic in `test_auth_backend.py::VerifyTokenTests` |
| **AC4** Recovery, same account+roles | re-auth via email → same account, same roles | `test_signin.py::RecoverySameAccountTests::test_reauth_returns_same_account_and_roles` |
| **AC5** Sign out | session ended; protected action needs re-auth | `test_logout.py::LogoutTests::test_logout_flushes_session_and_protected_action_requires_reauth` |
| **AC6** Role-gated + self-serve developer | self-serve developer on same account; gate allows/denies | `test_developer_role.py::DeveloperSelfServeTests::test_user_can_become_developer_on_same_account`; gate behavior in `test_roles.py::GateTests` |
| **AC7** Profile display name | set/change saved and reflected | `test_profile.py::MeApiTests::test_patch_updates_display_name`, `::test_get_me_returns_account_shape` |
| **AC8** Delete account | identity/credentials/roles/profile removed; cannot sign in; audit preserved | `test_deletion.py::DeletionTests` (all four) |
| **AC9** Admin granted, never self-assigned | non-admin refused; self-grant impossible; granted admin then succeeds; audited | `test_admin_roles.py::AdminRoleApiTests` (grant/revoke/refuse/404/400/granted-admin-acts/unauth) |
| **AC10** Single access method + extensibility | one magic-link path for all roles; roles additive via groups | one access path proven by AC1/AC3/AC4/AC9 all using the same verify flow; extensibility (unknown role denies, groups drive gate) in `test_roles.py::GateTests::test_unknown_role_denied` + `test_models.py::GroupSeedTests`; gate is the single point (`account_has_role`) |

## Edge cases covered

- **Tokens (sharpest edge):** happy path, expired, already-consumed (reuse), forged/unknown,
  and a **real concurrent double-spend** with two threads — exactly one succeeds
  (`test_auth_backend.py::ConcurrentVerifyTests`). Raw token never persisted (hash only).
- **Email case-insensitivity:** uniqueness and lookup (`test_models.py`), rate-limit keying
  (`apps/core/tests/test_ratelimit.py::PerEmailLimitTests::test_email_is_case_insensitive`).
- **Rate limiting:** under-limit pass, over-limit `429`, per-email vs per-IP isolation,
  window reset, safe methods exempt (`apps/core/tests/test_ratelimit.py`, `test_register.py`).
- **Config validation:** defaults, setting/env override, and fail-loud on non-numeric/zero/
  negative (`apps/core/tests/test_config.py`).
- **Email transport:** success via configured backend, fail-loud on a backend error
  (`apps/core/tests/test_email.py`).
- **Authorization fail-closed:** anonymous, None user, unknown role, and a simulated lookup
  error all deny (`test_roles.py::GateTests`).
- **Audit integrity:** grant/revoke append-only, never mutated; rows survive account deletion
  via SET_NULL (`test_roles.py::GrantRevokeAuditTests`, `test_models.py::RoleGrantAuditTests`).
- **Enumeration:** sign-in returns the generic `202` and sends no email for unknown addresses
  (`test_signin.py::SignInFlowTests::test_login_is_generic_for_unknown_email`).
- **Bootstrap:** `create_admin` creates/promotes, records a `granted_by=NULL` audit row, and is
  idempotent; `purge_expired_tokens` drops spent tokens only (`test_commands.py`).
- **Security:** cookie hardening, CSRF rejection of an unauthenticated form post, and no raw
  email in logs (`test_security.py`).
- **Health/metrics:** `/health` 200/503; metric emission is named, tagged, and never raises
  (`apps/core/tests/test_health.py`).

## Regression checklist (areas this feature touches)

- Migrations apply cleanly on a fresh PostgreSQL DB (`citext` enabled, three groups seeded).
- `AUTH_USER_MODEL = accounts.Account`; sessions are DB-backed and survive restarts.
- The single gate `account_has_role` remains the only authorization decision point.
- Magic-link consume stays atomic (the conditional UPDATE) — re-run the concurrency test.
- Rate-limit counters require a shared cache in production (LocMem under-counts across workers).
- Secure cookies / HSTS / SSL redirect activate when `DJANGO_DEBUG=false`.
