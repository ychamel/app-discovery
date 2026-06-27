# DESIGN.md — platform-staging

**Status:** **DRAFT — awaiting gate `DN-PS-DESIGN`** (see *§15 Decisions* + the gate block at
the end). **Stage 2 (Software Architect) artifact.**

**Upstream source:** [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (APPROVED 2026-06-27), global
[D-11](../../DECISIONS.md) (staging-validation-before-live) + [D-4](../../DECISIONS.md) (the
stack; server-rendered templates), bounded by **PS-1** (free tier now, **$20–100/mo** when
durable, **prod-bound**) / **PS-2** (no email provider yet → Architect picks one + ships an
`.md`) / **PS-3** (user performs the human-judgment walkthrough).

This feature is unusual: it ships **no new product capability**. Its "architecture" is a
**deployment + serving stack**, the **frontend shell** that makes the existing templates
presentable and responsive, and the **defect fixes** the walkthrough surfaces. Everything
below is in service of making the already-built wedge *reachable, credible, and operable*.

---

## 1. Reasoning summary (14-step protocol — condensed)

- **SCOPE.** Make the code-complete wedge reachable over HTTPS on a real domain with a real
  email transport, presentable on mobile, and operable — then walk it end-to-end and emit a
  go/no-go + frontend verdict. Lifespan = **platform** (PS-1 prod-bound: staging is promoted to
  production later), so effort targets durability, not a throwaway. OUT: new features, SPA
  rewrite, live recruitment, native apps, install-attribution (brief *Out of scope*).
- **REQUIREMENTS.** Functional = AC1.1–AC6.2. Non-functional = HTTPS/secure-cookies on (already
  gated on `not DEBUG`, C2), repeatable deploy (AC2), assets serve without `DEBUG` (close C4),
  persistent Postgres (C5), real email (PS-2), basic monitoring (AC5.2), mobile-usable
  templates (M4), within PS-1 budget. Assumptions A1–A3 resolved by the user; C1–C6 verified in
  the brief and re-verified against the code this session (see §2).
- **CONTEXT.** Django 5 / DRF / PostgreSQL ([D-4](../../DECISIONS.md)), shared root `apps/`,
  cross-cutting home `apps/core`. Settings are already 12-factor. **Gaps found in code:** no
  `STATIC_ROOT`/collectstatic, **zero static files**, **6 duplicated `base.html`** with no CSS,
  no WSGI server/process manifest, `DATABASE_URL` not parsed, default cache is per-process
  LocMem, `/health` opens a live SMTP socket. Reuse-first: the email interface already swaps
  transport by config ([apps/core/email.py](../../apps/core/email.py)); `/health` +
  structured logging already exist ([config/settings.py](../../config/settings.py) `LOGGING`).
- **MODULES → FAILURE** are covered in §3–§9. **SELF-CRITIQUE / TRADE-OFFS** in §10–§12.
- **DELIVER.** Smallest useful first version + increments in §14.

---

## 2. Current-state summary (diff against reality)

| Concern | Today (verified in code) | Gap to close |
|---|---|---|
| **Process model** | `runserver` only; `config/wsgi.py` exposes `application`. | No production WSGI server / start command. |
| **DB config** | Discrete `DB_NAME/USER/PASSWORD/HOST/PORT` env ([settings.py](../../config/settings.py) L154). | Managed hosts hand out a single `DATABASE_URL`; not parsed. |
| **Static** | `STATIC_URL` only; **no `STATIC_ROOT`, no `STATICFILES_DIRS`, no collectstatic, 0 static files.** `staticfiles/` is gitignored. | Non-`DEBUG` serving of CSS/JS + Django-admin assets (AC1.2). |
| **Media** | `MEDIA_ROOT` env-driven; served **only** under `if settings.DEBUG` in [config/urls.py](../../config/urls.py). | Non-`DEBUG` serving + persistence across deploys (AC1.2). |
| **Email** | `EMAIL_BACKEND` env; default **console stub**; `DefaultEmailSender` fails loud. | A real transactional provider + credentials (PS-2, AC3.1/M5). |
| **Security** | HTTPS/HSTS/secure-cookies/`SECRET_KEY`/`ALLOWED_HOSTS` all gated on `not DEBUG`; trusts `X-Forwarded-Proto`. | Nothing structural — just provide the env (AC2.2). `CSRF_TRUSTED_ORIGINS` needed for the HTTPS origin (Django 4+). |
| **Cache / rate limit** | No `CACHES` → per-process LocMem; auth limiter ([apps/core/ratelimit.py](../../apps/core/ratelimit.py)) is **fail-open**, counts in the default cache. | Multi-worker gunicorn → per-worker limits (security degradation). |
| **Health** | `/health` checks DB **and opens a live SMTP connection** (`_email_ok`), 503 if either fails. | Unsafe as an orchestrator liveness target — a transient SMTP blip would loop restarts. |
| **Frontend** | 6 per-app `base.html`, near-identical, **no stylesheet**; viewport meta present. Widget templates self-contained with inline `<style>`. | One responsive shell + one stylesheet; keep the widget isolated. |
| **Deploy repeatability** | None — no manifest, no runbook. | Declarative IaC + a written runbook (AC2.1). |

---

## 3. Proposed architecture (components)

```
                       ┌─────────────────────────────────────────────┐
   Internet (HTTPS) ──▶│  Hosting platform (Render) — TLS termination │
                       │  X-Forwarded-Proto=https  →  SECURE_* honored │
                       └───────────────┬─────────────────────────────┘
                                       │
                               ┌───────▼────────┐   static (hashed, immutable)
                               │   gunicorn     │──▶ WhiteNoise ──▶ apps/*/static + admin
                               │ config.wsgi    │   media (mutable) ─▶ persistent disk
                               └───┬────────┬───┘
                                   │        │
                   ┌───────────────▼┐     ┌─▼──────────────┐     ┌──────────────┐
                   │ Managed        │     │ Shared cache   │     │ Email (SMTP) │
                   │ PostgreSQL     │     │ (Redis, free)  │     │ Resend       │
                   │ DATABASE_URL   │     │ REDIS_URL      │     │ EMAIL_*      │
                   └────────────────┘     └────────────────┘     └──────────────┘

   Observability:  structured stdout logs → platform log stream
                   Sentry (env-gated DSN) → error visibility
                   /health/live (DB-only) → platform health check + UptimeRobot
                   /health (DB + email)   → human operator deep probe
```

Each piece has a single responsibility and is **replaceable by config** (the whole point of the
12-factor posture): swap host, DB, cache, or email by changing env, not code. The new code
surface is deliberately tiny — most of this feature is **configuration + templates + docs**.

### 3.1 Components added / modified

| Component | Responsibility | Owns / changes | Replaceable via |
|---|---|---|---|
| **Process manifest** (`render.yaml`, gunicorn) | Declarative description of the service, its build, its release step, its env. | New `render.yaml`; `gunicorn` dep. | Any host that reads a start command. |
| **DB config bridge** | Accept a single `DATABASE_URL` *or* the discrete vars (local). | `settings.DATABASES`; `dj-database-url` dep. | Env only. |
| **Static pipeline** | Collect + serve hashed, compressed static without a second web server. | `STATIC_ROOT`, `STORAGES["staticfiles"]`, WhiteNoise middleware; `whitenoise` dep. | `STORAGES` backend swap. |
| **Media serving** | Serve uploaded screenshots under non-`DEBUG`, persistent across deploys. | A non-`DEBUG` media route + a persistent disk mount. | `STORAGES["default"]` → object store (growth path). |
| **Email transport** | Deliver magic-link mail over a real provider. | `EMAIL_BACKEND=smtp` + creds via env; **no code change**. | `EMAIL_BACKEND`. |
| **Shared cache** | Make the auth rate limiter hold across workers. | `settings.CACHES` from `REDIS_URL`, LocMem fallback; `redis` dep. | `REDIS_URL` unset → LocMem. |
| **Liveness probe** | A cheap DB-only up/down signal safe for the orchestrator. | New `health_live` view + `/health/live` route. | n/a (additive). |
| **Error monitoring** | Surface unhandled exceptions to an operator. | Env-gated `sentry_sdk.init` in settings; `sentry-sdk` dep. | `SENTRY_DSN` unset → disabled. |
| **Frontend shell** | One responsive look every wedge surface inherits. | `apps/core/templates/core/base.html` + `apps/core/static/core/app.css`; 6 bases re-pointed. | Template inheritance. |
| **Deploy docs** | Make the deploy reproducible + email setup self-serve. | `docs/deploy/deploy-runbook.md`, `docs/deploy/email-provider-setup.md`; extended `.env.example`. | n/a. |

Coupling check: the cache, email, Sentry, and DB bridges are each **independently togglable by a
single env var** with a safe fallback — low coupling, each testable in isolation. The frontend
shell is a pure template-inheritance change with one consumer contract (§7).

---

## 4. Deployment & serving stack (the irreversible-ish choices)

### 4.1 Hosting — Render (Blueprint IaC) — **PS-DESIGN-1**

A **Render Blueprint** (`render.yaml`) declaring: one **Web Service** (Python, `gunicorn
config.wsgi:application`), one **Managed PostgreSQL** (C5), one **persistent disk** for media, and
(staging) a free **Key Value / Redis** instance. Env vars (secrets) are set in the Render
dashboard / Blueprint `envVars`, never committed (AC2.2).

- **Why Render:** repeatability is **structural, not a runbook of manual clicks** — the Blueprint
  *is* the second-run reproduction (AC2.1); managed Postgres + automatic HTTPS on a stable
  `*.onrender.com` URL (AC1.1, no domain purchase needed for staging) + env-based secrets +
  a documented Django path. Boring and well-understood (§5.5).
- **Cost (PS-1):** staging runs on **free** web + free Key Value; managed Postgres is free for 90
  days, then ~$7/mo. The **prod-bound durable tier** (paid web instance so it doesn't sleep +
  paid Postgres) lands around **$14–25/mo — inside the $20–100/mo envelope**. The free→paid
  switch is a Blueprint plan field, not a re-architecture.
- **Custom domain** is a **prod-promotion** step (a `*.onrender.com` URL satisfies AC1.1 for
  staging); when added it appends to `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` via env — no code.

Rejected: **Heroku** (no free tier; otherwise equivalent — Procfile path documented as the
portability note), **Fly.io** (more ops surface — volumes, regions — for no staging benefit),
**a raw VPS** (hand-rolled nginx/gunicorn/certbot/systemd = exactly the undocumented manual
surface AC2.1 forbids). Render's lock-in is mitigated because every choice under it is standard
Django + a single declarative file.

### 4.2 WSGI + static + DB bridge — **PS-DESIGN-2**

- **gunicorn** serves `config.wsgi`. Release command: `python manage.py migrate --noinput &&
  python manage.py collectstatic --noinput`.
- **WhiteNoise** middleware (immediately after `SecurityMiddleware`) +
  `STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"`
  serves hashed, compressed static (app CSS/JS **and Django-admin assets**, AC1.2) from
  `STATIC_ROOT` with far-future caching — **no second web server**. App `static/` dirs are picked
  up automatically by Django's `AppDirectoriesFinder` (so `apps/core/static/core/app.css` needs no
  `STATICFILES_DIRS`).
