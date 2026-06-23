# DECISIONS — open-search-browse

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 — Product Analyst (RESOLVED — DN-17 approved 2026-06-23; binding for Stage 2)

- **OSB-1 — Open surface is un-personalized and reception-neutral.** Browse/search is the
  *open* half of discovery; ordering uses only neutral published signals (recency /
  keyword relevance / alphabetical), never personalization, Quality Score, payment, or
  developer tier. **Why:** vision §4.1 + §5.6 (money buys tools, not position);
  personalization belongs to `weekly-digest`, reception-weighting to the impression
  economy. Coupling either into the open surface risks a buy-able proxy for position.
  *Rejected:* relevance-by-popularity ordering (a reception proxy → R2/R4); personalized
  ordering by `interest-profile` (that is the digest, not the open surface).
  **Status: RESOLVED** (DN-17). **OQ-OSB-2 resolution:** the concrete default order is
  **browse = newest-accepted-first (recency)**, **search = keyword relevance** — both
  neutral / non-purchasable (AC5). Tag-filter results inherit the same neutral order.

- **OSB-2 — Catalogue source is the live D-6 read, accepted-only.** All results come from
  `catalog.list_catalogued_apps` / `get_catalogued_apps`; non-accepted apps are never
  indexed or shown (AC1/AC2). **Why:** D-6 is the single source of "what is in the
  catalogue"; re-deriving acceptance here would duplicate state that can drift (CLAUDE.md
  §5.4 one-source-of-truth). *Rejected:* a separate search index seeded independently of
  D-6 (drift risk + duplicate acceptance logic). **Status: RESOLVED** (DN-17).

- **OSB-3 — Any exposure signal is non-curated by construction.** If this surface records
  a D-7 signal at all, it must be on a **non-`DIGEST`** surface so it can never confer
  curated-rating eligibility (AC6, D-8). **Why:** §4.1 — a self-driven view is not
  organic curation; allowing it to count would let a visitor confer score-eligibility on
  an app by viewing it. *Whether and how to emit (new surface vs. no emit at MVP) is a
  Stage-2 design call — see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-OSB-3.*
  **Status: RESOLVED** (DN-17) — the non-curated *rule* is binding; the emit mechanism
  (new surface vs. no emit at MVP) remains deferred to Stage 2 design (OQ-OSB-3).

- **OSB-4 — Interest tag/cluster filtering is in the MVP slice.** Filter/browse by an
  active D-5 tag (or cluster) ships in the MVP (S3/AC3), alongside full listing and
  keyword search. **Why:** D-5 is already released and tag-browse is the natural,
  non-purchasable discovery axis; deferring it would leave the open surface without its
  most-used category entry point. *Rejected:* keyword-search-only MVP (cheaper, but
  drops the primary browse axis with the vocabulary already in hand).
  **Status: RESOLVED** (DN-17 / OQ-OSB-1).

> Reuses **D-3** (accounts/roles — though the surface is open to anonymous), **D-5**
> (taxonomy), **D-6** (catalogue), **D-7/D-8** (signals + curated gate) **as-is — no new
> global ADR proposed at Stage 1.** Stage 2 will weigh whether a new non-curated
> `Surface` value is needed (would be an additive D-7 extension, not a new global rule).

## Stage 2 — Software Architect (PROPOSED — awaiting DN-18; see [DESIGN.md](DESIGN.md) §14)

- **OSB-DESIGN-1 — A paginated, DB-pushed query primitive `catalog.selectors.search_catalogue`
  is *the* open-surface read.** The existing D-6 `list_catalogued_apps()` materializes the
  whole accepted catalogue and resolves all tags in Python (O(catalogue) per call) — correct
  but unpaginatable at scale. The new primitive pushes filter + order + pagination + page-
  scoped tag resolution into the database, returning a `CatalogPage` of the **unchanged**
  `CatalogApp` DTO. **Why:** AC9 / §5.2 (works at 100×, bounded per page, no N+1) and D-6
  one-source-of-truth (catalogue queries belong to the catalog read surface).
  *Rejected:* slicing `list_catalogued_apps()` per page (re-loads + re-resolves the whole
  catalogue each page). **Status: PROPOSED** (DN-18).

