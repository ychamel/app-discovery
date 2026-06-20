# OPEN_QUESTIONS — app-pages

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped to this feature at scaffold time._

## Raised in Stage 1 (Product Analyst)

- **OQ-1 — Reviews slot at MVP.** The breakdown §4.2 MVP slice lists a "reviews block,"
  but `ratings-reviews` (which owns rating capture, the curated-rating gate, and review
  display) **depends on** app-pages and so does not exist yet. The brief scopes the slot
  as an **empty-state placeholder** at MVP (AC9, assumption A2), deferring all review
  content to `ratings-reviews`. *Confirm* this boundary is right, or decide app-pages
  should render reviews from a source that exists at its build time (there is none today).
  → Surfaced for approval as part of **DN-9**.

- **OQ-2 — Click-through attribution with no originating impression (design fork).**
  [D-7](../../DECISIONS.md) makes `click_through` an `EngagementEvent` with an
  `impression` link that is *required* for `click_through`. But a page reached by a
  **direct link or search** (the open-access case, AC5) has **no originating impression**.
  So: is a try-it click from an impression-less visit (a) recorded as a `click_through`
  with no/optional impression (needs a D-7 read — D-7 says impression is required for
  `click_through`), (b) recorded only when an originating impression exists and otherwise
  not captured, or (c) captured under a different event kind? This is a **Stage-2 design
  fork** for the Architect against the D-7 contract — not a Stage-1 blocker. *(Related: R2.)*

- **OQ-3 — How much "press kit" at MVP.** Vision §6 calls the app page the dev's
  press-kit / web home. The brief (assumption A3) scopes MVP press-kit to **the public
  page + stable shareable link + existing submission media**, with **no** separate
  downloadable press-asset bundle, press-contact field, or embargo controls. *Confirm*, or
  decide which press-kit extras (if any) belong in this MVP vs. a later dev-facing feature.
  → Surfaced for approval as part of **DN-9**.

- **OQ-4 — Page URL form & indexability (design-leaning).** AC4 requires a **stable,
  shareable URL** that survives metadata edits (which points at the `App.id` UUID rather
  than a mutable name/slug), and A1 proposes pages be **indexable** for direct discovery.
  The exact URL shape (UUID vs. a stable human-readable slug) and the robots/SEO posture
  are **Stage-2 design** concerns — noted here so design picks them deliberately, not a
  Stage-1 blocker.