- **`dj-database-url`** parses `DATABASE_URL` when present; the existing discrete `DB_*` vars
  remain the fallback so **local dev is unchanged**. One source of truth, env-selected.

### 4.3 Media — persistent disk now, object store as the growth path — **PS-DESIGN-3**

Uploaded screenshots ([apps/catalog](../../apps/catalog), D-6 media) are **mutable user data** —
they cannot live in the immutable WhiteNoise static set. Staging mounts a **Render persistent
disk** at `MEDIA_ROOT`; a **non-`DEBUG` media route** serves `MEDIA_URL` from it. This is a
**deliberate, bounded single-node trade-off** (CLAUDE.md §5.2): a disk doesn't serve
horizontally-scaled instances. The **documented 100× / prod-promotion path** is
`STORAGES["default"]` → an S3-compatible **object store** (Cloudflare R2: free 10 GB, no egress)
via `django-storages` — a `STORAGES`-only swap with **no caller change** (every uploader already
goes through Django's storage API). Not built now (§5.5 — no dep before it's needed).

> Media-route note: serving media through Django/WhiteNoise is acceptable at staging scale and is
> the boring choice; the object-store swap is the named upgrade, not a silent future rewrite.

### 4.4 Email — Resend over SMTP, zero code — **PS-DESIGN-4 (PS-2)**

