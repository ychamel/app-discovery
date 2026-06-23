# RELEASE_NOTES — open-search-browse

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway PostgreSQL database
(2026-06-23).* Sources: the verified Stage-4 build, [DESIGN.md §9/§11/§16](DESIGN.md)
(failure modes + operations + rollout/rollback), [FEATURE_BRIEF.md §Success metrics](FEATURE_BRIEF.md)
(M1–M6 + AC1–AC9), [TEST_PLAN.md](TEST_PLAN.md), [DECISIONS.md](DECISIONS.md) (OSB-DESIGN-1…6),
and the reused contracts [D-3](../../DECISIONS.md) (identity/roles), [D-4](../../DECISIONS.md)
(stack), [D-5](../../DECISIONS.md) (taxonomy `resolve_tag`/`is_valid_tag`/active-tag facets),
[D-6](../../DECISIONS.md) (the accepted-app catalogue read surface + the `CatalogApp` DTO),
[D-7](../../DECISIONS.md) (the behavioral-signal corpus — **not emitted here**) and
[D-8](../../DECISIONS.md) (the curated-rating gate — surface segregation). The
[app-pages release](../app-pages/RELEASE_NOTES.md) is the precedent this mirrors —
`apps/discovery/` is the second **model-less consumer app** activated by a single
`config/urls` include — but unlike app-pages this release **also extends two closed read
surfaces** (catalog + taxonomy) with additive, contract-preserving changes.

---

## 1. What this release is

The platform's **open discovery surface** — the open-access half of the integrity premise
(vision §4.1 / §6). **Anyone, signed-out visitors included**, can now **browse**, **keyword
search**, or **interest-tag filter** the [D-6](../../DECISIONS.md) accepted-app catalogue and
reach each app's [app-page](../app-pages/) at its stable `App.id` URL — in an order that is
**position-neutral and impossible to buy** (AC5 / M5 = 0, the *money-buys-tools-never-position*
invariant) and that **confers no curated-rating eligibility** (AC6 / D-8 surface segregation —
a self-driven view is never a `DIGEST` impression). It is the *finding* surface that points at
the app-pages app-pages already publishes; until now an accepted app was reachable only via a
digest or a direct link someone already held.

It ships as a **new model-less Django app, `apps/discovery/`** (owns no table, no migration —
deletable by one `config/urls` line), backed by **additive read-surface extensions** to the
already-closed `catalog` and `taxonomy` apps: a paginated DB-pushed catalog query primitive,
two additive nullable `catalog_app` columns (`accepted_at`, `search_vector`) with their indexes,
and a reverse-resolution taxonomy read. It changes **no existing feature's behavior** — the
`CatalogApp` DTO and every existing selector are unchanged — and satisfies all nine acceptance
criteria AC1–AC9 (mapping in [TEST_PLAN.md](TEST_PLAN.md), [DESIGN §15](DESIGN.md)).

## 2. What changed

- **New app `apps/discovery/`, owning no model** ([DESIGN §4c/§6.3](DESIGN.md)) — a pure read
  orchestrator: `views.catalogue` parses `q`/`tag`/`cluster`/`page` at the trust boundary,
  assembles the active-tag/cluster facet sidebar, computes the tag-match set, calls the catalog
  primitive, and renders `catalogue.html`. The view is **GET-only with NO `login_required`** —
  open access is structural (AC8). Route `discovery:browse`, mounted at **`/discover/`**. The app
  **imports nothing from `signals`** — AC6 is satisfied *by construction* and **AST-asserted** by
  a no-import test (a self-driven browse/search exposure can record no `DIGEST` impression and
  confers no curated-rating eligibility / Quality-Score weight). It owns no table, so it is
  removed cleanly by deleting one include line — the activation switch *is* the rollback.
