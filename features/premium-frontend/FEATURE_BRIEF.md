# FEATURE_BRIEF — premium-frontend

_Stage 1 (Product Analyst) artifact — **pending** (folder scaffolded by the Coordinator
2026-06-28; awaiting the Product Analyst to author the brief)._

## Upstream (why this feature exists)

- **Decision (user, 2026-06-28, recorded in [CONTROL.md](../../CONTROL.md) *Decisions Made* +
  Activity Log):** resolve the [D-11](../../DECISIONS.md) frontend evidence-gate **inside the
  [D-4](../../DECISIONS.md) envelope** — build a **premium server-rendered frontend = HTMX +
  Tailwind + Django templates** (polish, interactivity, premium feel), **NOT** a dedicated SPA.
- **Why it's load-bearing:** the developer's **app page is their marketing landing page** (the
  bring-your-own-audience thesis, [D-10](../../DECISIONS.md)), so a premium feel is load-bearing,
  and the page must stay **SEO-friendly + fast-first-paint** — an SPA would relocate the cost and
  regress SEO/first-paint. The current UI is barebone (one ~199-line
  [`app.css`](../../apps/core/static/core/app.css), system fonts, no design system): the gap is
  **design**, not architecture.
- **Sequencing:** activated **after** `platform-staging` closed out (user: "deploy staging first"
  was revised → build the premium frontend first, then deploy staging on the polished UI).
- **Known carry-in:** **PS-OQ-1** (the bare `/` 404 — no home/landing route) is the natural concern
  of this feature; resolve it here rather than with a throwaway redirect (see
  [platform-staging/OPEN_QUESTIONS.md](../platform-staging/OPEN_QUESTIONS.md)).

## Open scoping calls for Stage 1 (Product Analyst to surface as a gate)

- Tailwind introduces a **build step**, a deliberate revision of [D-12](../../DECISIONS.md)'s
  build-free stylesheet posture — likely a **new global ADR at Stage 2**; the brief should frame the
  appetite (which surfaces get the premium treatment first; scope of HTMX interactivity).

_Problem statement, user stories, acceptance criteria, metrics, scope, constraints: **pending** the
Product Analyst._