The transport is already pluggable ([apps/core/email.py](../../apps/core/email.py) swaps
console→SMTP by `EMAIL_BACKEND` alone). So the provider integration is **pure configuration**:
set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` + `EMAIL_HOST/PORT/HOST_USER/
HOST_PASSWORD/USE_TLS` + a verified `DEFAULT_FROM_EMAIL`.

- **Recommended provider: Resend.** Free tier (100/day, 3 000/mo) covers staging magic-links
  comfortably; clean SMTP; modern, low-friction domain verification. **Postmark** is the
  deliverability-premium alternative (100/mo free → $15/mo, inside PS-1) if inbox-placement
  becomes the bottleneck.
- **Deliverable (In scope):** `docs/deploy/email-provider-setup.md` — create the account, verify
  a sending domain (SPF/DKIM), obtain SMTP credentials, set the env vars, send a test. AC3.1/M5
  gate on a real inbox once wired.

### 4.5 Shared cache — make the rate limiter correct under workers — **PS-DESIGN-5**

The auth limiter ([apps/core/ratelimit.py](../../apps/core/ratelimit.py)) counts in Django's
**default cache** and **fails open**. With no `CACHES`, gunicorn's N workers each get a private
LocMem counter → the per-email/per-IP limits are effectively N× looser (a security degradation,
not a crash). Fix: wire `CACHES["default"]` to **Django 5's built-in `RedisCache`** from a
`REDIS_URL` env var (the `redis` client is the one new dep), **falling back to LocMemCache when
`REDIS_URL` is unset** (local dev unchanged; honors the standing `.env.example` note). Staging
provisions the free managed Redis so the limiter is correct under the default multi-worker
gunicorn — the prod-bound, correct choice at $0.

### 4.6 Observability — **PS-DESIGN-6 (AC5.2)**

Three layers, each independently degradable:

1. **Logs** — the existing structured `console` handler (request_id + account_id, no raw email)
   writes to stdout; Render captures and exposes the stream. **No change.**
2. **Liveness vs. deep health** — add a **DB-only `health_live`** view at `/health/live`
   (200 if `SELECT 1` succeeds, else 503) as the **platform health-check + UptimeRobot** target.
   Keep the existing `/health` (DB **+** live SMTP) as the **operator deep probe**. *Rationale:*
   `/health` opening an SMTP socket makes it unsafe for an orchestrator — a transient provider
   blip would mark the service unhealthy and loop restarts. Liveness must depend only on the
   process + DB. This is a small additive fix to a real production hazard found in code.
3. **Error visibility** — **Sentry**, initialized only when `SENTRY_DSN` is set (env-gated;
   unset = disabled, so local/test are untouched). Free tier (5 k events/mo) answers AC5.2's
   "are requests erroring." `sentry-sdk[django]` is an optional, env-guarded dep.

---

## 5. Frontend shell — one responsive look (PS-DESIGN-7)

This is the load-bearing UX work (M4; the app page + widget are the wedge's public face, D-11).
Current reality: **6 duplicated `base.html` and no CSS.** Polishing six copies independently would
duplicate the responsive stylesheet six times — a direct violation of CLAUDE.md §5.1/§5.3
(optimize for the reader; reuse before you write). The robust answer is **consolidation**:

- **One shared shell** — `apps/core/templates/core/base.html`: the responsive HTML scaffold
  (header with platform nav + auth state, `<main>`, footer), `<meta viewport>` (already present
  everywhere), one `<link rel="stylesheet" href="{% static 'core/app.css' %}">`, and the block
  contract in §7.1.
- **One stylesheet** — `apps/core/static/core/app.css`: a small, **dependency-free, mobile-first**
  stylesheet (system font stack, fluid container, responsive nav, accessible form/table/card
  styles). **No CSS framework, no build step** — honors D-4's server-rendered, zero-build posture
  and keeps the surface auditable (§5.5 boring). Standard breakpoints (e.g. ~600/900 px).
- **Re-point the 6 app bases** to `{% extends "core/base.html" %}` (each keeps its own
  `{% block %}` overrides), collapsing them toward deletion (CLAUDE.md §5.4 design-for-deletion;
  one source of truth for chrome).
- **The embeddable widget stays isolated.** [apps/widget/templates/widget/](../../apps/widget/templates/widget/)
  must **not** pull the platform stylesheet — it renders inside third-party iframes and must stay
  self-contained (it already carries inline `<style>`). Preserving this isolation also preserves
  the **AC3.3 firewall** (the widget imports nothing from the platform shell). This is an explicit
  non-change, called out so the build does not "helpfully" unify it.

Scope guard: this is **polish of existing templates**, not an SPA — AC6.2 only *gathers evidence*
for a later, separate D-4-revisit. No client framework is introduced (brief *Out of scope*).

---

## 6. Data design

**No new tables, no migrations, no schema change.** This feature touches deployment, serving,
templates, and config only. Existing data lifecycles are unchanged:

- **Postgres** is the one source of truth for all app data; staging gets a **fresh, empty**
  managed instance — AC1.3 verifies all existing migrations apply cleanly to it with no manual
  SQL. Retention = managed-provider backups (default; no app-level change).
- **Media files** live on the persistent disk (or object store on promotion); the DB holds the
  paths (unchanged). One source of truth per fact preserved.
- **Cache** (rate-limit counters; sessions are DB-backed already) is **ephemeral** — losing Redis
  loses only in-flight rate counts, and the limiter fails open by design.

---

## 7. Interface contracts

### 7.1 Frontend shell — template block contract (`core/base.html`)

The stable surface every wedge template inherits. **Additive-only** (new blocks never remove
old ones):

| Block | Purpose | Default |
|---|---|---|
| `{% block title %}` | `<title>` text. | `"App Discovery"` |
| `{% block head %}` | Per-page `<head>` extras (e.g. page-specific `<meta>`). | empty |
| `{% block content %}` | The page body inside `<main>`. | empty |

Invariant: the shell always emits the viewport meta + the single stylesheet link; child templates
never re-declare `<html>/<head>/<body>`. Evolves without breaking consumers because it only adds
blocks/markup, never renames an existing block.

### 7.2 Liveness endpoint

```
GET /health/live
  200 {"status": "ok"}        when SELECT 1 succeeds
  503 {"status": "down"}      when the DB is unreachable
