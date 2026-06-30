# DECISIONS.md — ui-modernization

Feature-local choices + rationale + rejected alternatives. Repo-wide decisions promote to
the global [DECISIONS.md](../../DECISIONS.md). Seeded by the Coordinator with the user's
Stage-2 lean so the Architect inherits it.

---

## UM-LEAN-1 — Build-posture lean (user, 2026-06-30) — NON-BINDING input to Stage 2

When activating the feature the user was asked their lean on the central build-posture fork
(the [D-13](../../DECISIONS.md) revisit), framed explicitly as **non-binding steering** for
the Architect, not a ratified decision.

- **User's lean:** **adopt Tailwind via the standalone CLI binary and stay no-Node** — i.e.
  the exact reversible fallback D-13 pre-specified ("Tailwind via the standalone CLI binary;
  no Node/npm; one `tailwindcss -i src.css -o app.css --minify` build step before
  `collectstatic`; binary fetched/vendored; `content` glob over `apps/**/templates/**`",
  fully specced in [features/premium-frontend/DESIGN.md](../premium-frontend/DESIGN.md) §11).
- **Implication the Architect must weigh:** this lean **rules out** the parts of the user's
  brainstorm that require the npm ecosystem — **DaisyUI, Flowbite, Preline, `django-tailwind`**
  are Tailwind *plugins / Node packages* and do not load under the standalone CLI without a
  Node toolchain. JS sprinkles the user wants (**Alpine.js, Swiper, GSAP, AOS, Lottie**) can
  still be **vendored as plain self-hosted JS** (the HTMX precedent, D-13) with no build step.
- **Why this is still a global ADR:** adopting even the no-Node Tailwind CLI **introduces a
  build step**, which D-13 deliberately rejected (risk R1 — a build step destabilising the
  parked D-12 staging deploy; D-4 single-language Python repo). So the Stage-2 decision is a
  **reversal/extension of D-13** and must be promoted to the global [DECISIONS.md](../../DECISIONS.md),
  with R1 re-assessed against the now-larger surface count.

> The Architect remains free to recommend against the lean (e.g. deepen the hand-authored
> token system further, or escalate the no-Node-vs-full-toolchain tension back to the user)
> — UM-LEAN-1 is steering, not a constraint. Record the final build posture here and promote
> it to a global ADR on DESIGN approval.