- **The paginated catalog query primitive — the risk centerpiece** ([DESIGN §4a/§6.1](DESIGN.md),
  OSB-DESIGN-1) — `catalog.selectors.search_catalogue(*, query, tag_ids, page, page_size) ->
  CatalogPage`. The existing D-6 `list_catalogued_apps()` **materializes the whole accepted
  catalogue and resolves every tag in Python** (O(catalogue)/call) → unpaginatable at scale. The
  new primitive pushes **filter + order + pagination + page-scoped tag resolution into the
  database**: always `status=ACCEPTED` (AC1/AC2 — pending/rejected/withdrawn unrepresentable in
  any result); optional `search_vector @@ websearch_to_tsquery(query)` keyword filter (AC2) and
  optional handed-in `tag_ids` filter (AC3), **AND-composed**; one `COUNT` + one `LIMIT/OFFSET`
  SELECT with `prefetch_related` + a page-scoped resolve → **a fixed, small query count per page
  regardless of catalogue size or page index** (AC9, the load-bearing
  *constant-query-count-at-5-vs-50-apps* assertion). Returns a page of the **unchanged**
  `CatalogApp` DTO inside a new frozen `CatalogPage` (apps/total/page/page_size/has_next).
- **Position-neutral ORDER BY only — the AC5/M5 invariant** ([DESIGN §6.1/§11](DESIGN.md)) —
  keyword present → `SearchRank(search_vector, query) DESC, accepted_at DESC, id`; keyword absent
  → `accepted_at DESC, id`. `id` is the stable final tie-break (deterministic pagination).
  **No payment / tier / Quality-Score / impression-count term exists in the ORDER BY** — M5 = 0 is
  structural, **enforced by a test** that asserts no paid/tier/score field participates. There is
  no purchasable input to count, so M5 is a structural guarantee, not a runtime counter.
- **Two additive, nullable columns on `catalog_app`** ([DESIGN §5](DESIGN.md), OSB-DESIGN-2/3;
  `catalog/0002`) — **`accepted_at: DateTimeField(null=True)`**, the single source of truth for
  "when this app (last) entered the accepted catalogue" = the newest-first browse-order key,
  composite-indexed `(status, -accepted_at)` (`catalog_app_status_acc_idx`) so the accepted-only
  browse page is one index range scan; and **`search_vector: SearchVectorField(null=True)`**, the
  Postgres FTS index of `name`(weight A) + `description`(weight B), `GinIndex`
  (`catalog_app_search_gin`). Both are **nullable and additive** — every existing row reads `NULL`
  until backfilled, and a never-accepted app keeps `accepted_at = NULL` (and is never listed, so
  `NULL` never appears in a result set). Adds **`django.contrib.postgres`** to `INSTALLED_APPS`
  (the home of `SearchVectorField`/`GinIndex`/`SearchRank`/`SearchQuery`; verified absent before).
  The `CatalogApp` DTO is unchanged → **no D-6 consumer breaks**.
- **Column maintenance in the single catalog write path** ([DESIGN §5/§6.1](DESIGN.md), T-02) —
  one-source `catalog.services._search_vector_expr()` (name A + description B) is the **only**
  place the FTS formula lives. `accept_app` stamps/re-stamps `accepted_at = timezone.now()`
  **inside its existing transaction** (a withdraw→resubmit→re-accept **re-stamps** → a re-entering
  app sorts as newest, the honest semantics); `submit_app`/`edit_app` recompute `search_vector`
  via `_maintain_search_vector` **only when `name`/`description` change** (a tags-only edit does
  not rewrite the vector). No other code writes either field → a stored value cannot drift.
  Acceptance freshness is ~immediate (M6): the column is stamped in the accept transaction, so the
  app is visible on the next query — asserted by an accept→visible test.
- **The reversible backfill** ([DESIGN §5](DESIGN.md), OSB-DESIGN-2/3; `catalog/0003`) — a one-off
  data migration populating both columns for apps already in the catalogue: `accepted_at` ← the
  **latest** `ReviewDecision(outcome=accepted).created_at` (the real acceptance time; a
  never-accepted app stays `NULL`); `search_vector` ← the **imported** `_search_vector_expr()` (so
  the formula stays single-sourced with the write path, never restated). Bounded by current
  catalogue size, run once, **reversible** (the reverse clears both columns back to `NULL`).
