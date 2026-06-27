# TASKS.md — platform-staging

**Status:** **READY FOR BUILD** 2026-06-27. **Stage 3 (Planner / Tech Lead) artifact.**

**Upstream source:** APPROVED [DESIGN.md](DESIGN.md) (PS-DESIGN-1…8 RATIFIED, global
[D-12](../../DECISIONS.md)) + APPROVED [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1.1–AC6.2,
PS-1/2/3). This decomposes the design into ordered, independently verifiable tasks; it does
**not** re-design (any gap → [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md), bounce to Stage 2).

---

## How to read this list

- **Order = build order.** Risk is front-loaded: the serving/static stack (the real gap in
  the codebase — no `STATIC_ROOT`, no WSGI manifest, `DATABASE_URL` unparsed) is **T-01**,
  per the [DESIGN.md §14](DESIGN.md) increment-1 ("serving stack reachable" first).
- **Every task leaves local dev + the test suite working.** Each new behavior is **env-gated
  with a dev-safe default** ([DESIGN.md §14](DESIGN.md)): `DEBUG=true` ⇒ LocMem cache, console
  email, DEBUG media route, no Sentry, discrete `DB_*`. So no task can regress local dev — the
  DoD "full suite green + `manage.py check` clean" holds at every step.
- **No schema, no migration** ([DESIGN.md §6](DESIGN.md)) — there is no data layer in this
  feature; sequencing is config → serving → email → frontend shell → observability → docs/tests.
- **`.env.example` is extended by the task that introduces each variable** (one source of
  truth, vertical), and **T-10** does the final completeness + no-committed-secret pass (AC2.2).
- **All tasks are S or M. No `L` remains** (persona exit criterion).

> **Defect-fix loop (Stage 4/5, not pre-listed):** [DESIGN.md §14](DESIGN.md) increment-5 and
> AC6 fix the defects the walkthrough *surfaces*. Those are emergent and cannot be enumerated
> now without guessing — they are handled as they arise, each logged in
> [TEST_PLAN.md](TEST_PLAN.md) / [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) with a disposition
> (fixed / logged, AC6.1/M7). This file lists only the *known* buildable work.

---

## Tasks

### T-01 — Production WSGI + static pipeline + `DATABASE_URL` bridge
- **Description.** Close the serving gap from [DESIGN.md §4.2](DESIGN.md) (PS-DESIGN-2) and the
  C4/§2 findings. Add deps `gunicorn`, `whitenoise`, `dj-database-url`. In
  [config/settings.py](../../config/settings.py): add `STATIC_ROOT` + set
  `STORAGES["staticfiles"]["BACKEND"]` to
  `whitenoise.storage.CompressedManifestStaticFilesStorage`; insert WhiteNoise middleware
  **immediately after** `SecurityMiddleware`; parse `DATABASE_URL` via `dj-database-url` when
  present, **falling back to the existing discrete `DB_*` vars** (local unchanged, one
  env-selected source of truth); add `CSRF_TRUSTED_ORIGINS` from env (Django 4+ behind a TLS
  proxy, [DESIGN.md §9](DESIGN.md) security model). App `static/` dirs are auto-discovered by
  `AppDirectoriesFinder` — **no `STATICFILES_DIRS`**.
- **Dependencies.** None (first — risk front-loaded).
- **Definition of done.**
  - `gunicorn config.wsgi:application` boots locally; `python manage.py collectstatic --noinput`
    produces a hashed, manifested `STATIC_ROOT` including **Django-admin assets** (AC1.2).
  - With `DATABASE_URL` set, the app connects to that DB; with it unset, the discrete `DB_*`
    path is byte-for-byte the prior behavior (local dev unchanged).
  - `manage.py check` clean under both `DEBUG=true` and a simulated `DEBUG=false` env; **full
    suite green**; `ruff` clean; no model/migration drift.
  - `.env.example` documents `DATABASE_URL` (optional; overrides `DB_*`) + `CSRF_TRUSTED_ORIGINS`.
- **Size.** M.
- **Files/areas.** [pyproject.toml](../../pyproject.toml), [config/settings.py](../../config/settings.py),
  [.env.example](../../.env.example).

