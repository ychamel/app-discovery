# DESIGN — open-search-browse

*Stage 2 artifact (Software Architect). Status: **APPROVED — DN-18 (2026-06-23)**;
ratified, binding for Stage 3 planning. Reads the **APPROVED** [FEATURE_BRIEF.md](FEATURE_BRIEF.md) + the codebase.
Produces the architecture, data design, interface contracts, UX, and rollout for the
open discovery surface. Traces every AC to ≥1 design element (§15). No "TBD" in any
contract (persona exit criteria).*

> Reuses **D-3/D-5/D-6/D-7/D-8** as-is. Adds **no new global ADR**; the catalog/taxonomy
> additions below are **additive, feature-local extensions of the existing D-5/D-6 read
> surfaces** (logged in [DECISIONS.md](DECISIONS.md) OSB-DESIGN-1…6), not new cross-feature
> rules. Resolves the two Stage-2 open questions: **OQ-OSB-3 → no D-7 emit at MVP** (AC6 by
> construction), **OQ-OSB-4 → name+description only** (tag-label search deferred).

---

## 1. Protocol trace (the 14 steps, condensed)

The full reasoning; each downstream section is its output.

1. **SCOPE.** *One sentence:* let **anyone, signed-out included**, find any accepted app by
   browsing, keyword search, or interest-tag filter, reaching its app-page, in a
   **neutral, non-purchasable** order. Stakeholders: visitors (find apps), developers
   (earned visibility), platform (the open-access half of the integrity premise).
   Out: personalization, reception-weighted ranking, collections/follows, faceted/fuzzy
   search, `DIGEST` emit, non-accepted apps. **Lifespan: platform** — a permanent public
   surface; effort matches.
2. **REQUIREMENTS.** Functional = AC1–AC9. Non-functional = anonymous access (AC8),
   bounded per-page DB work at 100× catalogue (AC9/§5.2), neutral order auditable to 0
   (AC5/M5), surface segregation (AC6). Constraints C1–C9. **Assumption ledger in §13** —
   every "Verified" item was checked against code this session.
3. **CONTEXT.** Inventoried below (§3). The decisive finding: the existing D-6 read
   `list_catalogued_apps()` **materializes the whole accepted catalogue in memory and
   resolves every tag in Python** — correct but O(catalogue) per call, so it **cannot** back
   a paginated surface at scale (AC9). The design's spine is a **DB-pushed paginated
   primitive**, not pagination over that list.
4. **MODULES.** Three single-responsibility parts (§4): (a) catalog gains a paginated
   query primitive — *the* D-6 search/browse read; (b) taxonomy gains a reverse-resolution
   read so a tag filter is correct across merges; (c) a new **model-less consumer app**
   `apps/discovery/` (mirrors `apps/pages/`) orchestrates facets + query + render. Discovery
   depends on catalog+taxonomy read surfaces (toward stability); neither depends on it.
5. **INTERFACES.** Fully specified in §6 before internals. `search_catalogue(...) ->
   CatalogPage`, `tag_ids_resolving_to(active_id) -> frozenset[UUID]`, the discovery view
   contract, the URL routes. Illegal states excluded by types + boundary coercion.