```
Invariant: depends on **process + DB only** — never on email, cache, or any external transport, so
it is safe as an automated health-check. Distinct from `GET /health` (DB **and** email; operator
deep probe, unchanged).

### 7.3 Configuration contract (env)

`.env.example` is extended (AC2.2) with every new variable, each with a comment and a safe local
default where one exists. New keys: `DATABASE_URL` (optional; overrides discrete `DB_*`),
`REDIS_URL` (optional; LocMem fallback), `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS`,
`CSRF_TRUSTED_ORIGINS`, `SENTRY_DSN` (optional), and the already-present
`DJANGO_*`/`MEDIA_ROOT`/`PUBLIC_BASE_URL`. **Invariant:** no secret is committed; required-in-prod
vars (`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, a DB source, an email transport) fail loud when
absent under `not DEBUG` (the existing `env(..., required=not DEBUG)` pattern, extended).

### 7.4 Deploy procedure contract

`docs/deploy/deploy-runbook.md` is an **ordered, copy-pasteable** procedure (provision Postgres
→ Redis → disk → set env → connect repo / apply Blueprint → release runs migrate+collectstatic →
verify AC1.1/AC1.2/AC1.3). AC2.1 is met iff a second clean run from *only* these steps yields an
equivalent working environment with **zero undocumented manual fix-ups**.

