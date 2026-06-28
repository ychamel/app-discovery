# TEST_PLAN.md — platform-staging

**Status:** built alongside the code (Stage 4, Senior Engineer). Maps **every** acceptance
criterion AC1.1–AC6.2 ([FEATURE_BRIEF.md](FEATURE_BRIEF.md)) to a concrete check, tagged
**agent-verifiable** (a command/route/assertion the engineer runs) vs **human-judgment** (a
sign-off the user records during the walkthrough, PS-3).

**Upstream:** APPROVED [DESIGN.md](DESIGN.md) (global [D-12](../../DECISIONS.md)) +
[TASKS.md](TASKS.md) (T-01…T-11). This feature ships **no new product capability**, so many
ACs assert a *deployed* property of the live staging instance (verified at Stage 5 against the
URL, per the [deploy-runbook.md](../../docs/deploy/deploy-runbook.md)); the *mechanisms* those
ACs depend on are unit-tested here in the repo. Both are listed.

The full suite is **975 tests green** as of this build (962 baseline + 13 added: media route 3,
SMTP wiring 1, liveness 3, cache selection 3, Sentry gating 3). `ruff` clean; no migration
drift (this feature adds **no schema/migration**).

---

## Local verification commands (the agent-verifiable spine)

```bash
. .venv/bin/activate
python manage.py test                        # full suite — 975 green
python manage.py check                        # clean under DEBUG=true and DEBUG=false
DJANGO_DEBUG=false python manage.py collectstatic --noinput   # manifest + hashed admin assets
ruff check apps/ config/
python manage.py makemigrations --check --dry-run             # "No changes detected"
```

---

## AC coverage map

