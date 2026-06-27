# FEATURE_BRIEF.md — platform-staging

_Stage 1 (Product Analyst) artifact — **pending**._

**Upstream source:** global [D-11](../../DECISIONS.md) (next bet = staging-validation-before-live),
[STRATEGY.md](../../STRATEGY.md) bet sequence, ratified by the user 2026-06-27 (DN-STRAT-1).

**One-line intent (to be refined in Stage 1):** stand up a reachable **staging**
environment, deploy the code-complete developer wedge, and walk it end-to-end as
**user / developer / admin on web + mobile** — polishing + making the server-rendered
Django templates ([D-4](../../DECISIONS.md)) responsive, and exercising the deferred deploy
work (hosting, domain, the stubbed D-4 email provider, monitoring). Live recruitment
(vision §5.4 step 3) follows once staging validates; the frontend stays on templates,
SPA split deferred + evidence-gated (D-11).

_The Product Analyst owns turning this into the approved brief (stories, acceptance
criteria, metrics, scope boundaries)._