---

## 8. UX flow (states)

No new screens. The shell adds consistent **chrome + responsive layout** to existing flows. The
states the polish must honor on every surface, desktop **and** phone width:

- **Loaded / normal** — content within the fluid container; nav reachable; no horizontal scroll.
- **Empty** — existing empty states (e.g. no apps, no followers, empty dashboard) render inside
  the shell without breaking layout.
- **Error** — Django error/permission pages and form-validation errors render readably (not raw),
  styled by the shared stylesheet.
- **Auth state** — the nav reflects signed-in vs anonymous (the shell reads the existing
  `request.user`).

The **suggested full-role walkthrough script** (`.md`, PS-3) that drives these states across the
three roles × web+mobile is a **Stage-4 deliverable** authored with `TEST_PLAN.md` — named here,
not written here (it is a test artifact, not architecture).

---

## 9. Non-functional handling & failure modes

| Component | Failure | Detection | Response |
|---|---|---|---|
| **Web service** | Process down / crash-loop | `/health/live` 503; platform health check | Platform restarts; logs + Sentry show cause. Liveness is DB-only so email blips don't trigger this. |
| **PostgreSQL** | Unreachable / slow | `SELECT 1` fails; 5xx | **Loud** — `/health/live` 503, app errors surface (no silent fallback to a degraded mode). Managed backups for recovery. |
| **Email (Resend/SMTP)** | Provider down / bad creds | `DefaultEmailSender` **raises** (`fail_silently=False`); registration surfaces 503 | **Loud, never silent** (existing contract). Magic-link sign-in is blocked → walkthrough notes it; does not corrupt state. `/health` (deep) shows email-degraded without failing liveness. |
| **Static assets** | Missing / not collected | AC1.2 check: assets 200, no broken styling | collectstatic in the release step is mandatory; manifest storage **fails loud at build** if a referenced asset is absent. |
| **Media disk** | Disk full / detached | Upload errors; broken images | Surfaced (not swallowed); object-store swap is the growth path. Staging volume sized for the test corpus. |
| **Cache (Redis)** | Outage | `cache` ops error | Limiter **fails open** (existing design) — auth still works, limits relax; degraded metric counted. Never blocks a user. |
| **Sentry** | DSN bad / quota | init/exception export fails | Env-gated + non-fatal — monitoring degrades, the app does not. |
| **Misconfig** (missing `SECRET_KEY`/hosts/DB) | Required var absent under `not DEBUG` | `env(required=...)` raises at startup | **Fail loud at boot** — the deploy fails visibly rather than serving insecurely. |

