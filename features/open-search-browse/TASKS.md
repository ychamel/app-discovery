# TASKS — open-search-browse

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-17 → approved) and the **ratified** [DESIGN.md](DESIGN.md) (DN-18 → approved; reuses
[D-3](../../DECISIONS.md)/[D-5](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md)/[D-8](../../DECISIONS.md)
as-is — **no new global ADR**). Produces an ordered, independently-verifiable task list; full per-AC
verification is written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a contract or
> decision the design does not already make. Two kinds of change exist here:
> 1. **Additive extensions to the closed [submission-intake](../submission-intake/) (catalog) and
>    [interest-taxonomy](../interest-taxonomy/) (taxonomy) read surfaces** — two nullable
>    `catalog_app` columns + their indexes (DESIGN §5), the maintenance wiring in the single catalog
>    write path (DESIGN §5a/§5b), the new paginated `catalog.selectors.search_catalogue` primitive
>    (DESIGN §6.1, OSB-DESIGN-1), and the new reverse read `taxonomy.selectors.tag_ids_resolving_to`
>    (DESIGN §6.2, OSB-DESIGN-4). These touch closed apps but **change no existing contract** — the
>    `CatalogApp` DTO and every existing selector/service signature are unchanged (DESIGN §5/§16).
> 2. **A new model-less consumer app `apps/discovery/`** (DESIGN §4c, OSB-DESIGN-6) — owns no table,
>    activated/rolled back by one `config/urls` include, a **near-twin of the closed-out
>    `apps/pages/`** (match its conventions, CLAUDE.md §5.5). It **imports nothing from `signals`**
>    (AC6 structural — DESIGN §4c/§10).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces → UI → telemetry → docs.** Spine: the two additive
   `catalog_app` columns + indexes + `django.contrib.postgres` (T-01) → forward maintenance of those
   columns in the single catalog write path (T-02) → the one-off backfill of existing accepted apps
   (T-03) → the isolated reverse-resolution taxonomy read (T-04) → **the paginated DB-pushed query
   primitive** (T-05) → the `apps/discovery/` consumer app + activation include (T-06) → docs/CODEMAP/
   DECISIONS (T-07).
2. **Risk first (DESIGN §1/§3/§9).** The decisive design finding is that the existing D-6 read
   **cannot back a paginated surface** (O(catalogue)/call) — so the load-bearing, most-uncertain piece
   is **`search_catalogue`**: a constant-query-count, no-N+1, FTS-ranked, neutrally-ordered, clamped
   paginated read (AC9 ∧ AC5 ∧ AC2 ∧ AC1 ∧ AC7). It lands at **T-05** and is unit-tested at the ORM
   level — including the **query-count-is-constant-across-catalogue-size** assertion and the
   **ORDER-BY-neutrality** assertion — before any view exists. Its only prerequisites (the schema +
   the maintained/backfilled columns) are deliberately front-loaded into T-01–T-03 so the risk surfaces
   as early as the data allows. The cross-app touches into the **closed** catalog/taxonomy apps are
   isolated to T-01–T-05, each leaving every existing test green (regression in every DoD).
