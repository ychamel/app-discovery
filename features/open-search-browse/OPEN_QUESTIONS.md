# OPEN_QUESTIONS — open-search-browse

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped to this feature at scaffold time._

## Stage 1 — Product Analyst

| ID | Question | Raised for | Working assumption in the brief | Status |
|----|----------|-----------|---------------------------------|--------|
| **OQ-OSB-1** | Is **filter/browse by interest tag (or cluster)** part of the MVP slice, or is keyword search + full listing enough for now? | User (scope) — DN-17 | **In scope** (S3/AC3) — D-5 is already available and tag-browse is the natural discovery axis. | **RESOLVED** (DN-17, 2026-06-23) — **in MVP scope** (S3/AC3, OSB-4). |
| **OQ-OSB-2** | What is the **default neutral result order** for the browse listing and for keyword search? | User (scope) — DN-17 | Browse = newest-accepted-first (recency); search = keyword relevance. Both neutral / non-purchasable (AC5). | **RESOLVED** (DN-17, 2026-06-23) — **browse = newest-accepted-first, search = keyword relevance**, both non-purchasable (OSB-1). |
| **OQ-OSB-3** | Should the open surface **record a D-7 exposure signal at MVP** (to measure search→app-page click-through, M2), and if so on what **non-curated** surface? | Stage 2 (design) | Deferred to design. The *binding rule* is AC6 (any signal must be non-curated); whether to emit at MVP, and whether a new `Surface` value is needed, is the Architect's call. | **RESOLVED in design** (DESIGN §14 OSB-DESIGN-5, DN-18 pending) — **no D-7 emit at MVP**; AC6 holds by construction (discovery imports no `signals`); M2 derived from app-pages' existing non-curated `APP_PAGE` impressions; a future `Surface.SEARCH` is a named seam, not built. |
| **OQ-OSB-4** | Does keyword search match **tag labels** too (not only name/description)? | Stage 2 (design) | Name + description only at MVP (AC2); tag-label matching is a possible additive refinement. | **RESOLVED in design** (DESIGN §14 OSB-DESIGN-3, DN-18 pending) — **name + description only** (the FTS `search_vector` fields); tag-label/fuzzy/semantic search deferred (gated on the M3 zero-result rate). |
