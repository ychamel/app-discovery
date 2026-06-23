# apps/discovery — open discovery surface

The **open** half of discovery: anyone — **including signed-out visitors** — can browse,
keyword-search, or interest-filter the **accepted** app catalogue and reach an app's page, in
a **neutral, non-purchasable** order. This is the surface where *money never buys position*
(vision §4.1). See [DESIGN.md](../../features/open-search-browse/DESIGN.md).

This app is a **pure read orchestrator** — it owns **no model and no migration**. It parses
the request, asks taxonomy for facets + the tag-match set, asks catalog for a page of results,
and renders. It **imports nothing from `signals`**, so a self-driven browse/search view can
never confer curated-rating eligibility (AC6, structural) and writes no visitor data.

## Route (mounted under `discover/`)

| Name | Method | Auth | Behavior |
|------|--------|------|----------|
| `discovery:browse` (`/discover/`) | GET | **AllowAny (no login wall, AC8)** | Browse (newest-accepted-first) / `?q=` keyword search (relevance) / `?tag=` or `?cluster=` interest filter over the accepted catalogue. Always **200** for a well-formed request, including zero results and an empty catalogue (AC7). |

Params (all optional, coerced at the trust boundary): `q` (stripped, length-clamped, blank ⇒
browse), `tag` (UUID; ignored unless an active tag, then expanded across merges via
`taxonomy.tag_ids_resolving_to`), `cluster` (UUID; expanded over its active tags — `tag` wins
if both arrive), `page` (int ≥ 1; the catalog primitive clamps an over-large page to the last).

## The neutral-order invariant (AC5 / M5)

Result order is decided **entirely** by `catalog.selectors.search_catalogue` —
`SearchRank` (when searching), then `accepted_at` DESC, then `id`. **No payment / tier /
Quality-Score / impression term participates**, so position-neutrality is 0 by construction;
the template never reorders, so the view layer cannot subvert it.

## Failure split (the load-bearing rule, DESIGN §7/§9)

- **Core results read fails loud** — a `search_catalogue` exception propagates to a normal
  **500** (counted `DISCOVERY_LISTING_DEGRADED`), **never** masked as a fake empty state
  (which would lie about M1/M3 and hide an outage).
- **Facet sidebar fails soft** — a taxonomy read error renders results normally with a quiet
  "filters unavailable" note (counted `DISCOVERY_FACETS_DEGRADED`).
- An unknown / retired / non-UUID `tag`/`cluster` is **ignored** (no stale filter), not an error.

## Observability

`discovery_browse_rendered`, `discovery_search_performed`, `discovery_tag_filtered`,
`discovery_zero_results` (M3), `discovery_facets_degraded`, `discovery_listing_degraded` (the
one actionable alert) — in `apps/core/observability.py`. **No D-7 signal is emitted**;
click-through (M2) is derived from app-pages' existing non-curated `APP_PAGE` impressions.

Config tunables (`apps/core/config.py`): `discovery_page_size` (24), `discovery_page_size_max`
(100), `discovery_query_max_length` (200).

## Rollback / operations

Additive, **no feature flag**. To disable: remove the
`path("discover/", include("apps.discovery.urls"))` include from
[config/urls.py](../../config/urls.py) — the surface vanishes with **zero data migration**
(this app owns no schema). The two additive `catalog_app` columns (`accepted_at`,
`search_vector`) are then inert data with no consumer; they can be dropped by reversing the
catalog migrations (`0002`/`0003`) on a **deliberate cleanup**, never as part of an emergency
rollback. No `.env` keys are required (all three tunables have defaults).