- **Reverse-resolution taxonomy read** ([DESIGN §4b/§6.2](DESIGN.md), OSB-DESIGN-4; T-04) —
  `taxonomy.selectors.tag_ids_resolving_to(active_id) -> frozenset[UUID]` returns the active tag
  **plus its transitive merge predecessors** (the reverse of `resolve_tag`), so a tag filter
  matches every stored id that *means* the selected tag now — consistent with the resolved labels
  the catalogue already displays (AC3). A bounded breadth walk over `related_name="replaces"`,
  cost bounded by **vocabulary size** (small, slow-growing reference data), **not** catalogue size
  — a deliberate, documented bound; tolerant of unknown/malformed ids (`frozenset()`), never
  raises. Discovery (not catalog) owns the expansion → catalog stays decoupled from D-5 merge
  semantics (it filters a handed-in id set). Active-tag/cluster facets come from the existing
  `list_active_tags`/`list_clusters` (active only → AC3: a retired tag offers no stale filter).
- **Failure split — loud where it matters, soft where it's chrome** ([DESIGN §7/§9](DESIGN.md)) —
  the **core results read fails LOUD**: a DB error propagates to a normal `500` and is **never**
  masked as a fake empty state (that would lie about M1/M3 and hide an outage), counted by
  `DISCOVERY_LISTING_DEGRADED` (the one actionable alert). The **facet sidebar fails SOFT**:
  results still render, the sidebar shows a quiet "filters unavailable" note, counted by
  `DISCOVERY_FACETS_DEGRADED` (informational chrome). All visitor input is coerced/clamped at the
  view boundary: `q` stripped + truncated to `discovery_query_max_length()` (blank ⇒ browse); an
  unknown/retired/non-UUID `tag` or `cluster` is **ignored** (no stale filter, no 500, AC3); a
  non-int / out-of-range `page` clamps to `[1, last_page]`. A well-formed request is **always
  `200`**, including zero results and an empty catalogue (AC7).
- **The `catalogue.html` 5-state contract** ([DESIGN §6.4](DESIGN.md)) — Results (cards: name,
  truncated description, first media thumbnail with `alt_text`, resolved tag chips; each card a
  link to `pages:app-page app.id` (AC4); prev/next pagination + "page X of Y"; the facet sidebar +
  a search box reflecting `q`) · Zero-results (200 + clear-filters link) · Empty-catalogue (200 +
  placeholder) · Facet-degraded (soft) · Error (loud 500). Semantic, keyboard-navigable markup
  carrying D-6 media `alt_text` (C7).
- **Shared-surface touches** — three config tunables in `apps/core/config.py`
  (`discovery_page_size()` default 24, `discovery_page_size_max()` default 100,
  `discovery_query_max_length()` default 200, all covered by the existing `validate_all()`); six
  metric constants in `apps/core/observability.py` (§7 below); `apps.discovery` +
  `django.contrib.postgres` added to `INSTALLED_APPS`; the
  `path("discover/", include("apps.discovery.urls"))` **activation switch** in `config/urls.py`.
  **No new `.env` key.** `apps/catalog` and `apps/taxonomy` gain only additive read surfaces — the
  full `apps.catalog` (142) and `apps.taxonomy` suites stay green.

> **One implementation note (no contract change), logged in [DECISIONS.md](DECISIONS.md):** the
> tag filter uses `id IN Subquery(...)` rather than a join + `.distinct()`, to avoid the Postgres
> `SELECT DISTINCT` + `ORDER BY SearchRank(...)` conflict (`DISTINCT` requires the ORDER BY
> expression in the select list). Same contract, same result set, same neutral order — an
> internal SQL-shape choice, not a behavior change.

## 3. Who is affected

- **Anyone, signed-out included** — can now reach `/discover/` to browse the full accepted
  catalogue (newest-accepted-first), keyword-search it, filter it by an interest tag or cluster,
  and click through to any app's app-page. **No login wall at any step** (AC8); signing in changes
  nothing about what is shown (the open surface is identical for everyone — personalization is out
  of scope, `weekly-digest`'s job).
- **Developers** — an accepted app now has a **non-digest path to being discovered**, on equal
  footing, ordered only by neutral published signals (recency / keyword relevance) — visibility
  here is **earned, never purchasable** (S5 / AC5).
- **The platform / the integrity premise** — the **open-access half** of "anyone can find and
  access any app" (vision §4.1) is now live alongside the already-enforced closed half (the D-8
  curated-rating gate). A search/browse exposure **cannot** leak into the curated gate (AC6 / R1).