3. **Each task leaves the system working and releasable.** T-01 adds inert nullable columns nothing
   reads. T-02 maintains them going forward (no read yet). T-03 backfills (no read yet). T-04/T-05 add
   unreached selectors. The surface becomes reachable **only** at T-06 — the single `config/urls`
   include is the entire activation switch; removing it is the entire rollback (DESIGN §11/§16), and
   the two columns are then inert additive data (dropped on a deliberate cleanup, never an emergency).

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/catalog/models.py` — **T-01** only (the two columns + the two indexes).
- `apps/catalog/services.py` — **T-02** only (`_search_vector_expr` + `accept_app`/`submit_app`/
  `edit_app` maintenance). T-03's data migration imports `_search_vector_expr` from here (reuse, no
  re-edit).
- `apps/catalog/selectors.py` — **T-05** only (the `search_catalogue` primitive + `CatalogPage` DTO);
  the existing reads (`list_catalogued_apps` etc.) and the reused `_resolve_tag_labels` are
  **unchanged**.
- `apps/taxonomy/selectors.py` — **T-04** only (`tag_ids_resolving_to`); `resolve_tag`/`is_valid_tag`
  unchanged.
- `apps/core/config.py` — **T-05** (`discovery_page_size` + `discovery_page_size_max`, both consumed by
  the primitive) and **T-06** (`discovery_query_max_length`, consumed by the view); sequential, each
  with its `validate_all()` entry.
- `apps/core/observability.py` — **T-06** only (the six `DISCOVERY_*` counters).
- `config/settings.py` `INSTALLED_APPS` — **T-01** (`django.contrib.postgres`) and **T-06**
  (`apps.discovery`); sequential.
- `config/urls.py` — **T-06** only (the one `discover/` include = the activation switch).
- `apps/discovery/` is a **new package** created in T-06; no existing file is shared with another task.

---

## T-01 — Catalog schema: additive `accepted_at` + `search_vector` columns, their indexes, and `django.contrib.postgres`

- **Description.** Add the two **additive, nullable** columns to `catalog.models.App` exactly per
  DESIGN §5 (no new table, no `CatalogApp` DTO change — the cross-feature D-6 shape is untouched). This
  task is **schema only**: the columns are inert (nothing writes or reads them yet; maintenance is T-02,
  backfill is T-03).
  - `accepted_at = models.DateTimeField(null=True)` — the one source of truth for "when this app (last)
    entered the accepted catalogue", the `accepted_at`-DESC browse-order key (OSB-DESIGN-2 / OQ-OSB-2).
    `NULL` until stamped/backfilled; an app that has never been accepted stays `NULL` (and is never
    listed, so `NULL` never appears in a result set — DESIGN §5a).
  - `search_vector = SearchVectorField(null=True)` (from `django.contrib.postgres.search`) — the stored,
    indexed FTS of name(weight A) + description(weight B) (OSB-DESIGN-3 / OQ-OSB-4 = these two fields
    only). `NULL` until maintained/backfilled (DESIGN §5b).
  - **Indexes (DESIGN §5a/§5b):** add to `App.Meta.indexes` the composite
    `models.Index(fields=["status", "-accepted_at"], name="catalog_app_status_acc_idx")` (the
    accepted-only ordered browse = one index range scan, AC9) **and**
    `GinIndex(fields=["search_vector"], name="catalog_app_search_gin")` (FTS, AC9). The existing
    `catalog_app_status_idx` / `catalog_app_normurl_idx` stay (DESIGN §5a).
  - **Prerequisite (DESIGN §5b/§13 assumption A7):** add `"django.contrib.postgres"` to
    `INSTALLED_APPS` (the documented home of `SearchVectorField`/`GinIndex`/`SearchRank`) — verified
    **absent** today. Place it among the `django.contrib.*` entries.
  - Generate `catalog/000N_…` (schema migration: two columns + two indexes). **Reversible** (drops both
    columns + both indexes).
- **Dependencies.** none (foundational — T-02 maintains, T-03 backfills, T-05 reads).
- **Definition of done.**
  - `"django.contrib.postgres"` present in `INSTALLED_APPS`; `python manage.py check` clean.
  - `makemigrations catalog` produces a migration adding `accepted_at`, `search_vector`, the composite
    `(status, -accepted_at)` index and the `search_vector` GIN index; `makemigrations --check` clean
    after commit.
  - A **structural test** asserts: both columns exist and are **nullable**; the composite
    `(status, -accepted_at)` index and the `search_vector` GIN index are present on the model `Meta`.
  - The migration is reversible: `migrate catalog <prev>` → `migrate catalog <new>` →
    `migrate catalog <prev>` all succeed and leave the schema clean (DESIGN §16).
  - **Regression:** the existing 616 tests stay green (columns are additive/nullable, no consumer
    reads them yet); `list_catalogued_apps`/`get_catalogued_app`/`get_catalogued_apps` behaviour
    unchanged. `ruff` clean.
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/models.py` (two fields + two indexes + the
  `SearchVectorField`/`GinIndex` imports), `apps/catalog/migrations/000N_*.py` (new),
  `config/settings.py` (`INSTALLED_APPS` += `django.contrib.postgres`),
  `apps/catalog/tests/` (structural/migration test).

## T-02 — Maintain the new columns in the single catalog write path (`accept_app` stamps `accepted_at`; `submit_app`/`edit_app` maintain `search_vector`)

