# OPEN_QUESTIONS — open-search-browse

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped to this feature at scaffold time._

## Stage 1 — Product Analyst

| ID | Question | Raised for | Working assumption in the brief | Status |
|----|----------|-----------|---------------------------------|--------|
| **OQ-OSB-1** | Is **filter/browse by interest tag (or cluster)** part of the MVP slice, or is keyword search + full listing enough for now? | User (scope) — DN-17 | **In scope** (S3/AC3) — D-5 is already available and tag-browse is the natural discovery axis. | **OPEN** → DN-17 |
| **OQ-OSB-2** | What is the **default neutral result order** for the browse listing and for keyword search? | User (scope) — DN-17 | Browse = newest-accepted-first (recency); search = keyword relevance. Both neutral / non-purchasable (AC5). | **OPEN** → DN-17 |
| **OQ-OSB-3** | Should the open surface **record a D-7 exposure signal at MVP** (to measure search→app-page click-through, M2), and if so on what **non-curated** surface? | Stage 2 (design) | Deferred to design. The *binding rule* is AC6 (any signal must be non-curated); whether to emit at MVP, and whether a new `Surface` value is needed, is the Architect's call. | **OPEN** → Stage 2 |
| **OQ-OSB-4** | Does keyword search match **tag labels** too (not only name/description)? | Stage 2 (design) | Name + description only at MVP (AC2); tag-label matching is a possible additive refinement. | **OPEN** → Stage 2 |