- **Analysts** — **M2 (discovery click-through)** is **derived, not emitted here**: a click that
  lands on an app-page is already captured by app-pages as a **non-curated `APP_PAGE`** impression
  (D-7); the analyst joins page-view signals to discovery traffic (thin until traffic). **M3
  (zero-result rate)** reads the `DISCOVERY_ZERO_RESULTS` counter. **M4 (latency)** reads request
  timing. **M1/M5/M6** are structural (§7).
- **`catalog` / `taxonomy` (closed features)** — gained additive, contract-preserving read
  surfaces only; their existing selectors/DTO are unchanged. **Future `weekly-digest` / matcher /
  Quality-Score work** inherits `search_catalogue` and `tag_ids_resolving_to` as stable,
  additive-only contracts.
- **Support** — no support-facing change at this release (local/dev target).

## 4. How to use it (operators)

The rollout is the ordered, additive steps from [DESIGN §16](DESIGN.md) — no new env var, no
feature flag, no recurring job:

1. `python manage.py migrate catalog` — applies, in order, **`catalog/0002`** (the two additive
   nullable columns + the `(status,-accepted_at)` composite index + the `search_vector` GIN; also
   pulls in `django.contrib.postgres`) then **`catalog/0003`** (the one-off backfill of both
   columns for existing accepted apps from their latest accept `ReviewDecision` + the shared FTS
   expr). Both columns are nullable and additive — every existing row is valid before backfill.
2. `python manage.py check` — must report no issues before the surface is considered live.
3. Deploy the build (which includes `apps.discovery` + `django.contrib.postgres` in
   `INSTALLED_APPS` and the `path("discover/", include("apps.discovery.urls"))` activation switch
   in `config/urls.py`). `/discover/` — browse, search, tag/cluster filter, app-page links — goes
   live on deploy.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with every prior feature
> (`identity-accounts` … `interest-profile`, [CONTROL.md](../../CONTROL.md)); the platform is
> still mid-development. The feature is verified locally (**676 tests green**, `ruff`/`check`/no
> drift, `catalog/0002`+`0003` apply and reverse cleanly). **Production promotion and a
> live-metrics monitoring window are deferred** until there is a production target and real
> traffic.