**Security model (Step-10).** TLS terminates at the platform; `SECURE_PROXY_SSL_HEADER` already
makes Django honor `X-Forwarded-Proto`, so HSTS/secure-cookies/SSL-redirect activate (C2). Add
`CSRF_TRUSTED_ORIGINS` for the HTTPS origin (required by Django 4+ for cross-origin-referer POSTs
behind a proxy). Least privilege: DB/email/Sentry creds are per-service env secrets, never
committed (AC2.2); logs identify actors by UUID only (existing). No new attack surface — no new
endpoints except a read-only DB-ping liveness probe. The widget firewall (AC3.3) is preserved by
**not** coupling the widget to the platform shell (§5).

---

## 10. Trade-offs & alternatives considered

1. **Static serving — WhiteNoise vs. a CDN/nginx sidecar.** Chose WhiteNoise: zero extra
   service, hashed+compressed, serves admin assets, standard Django. Sacrifice: the app process
   serves static (fine at staging scale; a CDN in front is the trivial growth path, env/DNS only).
2. **Media — persistent disk vs. object store now.** Chose disk for staging (no new dep, boring);
   sacrifice: single-node, doesn't scale horizontally — accepted + documented, with R2 +
   `django-storages` as the named promotion upgrade (§4.3). Object-store-now was rejected as a
   speculative dep/setup before it's needed (§5.5).
3. **Cache — Redis vs. single-worker gunicorn.** Both make the limiter correct. Chose env-wired
   Redis with LocMem fallback because it's the **prod-bound** answer at $0 and keeps multi-worker
   throughput; single-worker was the simpler-but-throughput-capped alternative, kept as the
   fallback if managed Redis is unavailable.
4. **Frontend — consolidate to one shell vs. polish 6 bases in place.** Chose consolidation
   (DRY, one source of truth, design-for-deletion); sacrifice: a one-time refactor touching ~30
   templates (mechanical, sequenced in Stage 3). In-place polish was rejected as debt that
   violates §5.1/§5.3.
