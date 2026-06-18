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
| [app-pages](app-pages/) | 1 Catalog | backlog | 2026-06-13 | H1, H2 | submission-intake | _backlog_ |
| [editorial-curation-tools](editorial-curation-tools/) | 1 Catalog | backlog | 2026-06-13 | H1, H3 | interest-taxonomy, submission-intake, weekly-digest | _backlog_ |
| [interest-profile](interest-profile/) | 2 User loop | backlog | 2026-06-13 | H1 | identity-accounts, interest-taxonomy | _backlog_ |
| [weekly-digest](weekly-digest/) | 2 User loop | backlog | 2026-06-13 | H1 | editorial-curation-tools, app-pages, signal-capture | _backlog_ |
| [ratings-reviews](ratings-reviews/) | 2 User loop | backlog | 2026-06-13 | H1, H3 | app-pages, signal-capture | _backlog_ |
| [open-search-browse](open-search-browse/) | 2 User loop | backlog | 2026-06-13 | enabler / H3 | app-pages | _backlog_ |
| [app-subscriptions](app-subscriptions/) | 2 User loop | backlog | 2026-06-18 | H1 (feeds H3) | app-pages, identity-accounts, signal-capture | _backlog — net-new from signal-capture SC-7/SC-8 (OQ-4): user-side engagement loop (follow apps + update/early-access notices) that generates the on-platform signal the corpus measures_ |
| [developer-dashboard](developer-dashboard/) | 3 Dev value | backlog | 2026-06-13 | H2 | signal-capture, ratings-reviews | _backlog_ |
| [developer-updates](developer-updates/) | 3 Dev value | backlog | 2026-06-18 | H2 | app-subscriptions, app-pages, signal-capture | _backlog — net-new from signal-capture SC-7/SC-8 (OQ-4): developer-side channel (post updates / early-access / talk to subscribers) — platform as the dev's front page_ |

> Stage values: see the routing table in [../CLAUDE.md](../CLAUDE.md) §2. `backlog` is a
> pre-pipeline holding state, not a canonical pipeline stage.
