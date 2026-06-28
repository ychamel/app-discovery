# DECISIONS.md — premium-frontend (feature-local)

_Choice + rationale + rejected alternatives. Repo-wide decisions go in the top-level
[DECISIONS.md](../../DECISIONS.md)._

**Inherited context:** this feature exists to execute the user's 2026-06-28 frontend-direction
decision (recorded in [CONTROL.md](../../CONTROL.md)): resolve the [D-11](../../DECISIONS.md)
frontend evidence-gate **inside the [D-4](../../DECISIONS.md) envelope** — a **premium
server-rendered frontend (HTMX + Tailwind + Django templates), not an SPA** — because the
developer's app page is their marketing landing page ([D-10](../../DECISIONS.md)) and must stay
SEO-friendly + fast-first-paint. Tailwind's build step is expected to be a **new global ADR at
Stage 2**, revising [D-12](../../DECISIONS.md)'s build-free posture.

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
| PF-D1 | **Brief APPROVED; scope fixed via DN-PF-BRIEF.** (Q1) restyle **wedge surfaces first** — landing + app page + discover/browse; (Q2) **light progressive enhancement only** for HTMX; (Q3) `/` is a **real platform landing** (resolves PF-CARRY-1). | The app page is the developer's marketing landing page ([D-10](../../DECISIONS.md)), so the public funnel is where "premium" is load-bearing; a shared design system makes authed surfaces a cheap follow-on. Light PE protects SEO/first-paint on those very surfaces. A real front door beats a throwaway redirect. "Premium feel" made checkable via a design system + a PS-3-style sign-off. | **RATIFIED** 2026-06-28 (user) |
| PF-2 | Tailwind **build step** (revises [D-12](../../DECISIONS.md)'s build-free posture). | Named as brief constraint **C3**; the Product Analyst does not decide architecture. | **DEFERRED → Stage 2** (Software Architect; likely a new global ADR) |
