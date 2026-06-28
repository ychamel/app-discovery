# Deploy runbook — platform-staging (Render)

Ordered, copy-pasteable procedure to stand up a reachable **staging** environment on
Render for the code-complete developer wedge (platform-staging `DESIGN`, global
[D-12](../../DECISIONS.md)). The Render Blueprint [`render.yaml`](../../render.yaml) is the
declarative source of truth — applying it **is** the repeatable second run (AC2.1). This
document covers the irreducible account/secret setup the Blueprint cannot encode, plus the
AC1 verification steps.

> **AC2.1 gate:** a second clean run using *only* the steps below must yield an equivalent
> working environment with **zero undocumented manual fix-ups**. If you hit a step that
> isn't written here, add it here rather than just doing it.

## What gets provisioned

From `render.yaml`: one **Web Service** (gunicorn), one **managed PostgreSQL**, one
**persistent disk** for media, one **Key Value (Redis)** for the shared cache. All four
are declared in the Blueprint; you only supply the secrets below.

## Prerequisites

- A Render account with this repo connected (GitHub/GitLab).
- An email provider account + verified domain — see
  [email-provider-setup.md](email-provider-setup.md) (do this first; you need the SMTP
  credentials in step 3).
- The repo's `render.yaml` on the branch you will deploy.

## Steps

### 1. Apply the Blueprint

In the Render dashboard: **New → Blueprint**, select this repository and branch. Render
reads `render.yaml` and provisions the web service, Postgres, disk, and Key Value in one
pass. `DATABASE_URL` and `REDIS_URL` are wired automatically (`fromDatabase` /
`fromService`); `DJANGO_SECRET_KEY` is generated automatically (`generateValue`).

### 2. Set the dashboard secrets (`sync: false` vars)

These are declared by name in `render.yaml` but have **no committed value** (AC2.2). Set
them on the web service under **Environment**:

| Variable | Value |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | the service host, e.g. `app-discovery.onrender.com` (+ any custom domain) |
| `CSRF_TRUSTED_ORIGINS` | the scheme-qualified origin, e.g. `https://app-discovery.onrender.com` |
| `PUBLIC_BASE_URL` | the same HTTPS base URL (used to build magic-link URLs) |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | from [email-provider-setup.md](email-provider-setup.md) |
| `DEFAULT_FROM_EMAIL` | a `no-reply@…` at your **verified** sending domain |
| `SENTRY_DSN` | optional; set to enable error monitoring (leave blank to disable) |

`DJANGO_DEBUG=false`, `EMAIL_BACKEND=…smtp…`, and `MEDIA_ROOT=/var/media` are already set
to constants in the Blueprint — do not change them for staging.

> **Fail-loud safety net:** `DJANGO_SECRET_KEY` is required when `DEBUG=false` (the
> `env(..., required=not DEBUG)` pattern in `config/settings.py`) — a missing secret makes
> the process fail at boot rather than serve insecurely. `DJANGO_ALLOWED_HOSTS` must be set
> or every request is rejected with `DisallowedHost`.

### 3. Wire email

Follow [email-provider-setup.md](email-provider-setup.md) end-to-end (account → verify
domain → SMTP creds → set the env vars in step 2 → send a test). Magic-link sign-in
(AC3.1 / M5) cannot be verified until a real email lands.

### 4. Deploy

Trigger the deploy. The release sequence runs automatically:

- **build:** `pip install -e . && python manage.py collectstatic --noinput` (bakes the
  hashed/compressed static set, incl. Django-admin assets, into the instance).
- **pre-deploy:** `python manage.py migrate --noinput` (applies all migrations to the
  empty PG on the first deploy — AC1.3).
- **start:** `gunicorn config.wsgi:application`.

The platform health check probes `/health/live` (DB-only) — see `DESIGN` §4.6.

### 5. Bootstrap an admin (cold start; idempotent)

In the web service shell:

```bash
python manage.py create_admin you@example.com
```

## Verification (AC1)

Run these against the live service URL once the deploy is green:

- **AC1.1 — HTTPS, DEBUG off, landing serves.**
  ```bash
  curl -fsS -o /dev/null -w "%{http_code}\n" https://<host>/discover/   # 200 over HTTPS
  ```
  Confirm the response is served over HTTPS (Render terminates TLS) and that
  `DEBUG=false` (no Django debug page on a forced error). The public landing surface is
  `/discover/` (the open browse surface). *Note: the bare domain `/` currently has no
  route — tracked as a walkthrough finding in
  [OPEN_QUESTIONS.md](../../features/platform-staging/OPEN_QUESTIONS.md).*

- **AC1.2 — primary routes 200 + CSS/media load.** Check each returns its expected status
  with the stylesheet linked and assets loading (no broken styling, no 404 images):
  `/discover/`, an app page `/apps/<id>/`, `/auth/signin`, `/auth/register`,
  `/dashboard/` (as a developer), a widget embed `/widget/<id>/`, and `/django-admin/`
  (admin CSS loads via WhiteNoise). Open one app page with a screenshot and confirm the
  image renders (served from the persistent disk, AC1.2 media).

- **AC1.3 — migrations apply to empty PG.** Confirmed by the pre-deploy `migrate` on the
  first deploy completing cleanly. Re-check with:
  ```bash
  python manage.py migrate --check    # no pending migrations
  ```

- **AC5.2 — observability.** Confirm logs stream in the Render dashboard; `/health/live`
  returns `{"status":"ok"}`; `/health` (operator deep probe) reports `email: true` once
  SMTP is wired; if `SENTRY_DSN` is set, force a test error and confirm it appears in Sentry.

## Rollback

There is no migration to reverse (this feature adds none). To roll back: redeploy the
previous commit, or suspend/tear down the Blueprint. Local development is unaffected at all
times (every new behavior is env-gated with a dev-safe default).

## Free → durable (prod-bound) tier

Staging starts on free plans. For the prod-bound durable tier (PS-1, ~$14–25/mo, inside the
$20–100/mo envelope): set the web service `plan` to `starter` (so it doesn't sleep **and**
so the persistent disk is available) and the database to a paid plan. This is a single
`plan` field per service in `render.yaml` — not a re-architecture (`DESIGN` §4.1).