- **Description.** Wire the **forward** maintenance of the two new columns into `apps/catalog/services.py`
  — the existing single catalog write path — exactly per DESIGN §5a/§5b. **No other code ever writes
  these columns** (one source of truth; a stored value cannot drift, DESIGN §5b).
  - **Shared FTS expression (DESIGN §5b/§8):** add one private helper `_search_vector_expr()` returning
    the `SearchVector("name", weight="A") + SearchVector("description", weight="B")` expression, so the
    formula — the search field list + weights — lives in **exactly one place** (the cheapest
    change-point, DESIGN §8). Used by `submit_app`, `edit_app`, **and** the T-03 backfill.
  - **`accepted_at` (DESIGN §5a):** inside `accept_app`'s existing `transaction.atomic()`, set
    `locked.accepted_at = timezone.now()` and add `"accepted_at"` to its `save(update_fields=...)`
    (currently `["status", "updated_at"]`). Re-acceptance (withdraw → resubmit → accept) **re-stamps**
    it → a re-entering app sorts as newest (the honest "newest in the catalogue" semantics, DESIGN §5a).
    Set **nowhere else**.
  - **`search_vector` (DESIGN §5b):** recompute it from `_search_vector_expr()` **only** where `name`/
    `description` change — `submit_app` (on create) and `edit_app` (when name/description actually
    change). Apply via an `App.objects.filter(pk=…).update(search_vector=_search_vector_expr())` (or the
    equivalent expression-save) so the vector is computed in the database from the row's own columns,
    inside the same atomic write. Keep it consistent with the existing `update_fields`/change-tracking
    in `edit_app` (only recompute when name or description is in `changed_fields`).
  - **No behavioural change** to acceptance/submission/edit semantics, transitions, validation, or
    existing counters — this task only *adds* column maintenance.
- **Dependencies.** T-01 (the columns + `django.contrib.postgres`).
- **Definition of done.** Tests at the service layer (real ORM, real taxonomy D-5 surface — no
  mocking):
  - **`accept_app` stamps `accepted_at`** to ~now inside the accept; an app accepted via `accept_app`
    has a non-null `accepted_at`. **Re-acceptance re-stamps:** withdraw → resubmit → accept again yields
    a strictly later `accepted_at` (AC5/M6 — accept→visible-as-newest).
  - **`submit_app` populates `search_vector`** for a new app (non-null; matches its name/description
    terms via `search_vector @@ websearch_to_tsquery(term)`); **`edit_app` recomputes** it when name or
    description changes, and a search for the **old** term no longer matches while the **new** term does
    (AC2). Editing a non-text field (e.g. tags only) does **not** needlessly rewrite the vector.
  - The FTS formula exists in **one** place (`_search_vector_expr`) — both write paths call it (a test
    or grep-level assertion that name/description weights A/B are defined once).
  - **M6 freshness:** an app accepted via `accept_app` is immediately matchable by the eventual read
    (here proven at the column level: `accepted_at` set + `search_vector` populated within the accept/
    submit transaction).
  - **Regression:** existing `accept_app`/`submit_app`/`edit_app` tests stay green; `update_fields`
    discipline preserved (no unintended field writes). `makemigrations --check` clean; `ruff` clean;
    full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/services.py` (`_search_vector_expr` + maintenance in
  `accept_app`/`submit_app`/`edit_app`; `SearchVector` import), `apps/catalog/tests/` (service tests
  for stamping + vector maintenance).

## T-03 — Data migration: backfill `accepted_at` + `search_vector` for existing accepted apps

- **Description.** A **one-off data migration** in `catalog/` that populates the two new columns for
  apps already in the catalogue (DESIGN §5a/§5b/§16) — bounded by current catalogue size, run once.
  - **`accepted_at` backfill (DESIGN §5a):** for every app, set `accepted_at` from its **latest
    `ReviewDecision(outcome=accepted).created_at`** (the real acceptance time — the same source the
    ordering key means). Apps with no accept decision (never-accepted) stay `NULL`.
  - **`search_vector` backfill (DESIGN §5b):** recompute via the shared
    `catalog.services._search_vector_expr()` (imported into the migration so the formula is **not**
    duplicated) with one bulk `update`. Compute for all apps (or at minimum all accepted apps — the
    only ones ever read); a cheap full backfill is acceptable at current scale.
  - **Reversible:** the reverse operation sets both columns back to `NULL` (a no-op-safe down
    migration). Use a data migration (not raw SQL bound to a hardcoded formula) so the field list stays
    single-sourced.
- **Dependencies.** T-01 (columns/indexes), T-02 (`_search_vector_expr`; the forward semantics this
  backfill mirrors).
- **Definition of done.**
  - A migration test seeds, **pre-migration**, an accepted app (with an accept `ReviewDecision`) whose
    `accepted_at`/`search_vector` are `NULL`, runs the data migration, and asserts both are populated —
    `accepted_at` equals the latest accept decision's `created_at`; `search_vector` matches the app's
    name/description terms. (Use Django's migration-test harness already used in the repo, or an
    equivalent applied-state assertion.)
  - An app that was **rejected/withdrawn and never accepted** keeps `accepted_at = NULL` after backfill.
  - An app **re-accepted** (multiple accept decisions) backfills from the **latest** accept decision.
  - The migration is **reversible** (down sets both columns `NULL`); `migrate` up→down→up succeeds.
  - `makemigrations --check` clean (the data migration introduces no model drift); `ruff` clean; full
    suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/migrations/000N_backfill_*.py` (new data migration),
  `apps/catalog/tests/` (backfill migration test).

