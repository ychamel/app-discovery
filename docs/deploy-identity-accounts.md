# Deploy runbook — identity-accounts

Operator guide for releasing the identity foundation. Follows the rollout order in
[DESIGN.md §12](../features/identity-accounts/DESIGN.md). Because this is the first
feature there is nothing to feature-flag off; safety comes from reversible migrations
and this ordered procedure.

## Prerequisites

- PostgreSQL 15+ reachable; the DB user may create the `citext` extension (the first
  migration runs `CREATE EXTENSION citext`).
- Python 3.12+ and the project installed (`pip install -e ".[dev]"`).
- Environment configured per [`.env.example`](../.env.example). In production:
  - `DJANGO_DEBUG=false` and a strong `DJANGO_SECRET_KEY` (required when not in debug).
  - `DJANGO_ALLOWED_HOSTS` set to the real host(s).
  - `EMAIL_BACKEND` set to a real transport (SMTP/SES/Postmark) and `PUBLIC_BASE_URL`
    set to the public HTTPS URL.
  - `CACHES` set to a **shared** backend (e.g. Redis) so rate-limit counters hold
    across workers. The default per-process cache under-counts with multiple workers.

## Deploy order (DESIGN.md §12)

1. **Apply migrations** — creates the schema, enables `citext`, and seeds the
   `user` / `developer` / `admin` groups:

   ```bash
   python manage.py migrate
   ```

2. **Bootstrap the first admin** (cold start; idempotent):

   ```bash
   python manage.py create_admin you@example.com
   ```

   This grants the `admin` role (recording a `RoleGrant` with `granted_by = NULL`) and
   makes the account Django staff/superuser. The operator then signs in via the normal
   magic link; `is_staff` admits them to `/django-admin/` for further cold-start grants.

3. **Configure & verify email** — set `EMAIL_BACKEND` for the environment, then confirm
   deliverability via the health check (must report `email: true`):

   ```bash
   curl -fsS https://<host>/health
   ```

4. **Enable registration / sign-in** — route public traffic to the app. The auth
   surfaces live at `/auth/register`, `/auth/signin`, `/auth/verify`, `/auth/logout`,
   `/profile`; the JSON contracts at `/me`, `/me/roles/developer`, `/admin/accounts/...`.

5. **Schedule token purge** — run periodically (e.g. hourly cron) to drop spent tokens:

   ```bash
   python manage.py purge_expired_tokens
   ```

## Health & monitoring

- `GET /health` → `200` when DB **and** email are reachable, `503` otherwise.
- Metrics (emitted via `apps.core.observability.increment`): `registration_completion`,
  `signin_success`, `auth_error`, `role_gate_decisions{result}`, `email_send_failure`,
  `developer_role_adoption`, `deletion_fulfilment`, `admin_role_change`, `signout`.
- **Alert on:** auth-error spikes, sustained `email_send_failure`, and **any**
  `admin_role_change` event.
- Logs are structured and carry `request_id` + `account_id` (UUID, never raw email).

## Rollback

There is no phased flag to flip. To roll back a bad release:

1. Revert the deploy to the previous release.
2. If a migration must be undone, revert the last migration:

   ```bash
   python manage.py migrate accounts <previous_migration_name>
   ```

   The initial migration is reversible (drops the schema and seeded groups). Reverting
   it destroys identity data — only do so on a fresh/empty deployment.

## Cross-feature note

When later features own data referencing an account (e.g. a developer's apps), they
must define their own account-deletion behavior (cascade or reassign) for AC8's
hard-delete. This feature deletes only identity data and cannot know their tables.
