# CONTROL.md — Project Control Board

**This is the durable channel between the user and the agent.** It replaces chat
memory. The agent reads it first every session and updates it last. The user checks
this one file to know *where we are* and *what is waiting on a decision*.

Rules:
- The agent **must not** act on a question listed under *Decisions Needed From You*
  until the user answers it here.
- Every work session ends by updating *Current State* and the *Activity Log*.
- Keep it short and current. Detail lives in the feature artifacts, not here.

---

## Current State

| Field              | Value                                                            |
|--------------------|------------------------------------------------------------------|
| **Active feature** | `signal-capture`                                                 |
| **Stage**          | `2-design`                                                       |
| **Persona**        | Software Architect (see [phase-2-architect.md](process/personas/phase-2-architect.md)) |
| **Folder**         | [features/signal-capture/](features/signal-capture/)             |
| **Last updated**   | 2026-06-18 — **FEATURE_BRIEF.md APPROVED** (DN-5 → A; SC-6 privacy posture ratified by the approval). Spine pivoted to on-platform engagement (SC-7/SC-8). Incentive surfaces logged as two backlog features — `app-subscriptions`, `developer-updates` (OQ-4 resolved). **Handed to the Software Architect for Stage 2** (event schema = repo-wide, near-irreversible decision). |

> **Closed out (Stage 6 skipped, reopenable):** `identity-accounts` (2026-06-17, 108
> tests), `interest-taxonomy` (2026-06-17, 184 tests), and `submission-intake`
> (2026-06-18, 315 tests) — all released local/dev, rollback rehearsed; live-metrics +
> outcome reports deferred until a consumer/prod target exists.

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 2-design | Feature: signal-capture | Persona: Software Architect (handed off this session by the Product Analyst)
Done: FEATURE_BRIEF.md APPROVED by the user (DN-5 → A); SC-6 privacy posture ratified by the approval
      (pseudonymous in-platform events keyed to Account.id, ToS consent, no auto-purge). Earlier this
      session the brief's spine was pivoted to on-platform engagement (SC-7/SC-8). Then, at the user's
      request, logged the incentive surfaces as TWO new backlog features: `app-subscriptions` (Phase 2,
      user-side — follow apps + update/early-access notices) and `developer-updates` (Phase 3,
      developer-side — post updates / early-access / talk to subscribers; early-access folded in, not
      split). Both scaffolded with the 7 standard artifacts + scope seed citing their provenance
      (signal-capture SC-7/SC-8, OQ-4); INDEX.md rows added; OQ-4 marked resolved; SC-8 updated.
Verified by: n/a (Stage-1 artifacts + backlog scaffolding only; no code).
Blocked/Deferred: none blocking. For Stage 2 (Architect): the event SCHEMA is a repo-wide,
      near-irreversible decision — design it and record it in the global /DECISIONS.md, not feature-local
      (breakdown §4.5, signal-capture R2). The off-platform proxy (OQ-1) is now SECONDARY — design a seam,
      do not over-build. The two new backlog features emit into this schema; design the capture contract
      so they (and weekly-digest/app-pages/ratings-reviews) call one write path (brief A5).
Decisions needed: none.
Next: Software Architect reads features/signal-capture/FEATURE_BRIEF.md + the codebase and writes
      features/signal-capture/DESIGN.md (event schema as a global decision; the on-platform capture contract).
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

| ID | Decision needed | Context | Answer |
|----|-----------------|---------|--------|
| _(none open)_ | — | — | — |

> Resolved decisions (DN-1 … DN-5) are summarized under *Decisions Made* below; full
> rationale lives in the decision logs.

---

## Decisions Made (recently)

A short, human-readable digest. Full rationale lives in [DECISIONS.md](DECISIONS.md)
(global) or `features/<slug>/DECISIONS.md` (local).