### T-02 — Non-`DEBUG` persistent-media serving route
- **Description.** [DESIGN.md §4.3](DESIGN.md) (PS-DESIGN-3) + §2 media gap. Today media is
  served **only** under `if settings.DEBUG` in [config/urls.py](../../config/urls.py); on
  staging (`DEBUG=false`) uploaded screenshots 404 (AC1.2 broken images). Add a media route that
  serves `MEDIA_URL` from `MEDIA_ROOT` **regardless of `DEBUG`** (the persistent-disk mount),
  keeping the existing DEBUG convenience path intact. This is the deliberate, bounded single-node
  trade-off ([DESIGN.md §10 #2](DESIGN.md)); the object-store swap (`STORAGES["default"]` → R2 +
  `django-storages`) is the **named growth path, not built here** (§5.5).
- **Dependencies.** T-01 (finalizes the static/media serving posture in one pass).
- **Definition of done.**
  - With `DEBUG=false` and a file under `MEDIA_ROOT`, requesting its `MEDIA_URL` returns the file
    (200), not a 404; the DEBUG path is unchanged.
  - A short test asserts the media route resolves with `DEBUG=false`; **full suite green**;
    `check`/`ruff` clean.
- **Size.** S.
- **Files/areas.** [config/urls.py](../../config/urls.py), [config/settings.py](../../config/settings.py)
  (media region only).

### T-03 — Render Blueprint (`render.yaml`): web + Postgres + disk + Redis
- **Description.** [DESIGN.md §4.1](DESIGN.md) (PS-DESIGN-1) + §7.4. Author `render.yaml`
  declaring: one **Web Service** (Python, start = `gunicorn config.wsgi:application`,
  **release/build = `python manage.py migrate --noinput && python manage.py collectstatic
  --noinput`**), one **Managed PostgreSQL** (auto-wires `DATABASE_URL` via `fromDatabase`), one
  **persistent disk** mounted at `MEDIA_ROOT`, and a **free Key Value / Redis** (auto-wires
  `REDIS_URL` via `fromService`). Declare the **complete §7.3 env contract** by name —
  `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
  `EMAIL_*`, `SENTRY_DSN` — as dashboard secrets (`sync:false`), **never committed values**
  (AC2.2). Declaring the names here is stable; the *settings consumers* for email/cache/Sentry
  land in T-04/T-08/T-09 and **do not require revisiting the Blueprint**.
- **Dependencies.** T-01, T-02 (release command runs `collectstatic`; disk mounts `MEDIA_ROOT`).
- **Definition of done.**
  - `render.yaml` is well-formed YAML, validates against the Render Blueprint schema (web +
    database + keyvalue + disk blocks present), and the release command includes both `migrate`
    and `collectstatic`.
  - No secret literal appears in the file (only names / `sync:false` / `fromDatabase` /
    `fromService` refs).
  - The free→paid tier is a single plan field (documented inline comment, [DESIGN.md §4.1](DESIGN.md)
    cost note).
- **Size.** M.
- **Files/areas.** `render.yaml` (new, repo root).

### T-04 — Email transport over SMTP + provider setup guide (PS-2)
- **Description.** [DESIGN.md §4.4](DESIGN.md) (PS-DESIGN-4). The transport is already pluggable
  by `EMAIL_BACKEND` ([apps/core/email.py](../../apps/core/email.py)), **but** Django's SMTP
  backend reads `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` from *settings*, which
  [config/settings.py](../../config/settings.py) does **not** currently expose — so wire those
  five from env (with Django's stock defaults as fallback, console default unchanged). Write
  [docs/deploy/email-provider-setup.md](../../docs/deploy/) for **Resend**: create account →
  verify a sending domain (SPF/DKIM) → obtain SMTP creds → set the env vars → send a test
  (Postmark named as the deliverability-premium alternative). **No change to the email-sending
  code path** (`DefaultEmailSender` still fails loud).
- **Dependencies.** None functionally (sequence after T-03; shares `config/settings.py`).
- **Definition of done.**
  - With `EMAIL_BACKEND=…smtp…` + the five env vars set, Django's SMTP backend uses them; with
    them unset the **console backend default is unchanged** (local dev / tests untouched).
  - `docs/deploy/email-provider-setup.md` exists and is a complete, ordered account→creds→test
    procedure; `.env.example` documents `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS`.
  - **Full suite green**; `check`/`ruff` clean. (AC3.1/M5 themselves gate on a real inbox at
    Stage 5, per PS-2.)
- **Size.** S.
- **Files/areas.** [config/settings.py](../../config/settings.py) (email region),
  [.env.example](../../.env.example), `docs/deploy/email-provider-setup.md` (new).

### T-05 — Shared responsive shell: `core/base.html` + `core/app.css`
- **Description.** [DESIGN.md §5](DESIGN.md) (PS-DESIGN-7) + the §7.1 block contract. Create
  `apps/core/templates/core/base.html` — the responsive HTML scaffold (header with platform nav
  + auth state read from `request.user`, `<main>`, footer), `<meta viewport>`, a single
  `<link rel="stylesheet" href="{% static 'core/app.css' %}">`, and the **additive-only** block
  contract: `{% block title %}` (default `"App Discovery"`), `{% block head %}` (empty),
  `{% block content %}` (empty). **Render Django `messages` once in `<main>`** so the consolidation
  preserves the message display that [apps/updates/templates/updates/base.html](../../apps/updates/templates/updates/base.html)
  carries today (no surface loses it). Create
  `apps/core/static/core/app.css` — a small **mobile-first, dependency-free, no-build** stylesheet
  (system font stack, fluid container, responsive nav, accessible form/table/card styling,
  standard ~600/900 px breakpoints). **No CSS framework, no build step** (honors D-4 zero-build).
- **Dependencies.** None (new files; nothing extends the shell yet, so zero visual change ships
  here — releasable in isolation).
- **Definition of done.**
  - `core/base.html` renders standalone; `collectstatic` picks up `core/app.css` (new
    `apps/core/static/` dir, which does not exist today); the stylesheet adds no external request.
  - Block contract matches [DESIGN.md §7.1](DESIGN.md) exactly (3 blocks, names + defaults).
  - `manage.py check` clean; **full suite green**.
- **Size.** M.
- **Files/areas.** `apps/core/templates/core/base.html` (new),
  `apps/core/static/core/app.css` (new).

### T-06 — Consolidate the 6 app `base.html` onto the shell (+ render-every-surface check)
- **Description.** [DESIGN.md §5](DESIGN.md) consolidation. Re-point each of the **6** app bases
  — [accounts](../../apps/accounts/templates/accounts/base.html),
  [catalog](../../apps/catalog/templates/catalog/base.html),
  [dashboard](../../apps/dashboard/templates/dashboard/base.html),
  [discovery](../../apps/discovery/templates/discovery/base.html),
  [pages](../../apps/pages/templates/pages/base.html),
  [updates](../../apps/updates/templates/updates/base.html) — to
  `{% extends "core/base.html" %}`, each **keeping its own `{% block title %}`/`{% block head %}`
  overrides**; the messages markup updates carried moves to the shared shell (T-05). The **19
  child templates** that `{% extends %}` these app bases are unchanged (multi-level block
  inheritance flows child → app base → shell). **The widget stays isolated** — do **not** add
  the platform stylesheet to [apps/widget/templates/widget/](../../apps/widget/templates/widget/)
  (self-contained inline `<style>` preserved); this preserves the **AC3.3 firewall** and is an
  explicit non-change ([DESIGN.md §5](DESIGN.md) final bullet).
- **Dependencies.** T-05 (the shell must exist to extend it).
- **Definition of done.**
  - All 6 app bases extend `core/base.html`; no app base re-declares `<html>/<head>/<body>`.
  - **Render-every-surface check:** every one of the **30** templates renders without
    `TemplateSyntaxError`, and each primary route ([DESIGN.md §13](DESIGN.md) AC1.2 list: home,
    an app page, search/browse, sign-in, dashboard, the widget embed, Django admin) returns its
    expected status with the stylesheet linked. Message display still works on a surface that
    emits messages (e.g. updates).
  - Widget templates are byte-unchanged (no platform stylesheet link); the AC3.3 firewall test /
    `apps/widget` import-isolation is still green.
  - **Full suite green**; `check`/`ruff` clean.
- **Size.** M.
- **Files/areas.** The 6 `apps/*/templates/*/base.html` listed above. (Widget templates:
  **explicitly untouched.**)

### T-07 — DB-only liveness probe `/health/live` (split from `/health`)
- **Description.** [DESIGN.md §4.6](DESIGN.md) (PS-DESIGN-6) + §7.2. The existing `/health`
  ([apps/core/views.py](../../apps/core/views.py) → `check_health` opens a live SMTP socket via
  `_email_ok`), which makes it **unsafe as an orchestrator liveness target** (a transient
  provider blip would loop restarts — a real footgun found in code). Add a `health_live` view
  + `/health/live` route that depends on **process + DB only** (reuse `_database_ok`): `200
  {"status":"ok"}` on `SELECT 1`, `503 {"status":"down"}` otherwise. **Keep `/health` (DB +
  email) unchanged** as the operator deep probe.
- **Dependencies.** None (additive; reuses `_database_ok`).
- **Definition of done.**
  - `GET /health/live` → 200 `{"status":"ok"}` when the DB is up; 503 `{"status":"down"}` when
    unreachable; it **never opens an SMTP connection** (asserted — email-down must not affect it).
  - `GET /health` behaviour is unchanged (test still green).
  - New tests cover both branches; **full suite green**; `check`/`ruff` clean.
- **Size.** S.
- **Files/areas.** [apps/core/views.py](../../apps/core/views.py),
  [apps/core/observability.py](../../apps/core/observability.py) (reuse `_database_ok`),
  [config/urls.py](../../config/urls.py), `apps/core/tests/`.

### T-08 — Shared cache from `REDIS_URL` (LocMem fallback) → limiter correct under workers
- **Description.** [DESIGN.md §4.5](DESIGN.md) (PS-DESIGN-5) + §2 cache gap. The auth limiter
  ([apps/core/ratelimit.py](../../apps/core/ratelimit.py)) counts in Django's **default cache**
  and **fails open**; with no `CACHES`, gunicorn's N workers each get a private LocMem counter →
  limits are N× looser (security degradation). Add `CACHES["default"]` = Django 5 built-in
  `RedisCache` from `REDIS_URL` when set, **falling back to `LocMemCache` when unset** (local /
  test unchanged). Add the `redis` client dep.
- **Dependencies.** None functionally (sequence after T-04; shares `config/settings.py`).
- **Definition of done.**
  - `REDIS_URL` unset → `LocMemCache` (the limiter still works; local/test behaviour unchanged).
  - `REDIS_URL` set → `RedisCache`; the limiter contract ([apps/core/ratelimit.py](../../apps/core/ratelimit.py))
    is unaffected (fail-open preserved). A test covers the fallback selection.
  - `.env.example` documents `REDIS_URL` (optional; LocMem fallback). **Full suite green**;
    `check`/`ruff` clean.
- **Size.** S.
- **Files/areas.** [config/settings.py](../../config/settings.py) (new `CACHES` region),
  [pyproject.toml](../../pyproject.toml), [.env.example](../../.env.example).

### T-09 — Env-gated Sentry error monitoring
- **Description.** [DESIGN.md §4.6 #3](DESIGN.md) (PS-DESIGN-6) + AC5.2. Initialize
  `sentry_sdk` **only when `SENTRY_DSN` is set** (env-gated; unset ⇒ disabled, so local/test are
  untouched). Add the `sentry-sdk[django]` optional dep. This is the only error-visibility layer
  beyond the existing stdout structured logs (which are **unchanged**).
- **Dependencies.** None functionally (sequence after T-08; shares `config/settings.py`).
- **Definition of done.**
  - `SENTRY_DSN` unset → no `sentry_sdk.init` call, no import-time failure (local/test untouched);
    set → initialized once at startup.
  - `.env.example` documents `SENTRY_DSN` (optional). `manage.py check` clean under both states;
    **full suite green**; `ruff` clean.
- **Size.** S.
- **Files/areas.** [config/settings.py](../../config/settings.py) (env-gated init block),
  [pyproject.toml](../../pyproject.toml), [.env.example](../../.env.example).

### T-10 — Deploy runbook + `.env.example` completeness / no-secret pass (AC2.1/AC2.2)
- **Description.** [DESIGN.md §7.4](DESIGN.md) + §7.3. Write
  [docs/deploy/deploy-runbook.md](../../docs/deploy/) — an **ordered, copy-pasteable** procedure:
  provision Postgres → Redis → disk → set env (secrets) → connect repo / apply the Blueprint →
  the release step runs `migrate` + `collectstatic` → verify AC1.1 (HTTPS, `DEBUG` off, landing)
  / AC1.2 (route + asset checklist) / AC1.3 (migrations on empty PG). Then a final pass: confirm
  `.env.example` documents **every** new variable introduced across T-01/T-03/T-04/T-08/T-09,
  each with a comment + safe local default where one exists, and **grep-confirm no secret literal
  is committed** anywhere (AC2.2).
- **Dependencies.** T-01, T-02, T-03, T-04, T-08, T-09 (documents the complete env + Blueprint;
  the completeness pass needs every var to exist).
- **Definition of done.**
  - `docs/deploy/deploy-runbook.md` is an ordered procedure ending in the AC1.1/AC1.2/AC1.3
    verification steps; AC2.1's "no undocumented manual fix-ups" is its explicit closing gate.
  - `.env.example` is complete vs. [DESIGN.md §7.3](DESIGN.md); a repo grep shows **no committed
    secret**; required-in-prod vars fail loud when absent under `not DEBUG` (existing
    `env(required=…)` pattern, verified).
- **Size.** M.
- **Files/areas.** `docs/deploy/deploy-runbook.md` (new), [.env.example](../../.env.example).

### T-11 — `TEST_PLAN.md` + suggested full-role walkthrough script (PS-3)
- **Description.** [DESIGN.md §8](DESIGN.md) + §13 + the brief's two `.md` deliverables. Author
  [TEST_PLAN.md](TEST_PLAN.md) mapping **every AC1.1–AC6.2** to a concrete check, tagged
  *agent-verifiable* (a command/route/assertion the engineer runs) vs *human-judgment* (a
  sign-off line the user records, AC3.2/AC4.2/AC6). Author `docs/deploy/staging-walkthrough.md` —
  the **suggested full-role walkthrough script** the user follows (PS-3): each of the three roles
  (end user / developer / admin) × **web + mobile**, step-by-step against the live staging URL,
  with explicit **sign-off lines** for the human-judgment ACs and a closing **go/no-go (AC6.1)** +
  **frontend verdict (AC6.2)** template. The user *performs* it (PS-3); the agent runs every
  agent-verifiable check.
- **Dependencies.** T-01…T-09 (the buildable surface the plan/script exercise). The walkthrough
  is *run* at Stage 4/5; this task **authors** the artifacts.
- **Definition of done.**
  - [TEST_PLAN.md](TEST_PLAN.md) covers **every** AC1.1–AC6.2 (no AC unmapped), each tagged
    agent-verifiable vs human-judgment with its check/sign-off.
  - `docs/deploy/staging-walkthrough.md` enumerates each role's primary journeys × web+mobile with
    explicit sign-off lines for AC3.2/AC4.2 and the AC6.1/AC6.2 verdict templates.
- **Size.** M.
- **Files/areas.** [TEST_PLAN.md](TEST_PLAN.md), `docs/deploy/staging-walkthrough.md` (new).

---

## AC → task coverage map (exit criterion: every design element in ≥1 task)

| AC | Covered by | Design element ([§](DESIGN.md)) |
|---|---|---|
| **AC1.1** HTTPS, DEBUG off, landing serves | T-01 (security/env, `CSRF_TRUSTED_ORIGINS`), T-03 (Render TLS + URL), T-10 (verify) | §4.1, §9 |
| **AC1.2** routes 200 + CSS/JS/media load | T-01 (WhiteNoise + admin static), T-02 (media route), T-06 (stylesheet on every surface), T-11 (route checklist) | §4.2, §4.3, §5 |
| **AC1.3** migrations apply to empty PG | T-03 (release `migrate`), T-10 (verify); §6 = no new migration | §4.1, §6 |
| **AC2.1** repeatable second run | T-03 (declarative `render.yaml`), T-10 (runbook + the no-fix-up gate) | §4.1, §7.4 |
| **AC2.2** no committed secret, vars documented | T-03 (`sync:false` env), T-10 (`.env.example` completeness + grep) | §7.3 |
| **AC3.1** dev journey + real email arrives | T-04 (SMTP wiring + setup `.md`); existing flows reachable via T-01/T-03 | §4.4 |
| **AC3.2** app page + widget credible on mobile | T-05 + T-06 (responsive shell; widget isolated), T-11 (sign-off) | §5 |
| **AC3.3** widget funnel records, firewall intact | T-06 (widget isolation = explicit non-change), T-11 (verify funnel) | §5 |
| **AC4.1** audience journey web + mobile | T-06 (shell across accounts/discovery/interests/subscriptions), T-11 | §5 |
| **AC4.2** mobile registration/browse usable | T-05/T-06 + §8 states, T-11 (sign-off) | §5, §8 |
| **AC5.1** admin ACCEPT → public per D-6 | no code change (existing admin + D-6 gate); reachable via T-01/T-03; T-11 verifies | §13 |
| **AC5.2** logs + uptime/error monitoring | T-07 (`/health/live`), T-09 (Sentry); existing stdout logs unchanged | §4.6 |
| **AC6.1 / AC6.2** go/no-go + frontend verdict | T-11 (TEST_PLAN + walkthrough script → verdicts authored Stage 4, signed Stage 5) | §8, §13 |

**Design-element check (each appears in ≥1 task):** §4.1→T-03 · §4.2→T-01 · §4.3→T-02 ·
§4.4→T-04 · §4.5→T-08 · §4.6→T-07+T-09 · §5→T-05+T-06 · §6 (no migration)→T-03 release ·
§7.1→T-05 · §7.2→T-07 · §7.3→T-01/04/08/09 (+T-10 completeness) · §7.4→T-10 · §8→T-11 ·
§9 security model→T-01 (`CSRF_TRUSTED_ORIGINS`) + T-07 (liveness) · §11 deps→T-01/T-08/T-09.
**Every §3.1 component and every PS-DESIGN-1…8 decision maps to a task. No element uncovered.**

## Dependency graph (build order)

```
T-01 ─┬─ T-02 ─ T-03 ─┐
      │                ├─ T-10
      ├─ T-04 ─────────┤
      ├─ T-08 ─────────┤
      ├─ T-09 ─────────┘
      └───────────────── T-11
T-05 ─ T-06 ───────────── (T-11)
```

`T-05/T-06` (the frontend shell) are independent of the serving/config chain and can be built
in parallel sessions; everything else funnels into **T-10** (docs/AC2) and **T-11** (test
artifacts). All 11 tasks are **S/M** — none requires splitting before build.

---

## Notes for the Senior Engineer (Stage 4)

- **Build T-01 first** (risk front-loaded — it closes the real C4/§2 serving gap) and write
  [TEST_PLAN.md](TEST_PLAN.md) (T-11) as the AC-coverage spine while building.
- **Reuse before writing** ([CLAUDE.md §5.3](../../CLAUDE.md)): T-07 reuses
  `apps.core.observability._database_ok`; T-04 reuses the pluggable
  [apps/core/email.py](../../apps/core/email.py) transport; T-08 reuses the
  [apps/core/ratelimit.py](../../apps/core/ratelimit.py) `cache` contract. Record any shared code
  in [CODEMAP.md](../../CODEMAP.md).
- **Hold the line on the firewall** (AC3.3): T-06 must **not** couple
  [apps/widget](../../apps/widget) to the platform shell — keep the import-isolation test green.
- **No re-design.** If a task reveals the design is missing something, log it in
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) and bounce to Stage 2 — do not fill the gap in code.