This is an **additive surface**: the new app changes nothing existing, and the two catalog columns
are nullable additions, so there is **no pre-existing behavior to ramp against and nothing to
feature-flag off** (an honest deviation from the internal→%→full template — DESIGN §16). Safety
comes from the **one-line activation switch** + the **reversible additive migrations**, not a kill
switch. **"Off" = remove the `config/urls` `discover/` include** (zero data migration; the two
columns then sit inert with no consumer and are droppable later by reversing `0002`/`0003`).
Backward-compatible: with the surface off, the rest of the site renders exactly as today and the
inert columns are ignored.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate catalog` applied through `0003`; `catalog_app.accepted_at` + `search_vector` (both nullable) and the `catalog_app_status_acc_idx` + `catalog_app_search_gin` indexes present; `django.contrib.postgres` loaded; `manage.py check` clean. |
| Backfill correct | existing accepted apps have `accepted_at` = their latest accept `ReviewDecision.created_at` and a populated `search_vector`; a never-accepted app stays `NULL` (and is never listed). |
| Surface live | `discovery:browse` resolves at `/discover/`; an **anonymous** GET renders browse (newest-accepted-first), keyword search, and a tag/cluster filter; result cards link to `pages:app-page`; pagination works. |
| Read primitive correct | `search_catalogue` returns ACCEPTED-only (AC1), name/desc keyword matches ranked excluding non-match/non-accepted (AC2), tag-set carriers deduped (AC3), keyword∧tag composed; **query count constant at 5 vs 50 apps** (AC9); the ORDER BY contains only `rank`/`accepted_at`/`id` — no paid/tier/score key (AC5/M5). |
| Segregation correct | `apps/discovery/` imports no `signals` (AC6, AST-asserted); a discovery click is captured only as a non-curated `APP_PAGE` impression. |
| Display correct | zero-result and empty-catalogue states render `200` (AC7); a retired/unknown `tag`/`cluster` is ignored with no 500 (AC3); `discovery_facets_degraded` reads 0. |
| Stable at target | the above holds with no sustained `discovery_listing_degraded` spike through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**One surface touch** ([DESIGN §11/§16](DESIGN.md)):

1. Remove the `path("discover/", include("apps.discovery.urls"))` line from `config/urls.py` — the
   `/discover/` surface is gone with **zero data migration** (mirrors app-pages). The two
   `catalog_app` columns become inert additive data with no consumer.

If the schema must also be undone — a **deliberate cleanup, not an emergency step** (the columns are
nullable and harmless when unread):

```bash
python manage.py migrate catalog 0001   # reverses 0003 (clears both columns) then 0002 (drops columns + both indexes)
```

Because the surface **emits no D-7 corpus events**, there is **nothing in another app's store to
unwind** — the rollback is fully contained to the `config/urls` line, plus optionally the two
catalog columns. The maintenance hooks in `accept_app`/`submit_app`/`edit_app` keep writing the
columns even with the surface off (harmless, keeps them backfill-free if re-activated); removing
them is part of the deliberate column-drop cleanup, not the emergency rollback.

**Rehearsed 2026-06-23** on a throwaway PostgreSQL database (`osb_release_rehearsal`, dropped
afterward): `migrate` applied `catalog/0002` then `catalog/0003` → both nullable columns
(`accepted_at` timestamptz, `search_vector` tsvector) and both indexes (`catalog_app_status_acc_idx`,
`catalog_app_search_gin`) confirmed present → `manage.py check` clean → `migrate catalog 0001`
**unapplied both cleanly** (columns and indexes confirmed gone) → re-`migrate catalog` **re-applied**
them (confirmed reversible **up→down→up**) → `discovery:browse` resolves at `/discover/`;
`makemigrations --check` reports no drift. **Who can trigger:** any operator with deploy access (the
one `config/urls` line) — the optional DB column-drop additionally needs DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; the six new constants live in
`apps/core/observability.py`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| **M1 open-access coverage (target 100%)** | **Structural** — `search_catalogue` lists **all** accepted apps; a property test asserts every accepted app is reachable across pages. `discovery_browse_rendered` / `discovery_search_performed` / `discovery_tag_filtered` track surface usage. | Trend, not an alert (coverage is by construction). |
| **M2 discovery click-through** | **Derived, no new emit** — a discovery click lands on an app-page, captured by app-pages as a non-curated `APP_PAGE` D-7 impression; analyst joins page-views to discovery traffic. | None in this layer (analyst-derived; thin until traffic). |
| **M3 zero-result rate** | `discovery_zero_results` — incremented when a keyword/filter query returns `total == 0`. | Trend — a sustained rise = vocabulary/coverage mismatch (analyst signal, not a page). |
| **M4 listing/search latency** | request timing via the existing logging/observability path. | Watched, not alerted unless degraded. |
| **M5 position-neutrality audit (= 0)** | **Structural + test-enforced** — the ORDER BY contains only `rank`/`accepted_at`/`id`; a test asserts no paid/tier/score field participates. There is **no purchasable input to count**, so this is a guarantee, not a runtime counter. | A non-zero would mean the premise leaked — but it is unrepresentable by construction. |
| **M6 catalogue freshness lag** | **~immediate** — `accepted_at` is stamped inside the accept transaction, so an app appears on the next query; an accept→visible test asserts it. | None (structural). |
| **Read display health** | `discovery_facets_degraded` — the facet sidebar fell back to its soft "filters unavailable" state (results still rendered). | Informational — a sustained rise means a taxonomy facet read is unhealthy; the listing is unaffected. |

**The one actionable alert:** `discovery_listing_degraded` — the **core results read raised** (the
page 500s). That is an **outage of the open surface** (and, because the read fails loud, it is never
masked as a fake empty state). `discovery_facets_degraded` (chrome), `discovery_zero_results`
(analyst signal), and latency are **not** pages.

## 8. Verification at release (2026-06-23)

- **676 automated tests pass** (616 baseline + 60 new open-search-browse tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model drift.
- Rollout→rollback **rehearsed** on a throwaway PostgreSQL DB (§6): `migrate` applied
  `catalog/0002` + `catalog/0003` (both nullable columns + the `(status,-accepted_at)` composite
  index + the `search_vector` GIN confirmed present) → `check` clean → `migrate catalog 0001`
  reversed both cleanly (columns + indexes confirmed gone) → re-`migrate catalog` re-applied them
  (reversible **up→down→up**) → no drift. Throwaway DB dropped after.
- `discovery:browse` resolves at `/discover/`; the six observability constants
  (`discovery_browse_rendered` / `_search_performed` / `_tag_filtered` / `_zero_results` /
  `_facets_degraded` / `_listing_degraded`) and the three config tunables (`discovery_page_size` /
  `discovery_page_size_max` / `discovery_query_max_length`, all under `validate_all()`) exist; the
  single `config/urls` `discover/` activation include and `django.contrib.postgres` +
  `apps.discovery` in `INSTALLED_APPS` are present.
- The **risk-centerpiece assertions** hold: `search_catalogue` query count is **constant at 5 vs 50
  apps** (AC9 — no N+1), and the **ORDER-BY-neutrality** test confirms no paid/tier/score key (AC5/M5).
  The **AC6 no-`signals`-import** is AST-asserted. Tested against the **real D-5/D-6 surfaces** (no
  selector mocking); the additive catalog/taxonomy changes leave the full `apps.catalog` (142) and
  `apps.taxonomy` suites green. [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 (+ M1/M3/M5/M6) to
  tests, with edge/security/failure/regression coverage.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §8/§14/§16](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **No first-party discovery signal — M2 is indirect (OQ-OSB-3 / OSB-DESIGN-5).** The surface emits
  **no D-7 event**; click-through is derived from app-pages' existing `APP_PAGE` impressions. This
  *strengthens* AC6 (nothing to mis-segregate) but makes M2 indirect until a non-curated
  `Surface.SEARCH` emit ships. That seam is **named, not built** — revisit once M2 needs first-party
  measurement.
- **Search is name + description only (OQ-OSB-4).** No tag-label, fuzzy/typo, or semantic search —
  the FTS covers `name`(A) + `description`(B). Named as the later path if the zero-result rate (M3)
  runs high; the search field list lives in one function (`_search_vector_expr`) for cheap change.
- **Single-axis tag/cluster filter — no boolean/faceted composition.** `tag` and `cluster` are
  mutually exclusive (if both arrive, `tag` wins); multi-tag boolean, platform/price facets, and
  sort controls are explicitly out of scope. Keyword ∧ a single tag/cluster compose (AND).
- **OFFSET pagination, not keyset (OSB-DESIGN / §14).** Boring and sufficient for MVP browse depth;
  deep-page O(offset) is a documented future swap to keyset **behind the same `CatalogPage`
  contract** — no caller change.
- **Reverse tag resolution is per-query, bounded by vocabulary size.** `tag_ids_resolving_to` walks
  merge predecessors (small reference data), not catalogue size — an explicit, acceptable bound; a
  recursive CTE replaces the walk behind the same signature if the vocabulary ever grows huge.
- **No live-metrics window measured.** Deferred with the local/dev target until a production target
  and real traffic exist (mirrors the eight prior closed-out features).

## 10. Stakeholder notification

On the first real (production) promotion: notify downstream feature owners that the **open-access
half of the integrity premise is live** — anyone, signed-out included, can now browse / keyword-search
/ interest-filter the accepted catalogue at `/discover/` and reach any app-page, in a neutral,
non-purchasable order that confers no curated-rating eligibility (AC5/AC6). Hand the future
`weekly-digest` / matcher / Quality-Score work its inheritance: the **paginated, neutral**
`catalog.selectors.search_catalogue(...) -> CatalogPage` and the reverse-resolution
`taxonomy.selectors.tag_ids_resolving_to(active_id)` are **stable, additive-only** read contracts.
Remind analysts that **M2 (click-through) is theirs to derive** by joining app-pages' non-curated
`APP_PAGE` impressions to discovery traffic — **nothing new is emitted here** (AC6). No support-facing
change at this release — the local/dev target carries no production traffic.