- **DN-5 → A (2026-06-18)** — **`signal-capture` FEATURE_BRIEF.md approved**; the SC-6 privacy posture (pseudonymous in-platform events keyed to `Account.id`, ToS consent, no auto-purge for the H3 backtest) **ratified by the approval**. Advanced to `2-design`; handed to the Software Architect (event schema = repo-wide decision). Same session: logged the incentive surfaces as two new backlog features — **`app-subscriptions`** (Phase 2) and **`developer-updates`** (Phase 3) — scaffolded + added to [INDEX.md](features/INDEX.md); OQ-4 resolved (SC-8).
- **SC-7/SC-8 (2026-06-18, user review)** — **`signal-capture` brief spine PIVOTED to on-platform engagement.** User's call: we can't track off-platform behavior, so measure observable on-platform signal and incentivize users/devs onto the platform rather than chase a lossy proxy. Captured spine is now impression→click-through→**return-to-platform(3d/14d)**→**subscribe/follow**→**on-page re-engagement**→share (all directly observed, more faithful to vision Open Q #4); off-platform open/return demoted to best-effort **secondary** (R1 High→Low). The incentive surfaces that generate the signal (subscriptions, dev↔user comms, early access) are held **out of scope** (CLAUDE.md §6.4) and logged as **OQ-4** for the Coordinator. Brief revised; still awaiting final approval + SC-6 (DN-5).
- **DN-4 → A (2026-06-18)** — **`signal-capture` activated** as the next feature (Phase-0, the last Foundation enabler; deps `identity-accounts` met). Chosen over `app-pages` to finish Phase 0 before widening. Set `Stage: 1-define`; scaffold already present; handed to Product Analyst.
- **DN-3 → A (2026-06-18)** — `submission-intake` **closed out**; Stage-6 retrospective **skipped** (outcome review deferred/reopenable when a consumer + live metrics exist — mirrors `identity-accounts` and DN-1/`interest-taxonomy`). Returned to Coordinator. Raised **DN-4** to pick the next feature (`signal-capture` vs `app-pages` — both now have all dependencies met).
- **Release-SI (2026-06-18)** — `submission-intake` **released to local/dev**. [RELEASE_NOTES.md](features/submission-intake/RELEASE_NOTES.md) written (changes, downstream D-6 action, operator rollout, gate-based promotion, success-metric→signal→alert map, known limits). Rollout→rollback **rehearsed on a throwaway Postgres DB**: migrate → 4 `catalog_*` tables + shared `citext` → `check` clean → `migrate catalog zero` reverses to 0 tables (`citext` retained) → re-apply (reversible). **315 tests / ruff / check / no-drift** re-verified. Live-metrics window deferred (no consumer/prod target). Advanced to `6-post-release`; **DN-3** raised (run Stage 6 now vs skip, as DN-1).
- **Build-SI (2026-06-18)** — `submission-intake` **built (T-01…T-14), 131 new tests / 315 total green**, ruff clean, no migration drift, reversibility rehearsed. New app `apps/catalog` (4 tables; fixed 5-floor gate enum, no "other"; single write/read paths; ACCEPTED-only D-6 catalogue substrate; developer+review API and pages; decision emails; admin inspection). Reused accounts gate + taxonomy D-5 + core as-is; added 2 media tunables + Pillow + MEDIA_ROOT. CODEMAP + README + .env.example + [TEST_PLAN.md](features/submission-intake/TEST_PLAN.md) (AC1–AC9) done; global **D-6** confirmed. Stage-4 deviations logged **SI-8…SI-11** in [features/submission-intake/DECISIONS.md](features/submission-intake/DECISIONS.md). Advanced to `5-release` / Release Engineer.
- **Plan-SI (2026-06-17)** — `submission-intake` [TASKS.md](features/submission-intake/TASKS.md) **complete** (14 ordered S/M tasks, no `L`). Risk-first per DESIGN §13: gate no-"other" enum (T-02), write-service invariants (T-05), decision atomicity + lifecycle (T-06), accepted-only catalog/D-6 (T-07) all precede the HTTP/UI tasks. Write path / HTTP surface / pages each split to stay off `L`. Full DESIGN-element + AC1–AC9 coverage table. Advanced to Stage 4; handed to Senior Engineer.
- **Design-SI (2026-06-17)** — `submission-intake` [DESIGN.md](features/submission-intake/DESIGN.md) **approved**. New Django app `apps/catalog/` reusing the accounts gate + taxonomy `is_valid_tag`/`resolve_tag` (D-5) + core email/observability/config (no new stack). Gate = fixed 5-floor code enum with **no "other"** → taste rejection (R1/AC6) unrepresentable; lifecycle state machine; FIFO queue, zero pay/tier/priority fields (AC3). Recorded global **[D-6](DECISIONS.md)** (catalogued-app contract: accepted `App.id` read only via `list_catalogued_apps`/`get_catalogued_app`). OQ-2/OQ-3 resolved in the design. Advanced to Stage 3; handed to Planner.
- **A-SI (2026-06-17)** — `submission-intake` brief **approved**; the 7 confirmation calls logged as **SI-1…SI-7** in [features/submission-intake/DECISIONS.md](features/submission-intake/DECISIONS.md) (web-only app=URL; human/admin checklist gate with no MVP automation; rejection non-terminal; individual ownership; offline founding-catalog recruitment → closes OQ-1; metadata-correction in / versioned-updates out; media=screenshots aligned to `app-pages`). Advanced to Stage 2; handed to Software Architect.
- **Release (2026-06-17)** — `interest-taxonomy` **released to local/dev**. [RELEASE_NOTES.md](features/interest-taxonomy/RELEASE_NOTES.md) written; rollout→rollback **rehearsed on a scratch DB** (migrate → seed 11/67 → check exit 0 → idempotent re-seed → `migrate taxonomy zero` drops 3 tables, keeps shared `citext`). 184 tests / ruff / check / no-drift re-verified. Live-metrics window deferred (no consumer/prod target yet). Stage-6 retrospective awaiting **DN-1** (run-now vs skip, as identity-accounts did). Advanced to `6-post-release`.
- **Build (2026-06-17)** — `interest-taxonomy` **built (T-01…T-10), 76 new tests / 184 total green**. Stage-4 deviations logged in [features/interest-taxonomy/DECISIONS.md](features/interest-taxonomy/DECISIONS.md): **ITX-9** (unauth read = `403` not `401`; DESIGN §5c corrected), **ITX-10** (PyYAML dep for the seed file), **ITX-11** (added `update_tag`/`update_cluster` sync setters; DESIGN §5b), **ITX-12** (founding size band 11 clusters / 67 tags, closes OQ-3). Handed to Release Engineer.
- **A4/A5 (2026-06-17)** — `interest-taxonomy` brief + [DESIGN.md](features/interest-taxonomy/DESIGN.md) **approved** (flat tags + named clusters via M2M; UUID stable identity; soft-retire + read-time `resolve_tag`; seed-file/command/admin management). Logged **ITX-1…ITX-5**; decomposed into [TASKS.md](features/interest-taxonomy/TASKS.md).

> **Foundational decisions** (`identity-accounts`, the stack, niche, build order — D1–D3,
> A1–A3, R1, DL-1/2, PL-1, global D-1/D-2/D-4) are recorded in [DECISIONS.md](DECISIONS.md)
> and the per-feature `DECISIONS.md` files. Highlights: niche = **"vibecoded webapps"**
> (D-1); stack = **Python / Django + PostgreSQL** (D-4); `identity-accounts` released
> local/dev (R1, 108 tests).

---

## Activity Log

Newest first. One line per session. **Keep the most recent ~10 rows here**; older rows
live in [process/activity-archive.md](process/activity-archive.md). The per-feature
folders remain the full record either way.

| Date       | Stage           | Summary                                                                 |
|------------|-----------------|-------------------------------------------------------------------------|
| 2026-06-18 | `1-define`→`2-design` | **Product Analyst** (hand-off) — **[signal-capture/FEATURE_BRIEF.md](features/signal-capture/FEATURE_BRIEF.md) APPROVED** (DN-5 → A); SC-6 privacy posture ratified by the approval. At the user's request, **logged the incentive surfaces as two new backlog features**: [app-subscriptions](features/app-subscriptions/) (Phase 2 User loop — user follows apps + update/early-access notices; H1, feeds H3) and [developer-updates](features/developer-updates/) (Phase 3 Dev value — dev posts updates/early-access/talks to subscribers; H2). Both scaffolded with the 7 standard artifacts + a scope seed citing provenance (signal-capture SC-7/SC-8, OQ-4); [INDEX.md](features/INDEX.md) rows added; **OQ-4 resolved**, SC-8 updated. Advanced `signal-capture` to **`2-design`** and handed to the **Software Architect** (event schema = repo-wide, near-irreversible decision → global /DECISIONS.md). |
| 2026-06-18 | `1-define`      | **Product Analyst** (brief review w/ user) — **pivoted the [signal-capture/FEATURE_BRIEF.md](features/signal-capture/FEATURE_BRIEF.md) spine to on-platform engagement** (SC-7). The draft hung the corpus on an off-platform funnel carried by a lossy proxy (R1 High/High); the user's steer — can't see off-platform, so measure observable on-platform signal and incentivize staying — is also more faithful to vision Open Q #4 (web-app return visits observed *via the platform*). New captured spine: impression→click-through→**return-to-platform(3d/14d)**→**subscribe/follow**→**on-page re-engagement**→share; off-platform open/return demoted to flagged **best-effort secondary** (R1→High/**Low**). Held the §6.4 line: the **incentive surfaces** (subscriptions, dev↔user comms, early access) that *generate* the signal are OUT (logged **OQ-4** for the Coordinator), not folded in. Rewrote Goal/terms/story 3/AC4–AC11/metrics/scope/A6/R1/R6/vision. Logged **SC-7/SC-8**, revised SC-3, added OQ-4. Brief still awaiting approval + SC-6 (**DN-5**). |
| 2026-06-18 | `1-define`      | **Product Analyst** — drafted [signal-capture/FEATURE_BRIEF.md](features/signal-capture/FEATURE_BRIEF.md): the Phase-0 measurement spine. Problem (capture-before-first-impression or lose the H3 corpus forever; schema-first because every later surface emits/reads it), goal, **7 stories / 10 G-W-T ACs / 6 metrics**, in/out-of-scope, C1–C5 + A1–A5, 5 risks, vision alignment. Defined **what** to capture (impression→click-through→open→return 3d/14d→share; keyed **user × `App.id` × impression**; capture-time `Tag.id` category tags; **raw-not-scored**) and kept the event **schema + attribution mechanism** for Stage 2. Adopted D-1 (web-only → native-install attribution out, click-through-and-return proxy), D-3/D-5/D-6 reference contracts. Logged **SC-1…SC-6** ([DECISIONS.md](features/signal-capture/DECISIONS.md)) + **OQ-1…OQ-3** ([OPEN_QUESTIONS.md](features/signal-capture/OPEN_QUESTIONS.md)). Raised **DN-5** (approve brief + confirm SC-6 privacy posture); awaiting approval before Stage-2 hand-off. |
| 2026-06-18 | `0-coordinator`→`1-define` | **Coordinator** — DN-4 resolved → Option A: **activated `signal-capture`** (Phase-0, last Foundation enabler; deps `identity-accounts` met) over `app-pages`. Scaffold already present from backlog; set `Stage: 1-define`, updated [INDEX.md](features/INDEX.md), handed to **Product Analyst** to draft [FEATURE_BRIEF.md](features/signal-capture/FEATURE_BRIEF.md). |
| 2026-06-18 | `6-post-release`→`0-coordinator` | **Coordinator** — DN-3 resolved → Option A: **`submission-intake` closed out**, Stage-6 retrospective skipped (outcome review deferred/reopenable, mirrors `identity-accounts`/`interest-taxonomy`). All three released features now closed-out. Updated [INDEX.md](features/INDEX.md). Surveyed backlog: with all deps met, **`signal-capture`** (Phase-0, last Foundation enabler) and **`app-pages`** (Phase-1, builds on `submission-intake`) are both available. Raised **DN-4** for the next-feature pick (D2). |
| 2026-06-18 | `5-release`→`6-post-release` | **Release Engineer** — released `submission-intake` to local/dev. Wrote [RELEASE_NOTES.md](features/submission-intake/RELEASE_NOTES.md) (changes, who's affected + the **D-6** action required of downstream, operator rollout, gate-based promotion, success-metric→signal→alert map, rehearsed rollback, known limits). **Rehearsed rollout→rollback on a throwaway Postgres DB**: `migrate` → 4 `catalog_*` tables (`catalog_app`/`_app_tag`/`_app_media`/`_review_decision`) + shared `citext` → `check` clean → `migrate catalog zero` reverses to **0 `catalog_*` tables** (shared `citext` retained) → re-`migrate catalog` re-applies (reversible). Re-verified **315 tests / `ruff` / `check` / no drift**. Live-metrics window deferred (local/dev, no consumer yet). Updated [INDEX.md](features/INDEX.md). Raised **DN-3** (run Stage 6 now vs skip, as DN-1). Handed to Retrospective Analyst. |
| 2026-06-18 | `4-build`→`5-release` | **Senior Engineer** — built `apps/catalog` from [TASKS.md](features/submission-intake/TASKS.md) (T-01…T-14), risk-first. 4 tables; **fixed 5-floor `Criterion` enum, no "other"** (taste rejection unrepresentable, AC6); single write path (invariants + atomic, row-locked §7 lifecycle) / single read path (owner-scoped, FIFO queue+dup hint, **ACCEPTED-only** `list_catalogued_apps`/`get_catalogued_app` = D-6 substrate, time-to-decision); after-commit decision emails; developer API (1–8) + review API (9–10) under `catalog/api/`; developer + admin-review pages; Django-admin inspection (append-only decisions). Reused accounts gate + taxonomy `is_valid_tag`/`resolve_tag` + core as-is; added 2 `core.config` media tunables + `Pillow` + `MEDIA_ROOT`. **131 new tests / 315 total green**, ruff clean, no drift, reversibility rehearsed. CODEMAP/README/.env.example/[TEST_PLAN.md](features/submission-intake/TEST_PLAN.md) done; **D-6** confirmed; logged SI-8…SI-11. Advanced to `5-release`. |
| 2026-06-17 | `3-plan`→`4-build` | **Planner / Tech Lead** — decomposed [submission-intake/DESIGN.md](features/submission-intake/DESIGN.md) into [TASKS.md](features/submission-intake/TASKS.md): **14 ordered S/M tasks** (T-01…T-14), no `L`. Risk front-loaded — the four §13 sharp edges (gate no-"other" enum T-02 / write invariants T-05 / decision atomicity + lifecycle T-06 / accepted-only catalog T-07) precede every HTTP/UI task. Write path split T-05/T-06, HTTP T-09/T-10, pages T-11/T-12. Coverage table maps every DESIGN element + AC1–AC9. Advanced to `4-build` / Senior Engineer. |
| 2026-06-17 | `2-design`→`3-plan` | **Software Architect** (hand-off) — [submission-intake/DESIGN.md](features/submission-intake/DESIGN.md) **approved**. Recorded global **[D-6](DECISIONS.md)** (catalogued-app contract: accepted `catalog.App`, `App.id` UUID stable ref, read only via `list_catalogued_apps`/`get_catalogued_app`, tags as `Tag.id` under D-5, ordered media). Marked DESIGN status APPROVED; CODEMAP entries deferred to Stage 4. Advanced to `3-plan` / Planner. |
| 2026-06-17 | `2-design`      | **Software Architect** — wrote [submission-intake/DESIGN.md](features/submission-intake/DESIGN.md): new `apps/catalog/` (App + soft-`tag_id` AppTag + AppMedia + append-only ReviewDecision); gate = **fixed 5-floor enum, no "other" value** → taste rejection (AC6/R1) unrepresentable; lifecycle state machine (rejection non-terminal); FIFO queue, zero pay/tier/priority fields (AC3). Reuses accounts gate + taxonomy `is_valid_tag`/`resolve_tag` (D-5) + core email/observability. Resolved **OQ-2** (gate wording) + **OQ-3** (media 1–8 imgs/PNG-JPEG-WebP/≤5MB/Pillow). Proposed global **D-6** (catalogued-app contract). All AC mapped. Awaiting approval. |
| 2026-06-17 | `1-define`      | **Product Analyst** — drafted [submission-intake/FEATURE_BRIEF.md](features/submission-intake/FEATURE_BRIEF.md): developer entry point + the **objective** quality gate (works / not malware-spam / not duplicate / honest metadata / basic policy — **floors only, never taste**, §5.5). 6 stories, 9 G/W/T criteria, 8 metrics. Fixed identical-free-intake fairness (AC3, §5.6), the D-5 tag contract (store by `Tag.id`), and the accepted-app downstream contract (AC9). Logged **OQ-1/OQ-2/OQ-3**; flagged 7 calls for confirmation. Awaiting approval before Stage-2 handoff. |
| 2026-06-17 | `6-post-release`→`0-coordinator` | **Coordinator** — DN-1 resolved → Option A: **`interest-taxonomy` closed out**, Stage-6 retrospective skipped (outcome review deferred/reopenable, mirrors identity-accounts). Both Phase-0 enablers now released local/dev. Updated [INDEX.md](features/INDEX.md). Raised **DN-2** for the next feature (`signal-capture` vs `submission-intake`). |
| 2026-06-17 | `5-release`→`6-post-release` | **Release Engineer** — released `interest-taxonomy` to local/dev. Wrote [RELEASE_NOTES.md](features/interest-taxonomy/RELEASE_NOTES.md) (changes, audience, operator rollout, gate-based promotion, metric→alert map, known limits). **Rehearsed rollout→rollback on a throwaway Postgres DB**: migrate (3 tables) → `seed_taxonomy` (11 clusters / 67 tags) → `check_taxonomy` exit 0 → idempotent re-seed (no writes) → `migrate taxonomy zero` reverses to 0 `taxonomy_*` tables, shared `citext` retained. Re-verified 184 tests / `ruff` / `check` / no migration drift. Raised **DN-1** (run Stage 6 now vs skip, as identity-accounts). Handed off to Retrospective Analyst. |
| 2026-06-17 | `4-build`→`5-release` | **Senior Engineer** — built `apps/taxonomy` from TASKS.md (T-01…T-10): data model (UUID/citext/normalized-label unique index, reversible migration), single write path with all invariants + cycle-guarded `resolve_tag`, 3-endpoint read API, idempotent `seed_taxonomy` (PyYAML) + founding vocabulary (11 clusters / 67 tags), `check_taxonomy` gate, services-routed admin, docs/CODEMAP/D-5. **76 new tests, 184 total green**; ruff clean; no migration drift. Logged ITX-9/10/11/12. Wrote [TEST_PLAN.md](features/interest-taxonomy/TEST_PLAN.md). Handed off to Release Engineer. |
| 2026-06-17 | `3-plan`→`4-build` | **Planner** — A5 approved → decomposed [DESIGN.md](features/interest-taxonomy/DESIGN.md) into [TASKS.md](features/interest-taxonomy/TASKS.md): 10 ordered S/M tasks, risk front-loaded (write-service invariants + `replaced_by` cycle guard in T-03/T-04), full DESIGN/AC coverage. Flagged deferral PL-1. Handed off to Senior Engineer. |

> Older rows (`interest-taxonomy` design/define, `identity-accounts` build/release, and
> earlier) live in
> [process/activity-archive.md](process/activity-archive.md).