## T-04 — Taxonomy reverse resolution: `tag_ids_resolving_to(active_id) -> frozenset[UUID]`

- **Description.** Add the new reverse-resolution read to `apps/taxonomy/selectors.py` exactly per
  DESIGN §6.2 (OSB-DESIGN-4) — the reverse of `resolve_tag`, so a tag filter is consistent with the
  resolved labels the catalogue already displays (AC3). Isolated, low-risk, depends on nothing in
  catalog; the catalog primitive (T-05) filters a **handed-in** id set, so catalog stays decoupled from
  merge semantics (DESIGN §3/§6.2).
  - `tag_ids_resolving_to(active_id: UUID) -> frozenset[UUID]` returns
    `{active_id} ∪ {all tag_ids whose replaced_by chain resolves to active_id}` — the active tag **plus
    its transitive merge predecessors** (tags whose `replaced_by` chain leads to it).
  - **Implementation:** a bounded breadth walk over `replaced_by_id IN frontier` (the inverse of the
    `replaced_by` FK — the existing `related_name="replaces"`), starting from `{active_id}`,
    accumulating predecessors until the frontier is empty. Cost is bounded by **vocabulary size**
    (small, slow-growing reference data) — **not** catalogue size; a documented, acceptable bound
    (DESIGN §5.2/§14). (A recursive CTE behind the same signature is the named future swap if the
    vocabulary ever grows huge — DESIGN §13; not built.)
  - **Tolerant of bad input** (mirrors `is_valid_tag`): an unknown / non-UUID / malformed id →
    `frozenset()`; **never raises**. The caller has already validated via `is_valid_tag` (DESIGN §6.2).
  - **Invariant:** `active_id ∈ result` for any known active id. Additive read — does **not** change
    `resolve_tag`/`is_valid_tag`.
- **Dependencies.** none (reads only the taxonomy model; independent of the catalog tasks).
- **Definition of done.** Tests over seeded taxonomy fixtures (real merge chains via `retire_tag` with
  a successor):
  - **singleton** (a tag with no predecessors) → `{active_id}`.
  - **merge chain** X → W → Y (X merged into W, W merged into Y): `tag_ids_resolving_to(Y) == {X, W, Y}`
    (AC3 correctness — every predecessor that now *means* Y is included).
  - **branching merges** (two tags both merged into the same active tag) → both predecessors included.
  - **unknown / non-UUID id** → `frozenset()`, no exception.
  - **bounded query count** independent of catalogue size (`assertNumQueries` bounded by chain depth,
    not by number of apps — DESIGN §6.2/§10).
  - `ruff` clean; full suite green (no change to existing taxonomy behaviour).
- **Estimated size.** S.
- **Files/areas touched.** `apps/taxonomy/selectors.py` (`tag_ids_resolving_to`),
  `apps/taxonomy/tests/` (reverse-resolution test).

## T-05 — The paginated DB-pushed query primitive: `catalog.selectors.search_catalogue(...) -> CatalogPage` (+ page-size config)

