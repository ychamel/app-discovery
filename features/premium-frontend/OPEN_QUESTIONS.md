# OPEN_QUESTIONS.md — premium-frontend

_All stages: ambiguities, deferrals, escalations._

| ID | Question | Raised by | Stage | Status |
|----|----------|-----------|-------|--------|
| PF-CARRY-1 | **PS-OQ-1 carried in:** the bare domain `/` has no route (404) — there is no home/landing surface. A landing/home page is this feature's concern. | Coordinator | 0-coordinator | **RESOLVED** 2026-06-28 (PF-1 Q3) — a **real platform landing** at `/` (US-3 / AC-3), not a redirect. |
| PF-1 (Q1) | **Surface prioritisation** — which surfaces get the premium treatment in *this* feature? Wedge surfaces first (landing + app page + discover) vs. all surfaces now. | Product Analyst | 1-define | **RESOLVED** 2026-06-28 — **wedge surfaces first** (landing + app page + discover/browse); authed surfaces a cheap follow-on later. |
| PF-1 (Q2) | **HTMX interactivity appetite** — light progressive enhancement (never breaks no-JS) vs. broad client-driven interactivity. | Product Analyst | 1-define | **RESOLVED** 2026-06-28 — **light progressive enhancement only** (never breaks the no-JS path). |
| PF-1 (Q3) | **Landing page (`/`) intent** — a real platform landing (value prop + entry points) vs. a redirect into `/discover`. Resolves PF-CARRY-1's intent. | Product Analyst | 1-define | **RESOLVED** 2026-06-28 — **real platform landing**. |
| PF-2 | **Tailwind build step** revises [D-12](../../DECISIONS.md)'s build-free posture → a **Stage-2 architecture call** (likely a new global ADR). Named in the brief as constraint **C3**; not a Stage-1 decision. | Product Analyst | 1-define | **DEFERRED to Stage 2** (Software Architect). |
