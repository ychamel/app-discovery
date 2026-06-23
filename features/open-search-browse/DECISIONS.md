# DECISIONS — open-search-browse

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 — Product Analyst (proposed; binding once DN-17 approved)

- **OSB-1 — Open surface is un-personalized and reception-neutral.** Browse/search is the
  *open* half of discovery; ordering uses only neutral published signals (recency /
  keyword relevance / alphabetical), never personalization, Quality Score, payment, or
  developer tier. **Why:** vision §4.1 + §5.6 (money buys tools, not position);
  personalization belongs to `weekly-digest`, reception-weighting to the impression
  economy. Coupling either into the open surface risks a buy-able proxy for position.
  *Rejected:* relevance-by-popularity ordering (a reception proxy → R2/R4); personalized
  ordering by `interest-profile` (that is the digest, not the open surface).
  **Status: PROPOSED** — pending DN-17.

- **OSB-2 — Catalogue source is the live D-6 read, accepted-only.** All results come from
  `catalog.list_catalogued_apps` / `get_catalogued_apps`; non-accepted apps are never
  indexed or shown (AC1/AC2). **Why:** D-6 is the single source of "what is in the
  catalogue"; re-deriving acceptance here would duplicate state that can drift (CLAUDE.md
  §5.4 one-source-of-truth). *Rejected:* a separate search index seeded independently of
  D-6 (drift risk + duplicate acceptance logic). **Status: PROPOSED** — pending DN-17.

- **OSB-3 — Any exposure signal is non-curated by construction.** If this surface records
  a D-7 signal at all, it must be on a **non-`DIGEST`** surface so it can never confer
  curated-rating eligibility (AC6, D-8). **Why:** §4.1 — a self-driven view is not
  organic curation; allowing it to count would let a visitor confer score-eligibility on
  an app by viewing it. *Whether and how to emit (new surface vs. no emit at MVP) is a
  Stage-2 design call — see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-OSB-3.*
  **Status: PROPOSED** — pending DN-17 (the non-curated *rule* is binding; the emit
  mechanism is deferred to design).

> Reuses **D-3** (accounts/roles — though the surface is open to anonymous), **D-5**
> (taxonomy), **D-6** (catalogue), **D-7/D-8** (signals + curated gate) **as-is — no new
> global ADR proposed at Stage 1.** Stage 2 will weigh whether a new non-curated
> `Surface` value is needed (would be an additive D-7 extension, not a new global rule).