5. **Host — Render vs. Heroku/Fly/VPS.** Covered in §4.1; Render chosen for declarative
   repeatability + managed everything within budget; portability preserved by standard Django.

**What the chosen design sacrifices overall:** a small amount of host lock-in (mitigated by
standard Django + one declarative file) and single-node media/throughput at staging (both with
named, config-only growth paths). It buys: structural repeatability, correct security/limiter
behavior under load, and a credible responsive face — the things the brief actually requires.

---

## 11. Tech-stack decision (global)

This feature makes **repo-wide infrastructure + frontend-shell decisions every later feature
inherits** (a later feature would be wrong to hardcode DB config, bypass the shared shell, or
assume a different host/email/cache wiring). On approval these are recorded as a single global
ADR **D-12** in [DECISIONS.md](../../DECISIONS.md) (deployment/serving stack + the shared
frontend shell), per the persona hand-off. New dependencies added to
[pyproject.toml](../../pyproject.toml): `gunicorn`, `whitenoise`, `dj-database-url`, `redis`,
`sentry-sdk[django]`. No change to D-4's language/framework/DB — this **implements** D-4's
"email provider is ops config" and D-11's "polish the templates" clauses; it does not introduce
an SPA or a second language.

---

## 12. Self-critique (skeptical pass)

- *"Is consolidating 6 base templates scope creep?"* No — it's the only non-duplicative way to do
  the responsive polish the brief mandates; doing it any other way violates §5.1/§5.3. But it does
  touch many files → flagged for Stage-3 sequencing and a render-every-surface check.
- *"Does this design hide any silent failure?"* The pre-existing `/health` SMTP-socket hazard is
  the one real footgun found — fixed by the liveness split (§4.6). Everything else fails loud.
- *"Any speculative abstraction?"* No object store, no CDN, no SPA, no Celery — all named as growth
  paths, none built (§5.5). The only new runtime code is a 3-line liveness view + env-gated Sentry
  init + the cache/DB env bridges.
- *"Is the deploy genuinely repeatable, or a runbook of clicks?"* The Blueprint is declarative, so
  the second run *is* re-applying it; the runbook documents the irreducible account/secret setup.
  AC2.1's "no undocumented manual fix-ups" is the explicit gate.
- *"Residual user decisions?"* Host + email provider are external accounts/spend, and the
  base-template consolidation is a scope-appetite call — surfaced as **DN-PS-DESIGN** rather than
  assumed.

---

## 13. AC → design-element coverage (exit criteria)

| AC | Design element |
|---|---|
| **AC1.1** HTTPS, DEBUG off, landing serves | §4.1 Render TLS + `*.onrender.com`; C2 security gating; §7.3 env |
| **AC1.2** all primary routes 200 + assets load | §4.2 WhiteNoise (incl. admin) + §4.3 media route; route checklist in TEST_PLAN |
| **AC1.3** migrations apply to empty PG | §4.1 managed Postgres; §6 no new migration; release `migrate` |
| **AC2.1** repeatable second run | §4.1 declarative `render.yaml` + §7.4 runbook |
| **AC2.2** no committed secret, vars documented | §7.3 `.env.example` extension; env-only secrets |
| **AC3.1** dev journey + real email arrives | §4.4 Resend/SMTP + email-setup `.md`; existing flows |
| **AC3.2** app page + widget credible on mobile | §5 shared responsive shell; widget isolated (human sign-off, PS-3) |
| **AC3.3** widget funnel records, firewall intact | §5 widget isolation preserved; no change to widget code |
| **AC4.1** audience journey web + mobile | §5 shell across accounts/discovery/interests/subscriptions |
| **AC4.2** mobile registration/browse usable | §5 + §8 states (human sign-off, PS-3) |
| **AC5.1** admin ACCEPT → public per D-6 | no change (existing admin + D-6 gate); deployed reachably |
| **AC5.2** logs + uptime/error monitoring | §4.6 stdout logs + `/health/live` + Sentry |
| **AC6.1 / AC6.2** go/no-go + frontend verdict | Stage-4 walkthrough vs §5 evidence; verdicts are walkthrough outputs |

Every AC maps to ≥1 element. The two `.md` deliverables: email-setup (§4.4, deploy work);
walkthrough script (§8, Stage 4). No "TBD" in any §7 contract.

