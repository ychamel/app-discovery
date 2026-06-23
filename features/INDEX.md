# features/INDEX.md — Feature Registry

**Every feature ever started is listed here, once.** [CONTROL.md](../CONTROL.md) tracks
*where we are now* (the active feature); this file is the answer to *"have we built
anything about X, and where is it?"* — findability that a single active-feature dashboard
can't give you at volume.

Maintained by the **Coordinator** (adds a row when a feature folder is created) and the
**Retrospective Analyst** (fills in the outcome when a feature reaches `done`).

## Registry

Listed in dependency-build order (breakdown §5), grouped by phase — more useful for a
backlog than newest-first. Keep each outcome to one line; detail lives in the feature
folder.

**`backlog`** = folder + the 7 artifacts scaffolded by the Coordinator from
[../docs/mvp-component-breakdown.md](../docs/mvp-component-breakdown.md), but **not yet
entered Stage 1**. Activating one (set `Stage: 1-define` in [../CONTROL.md](../CONTROL.md))
is decision **D2** and belongs to the user.

| Slug | Phase | Stage | Started | Proves | Depends on | One-line outcome |
|------|-------|-------|---------|--------|------------|------------------|
| [identity-accounts](identity-accounts/) | 0 Foundation | closed-out | 2026-06-13 | enabler | — | _released local/dev (108 tests green); Stage 6 retrospective skipped per user — outcome review deferred/reopenable_ |
| [interest-taxonomy](interest-taxonomy/) | 0 Foundation | closed-out | 2026-06-17 | enabler | — | _released local/dev (11 clusters / 67 tags, 184 tests green; rollback rehearsed); Stage 6 retrospective skipped per user (DN-1 A) — live-metrics/real-catalog coverage + outcome report deferred/reopenable_ |
| [signal-capture](signal-capture/) | 0 Foundation | closed-out | 2026-06-18 | H3 | identity-accounts | _released local/dev ([RELEASE_NOTES.md](signal-capture/RELEASE_NOTES.md), apps/signals, 374 tests green; rollout→rollback rehearsed); established global D-7 event-schema contract; Stage 6 retrospective skipped per user (DN-7 A) — outcome review needs a live emitter (weekly-digest), deferred/reopenable_ |
| [submission-intake](submission-intake/) | 1 Catalog | closed-out | 2026-06-17 | H2 | identity-accounts, interest-taxonomy | _released local/dev (apps/catalog, 315 tests green; rollout→rollback rehearsed); established global D-6 catalogued-app contract; Stage 6 retrospective skipped per user (DN-3 A) — live-metrics/outcome report deferred/reopenable_ |
| [app-pages](app-pages/) | 1 Catalog | closed-out | 2026-06-20 | H1, H2 | submission-intake | _released local/dev ([RELEASE_NOTES.md](app-pages/RELEASE_NOTES.md); new app `apps/pages/`, pure D-6/D-7 consumer owning no model/migration; 3 thin views + `app_page` template; 417 tests green; rollout→rollback rehearsed — primary rollback = remove the `config/urls` include, zero data migration); first live emitter of D-7 `app_page` impressions (AP-3/4/5); Stage 6 retrospective skipped per user — build re-verified (417 tests / ruff / check / no drift); outcome review deferred/reopenable until a prod target/traffic exists_ |
| [editorial-curation-tools](editorial-curation-tools/) | 1 Catalog | backlog | 2026-06-13 | H1, H3 | interest-taxonomy, submission-intake, weekly-digest | _backlog_ |
| [interest-profile](interest-profile/) | 2 User loop | closed-out | 2026-06-22 | H1 | identity-accounts, interest-taxonomy | _released local/dev ([RELEASE_NOTES.md](interest-profile/RELEASE_NOTES.md); new app `apps/interests/` owning one mutable table `interests_interest` — the user side of the Ring-0 match via the `declared_tag_ids` matcher contract (AC8); **no parent row** → empty=structural default AC6, **CASCADE** user FK AC9; §7 set-replace **preserve-on-edit** reconcile (AC4 × AC7/M5=0); **no `signals.capture` import** (IP-5); two-part activation switch, no flag; 616 tests green; rollout→rollback rehearsed up→down→up). Stage 6 retrospective skipped per user — build re-verified (616 tests / ruff / check / no drift); outcome review deferred/reopenable until a prod target/traffic + a matcher/digest consumer exist_ |
| [weekly-digest](weekly-digest/) | 2 User loop | backlog | 2026-06-13 | H1 | editorial-curation-tools, app-pages, signal-capture | _backlog_ |
| [ratings-reviews](ratings-reviews/) | 2 User loop | closed-out | 2026-06-21 | H1, H3 | app-pages, signal-capture | _released local/dev ([RELEASE_NOTES.md](ratings-reviews/RELEASE_NOTES.md); new app `apps/ratings/` owning one mutable table `ratings_rating` + one additive index on signals; established global **D-8** curated-rating gate ("curated = a `DIGEST` impression"); 486 tests green; rollout→rollback rehearsed up→down→up); Stage 6 retrospective skipped per user — build re-verified (486 tests / ruff / check / no drift); outcome review deferred/reopenable until a prod target/traffic + a `DIGEST` emitter exist_ |
| [open-search-browse](open-search-browse/) | 2 User loop | `4-build` | 2026-06-23 | enabler / H3 | app-pages | _**active** — Phase-2 open discovery surface: browse / keyword-search / interest-filter the D-6 accepted-app catalogue → app-page, **money never buys position** (vision §4.1). [DESIGN.md](open-search-browse/DESIGN.md) **APPROVED** (DN-18) → [TASKS.md](open-search-browse/TASKS.md) decomposed into **7 ordered tasks (all S/M, no L)**: T-01 additive `catalog_app.accepted_at` + `search_vector` columns/indexes + `django.contrib.postgres` → T-02 write-path maintenance (`_search_vector_expr`, `accept_app` stamp, `submit_app`/`edit_app` FTS) → T-03 backfill data migration → T-04 reverse-resolution `taxonomy.tag_ids_resolving_to` (AC3) → **T-05 the risk centerpiece** paginated DB-pushed `catalog.search_catalogue -> CatalogPage` (no-N+1 + ORDER-BY neutrality, AC9/AC5) → T-06 model-less `apps/discovery/` + `config/urls` include (the activation switch; no `signals` import = AC6) → T-07 docs/CODEMAP. Reuses D-3/D-5/D-6/D-7/D-8 — no new global ADR. Handed to **Senior Engineer** (build T-01 first, produce TEST_PLAN.md)_ |
| [app-subscriptions](app-subscriptions/) | 2 User loop | closed-out | 2026-06-21 | H1 (feeds H3) | app-pages, identity-accounts, signal-capture | _released local/dev ([RELEASE_NOTES.md](app-subscriptions/RELEASE_NOTES.md)); new app `apps/subscriptions/` owning one mutable table `subscriptions_subscription` (near-twin of `apps/ratings/`) with three deliberate contrasts: deletion **CASCADE**s (AS-5/AC9), the follow-write + its one `subscribe` emit are **one `transaction.atomic()`** (M5 1:1 by construction), and an empty-until-producer notice seam (AS-3=A); **no feature flag** (activation = the `config/urls` `subscriptions/` include + the one `app_page.html` Follow section); 552 tests green; rollout→rollback rehearsed up→down→up. Stage 6 retrospective skipped per user — build re-verified (552 tests / ruff / check / no drift); outcome review deferred/reopenable until a prod target/traffic + a `developer-updates` notice producer exist_ |
| [developer-dashboard](developer-dashboard/) | 3 Dev value | backlog | 2026-06-13 | H2 | signal-capture, ratings-reviews | _backlog_ |
| [developer-updates](developer-updates/) | 3 Dev value | backlog | 2026-06-18 | H2 | app-subscriptions, app-pages, signal-capture | _backlog — net-new from signal-capture SC-7/SC-8 (OQ-4): developer-side channel (post updates / early-access / talk to subscribers) — platform as the dev's front page_ |

> Stage values: see the routing table in [../CLAUDE.md](../CLAUDE.md) §2. `backlog` is a
> pre-pipeline holding state, not a canonical pipeline stage.