| AC | Tag | Mechanism test (repo) | Live-instance check (Stage 5, runbook) |
|---|---|---|---|
| **AC1.1** HTTPS, DEBUG off, landing serves | agent | `check` clean under simulated `DEBUG=false`; `CSRF_TRUSTED_ORIGINS` parsed from env (T-01); secure-cookie/HSTS gating already covered by `apps/accounts` security tests | runbook §Verification AC1.1: `curl -fsS https://<host>/discover/` → 200 over HTTPS, no debug page |
| **AC1.2** primary routes 200 + CSS/JS/media load | agent | `collectstatic` produces hashed admin+app assets + manifest; `apps/core/tests/test_media.py` (media served with `DEBUG=false`, 200 not 404; missing → 404); shell renders 200 with `core/app.css` linked on every consolidated surface (`apps/pages/tests/test_template.py` + the render-every-surface check, T-06) | runbook §Verification AC1.2: each of home/app page/search/sign-in/dashboard/widget/admin returns its status with assets loading; one screenshot renders from the disk |
| **AC1.3** migrations apply to empty PG | agent | no new migration (DESIGN §6); `makemigrations --check` → no drift | runbook step 4 pre-deploy `migrate --noinput` on the empty managed PG; `migrate --check` clean |
| **AC2.1** repeatable second run | agent | `render.yaml` is declarative (well-formed YAML; web+db+keyvalue+disk blocks; release runs migrate+collectstatic — verified in build) | runbook is the ordered procedure; AC2.1 gate = a 2nd clean Blueprint apply with zero undocumented fix-ups |
| **AC2.2** no committed secret, vars documented | agent | `.env.example` documents all 9 new vars (`DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `REDIS_URL`, `SENTRY_DSN`); `.env` gitignored; `render.yaml` uses `sync:false`/`generateValue`/`from*` only — **no secret literal** (grep-confirmed, T-10) | runbook step 2 sets secrets in the dashboard, never in git |
| **AC3.1** dev journey + real email arrives | mixed | SMTP backend consumes the five wired settings (`apps/core/tests/test_email.py::SmtpSettingsWiringTests`); the dev flow surfaces (submit/edit/post/dashboard) are covered by their features' existing suites | **email arrival is human-judgment**: walkthrough §Developer "magic-link email arrives" sign-off (gates on a real inbox once Resend is wired, PS-2) |
| **AC3.2** app page + widget credible on mobile | human | n/a (UX quality) | walkthrough §Developer (mobile) sign-off line |
| **AC3.3** widget funnel records, firewall intact | agent | widget impression→click→conversion + the AST import-isolation firewall: `apps/widget/tests/` (incl. `test_imports.py`) — **unchanged by this feature** (widget templates byte-untouched; verified via `git diff`) | walkthrough §Developer: embed the widget, click through, confirm the dashboard funnel increments |
| **AC4.1** audience journey web + mobile | mixed | register/follow/interests/browse flows covered by `apps/accounts`, `apps/subscriptions`, `apps/interests`, `apps/discovery` suites; all surfaces now render in the responsive shell | walkthrough §Audience completion (web) + the mobile sign-off (AC4.2) |
| **AC4.2** mobile registration/browse usable | human | n/a (UX quality) | walkthrough §Audience (mobile) sign-off line |
| **AC5.1** admin ACCEPT → public per D-6 | agent | the D-6 ACCEPTED-only gate + admin review path: `apps/catalog` suite (`accept_app`, `list_catalogued_apps`) — unchanged | walkthrough §Admin: ACCEPT a PENDING submission → it appears on `/discover/` |
| **AC5.2** logs + uptime/error monitoring | agent | `/health/live` DB-only 200/503 + never opens SMTP (`apps/core/tests/test_health.py::LivenessEndpointTests`); env-gated Sentry init (`apps/core/tests/test_sentry.py`); structured stdout logging unchanged | runbook §Verification AC5.2: logs stream in the dashboard; `/health/live` ok; Sentry receives a forced test error (if DSN set) |
| **AC6.1** go/no-go verdict | human | n/a | walkthrough §Verdict — go/no-go template + defect register (M7) |
| **AC6.2** frontend verdict | human | n/a | walkthrough §Verdict — "templates sufficient" or named surface(s) (D-11 evidence) |

**Every AC1.1–AC6.2 is mapped. No AC unmapped.**

---

## Edge cases covered by the added tests

- **Media route:** file present under `DEBUG=false` → 200 (the staging gap); same route under
  `DEBUG=true` → 200 (dev behaviour preserved); missing file → **404, not a 500**.
- **DB bridge:** `DATABASE_URL` set → parsed (engine/name/host/port); unset → discrete `DB_*`
  path byte-for-byte unchanged (local dev untouched).
- **Static storage:** manifest+compressed backend under `DEBUG=false`; plain backend under
  `DEBUG=true`/tests so `{% static %}` resolves without a pre-built manifest (dev-safe default).
- **Cache:** `REDIS_URL` set → `RedisCache`; unset/blank → `LocMemCache` (limiter unchanged
  locally).
- **Liveness:** DB up → 200 `{"status":"ok"}`; DB down → 503 `{"status":"down"}`; email outage
  → liveness **still 200** and **never opens an SMTP socket** (the whole point of the split).
- **Sentry:** DSN unset/blank → not initialized (and `sentry_sdk` untouched); set → init once,
  `send_default_pii=False`.
- **SMTP wiring:** the five env-wired settings are exactly the ones Django's SMTP backend
  consumes; console default unchanged when unset.

## Regression checklist (areas this feature touched)

- [x] Full suite green (975) after every task; no skips.
- [x] `manage.py check` clean under both `DEBUG=true` and `DEBUG=false`.
- [x] No migration drift (`makemigrations --check`).
- [x] `ruff` clean across `apps/` + `config/`.
- [x] **Widget firewall preserved** — `apps/widget` import-isolation test green; widget
      templates byte-unchanged (no platform stylesheet); the AC3.3 funnel untouched.
- [x] gunicorn boots `config.wsgi`; collectstatic includes Django-admin assets + a manifest.
- [x] Every consolidated surface renders 200 with the shared stylesheet; messages still display
      (no surface lost the message UI); no template double-renders messages.

## Deferred / gated (not closable in the repo)

- **AC3.1 email arrival / M5**, **AC3.2 / AC4.2 mobile sign-off**, **AC6.1 / AC6.2 verdicts** —
  human-judgment, performed by the user (PS-3) using
  [staging-walkthrough.md](../../docs/deploy/staging-walkthrough.md) against the live URL.
- The **defect-fix loop** (DESIGN §14 increment-5) is emergent: defects the walkthrough
  surfaces are fixed or logged here / in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) with a
  disposition (AC6.1 / M7).