6. **DATA & STATE.** Two **additive, nullable** columns on `catalog_app` (§5):
   `accepted_at` (the ordering key — one source of truth for "when it entered the
   catalogue") and `search_vector` (indexed FTS). Both written **only** through the
   existing single catalog write path; backfilled by data migration. Discovery owns **no
   table** (design-for-deletion).
7. **FAILURE.** Per-component table in §9. Core results read **fails loud** (a DB error is
   never masked as a fake empty state — that would lie about M1/M3); the **facet sidebar
   degrades soft** (secondary chrome). All visitor input coerced/clamped at the view
   boundary.
8. **CHANGE.** Cheapest-to-change points isolated (§8): the search field list + weights,
   page size, query-length cap, ordering keys, and the (future) non-curated `Surface`
   seam — all config/constants. Irreversible: the two `catalog_app` columns (justified
   §5/§14) and the public route shape.
9. **TRADE-OFFS.** ≥2 real alternatives weighed in §14 (separate search index; annotate
   ordering from `ReviewDecision`; `icontains` instead of FTS; direct tag match instead of
   reverse-resolution; pagination over the existing list). Chosen = the boring, indexed
   Postgres-native path. Sacrifices stated in §14.
10. **SECURITY.** §10 — anonymous-by-design but read-only over **accepted** apps only;
    no PII (no signal emit, AC6); ORM-parameterized FTS (no injection); accepted-only
    filter prevents non-public app leakage; no enumeration surface beyond what is already
    public on the app-page.
11. **OPERATIONS.** §11 — metrics M1–M6 mapped to counters/derivations, the one actionable
    alert (`DISCOVERY_LISTING_DEGRADED`), and the include-line rollback.
12. **TESTS.** §12 — each module isolated; AC1–AC9 each mapped to a concrete check;
    edge cases (empty catalogue, zero-result, retired tag, merged tag, huge page number,
    malformed query, anonymous).
13. **SELF-CRITIQUE.** §13 — attacked the ordering-key choice, the FTS-vs-trigram call,
    the reverse-resolution cost, and the "is discovery its own app" question; ran a
    simplification pass (dropped a speculative `Surface.SEARCH` emit and a faceted-search
    abstraction).
14. **DELIVER.** §14 decisions + rationale + rejected alternatives; §16 smallest first
    version + increments; flags to revisit on real traffic.

---

## 2. Current-state summary

| Capability | Where it lives today | Relevance |
|---|---|---|
| Accepted-app catalogue (D-6) | `catalog.selectors.list_catalogued_apps()` / `get_catalogued_app()` / `get_catalogued_apps(ids)` → `CatalogApp` DTO | The **only** catalogue source (OSB-2). `list_*` materializes the whole catalogue + resolves all tags in Python → **not paginatable at scale** (the gap this design fills). |
| App table | `catalog.models.App` (`status`, `name`, `description`, `last_submitted_at`, `created_at`, `updated_at`; **no acceptance timestamp**, no search index) | Ordering key + search index must be added here (§5). |
| Accept write path | `catalog.services.accept_app(app, reviewer)` — single transactional accept; saves `["status","updated_at"]` only | The one place to stamp `accepted_at`/`search_vector` (§5). |
| Interest vocabulary (D-5) | `taxonomy.selectors.list_active_tags()` / `list_clusters()` / `resolve_tag(id)` / `is_valid_tag(id)` | Facets (active tags + clusters) and forward resolution. **No reverse** (predecessors-of-a-tag) read exists → added (§4b). |
| App-page destination | `pages:app-page` route, keyed on `App.id` (released) | AC4 link target. Discovery never renders app detail; it links here. |
| Behavioral signals (D-7) + curated gate (D-8) | `signals.capture.*`, `signals.kinds.Surface={DIGEST,APP_PAGE}`, `ratings.gate.CURATED_SURFACES` | AC6 segregation. Discovery **emits nothing** (OQ-OSB-3 resolution); a click that lands on the app-page is already captured by app-pages as a **non-curated `APP_PAGE`** impression. |
| Model-less consumer pattern | `apps/pages/` (owns no model/migration; views+urls+templates+emission; activated by a `config/urls` include) | The template `apps/discovery/` follows exactly. |

---

## 3. Proposed architecture

```
                          ┌──────────────────────────────────────────────┐
  anonymous or signed-in  │  apps/discovery/  (NEW — owns no model)       │
  visitor ───GET────────► │  views.catalogue   urls(discovery:browse)    │
                          │  templates/discovery/catalogue.html          │
                          │  (no signals import → AC6 by construction)   │
                          └──────┬───────────────────────────┬───────────┘
             facets (D-5)        │                           │   results (D-6)
                ┌────────────────▼───────────┐   ┌───────────▼────────────────────┐
                │ taxonomy.selectors          │   │ catalog.selectors               │
                │  list_active_tags()         │   │  search_catalogue(              │
                │  list_clusters()            │   │    query, tag_ids, page, size)  │
                │  tag_ids_resolving_to(id)   │   │   -> CatalogPage                │  ← NEW
                │   ──── NEW (reverse D-5) ────│   │  (DB-pushed: FTS rank /         │
                └─────────────────────────────┘   │   accepted_at order / LIMIT-    │
                                                  │   OFFSET / page-scoped resolve) │
                                                  └───────────┬─────────────────────┘
                                                              │ reads
                                                  ┌───────────▼─────────────────────┐
                                                  │ catalog.models.App  (+accepted_at│
                                                  │  +search_vector, GIN-indexed)    │  ← NEW cols
                                                  │  written ONLY via accept_app /   │
                                                  │  submit_app / edit_app           │
                                                  └──────────────────────────────────┘
   each result row ──links──► pages:app-page (App.id)   [AC4]
```

**Single responsibilities & coupling.** `apps/discovery/` is a pure read orchestrator —
it parses the request, asks taxonomy for facets + the tag-match set, asks catalog for a
page of results, and renders. It is **replaceable and deletable** by removing one
`config/urls` include (no schema, no data). The catalog primitive is the one place that
knows how to *query* the catalogue (order/filter/paginate); the taxonomy reverse read is
the one place that knows merge predecessors. Dependencies point toward the stable D-5/D-6
read surfaces; nothing depends on discovery. Catalog stays **decoupled from taxonomy merge
semantics**: it filters on a *set of tag_ids handed to it*, so discovery (not catalog)
owns the expansion — preserving catalog's existing "tag_id is an opaque soft ref" stance.

---

## 4. Modules (what each owns / exposes / hides)

### 4a. `catalog.selectors.search_catalogue` — the paginated D-6 query primitive (NEW)
- **Owns:** how the accepted catalogue is queried for a *page* — neutral ordering, keyword
  match, tag-set filter, pagination, and page-scoped tag resolution. The single read that
  pushes all of this into the database.
- **Exposes:** `search_catalogue(...) -> CatalogPage` (§6.1).
- **Hides:** the FTS expression, the `accepted_at` ordering, the LIMIT/OFFSET, and the
  `_resolve_tag_labels` reuse. Callers see a page of the **existing** `CatalogApp` DTO.
- **Isolation:** unit-testable against the ORM with seeded apps; no view/HTTP needed.

### 4b. `taxonomy.selectors.tag_ids_resolving_to` — reverse resolution (NEW, D-5)
- **Owns:** "which stored tag_ids *mean* this active tag now" = the active tag **plus its
  transitive merge predecessors** (tags whose `replaced_by` chain leads to it). The reverse
  of `resolve_tag`, so a tag filter is consistent with the resolved labels the catalogue
  already displays (AC3).
- **Exposes:** `tag_ids_resolving_to(active_id: UUID) -> frozenset[UUID]` (§6.2).
- **Hides:** the bounded predecessor walk. Cost is bounded by **vocabulary size** (small,
  slow-growing reference data), **not** catalogue size — a deliberate, documented bound
  (§5.2 allowance; §14).
- **Isolation:** unit-testable against a seeded merge chain; no catalog/discovery needed.

### 4c. `apps/discovery/` — the open-discovery consumer app (NEW, owns no model)
- **Owns:** the public listing UX and request handling: parse `q`/`tag`/`cluster`/`page`,
  assemble facets, compute the tag-match set, call the catalog primitive, render results +
  pagination + empty states. **Imports nothing from `signals`** (AC6 structural).
- **Exposes:** route `discovery:browse` and the `catalogue.html` template.
- **Hides:** request parsing/clamping, facet assembly, empty-vs-error distinction.
- **Isolation:** view-tested with the Django test client (anonymous + signed-in).

Cross-cutting concerns reuse the established singletons: `apps.core.config` (new tunables),
`apps.core.observability` (new metric constants), request-context logging middleware — none
duplicated here.

---

## 5. Data design

Two **additive, nullable** columns on the existing `catalog_app` table. No new table. No
change to the `CatalogApp` DTO (the cross-feature D-6 shape is unchanged → no consumer
breaks).

### 5a. `App.accepted_at: DateTimeField(null=True)`
- **Source of truth** for "when this app (last) entered the accepted catalogue" — the
  `accepted_at`-DESC browse order (OSB-1 / OQ-OSB-2). One fact, one column; not re-derived.
- **Lifecycle:** set to `timezone.now()` **inside `accept_app`'s transaction** (the single
  accept path), added to its `save(update_fields=...)`. Re-acceptance (withdraw → resubmit →
  accept) **re-stamps** it → a re-entering app sorts as newest (the honest "newest in the
  catalogue" semantics). Never set elsewhere; `NULL` for any app that has never been
  accepted (and such apps are never listed, so `NULL` never appears in a result set).
- **Index:** composite `Index(fields=["status", "-accepted_at"])` so the accepted-only
  browse page is a single index range scan (AC9). (The existing `catalog_app_status_idx`
  stays; this composite serves the ordered browse.)
- **Migration:** schema migration adds the column + index; **data migration** backfills
  existing accepted apps from their latest `ReviewDecision(outcome=accepted).created_at`
  (a one-off, bounded by current catalogue size). Reversible (drop column/index).

### 5b. `App.search_vector: SearchVectorField(null=True)` + `GinIndex`
- **Derived** index of `name` (weight A) + `description` (weight B) for keyword relevance
  (OSB-1 search order / OQ-OSB-4 = these two fields only). Derived data, but materialized +
  indexed because re-deriving per query (ad-hoc `SearchVector`) is a sequential scan that
  fails AC9 at 100× (§14).
- **Lifecycle:** recomputed **only** in the single catalog write path — `submit_app` and
  `edit_app` (the only places `name`/`description` change) — via a shared
  `catalog._search_vector_expr()` so the formula lives in exactly one place. Backfilled by
  the same data migration. A stored vector that drifts is impossible because no other code
  writes those fields.
- **Index:** `GinIndex(fields=["search_vector"], name="catalog_app_search_gin")`.
- **Prerequisite:** add `django.contrib.postgres` to `INSTALLED_APPS` (the documented home
  of `SearchVectorField`/`GinIndex`/`SearchRank`); verified absent today (§13).

> **Why these live on `catalog_app` and not in `apps/discovery/`:** D-6 mandates that
> nothing reads `catalog_app` past the catalog read surface. Ordering and full-text
> matching **are** catalogue reads; their supporting columns + indexes belong with the
> table that owns them (one source of truth, catalog owns its own indexes). A separate
> discovery-owned search table would duplicate acceptance state and drift (rejected, §14).

---

## 6. Interface contracts (no TBD)

### 6.1 `catalog.selectors.search_catalogue(...) -> CatalogPage`

```python
@dataclass(frozen=True)
class CatalogPage:
    apps: list[CatalogApp]   # the page, already in final neutral order; existing D-6 DTO
    total: int               # total accepted apps matching the filter (for "N results" + page count)
    page: int                # 1-based page actually returned (clamped into range)
    page_size: int           # the page size applied
    has_next: bool           # page < ceil(total / page_size)

def search_catalogue(
    *,
    query: str | None = None,                 # keyword; None/blank → no keyword filter (browse)
    tag_ids: Collection[UUID] | None = None,  # pre-expanded match set; None/empty → no tag filter
    page: int = 1,
    page_size: int | None = None,             # None → config.discovery_page_size()
) -> CatalogPage
```

- **Inputs / coercion:** `query` is stripped; blank ⇒ browse mode. `tag_ids` is the
  **already-expanded** set from `tag_ids_resolving_to` (catalog does not resolve tags
  itself — clean separation, §4). `page` clamped to `[1, last_page]`; `page_size` clamped
  to `[1, discovery_page_size_max()]`.
- **Filter:** always `status=ACCEPTED` (OSB-2; AC1/AC2 — pending/rejected/withdrawn never
  appear). `+ search_vector @@ websearch_to_tsquery(query)` when `query` present.
  `+ app_tags.tag_id IN tag_ids` (`.distinct()`) when `tag_ids` present. Keyword and tag
  filters **compose** (AND).
- **Order (the AC5 invariant — only neutral, published, non-purchasable keys):**
  - keyword present → `ORDER BY SearchRank(search_vector, query) DESC, accepted_at DESC, id`
  - keyword absent → `ORDER BY accepted_at DESC, id`
  - `id` is the final, stable tie-break (deterministic pagination). **No payment / tier /
    Quality-Score / impression-count term exists in the ORDER BY** — M5 = 0 by construction
    (enforced by test, §12).
- **Pagination & N+1:** `total` via one `COUNT`; the page via one `LIMIT/OFFSET` SELECT
  with `prefetch_related("media","app_tags")`; tags resolved for **only the page's apps**
  via the existing deduped `_resolve_tag_labels`. ⇒ a **fixed, small number of queries per
  page regardless of catalogue size or page index** (AC9).
- **Invariants:** every element is `status=ACCEPTED`; `len(apps) <= page_size`;
  `apps == []` is a valid empty page (caller renders the empty state, never an error).
- **Errors:** raises only on a genuine DB failure (loud — never returns a fake empty page).
  Malformed `query` cannot raise: `websearch_to_tsquery` accepts arbitrary text.
- **Evolution:** new optional keyword-only params can be added without breaking callers;
  the DTO is additive. Today's three modes (browse / search / tag-filter) and their
  composition are the full surface.

### 6.2 `taxonomy.selectors.tag_ids_resolving_to(active_id: UUID) -> frozenset[UUID]`

- **Returns** `{active_id} ∪ {all tag_ids whose replaced_by chain resolves to active_id}`.
  For a tag with no predecessors → `{active_id}`. For an unknown/non-UUID id → `frozenset()`
  (tolerant, like `is_valid_tag`; the caller has already validated via `is_valid_tag`).
- **Bounded** by a breadth walk over `replaced_by_id IN frontier` (a handful of queries
  bounded by merge-chain depth; total work bounded by vocabulary size). Never raises on a
  malformed id.
- **Invariant:** `active_id ∈ result`. **Evolution:** additive read; does not change
  `resolve_tag`/`is_valid_tag`.

### 6.3 Discovery view + routes

```python
# apps/discovery/urls.py
app_name = "discovery"
urlpatterns = [ path("", views.catalogue, name="browse") ]   # mounted at /discover/
```

`views.catalogue(request) -> HttpResponse` — **GET only, NO `login_required`** (AC8).
Query params (all optional, parsed at the trust boundary):

| Param | Meaning | Coercion / invalid handling |
|---|---|---|
| `q` | keyword | stripped; truncated to `discovery_query_max_length()` (default 200); blank ⇒ browse |
| `tag` | one active tag id to filter by | `UUID` coerced; ignored (no filter) unless `is_valid_tag` (AC3 — a retired/unknown tag offers no stale filter); when valid, expanded via `tag_ids_resolving_to` |
| `cluster` | one cluster id to filter by | `UUID` coerced; expanded to the union of `tag_ids_resolving_to(t)` over the cluster's **active** tags; unknown ⇒ ignored |
| `page` | 1-based page | int-coerced; non-int/<1 ⇒ 1; the primitive clamps an over-large page to the last page |

`tag` and `cluster` are mutually exclusive; if both arrive, `tag` wins (documented; a
single-axis MVP filter, no boolean composition — out of scope). Response is **always
`200`** for a well-formed request, including zero results / empty catalogue (AC7).

### 6.4 UI states (the `catalogue.html` contract)

| State | Trigger | Render |
|---|---|---|
| Results | `page.apps` non-empty | listing of cards (name, truncated description, first media as thumbnail w/ `alt_text`, resolved tag chips), each card a link to `pages:app-page app.id` (AC4); pagination (prev/next + "page X of Y"); the active-tag/cluster facet sidebar + a search box reflecting `q` |
| Zero results | well-formed query/filter, `total == 0`, catalogue non-empty | "No apps match …" + a clear-filters link; **`200`** (AC7) |
| Empty catalogue | no accepted apps at all | "No apps in the catalogue yet" placeholder; **`200`** (AC7) |
| Facet-degraded | facet read failed (soft) | results render normally; the sidebar shows a quiet "filters unavailable" note; `DISCOVERY_FACETS_DEGRADED` counted (§9) |
| Error | core results read raised | normal Django `500` (loud) — **never** masked as an empty state (§7/§9) |

---

## 7. UX flow

1. Visitor (anonymous or signed-in) opens `/discover/` → **browse**: newest-accepted-first,
   page 1, facet sidebar of active tags grouped by cluster, a search box.
2. Types a keyword + submit → `?q=…` → relevance-ordered results.
3. Clicks a tag/cluster facet → `?tag=…` / `?cluster=…` → that category, newest-first;
   combinable with `q` (AND).
4. Clicks a result card → `pages:app-page` (the app's stable `App.id` page) — AC4. No login
   wall at any step (AC8).
5. Pagination via prev/next. Empty/zero-result states per §6.4. Signing in changes nothing
   about what is shown (the open surface is identical for everyone — out-of-scope
   personalization).

---

## 8. Change-cost map (cheapest places to change)

| Likely to change | Where it lives | Cost |
|---|---|---|
| Page size / max page size | `config.discovery_page_size()` / `discovery_page_size_max()` | one constant |
| Keyword max length | `config.discovery_query_max_length()` | one constant |
| Search fields / weights | `catalog._search_vector_expr()` (one function) | one function; re-backfill |
| Neutral ordering keys | the `ORDER BY` in `search_catalogue` (one place) | one function |
| Whether to emit a non-curated discovery signal later | a future `Surface.SEARCH` value + a thin emission wrapper (seam noted, **not built** — §16/OQ-OSB-3) | additive enum value |

**Irreversible (justified with extra rigor, §5/§14):** the two `catalog_app` columns +
indexes (additive, nullable, reversible migrations, but a schema change on the shared D-6
table) and the public `discovery:browse` route shape. No speculative abstraction added —
no faceted/boolean search layer, no pluggable ranking strategy, no search-service
indirection (all explicitly out of scope or unjustified by a named change).

---

## 9. Failure modes (detection → response; never silent)

| Component | Failure | Detection | Response |
|---|---|---|---|
| `search_catalogue` core read | DB down/slow/error | exception from the ORM | **Fail loud** → propagates to a `500`. **Never** caught and rendered as an empty state (that would lie about M1/M3 and hide an outage). |
| Facet sidebar (`list_active_tags`/`list_clusters`) | taxonomy read error | exception caught **around the sidebar only** | **Fail soft** → results still render; sidebar shows "filters unavailable"; `DISCOVERY_FACETS_DEGRADED` counted (secondary chrome, mirrors the inclusion-tag pattern). |
| Tag/cluster param | unknown / retired / non-UUID | `is_valid_tag` false / coercion fails | **Ignore the filter** (no stale facet, AC3); render the unfiltered listing. Not an error. |
| `q` param | over-long / odd syntax | length clamp; `websearch_to_tsquery` tolerates any text | Clamp; never raises. |
| `page` param | non-int / out of range | int-coerce; primitive clamps | Clamp to `[1, last_page]`; a valid page is always returned. |
| Result → app-page link | target app withdrawn between query and click | app-pages already returns its own not-available page | Out of scope here; app-pages owns that state (its `APP_PAGE_NOT_AVAILABLE`). |
| Tag resolution for a page | a stored `tag_id` never existed / merged | `resolve_tag` drops the unknown, follows merges | Page renders with the resolved set (D-5 semantics; nothing silently wrong). |

---

## 10. Non-functional handling

- **Security / authz:** read-only, anonymous-by-design (AC8) but strictly over
  `status=ACCEPTED` rows — a pending/rejected/withdrawn app is unrepresentable in any
  result (enforced in the one primitive). No write surface, no IDOR (no per-result mutable
  id; the only id exposed is the already-public `App.id` link). FTS is **ORM-parameterized**
  (`websearch_to_tsquery`) → no SQL injection. No catalogue enumeration beyond what the
  public app-pages already expose.
- **Privacy / PII:** the surface **records no D-7 signal** (OQ-OSB-3 resolution) → no
  visitor data, anonymous or otherwise, is written (C8 satisfied by construction; AC6).
- **Performance (M4/AC9):** browse = one index range scan on `(status,-accepted_at)`;
  search = GIN-backed FTS; both `LIMIT`-bounded with page-scoped tag resolution. No hard SLA
  (CLAUDE.md §6.2) — an observable target, watched via timing logs/metrics.
- **Accessibility (C7):** semantic `<ul>`/`<article>` listing, `alt_text` carried from D-6
  media, keyboard-navigable links/form, facets as real links/controls.
- **Observability / rollback:** §11.

---

## 11. Operations

**Metrics → source.**

| Metric (brief) | Realised as |
|---|---|
| M1 open-access coverage (100%) | by construction — the primitive lists **all** accepted apps; a property test asserts every accepted app is reachable across pages. |
| M2 discovery click-through | **derived**, no new emit: a click that lands on the app-page is captured by app-pages as a non-curated `APP_PAGE` impression; analyst joins page-view signals to discovery traffic later (thin until traffic). |
| M3 zero-result rate | `DISCOVERY_ZERO_RESULTS` counter incremented when a keyword/filter query returns `total == 0`. |
| M4 latency | request timing via the existing logging/observability path; watched, not alerted unless degraded. |
| M5 position-neutrality audit (=0) | **structural + test-enforced**: the `ORDER BY` contains only neutral keys; a test asserts no paid/tier/score field participates. Not a runtime counter (there is no purchasable input to count). |
| M6 freshness lag | ~immediate: `accepted_at` is stamped in the accept transaction, so the app appears on the next query (a test asserts accept → visible). |

**Counters (new constants in `apps/core/observability.py`):** `DISCOVERY_BROWSE_RENDERED`,
`DISCOVERY_SEARCH_PERFORMED`, `DISCOVERY_TAG_FILTERED`, `DISCOVERY_ZERO_RESULTS`,
`DISCOVERY_FACETS_DEGRADED`, `DISCOVERY_LISTING_DEGRADED`.

**The one actionable alert:** `DISCOVERY_LISTING_DEGRADED` (a core results read raised /
the page 500s) — that is an outage of the open surface. `DISCOVERY_FACETS_DEGRADED` is
informational (chrome). Zero-result / latency are analyst signals, not pages.

**Rollback:** remove the `path("discover/", include("apps.discovery.urls"))` line from
`config/urls.py` — the surface is gone with **zero data migration** (mirrors app-pages).
The two `catalog_app` columns are inert additive data with no consumer once the include is
gone; they can be dropped by reversing their migration on a deliberate cleanup, not as part
of an emergency rollback.

---

## 12. Tests (per-module isolation + AC map)

- **`search_catalogue` (catalog, ORM-level):** browse order = accepted_at DESC + id
  tie-break (AC5); search returns name/description matches ranked, excludes non-matching +
  non-accepted (AC2); tag-set filter returns only carriers, deduped (AC3); keyword∧tag
  compose; pagination bounds + `has_next`/`total`/clamped over-large page (AC9); **query
  count is constant across catalogue size** (no N+1, AC9); only ACCEPTED ever returned
  (AC1); empty input → empty page, no error (AC7); **ORDER-BY-neutrality test** asserts no
  paid/tier/score key (AC5/M5).
- **`tag_ids_resolving_to` (taxonomy):** singleton tag → `{id}`; a merge chain X→W→Y,
  `tag_ids_resolving_to(Y) == {X,W,Y}` (AC3 correctness); unknown id → `frozenset()`.
- **`accept_app` (catalog):** stamps `accepted_at`; re-acceptance re-stamps; backfill data
  migration populates existing accepted apps (AC5/M6). `submit_app`/`edit_app` maintain
  `search_vector` (AC2).
- **discovery view (Django test client):** anonymous GET 200 for browse/search/tag/empty
  (AC8/AC1/AC2/AC7); result card links to `pages:app-page` (AC4); retired/unknown `tag`
  ignored, no 500 (AC3); zero-result + empty-catalogue render 200 with the message (AC7);
  core-read error → 500 not a fake empty state; facet failure → soft-degrade.
- **Regression:** existing 616 tests + `list_catalogued_apps`/`get_catalogued_app`
  unchanged behavior; `accept_app` callers unaffected by the added field.

Every AC1–AC9 maps to ≥1 check above (consolidated in §15).

---

## 13. Self-critique & assumption ledger

- **Ordering key.** Rejected reusing `last_submitted_at` as a proxy — for an accepted app
  it is the submission that *preceded* acceptance, and review latency can invert two apps'
  true acceptance order; "newest-accepted-first" demands the real acceptance time. Adding
  `accepted_at` is the one-source-of-truth, indexable choice (§14).
- **FTS vs. simpler.** `icontains`/`ILIKE %term%` cannot use a btree index (seq scan at
  100×) and yields **no relevance order** — but OQ-OSB-2 mandates "search = keyword
  relevance". Postgres FTS is the boring, native, indexable answer that delivers ranking.
  pg_trgm was considered for typo tolerance but that is fuzzy search (out of scope).
- **Reverse resolution cost.** `tag_ids_resolving_to` walks predecessors; bounded by
  vocabulary size (small reference data), **not** catalogue size — an explicit, acceptable
  bound (§5.2). If the vocabulary ever grows huge, a recursive CTE replaces the walk behind
  the same signature.
- **Is discovery its own app?** Yes — it owns no model and is deletable by one include line
  (design-for-deletion), exactly like `apps/pages/`; folding it into `catalog` would couple
  a public UX to the intake/review app and muddy deletion boundaries.
- **Simplification pass:** dropped (a) emitting a `Surface.SEARCH` D-7 signal at MVP — not
  needed for any AC, adds a write path + a privacy surface for anonymous visitors; AC6 is
  *more strongly* satisfied by emitting nothing (OQ-OSB-3); (b) a faceted/boolean multi-tag
  filter — out of scope; the single-axis `tag`/`cluster` filter covers S3.

**Assumption ledger** (✓ = verified against code this session):

| # | Assumption | Status |
|---|---|---|
| A1 | D-6 `list_catalogued_apps` materializes all + resolves tags in Python (not paginatable) | ✓ `catalog/selectors.py` |
| A2 | `accept_app` is the single accept path; saves only `status,updated_at`; no `accepted_at` exists | ✓ `catalog/services.py`, `models.py` |
| A3 | `resolve_tag` follows `replaced_by` forward; **no reverse** read exists | ✓ `taxonomy/selectors.py` |
| A4 | `Surface = {DIGEST, APP_PAGE}`; curated = `ratings.gate.CURATED_SURFACES` only | ✓ `signals/kinds.py`, CODEMAP |
| A5 | app-pages route `pages:app-page` keyed on `App.id`, released | ✓ `pages/urls.py`, CONTROL |
| A6 | `apps/pages/` is the model-less-consumer + include-line-activation template | ✓ `pages/apps.py`, `config/urls.py` |
| A7 | `django.contrib.postgres` is **not** yet in `INSTALLED_APPS` (must be added for FTS) | ✓ `config/settings.py` |

---

## 14. Decisions, alternatives & sacrifices (full record in [DECISIONS.md](DECISIONS.md))

- **OSB-DESIGN-1 — paginated DB-pushed primitive in catalog, not pagination over the
  existing list.** *Rejected:* slicing `list_catalogued_apps()` (loads + tag-resolves the
  whole catalogue every page → O(catalogue) per page, fails AC9). *Sacrifice:* a new
  catalog selector + its tests.
- **OSB-DESIGN-2 — add `accepted_at` to `catalog_app` as the browse-order key.** *Rejected:*
  annotate the latest accept `ReviewDecision.created_at` per query (correlated subquery,
  hard to index, muddy re-acceptance) and `last_submitted_at`-as-proxy (semantically wrong).
  *Sacrifice:* a schema + backfill migration on the shared D-6 table.
- **OSB-DESIGN-3 — Postgres FTS (`SearchVectorField` + GIN + `SearchRank`), name(A)+desc(B).**
  *Rejected:* `icontains` (no rank, seq scan); ad-hoc per-query `SearchVector` (no index,
  seq scan). *Sacrifice:* a stored derived column maintained in the write path + the
  `django.contrib.postgres` install; tag-label/fuzzy/semantic search excluded (OQ-OSB-4).
- **OSB-DESIGN-4 — tag filter via `tag_ids_resolving_to` (reverse D-5), catalog filters a
  handed-in id set.** *Rejected:* direct `AppTag.tag_id == selected` (misses merged
  predecessors → inconsistent with the resolved labels shown, violates AC3). *Sacrifice:* a
  new taxonomy read; bounded by vocabulary size.
- **OSB-DESIGN-5 — no D-7 emit at MVP (resolves OQ-OSB-3).** AC6 satisfied by construction;
  click-through (M2) derived from app-pages' existing `APP_PAGE` impressions; the future
  non-curated `Surface.SEARCH` seam is named, not built. *Sacrifice:* M2 is indirect until
  a later emit ships.
- **OSB-DESIGN-6 — discovery is a model-less consumer app, activated/rolled back by one
  `config/urls` include** (mirrors app-pages). *Sacrifice:* none material; maximizes
  deletion-isolation.
- **OFFSET pagination** (not keyset) — boring + sufficient for MVP browse depth; deep-page
  O(offset) is a documented future swap (keyset behind the same `CatalogPage` contract).

Reuses **D-3/D-5/D-6/D-7/D-8 as-is** — **no new global ADR**. The catalog/taxonomy
additions are additive extensions of the existing D-5/D-6 **read** surfaces (new CODEMAP
entries at build), changing no cross-feature rule.

---

## 15. AC → design-element map (persona exit criterion)

| AC | Design element(s) |
|---|---|
| **AC1** open browse, accepted-only, paginated | `search_catalogue` (status=ACCEPTED filter + pagination); browse mode order §6.1 |
| **AC2** keyword search name/desc, excludes non-match/non-accepted | `search_vector` FTS §5b + `search_catalogue` keyword mode (OQ-OSB-4 = name+desc) |
| **AC3** tag filter, resolved per D-5, no stale facet | `tag_ids_resolving_to` §6.2 + facets = `list_active_tags`/`list_clusters` (active only) + invalid-tag-ignored §6.3/§9 |
| **AC4** result → stable app-page URL | result card links to `pages:app-page App.id` §6.4 |
| **AC5** order only by neutral non-purchasable keys | `search_catalogue` ORDER BY (rank/accepted_at/id only) §6.1; M5 neutrality test §12 |
| **AC6** exposure never curated/`DIGEST` | discovery imports no `signals`; **no emit at MVP** (OSB-DESIGN-5); a click → app-pages' non-curated `APP_PAGE` |
| **AC7** empty / zero-result = 200, never broken | UI states §6.4 + empty page is valid §6.1; core-read error stays loud (not masked) |
| **AC8** anonymous access, no login wall | `catalogue` view has **no** `login_required` §6.3; reads need no auth |
| **AC9** paginated, bounded per page, no N+1 at 100× | DB-pushed primitive §6.1 (COUNT + LIMIT page + page-scoped resolve) + `(status,-accepted_at)` index + search GIN §5 |

---

## 16. Rollout & increments

- **Stack:** no new stack decision — Django + PostgreSQL (D-4). Prerequisite: add
  `django.contrib.postgres` to `INSTALLED_APPS`.
- **Migration order:** (1) catalog schema migration — `accepted_at` + `search_vector` +
  the two indexes; (2) catalog data migration — backfill both for existing accepted apps;
  (3) wire `accept_app`/`submit_app`/`edit_app` to maintain the columns; (4) add the
  `search_catalogue` primitive + `tag_ids_resolving_to`; (5) the `apps/discovery/` app +
  template + `config/urls` include. Backward-compatible throughout: the `CatalogApp` DTO
  and all existing selectors are unchanged.
- **Activation / rollback:** the `config/urls` include is the switch (no feature flag);
  removing it rolls back with zero data migration (§11).
- **Smallest useful first version:** browse (newest-accepted-first) + keyword search +
  single-axis tag/cluster filter + app-page links + empty states — i.e. all of AC1–AC9.
  This *is* the MVP slice; there is no smaller version that satisfies the approved brief.
- **Flagged to revisit on real traffic:** OFFSET→keyset pagination if deep paging gets hot;
  emitting a non-curated `Surface.SEARCH` signal (OQ-OSB-3) once M2 needs first-party
  measurement; tag-label/fuzzy search (OQ-OSB-4) if zero-result rate (M3) is high.

---

*Raises **DN-18** — approve this DESIGN (incl. the two additive `catalog_app` columns +
backfill, the `tag_ids_resolving_to` taxonomy read, no-emit-at-MVP for OQ-OSB-3, and
name+desc-only search for OQ-OSB-4). No Stage advance until approved.*
