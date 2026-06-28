# DECISIONS.md — platform-staging (feature-local)

_Choice + rationale + rejected alternatives. Repo-wide decisions go in the top-level
[DECISIONS.md](../../DECISIONS.md)._

**Inherited context:** this feature exists to execute global [D-11](../../DECISIONS.md)
(staging-validation-before-live; frontend stays on Django templates, SPA split deferred +
evidence-gated).

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| PS-DESIGN-1…8 | The Stage-2 deployment/serving stack + shared frontend shell — see [DESIGN.md](DESIGN.md) §15 for the eight-line table. | Promoted to a single repo-wide ADR because they bind infrastructure + a frontend shell every later feature inherits. | **RATIFIED 2026-06-27** as global **[D-12](../../DECISIONS.md)** (DN-PS-DESIGN: user confirmed Render / Resend / Consolidate; standard items 2/3/5/6/8 proceeded on that approval). |

## Stage-4 implementation notes (Senior Engineer, faithful to DESIGN — not re-design)

| ID | Note | Why |
|----|------|-----|
| PS-IMPL-1 | The WhiteNoise **manifest** static backend is gated on `not DEBUG`; under `DEBUG=true` (local dev **and** this project's tests, which preserve DEBUG) the plain `StaticFilesStorage` is used. | DESIGN §4.2 specifies the manifest backend for production; §14 mandates "every new behavior env-gated with a dev-safe default." A manifest backend in DEBUG would make `{% static 'core/app.css' %}` raise "missing manifest entry" on a fresh checkout (no pre-built manifest). Gating preserves the prod intent while keeping dev/test green — the faithful implementation of both §4.2 and §14. |
| PS-IMPL-2 | Media is served by a thin `apps.core.views.serve_media` view that reads `settings.MEDIA_ROOT` **at request time**, rather than binding `document_root` at URLconf import. | One source of truth (CLAUDE.md §5.4): the route tracks `MEDIA_ROOT` instead of snapshotting it, which also makes `override_settings(MEDIA_ROOT=…)` testable. |
| PS-IMPL-3 | settings.py did not previously expose `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS`; T-04 wires all five from env with Django's stock defaults (console default unchanged). | Already flagged in [TASKS.md](TASKS.md) T-04 as a faithful decomposition note — Django's SMTP backend reads these from *settings*, so the pluggable-by-`EMAIL_BACKEND` transport needed the settings exposed to actually use a provider. |
| PS-IMPL-4 | The cache and Sentry selection are small pure functions in settings (`_cache_settings(redis_url)`, `_init_sentry(dsn)`), called at module load. | Makes the env-gated branch directly unit-testable (T-08/T-09) without import-reload gymnastics; the branch logic lives in one obvious place. |
| PS-IMPL-5 | `apps/pages/tests/test_template.py::_slot_labels` now excludes the shared-shell chrome landmarks (`Primary`, `Messages`) so its slot fingerprint stays about the **page's own** slots after consolidation. | T-06 wraps every page in `core/base.html`, which adds the nav landmark — the test's intent (page slots stable across empty/single states) is preserved, and it's now robust to shell changes. |
