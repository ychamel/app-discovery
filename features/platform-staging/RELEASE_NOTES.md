# RELEASE_NOTES — platform-staging

*Stage 5 artifact (Release Engineer). Status: **BUILD COMPLETE + VERIFIED LOCALLY** 2026-06-28;
released to the same local/dev posture as the prior thirteen features. **The live Render deploy is
deliberately deferred** — the user decided to land the `premium-frontend` feature first and deploy
staging on the polished UI rather than the current barebone one (see §7 and [global D-11](../../DECISIONS.md) /
the 2026-06-28 frontend-direction decision in [CONTROL.md](../../CONTROL.md)). Deploy artifacts are
written, secret-clean, and ready to run unchanged when staging is reactivated.*

Traces to [DESIGN §14 Rollout](DESIGN.md) · [FEATURE_BRIEF.md](FEATURE_BRIEF.md) success metrics
M1–M7 · [TEST_PLAN.md](TEST_PLAN.md) (AC1.1–AC6.2) · global ADR [D-12](../../DECISIONS.md).

---

## 1. What changed

Unlike the prior features, `platform-staging` ships **no new product capability**. Its deliverable is
a **deployment / serving stack + a shared responsive frontend shell** that turns the code-complete
developer wedge from a localhost-only project into something that can be **reached** by a real
developer, user, and admin on web + mobile. All eleven tasks **T-01…T-11** from the APPROVED
[TASKS.md](TASKS.md) / [DESIGN.md](DESIGN.md) (global [D-12](../../DECISIONS.md)) are built and
verified locally. Every new behavior is **env-gated with a dev-safe default**, so local dev and the
test suite run exactly as before.

**Shipped components:**

- **Production serving stack (T-01)** — **gunicorn** as the WSGI server, **WhiteNoise** serving
  hashed/compressed static (including the Django admin) with no second web server, and
  **`dj-database-url`** parsing a single `DATABASE_URL` (the discrete `DB_*` local fallback is
  unchanged). Added `STATIC_ROOT` + a `collectstatic` step and `CSRF_TRUSTED_ORIGINS` from env. The
  WhiteNoise **manifest** static backend is gated on `not DEBUG` (PS-IMPL-1) so a fresh checkout's
  `{% static %}` never raises a missing-manifest error in dev/test. This closes the real **C4 static
  gap** — there was no `STATIC_ROOT`/deploy manifest in the repo before.
- **Non-`DEBUG` media route (T-02)** — [`apps.core.views.serve_media`](../../apps/core/views.py), a
  thin view that reads `settings.MEDIA_ROOT` **at request time** (PS-IMPL-2 — one source of truth,
  and `override_settings`-testable). Django's built-in static server only runs under `DEBUG`; this
  serves uploaded media off the persistent disk in production.
- **The [`render.yaml`](../../render.yaml) Blueprint (T-03)** — Infrastructure-as-code for a Render
  web service (`app-discovery`) + managed Postgres (`app-discovery-db`) + a persistent disk + a free
  Redis keyvalue (`app-discovery-cache`); the release command runs `migrate` + `collectstatic`.
  **Zero secret literals** — every secret is `sync:false` / `generateValue` / `fromDatabase|fromService`;
  the only literal `value:` entries are non-secret constants (python version, `DEBUG=false`, the
  `EMAIL_BACKEND` class, `MEDIA_ROOT`).
- **Email transport wiring + setup guide (T-04)** — settings now expose
  `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` from env (PS-IMPL-3; the console backend stays the
  dev default). Provider = **Resend** over Django's stock SMTP backend = **pure config, no code** —
  [`apps/core/email.py`](../../apps/core/email.py) already swaps transport by `EMAIL_BACKEND`. Ships
  [`docs/deploy/email-provider-setup.md`](../../docs/deploy/email-provider-setup.md) (account +
  verified sending domain + credential wiring). Magic-link auth / M5 gate on a real inbox once
  configured (PS-2).
- **Shared responsive frontend shell (T-05/T-06)** — one mobile-first
  [`apps/core/templates/core/base.html`](../../apps/core/templates/core/base.html) + a real
  [`app.css`](../../apps/core/static/core/app.css), with the **6 per-app `base.html` consolidated**
  onto it as thin `{% extends %}` children. Django messages render **once** in the shell (the
  duplicate markup was removed from `updates/base` + `interests/picker`). **The widget templates are
  byte-unchanged** — `apps/widget` stays visually isolated, so the **AC3.3 firewall holds**
  (PS-DESIGN-7).
