# TEST_PLAN — open-search-browse

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (Given/When/Then) in the
approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md) to the automated test(s) that verify it, plus the
edge / security / failure / regression coverage. Built against the ratified
[DESIGN.md](DESIGN.md) and [TASKS.md](TASKS.md). **676 tests green** (was 616; +60), `ruff`
clean, `manage.py check` clean, `makemigrations --check` clean.*

## How the suite is structured

| File | Layer | Covers |
|------|-------|--------|
| `apps/catalog/tests/test_models.py` | schema | T-01 columns + indexes (structural) |
| `apps/catalog/tests/test_services_search.py` | service | T-02 `accepted_at` stamping + `search_vector` maintenance + single-source formula |
| `apps/catalog/tests/test_backfill_migration.py` | migration | T-03 backfill / reverse |
| `apps/taxonomy/tests/test_selectors.py` (`TagIdsResolvingToTests`) | selector | T-04 reverse resolution |
| `apps/catalog/tests/test_search_catalogue.py` | ORM/selector | T-05 the paginated primitive (the risk centerpiece) |
| `apps/discovery/tests/test_views.py` | HTTP (test client) | T-06 the view, end-to-end through the project URLconf |
| `apps/discovery/tests/test_imports.py` | structural | T-06 AC6 import-absence |

## Acceptance-criterion coverage (each AC → test)

| AC | Given / When / Then | Verifying test(s) |
|----|---------------------|-------------------|
| **AC1** browse, accepted-only, paginated | accepted apps exist → signed-out browse → every accepted app appears paginated; no pending/rejected/withdrawn shown | `test_search_catalogue.BrowseTests.test_returns_only_accepted_apps_newest_first`, `…test_pending_rejected_withdrawn_never_returned`; `test_views.BrowseTests.test_accepted_apps_listed_non_catalogued_excluded`, `…test_pagination_controls_render` |
| **AC2** keyword search name/desc, excludes non-match/non-accepted | keyword query → search → name/description matches returned, non-matching + non-accepted excluded | `test_services_search.SearchVectorMaintenanceTests.*` (vector populated/recomputed); `test_search_catalogue.KeywordSearchTests.*`; `test_views.KeywordSearchTests.test_query_returns_matches_and_excludes_non_matching`, `…test_query_excludes_non_accepted` |
| **AC3** tag filter resolved per D-5, no stale facet | selected interest tag → filter → only carriers (resolved across merges) shown; retired-no-successor offers no stale filter | `test_selectors.TagIdsResolvingToTests.*`; `test_search_catalogue.TagFilterTests.*`; `test_views.TagFilterTests.test_filter_shows_only_carriers`, `…test_filter_includes_merged_predecessor_carriers`, `…test_retired_no_successor_tag_is_ignored_no_500`, `…test_unknown_and_malformed_tag_are_ignored_no_500` |
| **AC4** result → stable app-page URL | result row for X → select → land on X's `pages:app-page` `App.id` URL | `test_views.BrowseTests.test_result_card_links_to_the_stable_app_page_url` |
| **AC5** order only by neutral non-purchasable keys | two accepted apps → ordered → order determined only by relevance/recency/id, never payment/tier | `test_search_catalogue.OrderNeutralityTests.*` (asserts the ORDER BY is exactly `rank`/`accepted_at`/`id` with **no** purchasable key); `test_services_search.AcceptedAtStampingTests.*` (the key itself is honest acceptance time) |
| **AC6** exposure never curated/`DIGEST` | visitor views/clicks a result → any recorded signal is non-curated | `test_imports.DiscoveryImportsTests.test_no_module_in_the_app_imports_signals` (the app emits **no** D-7 signal at all — by construction it cannot confer curated eligibility) |
| **AC7** empty / zero-result = 200, never broken | no match / empty catalogue → render → clear empty-state message + `200` | `test_search_catalogue.EmptyStateTests.*`; `test_views.EmptyStateTests.test_empty_catalogue_renders_its_message_200`, `…test_zero_result_query_renders_its_message_200` |
| **AC8** anonymous access, no login wall | not signed in → access browse/search/result → succeeds, no redirect | `test_views.AnonymousAccessTests.test_anonymous_browse_search_and_filter_all_return_200`, `…test_signed_in_sees_the_same_surface` |
| **AC9** paginated, bounded per page, no N+1 at 100× | catalogue grows → page renders → paginated, DB work per page bounded | `test_search_catalogue.PaginationTests.*` (bounds/flags/clamp/coverage); `test_search_catalogue.ScaleTests.test_query_count_constant_across_catalogue_size` (**the load-bearing assertion: identical query count at 5 vs 50 apps**); `test_models.AppModelTests.test_browse_order_and_search_indexes_present` |

