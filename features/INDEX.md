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
| [interest-profile](interest-profile/) | 2 User loop | backlog | 2026-06-13 | H1 | identity-accounts, interest-taxonomy | _backlog_ |
| [weekly-digest](weekly-digest/) | 2 User loop | backlog | 2026-06-13 | H1 | editorial-curation-tools, app-pages, signal-capture | _backlog_ |
| [ratings-reviews](ratings-reviews/) | 2 User loop | closed-out | 2026-06-21 | H1, H3 | app-pages, signal-capture | _released local/dev ([RELEASE_NOTES.md](ratings-reviews/RELEASE_NOTES.md); new app `apps/ratings/` owning one mutable table `ratings_rating` + one additive index on signals; established global **D-8** curated-rating gate ("curated = a `DIGEST` impression"); 486 tests green; rollout→rollback rehearsed up→down→up); Stage 6 retrospective skipped per user — build re-verified (486 tests / ruff / check / no drift); outcome review deferred/reopenable until a prod target/traffic + a `DIGEST` emitter exist_ |
| [open-search-browse](open-search-browse/) | 2 User loop | backlog | 2026-06-13 | enabler / H3 | app-pages | _backlog_ |
| [app-subscriptions](app-subscriptions/) | 2 User loop | `5-release` | 2026-06-21 | H1 (feeds H3) | app-pages, identity-accounts, signal-capture | _active — **built T-01…T-08 (552 tests green, +66; `ruff`/`check`/no drift)**. New app `apps/subscriptions/` owning one mutable table `subscriptions_subscription` (near-twin of `apps/ratings/`) with three deliberate contrasts: deletion **CASCADE**s (AS-5/AC9), the follow-write + its one `subscribe` emit are **one `transaction.atomic()`** (M5 1:1 by construction, forced-failure rollback verified), and an empty-until-producer notice seam (AS-3=A). Shipped: additive bulk `catalog.get_catalogued_apps(ids)` (no N+1), the `Subscription` store + migration, `services.follow_app`/`unfollow_app`, `selectors.is_following`/`followed_apps`, `notices.Notice`+`notices_for_apps`→`[]`, thin `follow`/`unfollow`/`feed` views + `feed.html` + the `subscriptions/` include, the `{% app_follow %}` Follow slot (one `app_page.html` section), read-only admin + README/CODEMAP/DECISIONS. [TEST_PLAN.md](app-subscriptions/TEST_PLAN.md) maps AC1–AC9. Migration `0001` rehearsed up→down→up. Now with the Release Engineer_ |
| [developer-dashboard](developer-dashboard/) | 3 Dev value | backlog | 2026-06-13 | H2 | signal-capture, ratings-reviews | _backlog_ |
| [developer-updates](developer-updates/) | 3 Dev value | backlog | 2026-06-18 | H2 | app-subscriptions, app-pages, signal-capture | _backlog — net-new from signal-capture SC-7/SC-8 (OQ-4): developer-side channel (post updates / early-access / talk to subscribers) — platform as the dev's front page_ |

> Stage values: see the routing table in [../CLAUDE.md](../CLAUDE.md) §2. `backlog` is a
> pre-pipeline holding state, not a canonical pipeline stage.