- **DB-only liveness probe (T-07)** — a new [`/health/live`](../../apps/core/views.py) that reuses
  `_database_ok` and **never opens SMTP**, split from the existing SMTP-touching `/health`. A real
  footgun found in code: a liveness probe that fails when the mail provider hiccups would flap the
  whole service. Readiness (`/health`) keeps checking email; liveness doesn't.
- **Shared cache from `REDIS_URL` (T-08)** — `_cache_settings(REDIS_URL)` selects Django's built-in
  `RedisCache`, with a **LocMem fallback** when unset (PS-IMPL-4). This makes the fail-open auth rate
  limiter **correct across gunicorn workers** (a per-process LocMem cache would let the limit be
  bypassed N-ways).
- **Env-gated Sentry (T-09)** — `_init_sentry(SENTRY_DSN)`; error monitoring is active **only when
  `SENTRY_DSN` is set** (PS-IMPL-4). Observability otherwise = the existing stdout structured logs.
- **Deploy runbook + secret-hygiene pass (T-10)** —
  [`docs/deploy/deploy-runbook.md`](../../docs/deploy/deploy-runbook.md) (email-setup → Blueprint →
  secrets → `create_admin`) + an **AC2.2 no-committed-secret** pass (`.env` gitignored + untracked;
  `.env.example` complete).
- **Test plan + walkthrough script (T-11)** — [`TEST_PLAN.md`](TEST_PLAN.md) maps **every**
  AC1.1–AC6.2 (each tagged agent-verifiable vs human-judgment) and
  [`docs/deploy/staging-walkthrough.md`](../../docs/deploy/staging-walkthrough.md) (3 roles ×
  web + mobile + go/no-go + frontend verdict templates) for the user-run walkthrough (PS-3).

**Five new dependencies** ([`pyproject.toml`](../../pyproject.toml)): `gunicorn`, `whitenoise`,
`dj-database-url`, `redis`, `sentry-sdk[django]`. **No schema, no migration.**

**Verified before ship (this session, independently re-run):** **975 tests** green (+13 over the 962
baseline — media 3, SMTP wiring 1, liveness 3, cache 3, sentry 3); `ruff check .` clean;
`python manage.py check` clean under **both** `DEBUG=true` and `DEBUG=false` (`--deploy`: only the
expected W009 from a throwaway key); `makemigrations --check` → **no drift**; `render.yaml` YAML-parses
with zero secret literals; `collectstatic` (DEBUG=false manifest) → 155 copied / 447 post-processed
incl. hashed+gz `core/app.css`; `gunicorn config.wsgi` loads the `WSGIHandler` under `DEBUG=false`.

## 2. Who is affected

- **Operators / the deploying user** — gain a runnable, reproducible deploy path: a committed
  Blueprint + a step-by-step runbook + an email-setup guide, all secret-clean. Standing up staging is
  now `render blueprint launch` + setting secrets + `create_admin`, not bespoke server work.
- **Developers, users, admins** — **once staging is live**, the wedge becomes reachable on web + mobile
  with a single consistent responsive look (the shell), instead of the per-app bare templates. **No
  behavior change locally**: every new path is env-gated and dev keeps its old defaults (LocMem cache,
  console email, DEBUG media route, no Sentry).
- **No regression to any existing feature.** No product contract changed; the only additions are
  additive (a liveness route, new template blocks, env-gated settings branches). The widget firewall is
  preserved structurally (templates byte-unchanged).

## 3. How to use it

**To stand up staging** (deferred until after `premium-frontend` — see §7), follow
[`docs/deploy/deploy-runbook.md`](../../docs/deploy/deploy-runbook.md):

1. [`email-provider-setup.md`](../../docs/deploy/email-provider-setup.md) — create the Resend account,
   **verify a sending domain**, grab the SMTP credentials.
2. `render blueprint launch` against [`render.yaml`](../../render.yaml) (web + Postgres + disk + Redis).
3. Set the live secrets in the Render dashboard (`SECRET_KEY` is `generateValue`; `EMAIL_*`,
   `CSRF_TRUSTED_ORIGINS`, optional `SENTRY_DSN` are `sync:false`).
4. The release command runs `migrate` + `collectstatic` automatically; create the admin via
   `create_admin`.
5. Hit `/health/live` (liveness) and `/health` (readiness incl. email) to confirm.

**Locally, nothing changes** — `python manage.py runserver` behaves exactly as before.

## 4. Operator rollout

- **Stack:** reuses **D-4** (Python/Django + PostgreSQL) and adds the **D-12** serving stack — Render
  Blueprint + the five deps above. No application schema.