- **Description.** Implement the open-surface read in `apps/catalog/selectors.py` exactly per DESIGN
  §6.1 (OSB-DESIGN-1) — **the** paginated catalogue query, the one place that knows how to *query* the
  catalogue (order/filter/paginate/page-scoped resolve). This is the **risk centerpiece** (AC9 ∧ AC5 ∧
  AC2 ∧ AC1 ∧ AC7); build and verify it at the ORM level before any view. It returns a page of the
  **unchanged** `CatalogApp` DTO — no DTO change, no break to existing D-6 consumers.
  - `CatalogPage` — `@dataclass(frozen=True)` with `apps: list[CatalogApp]` (the page, already in final
    neutral order), `total: int`, `page: int` (clamped, 1-based), `page_size: int`, `has_next: bool`
    (DESIGN §6.1).
  - `search_catalogue(*, query=None, tag_ids=None, page=1, page_size=None) -> CatalogPage`:
    - **Coercion/clamp (DESIGN §6.1):** `query` stripped, blank ⇒ browse mode; `tag_ids` is the
      **already-expanded** set (catalog does **not** resolve tags itself — clean separation, §3/§4);
      `page` clamped to `[1, last_page]`; `page_size` defaults to `config.discovery_page_size()`, clamped
      to `[1, config.discovery_page_size_max()]`.
    - **Filter (DESIGN §6.1):** always `status=ACCEPTED` (OSB-2; AC1/AC2 — pending/rejected/withdrawn
      never appear); `+ search_vector @@ websearch_to_tsquery(query)` when `query` present;
      `+ app_tags__tag_id__in=tag_ids` with `.distinct()` when `tag_ids` present. Keyword ∧ tag
      **compose** (AND).
    - **Order — the AC5 invariant, only neutral published non-purchasable keys (DESIGN §6.1):** keyword
      present → `SearchRank(search_vector, query) DESC, accepted_at DESC, id`; keyword absent →
      `accepted_at DESC, id`. `id` is the final stable tie-break (deterministic pagination). **No
      payment / tier / Quality-Score / impression-count term may appear in the ORDER BY** (M5 = 0 by
      construction).
    - **Pagination & N+1 (DESIGN §6.1/§10):** `total` via one `COUNT`; the page via one `LIMIT/OFFSET`
      SELECT with `prefetch_related("media", "app_tags")`; tags resolved for **only the page's apps**
      by reusing the existing deduped `_resolve_tag_labels` (no change to it). ⇒ a **fixed, small number
      of queries per page regardless of catalogue size or page index**.
    - **Invariants/errors (DESIGN §6.1):** every element is `status=ACCEPTED`; `len(apps) <= page_size`;
      `apps == []` is a **valid empty page** (never an error). Raises **only** on a genuine DB failure
      (loud — never a fake empty page). A malformed `query` cannot raise (`websearch_to_tsquery` accepts
      arbitrary text).
  - **Config (DESIGN §8/§10) — add to `apps/core/config.py`** with the existing `_positive_int`
    precedence + a `validate_all()` entry each: `discovery_page_size() -> int` (default **24**, the
    browse/search page size) and `discovery_page_size_max() -> int` (default **100**, the clamp
    ceiling). Both are change-cheap constants (DESIGN §8); document the literal in the config docstring
    (no magic number in the selector), mirroring the existing `DEFAULT_FOLLOWED_FEED_PAGE_SIZE` pattern.
- **Dependencies.** T-01 (columns/indexes), T-02 (`search_vector` maintained so search tests have real
  vectors; `accepted_at` stamped so order tests are real). (T-03 not required for unit tests, which seed
  via the write path; T-04 not required — the primitive takes a handed-in id set.)
- **Definition of done.** ORM-level tests (seeded apps via the catalog write path — real `accept_app`/
  `submit_app` so `accepted_at`/`search_vector` are real):
  - **AC1 browse** — accepted apps only, paginated; order = `accepted_at DESC` with `id` tie-break;
    pending/rejected/withdrawn **never** returned.
  - **AC2 keyword** — name/description matches returned, ranked by relevance; non-matching and
    non-accepted excluded.
  - **AC3 tag-set filter** — only apps carrying an id in `tag_ids` returned, **deduped** (`.distinct()`,
    no row multiplied by multiple matching tags); keyword ∧ tag **compose** (AND).
  - **AC5/M5 ORDER-BY neutrality** — a test asserts the query's ordering contains **only**
    rank/`accepted_at`/`id` and **no** paid/tier/score/impression field (the position-neutrality audit
    = 0 by construction).
  - **AC9 pagination + no-N+1** — `has_next`/`total`/`page` correct across pages; an over-large `page`
    **clamps** to the last page (still a valid result); **the query count is constant across catalogue
    size** (`assertNumQueries` equal for 5 apps vs. 50 apps — the load-bearing scale assertion).
  - **AC7 empty** — a filter matching nothing → `CatalogPage(apps=[], total=0, has_next=False)`, **no
    error**; an empty catalogue → likewise.
  - **M1 coverage** — a property check: every accepted app is reachable across the full set of pages
    (browse mode) — 100% by construction.
  - `config.discovery_page_size()` / `discovery_page_size_max()` return defaults and are covered by
    `validate_all()`; the primitive clamps to them.
  - **Regression:** existing catalog selectors unchanged and green; `CatalogApp` DTO unchanged.
    `makemigrations --check` clean; `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/catalog/selectors.py` (`CatalogPage` + `search_catalogue`;
  `SearchRank`/`websearch_to_tsquery`-style FTS imports; reuses `_resolve_tag_labels`),
  `apps/core/config.py` (two page-size tunables + `validate_all`), `apps/catalog/tests/`
  (primitive tests).