- **OSB-DESIGN-2 — Add `accepted_at` to `catalog_app` as the neutral browse-order key.**
  An additive nullable column stamped inside `accept_app`'s transaction (re-stamped on
  re-acceptance), composite-indexed `(status, -accepted_at)`, backfilled from the latest
  accept `ReviewDecision`. Browse order = `accepted_at DESC, id` (OQ-OSB-2). **Why:**
  "newest-accepted-first" needs the real acceptance time as one source of truth; no such
  field exists today. *Rejected:* per-query subquery over `ReviewDecision.created_at`
  (un-indexable, muddy re-acceptance); `last_submitted_at`-as-proxy (semantically the
  pre-acceptance submission, can invert true order). **Status: PROPOSED** (DN-18).

- **OSB-DESIGN-3 — Keyword search = Postgres FTS (`SearchVectorField` + GIN + `SearchRank`),
  name(weight A) + description(weight B).** A stored `search_vector` column maintained only
  in the single catalog write path (`submit_app`/`edit_app`) via one shared expression,
  GIN-indexed; search order = `SearchRank DESC, accepted_at DESC, id` (OQ-OSB-2 relevance).
  Requires adding `django.contrib.postgres` to `INSTALLED_APPS`. **Why:** OQ-OSB-2 mandates
  relevance order, which `icontains` cannot give, and an indexed vector is the scalable
  (AC9) Postgres-native choice. *Rejected:* `icontains`/`ILIKE` (no rank, seq scan); ad-hoc
  per-query `SearchVector` (no index, seq scan). **Status: PROPOSED** (DN-18).

- **OSB-DESIGN-4 — Tag filter resolves correctly across merges via a new reverse-resolution
  taxonomy read `tag_ids_resolving_to(active_id) -> frozenset[UUID]`.** Facets are active
  tags/clusters only (no stale facet, AC3); a selected active tag is expanded to itself +
  its transitive merge predecessors, and the catalog primitive filters `AppTag.tag_id IN`
  that handed-in set (catalog stays decoupled from merge semantics). **Why:** AC3 requires
  "carrying that tag, resolved per D-5"; an app tagged with a predecessor that merged into
  the selected tag must still match, consistent with the resolved label it already displays.
  Bounded by vocabulary size (small reference data), not catalogue size. *Rejected:* direct
  `AppTag.tag_id == selected` (misses merged predecessors → violates AC3). **Status:
  PROPOSED** (DN-18).

- **OSB-DESIGN-5 — No D-7 emit at MVP (resolves OQ-OSB-3).** The discovery app imports
  nothing from `signals`; AC6 (a self-driven view never confers curated eligibility) holds
  **by construction**. Click-through (M2) is derived from app-pages' existing non-curated
  `APP_PAGE` impressions. A future non-curated `Surface.SEARCH` value is named as a seam,
  **not built**. **Why:** §4.1 integrity + privacy for anonymous visitors; emitting nothing
  is the strongest, simplest guarantee of AC6 and removes an anonymous-PII surface.
  *Rejected:* adding `Surface.SEARCH` + an emission path at MVP (unneeded by any AC, adds a
  write path and a privacy surface). **Status: PROPOSED** (DN-18).

- **OSB-DESIGN-6 — Discovery is a model-less consumer app (`apps/discovery/`), activated
  and rolled back by a single `config/urls` include** (mirrors `apps/pages/`). Owns no
  table/migration; reads only the D-5/D-6 selectors; deletable by removing one line (design-
  for-deletion). **Status: PROPOSED** (DN-18).

> **OQ-OSB-4 resolved in design:** keyword search matches **name + description only** at
> MVP (the `search_vector` fields); tag-label/fuzzy/semantic search stay out of scope
> (a future additive refinement gated on the M3 zero-result rate).
>
> Still reuses **D-3/D-5/D-6/D-7/D-8 as-is — no new global ADR.** The `accepted_at` /
> `search_vector` columns + `search_catalogue` (D-6) and `tag_ids_resolving_to` (D-5) are
> **additive extensions of existing read surfaces** indexed in [CODEMAP.md](../../CODEMAP.md)
> at build, changing no cross-feature rule.
