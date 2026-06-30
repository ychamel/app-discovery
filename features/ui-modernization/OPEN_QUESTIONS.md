# OPEN_QUESTIONS.md — ui-modernization

All-stages log of ambiguities, deferrals, and escalations. Carried-in context below is
seeded by the Coordinator at activation so Stage 1/2 inherit it (contracts over
conversation, CLAUDE.md §6.1).

---

## Carried-in activation context (Coordinator, 2026-06-30)

This feature is the **activation of the held `ui-modernization` future bet** scoped on
2026-06-28 at the `premium-frontend` M7 sign-off (see [features/INDEX.md](../INDEX.md)
`premium-frontend` row, and global [D-13](../../DECISIONS.md)). The user activated it (the
D2 call) on 2026-06-30 with this framing:

- **Trigger:** the hand-authored `apps/core/static/core/app.css` is *"growing too big"*
  (**1113 lines** as of activation) and the result still reads **bland**. This is the
  **exact revisit trigger D-13 pre-installed** ("if the hand-authored approach cannot reach
  the premium bar or proves too slow to extend → adopt Tailwind").
- **Scope ambition (user brainstorm, candidate input only — not ratified):** modernize the
  whole UI with a Django-native HTML-over-the-wire stack — Tailwind CSS, Alpine.js, expand
  HTMX (already vendored), plus carousels (Swiper/Splide), animation (GSAP/AOS/Lottie),
  and component/icon libraries. The user explicitly noted **"the whole UI might be
  scrapped"** — this is a deep redesign, not a restyle of `premium-frontend`.
- **Distinction the user has held since 2026-06-28:** "bland" is a **design** problem
  (distinctive palette + stylized/animated navigation + premium motion + brand identity),
  which Tailwind alone does **not** fix (D-13: "Tailwind does not give a premium look — you
  still design the tokens"). Tooling and visual-design are separable concerns; this feature
  owns both, but the Product Analyst should keep them distinct in the brief.

## OQ-UM-1 — sequencing vs. the parked live deploy

`ui-modernization` was sequenced **behind** the live staging deploy (`DN-PS-DEPLOY`, the
prior active next bet). By activating it now the user has placed it **ahead of** that
deploy. `DN-PS-DEPLOY` stays parked, reopenable, behind this feature (mirrors how
`premium-frontend` / `app-page-redesign` parked it). No further user input needed — recorded
for traceability.

## OQ-UM-2 — relationship to the just-closed `interface-cleanup`

`interface-cleanup` (the prior feature, presentation cleanup of `app.css`) was
**closed-out at activation** because, in the user's words, *"its results aren't
satisfactory, so the whole UI might be scrapped."* Its committed code remains in the tree.
The Architect must decide in Stage 2 how much of that cleanup layer (the `{% icon %}` tag,
the enumeration guard, the inline-style consolidation) is **kept, evolved, or superseded**
by the new stack — this is a design input, not a user block.