## T-06 — `apps/discovery/` consumer app: views + urls + `catalogue.html` + the `config/urls` include (+ query-length config + observability)

- **Description.** Create the new **model-less consumer app** `apps/discovery/` (a near-twin of
  `apps/pages/`) exactly per DESIGN §4c/§6.3/§6.4/§7 — the public listing UX and request handling — then
  add `path("discover/", include("apps.discovery.urls"))` to `config/urls.py`: the **entire activation
  switch** (DESIGN §16; removing it = the entire rollback). The app **owns no model/migration** and
  **imports nothing from `signals`** (AC6 structural — DESIGN §4c/§10). The view holds **no business
  logic and no ORM access** beyond calling the catalog/taxonomy read surfaces (the pages/ratings house
  pattern).
  - **Scaffold:** `__init__.py`, `apps.py` (`AppConfig`, `name="apps.discovery"`), `urls.py`
    (`app_name="discovery"`, `path("", views.catalogue, name="browse")`), `tests/`. Register
    `"apps.discovery"` in `INSTALLED_APPS`.
  - **`views.catalogue(request) -> HttpResponse` (DESIGN §6.3) — GET only, NO `login_required` (AC8):**
    parse the trust-boundary params (all optional):
    - `q` → stripped, truncated to `config.discovery_query_max_length()` (default 200), blank ⇒ browse.
    - `tag` → `UUID`-coerced; **ignored** unless `taxonomy.is_valid_tag` (AC3 — a retired/unknown tag
      offers no stale filter); when valid, expanded via `taxonomy.tag_ids_resolving_to` (T-04).
    - `cluster` → `UUID`-coerced; expanded to the union of `tag_ids_resolving_to(t)` over the cluster's
      **active** tags; unknown ⇒ ignored. `tag` and `cluster` are **mutually exclusive — `tag` wins**
      if both arrive (DESIGN §6.3).
    - `page` → int-coerced; non-int/<1 ⇒ 1 (the primitive clamps over-large).
    - Calls `catalog.search_catalogue(query=…, tag_ids=…, page=…)` and renders `catalogue.html`.
      Assembles the facet sidebar from `taxonomy.list_active_tags()`/`list_clusters()`. Response is
      **always 200** for a well-formed request, including zero results / empty catalogue (AC7).
  - **`templates/discovery/catalogue.html` (DESIGN §6.4) — the five UI states:** results listing
    (semantic `<ul>`/`<article>` cards: name, truncated description, first media as thumbnail with
    `alt_text`, resolved tag chips), **each card a link to `pages:app-page app.id`** (AC4); pagination
    (prev/next + "page X of Y" from `CatalogPage`); the active-tag/cluster facet sidebar + a search box
    reflecting `q`; the **zero-results** state ("No apps match…" + clear-filters link, 200);
    the **empty-catalogue** state ("No apps in the catalogue yet", 200); the **facet-degraded** state
    (results render, sidebar shows "filters unavailable"). All app/tag text rendered through Django
    auto-escaping (no `|safe`). Keyboard-navigable links/controls (C7/§10). Mirror the `apps/pages/`
    `base.html`/template structure for consistency.
  - **Failure split (DESIGN §7/§9) — the load-bearing rule:** the **core results read** fails **loud**
    — a `search_catalogue` exception propagates to a normal `500` (count `DISCOVERY_LISTING_DEGRADED`
    around the raise, then re-raise — **never** masked as a fake empty state, which would lie about
    M1/M3). The **facet sidebar** fails **soft** — wrap only the `list_active_tags`/`list_clusters`
    call; on error render results normally with a quiet "filters unavailable" note + count
    `DISCOVERY_FACETS_DEGRADED`.
  - **No D-7 emit (AC6 / OSB-DESIGN-5):** the app imports nothing from `signals`; a click that lands on
    the app-page is captured by `app-pages` as a non-curated `APP_PAGE` impression (M2 derived there).
    A **structural test** asserts `apps.discovery` does not import `signals.capture`.
  - **Config (DESIGN §6.3/§8) — add to `apps/core/config.py`:** `discovery_query_max_length() -> int`
    (default **200**) with its `validate_all()` entry.
  - **Observability (DESIGN §11) — add the six counters to `apps/core/observability.py`:**
    `DISCOVERY_BROWSE_RENDERED`, `DISCOVERY_SEARCH_PERFORMED`, `DISCOVERY_TAG_FILTERED`,
    `DISCOVERY_ZERO_RESULTS` (M3 — counted when `total == 0`), `DISCOVERY_FACETS_DEGRADED`,
    `DISCOVERY_LISTING_DEGRADED` (the one actionable alert). Increment from the view per DESIGN §11.