---

## 14. Rollout strategy

- **No feature flag / no migration** — the activation switch is **the deploy itself**; rollback =
  point traffic back / tear the Blueprint down. The codebase keeps running locally exactly as
  before (every new behavior is env-gated with a dev-safe default: `DEBUG=true` ⇒ LocMem, console
  email, DEBUG media route, no Sentry).
- **Smallest useful first version (increment 1):** the serving stack reachable — gunicorn +
  WhiteNoise + DB bridge + `render.yaml` + `STATIC_ROOT`/collectstatic, deployed, AC1.1/AC1.2/AC1.3
  green on the bare (unstyled) templates.
- **Increment 2:** email provider wired (AC3.1/M5) + the email-setup `.md`.
- **Increment 3:** the responsive shell (§5) — the M4 polish.
- **Increment 4:** observability (liveness split + Sentry) + the shared cache.
- **Increment 5:** run the walkthrough, fix surfaced defects, emit the two verdicts (AC6).
- **Backward compat:** local dev and the test suite are unaffected (env-gated). No consumer of any
  existing contract changes; the only API additions are additive (a liveness route, new template
  blocks).

---

## 15. Decisions (PROPOSED — ratify at `DN-PS-DESIGN`)

| ID | Decision | Status |
|---|---|---|
| **PS-DESIGN-1** | Host = **Render** Blueprint (web + managed Postgres + disk + free Redis); free now, ~$14–25/mo durable. | PROPOSED |
| **PS-DESIGN-2** | **gunicorn** + **WhiteNoise** (CompressedManifest) + **`dj-database-url`** (discrete-var fallback). | PROPOSED |
| **PS-DESIGN-3** | Media on a **persistent disk**; object store (R2 + `django-storages`) = documented growth path. | PROPOSED |
| **PS-DESIGN-4** | Email = **Resend** over Django SMTP (pure config); Postmark = premium alt; ships `email-provider-setup.md`. | PROPOSED |
| **PS-DESIGN-5** | Shared cache from **`REDIS_URL`** (Django built-in `RedisCache`), LocMem fallback → limiter correct under workers. | PROPOSED |
| **PS-DESIGN-6** | Observability = stdout logs + **Sentry** (env-gated) + a new **DB-only `/health/live`** liveness probe (split from `/health`). | PROPOSED |
| **PS-DESIGN-7** | One **shared responsive base template + stylesheet** in `apps/core`; 6 bases consolidated; **widget stays isolated**. | PROPOSED |
| **PS-DESIGN-8** | Committed deploy artifacts: `render.yaml`, the 5 deps, settings/env changes, `docs/deploy/{deploy-runbook,email-provider-setup}.md`. | PROPOSED |

---

## Gate — `DN-PS-DESIGN` (raised; Architect stops here)

The architecture is fully specified; three calls benefit from explicit user confirmation before
ratification (external accounts / spend / a scope-shape call). Recorded in
[CONTROL.md](../../CONTROL.md) *Decisions Needed From You*:

1. **Hosting stack (PS-DESIGN-1).** Confirm **Render** (Blueprint + managed Postgres + disk +
   free Redis; free tier now, ~$14–25/mo on the durable/prod-bound tier within PS-1). The user
   holds the account + card and may have a region/provider preference (e.g. an existing Fly/Heroku
   account).
2. **Email provider (PS-DESIGN-4 / PS-2).** Confirm **Resend** (free tier fits staging) vs.
   **Postmark** (deliverability-premium, $15/mo). The user creates the account; the deploy ships
   the setup `.md` for the chosen one.
3. **Frontend consolidation appetite (PS-DESIGN-7).** Confirm consolidating the 6 `base.html` into
   **one shared responsive shell + stylesheet** now (the recommended, DRY, long-term answer — a
   one-time refactor touching ~30 templates) vs. a lighter in-place polish (faster, more debt).

The remaining decisions (PS-DESIGN-2/3/5/6/8) are standard architecture within the ratified
budget and proceed on approval of the above. On ratification: promote PS-DESIGN-1…8 → RATIFIED,
record global **D-12**, set `Stage: 3-plan`, hand to the **Planner / Tech Lead**.