- **Activation = the deploy itself** (DESIGN §14): there is no feature flag and no migration. The
  codebase keeps running locally exactly as before; "turning it on" is running the runbook against
  Render.
- **Promotion table:**

  | Stage | Target | Promotion criterion |
  |-------|--------|---------------------|
  | local/dev (build + artifacts verified) | **done (2026-06-28)** | 975 tests green; ruff/check clean (both DEBUG); no drift; `render.yaml` secret-clean; collectstatic + gunicorn OK |
  | live staging | **deferred (sequenced after `premium-frontend`)** | runbook executed; AC1.1/AC1.2/AC1.3/AC5.2 agent checks green against the live URL; the user's AC6.1/AC6.2 walkthrough verdicts |
  | prod | _deferred_ | staging validated end-to-end; promote the same Blueprint per PS-1 (prod-bound) |

## 5. Rollback (deploy-time)

Because this feature adds **no migration and no product code path**, rollback is operational, not a
data concern:

- **Pre-deploy (where we are now):** the changes are inert by default. `git revert` of the build commit
  (`9e147f7` *platform-staging/ development*) removes the serving settings, the `render.yaml`, the
  shared shell + the 6 base re-points, the media/liveness/cache/sentry additions, and the deploy docs
  together; `manage.py check` stays clean and local dev returns to the pre-feature templates. (Not
  rehearsed this session — no migration to reverse and no live target; rehearsal folds into the live
  deploy when staging is reactivated.)
- **Post-deploy (when live):** point Render traffic back to the prior deploy or tear the Blueprint
  down; the codebase keeps running locally unchanged. No data backfill, no schema to unwind.

## 6. Monitoring — signals → alert

- **Liveness `/health/live`** (DB-only) — the orchestrator restart signal; never flaps on an email
  outage. **Readiness `/health`** (DB + SMTP) — load-balancer "ready to serve" incl. the mail path.
- **Sentry** (env-gated on `SENTRY_DSN`) — unhandled-error capture once a DSN is set; the actionable
  alert channel in production. Otherwise stdout structured logs.
- **The auth rate limiter** is now backed by the shared Redis cache, so its counters are correct across
  workers — a prerequisite for trusting any abuse signal in a multi-worker deploy.
- **M1–M7** (FEATURE_BRIEF) are deploy/walkthrough outcomes (reachability, the go/no-go verdict, the
  frontend verdict, defects found+fixed). They are measured **during the live walkthrough** (PS-3),
  which opens when staging is reactivated.

## 7. Known limitations

- **Not deployed live yet — by deliberate sequencing.** The user decided on 2026-06-28 to build
  `premium-frontend` (HTMX + Tailwind + Django templates, within the [D-4](../../DECISIONS.md) envelope)
  **before** the staging launch, so the developer's app page — their bring-your-own-audience marketing
  landing page — debuts polished rather than barebone (the current UI is one ~199-line stylesheet, no
  design system). The live Render deploy + the AC1/AC5/AC6 walkthrough are therefore **deferred, not
  cancelled**; every deploy artifact is written and verified and runs unchanged when staging is
  reactivated. This is the only reason M1–M7 have no live readings.
- **PS-OQ-1 — the bare domain `/` 404s.** Routes resolve `/discover/`, `/signin`, etc., but `/` has no
  route, while AC1.1 says "serves the home/landing surface." Logged, **not fixed in code** (out of
  TASKS/DESIGN scope — no silent expansion). Recommended fix: a one-line root redirect `/` →
  `discovery:browse`. **Carry into `premium-frontend`** — a landing/home page is squarely that feature's
  concern, so it's the natural place to resolve PS-OQ-1 rather than a throwaway redirect now.
- **Email needs a verified sending domain** before magic-link auth / M5 work on staging (PS-2) — this is
  an account-setup step in the runbook, not a code gap.
- **Media on a persistent disk, not an object store.** Fine for staging; the documented growth path is
  R2 + `django-storages` (PS-DESIGN-3) when durability/scale demands it.
- **The live deploy is outward-facing user action** (Render account, verified domain, live secrets, the
  paid-tier choice) — the agent supplies and verifies the artifacts; a human runs the deploy.

---

*Reuses **D-3** (roles), **D-4** (stack) and establishes the **D-12** serving stack + shared frontend
shell as the global infrastructure ADR every later feature inherits. No application schema/migration.
Feature-local decisions PS-DESIGN-1…8 (**RATIFIED → D-12**) + impl notes PS-IMPL-1…5 in
[DECISIONS.md](DECISIONS.md); the one open finding PS-OQ-1 in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
(carried into `premium-frontend`).*