- **Dependencies.** T-04 (`tag_ids_resolving_to`), T-05 (`search_catalogue` + page-size config).
- **Definition of done.** Integration tests (Django test client, project URLconf with the `discover/`
  include):
  - **AC8 anonymous** — a signed-out GET to `/discover/` (browse), `?q=…` (search), `?tag=…` (filter)
    each returns **200** with **no login redirect**; signing in changes nothing about what is shown.
  - **AC1 browse** — every accepted app appears across pages; no pending/rejected/withdrawn app shown;
    pagination controls render with correct "page X of Y".
  - **AC2 search** — `?q=term` returns name/description matches, excludes non-matching/non-accepted.
  - **AC3 tag filter** — `?tag=<active>` shows only carriers (including merged predecessors per T-04);
    `?tag=<retired-no-successor>` and `?tag=<unknown>` and a non-UUID `tag` are **ignored** (unfiltered
    listing, **no 500**); facets list **only active** tags grouped by cluster.
  - **AC4 link** — a result card links to `pages:app-page` at the app's stable `App.id` URL.
  - **AC7 empty/zero-result** — a non-matching query and an empty catalogue each render the empty-state
    message with **200** (not 404/500/blank).
  - **AC6 structural** — `apps.discovery` imports nothing from `signals.capture` (the cleanest proof a
    self-driven view never confers curated eligibility).
  - **failure split** — `search_catalogue` patched to raise → **500** (not a masked empty state) +
    `DISCOVERY_LISTING_DEGRADED`; `list_active_tags`/`list_clusters` patched to raise → results still
    render (soft-degrade) + `DISCOVERY_FACETS_DEGRADED`.
  - `config.discovery_query_max_length()` returns its default and is covered by `validate_all()`; the
    six observability counters exist and fire on their paths.
  - `manage.py check` clean; `makemigrations --check` clean (the app owns no model); `ruff`/template
    lint clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/discovery/` (new package: `__init__.py`, `apps.py`, `views.py`,
  `urls.py`, `templates/discovery/catalogue.html` (+ a `base.html` if mirroring pages),
  `tests/__init__.py`, `tests/test_views.py`, `tests/test_imports.py`), `config/urls.py` (the
  `discover/` include), `config/settings.py` (`INSTALLED_APPS` += `apps.discovery`),
  `apps/core/config.py` (`discovery_query_max_length` + `validate_all`),
  `apps/core/observability.py` (the six `DISCOVERY_*` counters).

## T-07 — README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: docs + the shared-code index — no behavioural change (DESIGN §16).
  - `apps/discovery/README.md` — the app's single responsibility (a pure read orchestrator over the
    D-5/D-6 surfaces; **owns no model**, **emits no D-7 signal**), the one route (`discovery:browse` at
    `/discover/`), the neutral-order invariant (AC5/M5), and the **rollback** (remove the `config/urls`
    `discover/` include; the two `catalog_app` columns are then inert and droppable by reversing
    T-01/T-03 on a deliberate cleanup — **not** an emergency step, DESIGN §11/§16).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: the additive D-6 read
    `catalog.selectors.search_catalogue` (+ the `CatalogPage` DTO) and the two new `catalog_app`
    columns (`accepted_at` browse-order key + `search_vector` FTS) with the `_search_vector_expr`
    single-source formula; the additive D-5 read `taxonomy.selectors.tag_ids_resolving_to`; the
    `discovery:browse` route + `catalogue.html`; the three new config tunables
    (`discovery_page_size`/`discovery_page_size_max`/`discovery_query_max_length`); the six
    `DISCOVERY_*` observability constants.
  - [features/open-search-browse/DECISIONS.md](DECISIONS.md) — mark **OSB-DESIGN-1…6** as **built**.
    Note the named-not-built revisit flags (OFFSET→keyset pagination if deep paging gets hot; a
    non-curated `Surface.SEARCH` D-7 emit once M2 needs first-party measurement, OQ-OSB-3; tag-label/
    fuzzy/semantic search if the M3 zero-result rate is high, OQ-OSB-4) per DESIGN §16.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit artifact,
    produced alongside the build, **not** in this task.
- **Dependencies.** T-01…T-06.
- **Definition of done.** `apps/discovery/README.md` matches the shipped route/store/rollback;
  `CODEMAP.md` lists every new shared surface above; `DECISIONS.md` marks OSB-DESIGN-1…6 built;
  `makemigrations --check` clean; **full suite green, `ruff` clean, no drift** (the close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/discovery/README.md` (new), [CODEMAP.md](../../CODEMAP.md),
  `features/open-search-browse/DECISIONS.md`.

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §5a `accepted_at` column + composite `(status, -accepted_at)` index (OSB-DESIGN-2) | **T-01** (schema) + **T-02** (stamped in `accept_app`) + **T-03** (backfill) |
| §5b `search_vector` `SearchVectorField` + GIN index + `django.contrib.postgres` (OSB-DESIGN-3) | **T-01** (schema + install) + **T-02** (`_search_vector_expr` maintenance) + **T-03** (backfill) |
| §5b single-source FTS formula `_search_vector_expr()` (change-cheap, §8) | **T-02** (defined) + **T-03** (reused in backfill) |
| §6.1 `search_catalogue(...) -> CatalogPage` paginated DB-pushed primitive (OSB-DESIGN-1) | **T-05** |
| §6.1 neutral ORDER BY (rank/`accepted_at`/`id` only) + M5 neutrality (AC5) | **T-05** (order + neutrality test) + **T-02** (`accepted_at` as the key) |
| §6.1/§10 pagination + no-N+1 / constant-query-count at 100× (AC9) | **T-01** (indexes) + **T-05** (primitive + scale assertion) |
| §6.2 `tag_ids_resolving_to(active_id) -> frozenset[UUID]` reverse D-5 read (OSB-DESIGN-4, AC3) | **T-04** |
| §4c/§6.3 `apps/discovery/` model-less consumer app + view + routes (OSB-DESIGN-6) | **T-06** |
| §6.3 trust-boundary param coercion (`q`/`tag`/`cluster`/`page`); tag wins over cluster; invalid-tag ignored (AC3) | **T-06** |
| §6.4 the five `catalogue.html` UI states (results/zero/empty/facet-degraded/error) + card→`pages:app-page` link (AC4/AC7) | **T-06** |
| §4c/§10 AC6 structural — discovery imports no `signals` (no D-7 emit, OSB-DESIGN-5) | **T-06** (import-absence assertion) |
| §6.3/§8 anonymous access — `catalogue` view has no `login_required` (AC8) | **T-06** |
| §7/§9 failure split — core read fails loud (500, not masked); facet sidebar fails soft | **T-06** |
| §8/§10 config tunables `discovery_page_size`/`discovery_page_size_max`/`discovery_query_max_length` | **T-05** (page-size) + **T-06** (query-length) |
| §11 observability (`DISCOVERY_BROWSE_RENDERED`/`_SEARCH_PERFORMED`/`_TAG_FILTERED`/`_ZERO_RESULTS`/`_FACETS_DEGRADED`/`_LISTING_DEGRADED`) | **T-06** |
| §11 metrics realisation: M1 coverage (property test), M3 zero-result counter, M5 neutrality test, M6 freshness | **T-05** (M1/M5) + **T-02** (M6) + **T-06** (M3) |
| §11/§16 activation/rollback = one `config/urls` include; design-for-deletion | **T-06** (include) + **T-07** (rollback note) |
| §16 docs/CODEMAP + OSB-DESIGN-1…6 built | **T-07** |
| §15 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-01+T-05+T-06; AC2 → T-01+T-02+T-05+T-06; AC3 → T-04+T-05+T-06; AC4 → T-06;
AC5 → T-02+T-05; AC6 → T-06; AC7 → T-05+T-06; AC8 → T-06; AC9 → T-01+T-05. All nine acceptance criteria
are covered; **no `L` tasks** (all S/M); every task has a checkable definition of done and declared
files; every task leaves the system green and releasable (the surface goes live only at the T-06
`config/urls` include).
