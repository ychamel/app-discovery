# DECISIONS.md — platform-staging (feature-local)

_Choice + rationale + rejected alternatives. Repo-wide decisions go in the top-level
[DECISIONS.md](../../DECISIONS.md)._

**Inherited context:** this feature exists to execute global [D-11](../../DECISIONS.md)
(staging-validation-before-live; frontend stays on Django templates, SPA split deferred +
evidence-gated).

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| PS-DESIGN-1…8 | The Stage-2 deployment/serving stack + shared frontend shell — see [DESIGN.md](DESIGN.md) §15 for the eight-line table. | Promoted to a single repo-wide ADR because they bind infrastructure + a frontend shell every later feature inherits. | **RATIFIED 2026-06-27** as global **[D-12](../../DECISIONS.md)** (DN-PS-DESIGN: user confirmed Render / Resend / Consolidate; standard items 2/3/5/6/8 proceeded on that approval). |