## Metric realisation (DESIGN §11)

| Metric | Verified by |
|--------|-------------|
| M1 open-access coverage (100%) | `test_search_catalogue.PaginationTests.test_every_accepted_app_is_reachable_across_pages` (property: every accepted app reachable across pages) |
| M3 zero-result rate | `test_views.CounterTests.test_browse_search_and_zero_result_counters_fire` (`discovery_zero_results` fires when `total == 0`) |
| M5 position-neutrality audit = 0 | `test_search_catalogue.OrderNeutralityTests.test_no_purchasable_key_participates_in_ordering` (structural, by construction) |
| M6 freshness lag | `test_services_search.AcceptedAtStampingTests.test_accept_stamps_accepted_at_to_now`, `…test_reacceptance_restamps_accepted_at_strictly_later` (accept → immediately ordering-visible) |

## Edge cases covered

- **Empty:** empty catalogue, zero-result query, empty `tag_ids`, blank/whitespace query (browse mode).
- **Huge / boundary:** over-large `page` clamps to the last page; absurd `page_size` clamps to the configured ceiling; `page < 1` clamps to 1.
- **Malformed:** non-UUID `tag`, unknown UUID `tag`, retired-no-successor `tag` — all ignored (no 500); odd/unbalanced FTS punctuation (`websearch_to_tsquery` tolerates it, never raises).
- **Merge semantics:** singleton tag, linear chain X→W→Y, branching merges — `tag_ids_resolving_to` correctness; a merged-predecessor carrier still matches the successor filter.
- **Re-acceptance:** withdraw → resubmit → accept re-stamps `accepted_at` strictly later.
- **Tags-only edit:** does not needlessly rewrite the `search_vector`.

## Security / boundary

- **Accepted-only is structural:** every `search_catalogue` result is `status=ACCEPTED` — a pending/rejected/withdrawn app is unrepresentable in a result (one primitive enforces it).
- **Anonymous-by-design but read-only:** no write surface; the only id exposed is the already-public `App.id` link (no IDOR).
- **FTS is ORM-parameterized** (`SearchQuery(..., search_type="websearch")`) → no SQL injection.
- **No PII:** the surface records **no** D-7 signal (`test_imports` enforces no `signals` import) → no visitor data written, anonymous or otherwise.
- **Auto-escaping:** all app/tag text rendered through Django auto-escaping (no `|safe` in `catalogue.html`).

## Failure modes

- **Core results read fails loud:** `search_catalogue` patched to raise → **500** (not a masked empty state) + `DISCOVERY_LISTING_DEGRADED` — `test_views.FailureSplitTests.test_core_read_failure_is_a_loud_500_not_a_fake_empty_state`.
- **Facet sidebar fails soft:** `list_active_tags` patched to raise → results still render + "Filters are unavailable" + `DISCOVERY_FACETS_DEGRADED` — `test_views.FailureSplitTests.test_facet_read_failure_degrades_soft_results_still_render`.

## Regression checklist (areas touched in closed apps)

- **catalog (submission-intake):** existing `submit_app`/`edit_app`/`accept_app` semantics, `update_fields` discipline, and the `list_catalogued_apps`/`get_catalogued_app`/`get_catalogued_apps` D-6 reads + the `CatalogApp` DTO are **unchanged** — full `apps.catalog` suite green (142 tests). The two new columns are additive/nullable; the FTS/`accepted_at` maintenance only *adds* writes.
- **taxonomy (interest-taxonomy):** `resolve_tag`/`is_valid_tag`/`list_active_tags`/`list_clusters` unchanged; `tag_ids_resolving_to` is purely additive — full `apps.taxonomy` suite green.
- **config / observability:** additive tunables + counters only; `validate_all()` covers the three new tunables.
- **migrations:** `catalog/0002` (schema) and `catalog/0003` (backfill) are reversible up→down→up; `makemigrations --check` reports no drift; `apps/discovery/` owns no model/migration.
- **Whole suite:** 676 tests green (+60 over the 616 baseline).
