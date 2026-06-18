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
| **Active feature** | `submission-intake`                                              |
| **Stage**          | `6-post-release`                                                 |
| **Persona**        | Retrospective Analyst (see [phase-6-retrospective-analyst.md](process/personas/phase-6-retrospective-analyst.md)) |
| **Folder**         | [features/submission-intake/](features/submission-intake/)       |
| **Last updated**   | 2026-06-18 (**RELEASED local/dev** — [RELEASE_NOTES.md](features/submission-intake/RELEASE_NOTES.md) written; rollout→rollback **rehearsed on a throwaway DB** (migrate → 4 `catalog_*` tables + shared `citext` → `check` clean → `migrate catalog zero` reverses to 0 tables, `citext` retained → re-apply); **315 tests green**, ruff clean, no drift re-verified. Advanced to Stage 6 — **DN-3** asks run-now-vs-skip retrospective, mirroring DN-1) |

> **`interest-taxonomy` closed out 2026-06-17** per **DN-1 Option A** — Stage 6
> (retrospective) skipped, mirroring `identity-accounts`. Build/release artifacts stand
> (184 tests green, released local/dev; rollback rehearsed); live-metrics + real-catalog
> coverage measurement + outcome report remain deferred (reopenable).

> **`identity-accounts` closed out 2026-06-17** at user request — Stage 6 (retrospective)
> skipped. Build/release artifacts stand (108 tests green, released local/dev basis);
> live-metric measurement + outcome report remain deferred (R1, reopenable).

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 5-release → 6-post-release | Feature: submission-intake | Persona: Release Engineer
Done: RELEASED submission-intake to local/dev. Wrote RELEASE_NOTES.md (what changed; who is
      affected incl. the D-6 action required of downstream; operator rollout; gate-based promotion;
      success-metric→signal→alert map; rehearsed rollback; known limits). Re-verified the Stage-4
      build green and rehearsed rollout→rollback on a throwaway Postgres DB (catalog_release_rehearsal,
      dropped after): migrate created the 4 catalog_* tables (catalog_app / _app_tag / _app_media /
      _review_decision) with shared citext present → manage.py check clean → migrate catalog zero
      reversed to 0 catalog_* tables (shared citext RETAINED, used by accounts/taxonomy) → re-migrate
      catalog re-applied (migration confirmed reversible). Updated features/INDEX.md.
Verified by: 315 tests green; ruff clean; manage.py check clean; no migration drift
      (makemigrations --check); rollout→rollback rehearsed on a scratch DB (above), dev DB untouched.
      TEST_PLAN.md maps AC1–AC9.
Blocked/Deferred: live-metrics monitoring window deferred (local/dev target, no consumer yet —
      mirrors identity-accounts/interest-taxonomy). Flagged-for-data (not blockers, DESIGN §13):
      re-review-on-any-accepted-edit churn; owner-account-deletion CASCADE (revisit at signal-capture);
      accepted-URL partial-unique; manual review scaling. app-pages must adopt §9 media limits + the
      D-6 read contract before storing any app reference.
Decisions needed: DN-3 — run Stage 6 retrospective now vs skip & close out (mirrors DN-1/identity).
Next: Retrospective Analyst awaits DN-3. If skip → close out submission-intake (Stage 6 deferred/
      reopenable), update INDEX, return to Coordinator for the next feature (app-pages is now unblocked).
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

**DN-3 — Run `submission-intake` Stage 6 (retrospective) now, or skip and close out?**
`submission-intake` is released to local/dev (RELEASE_NOTES.md written, rollout→rollback rehearsed,
315 tests green). As with `identity-accounts` (R1) and `interest-taxonomy` (DN-1), there is no
production target or live consumer yet, so an outcome-measurement window has no real signal to read.

| Option | Meaning | Answer |
|--------|---------|--------|
| **A — Skip & close out** *(recommended; mirrors DN-1)* | Mark the feature closed-out; defer the outcome review (reopenable when a consumer + live metrics exist). Return to Coordinator — `app-pages` is now unblocked. | |
| **B — Run Stage 6 now** | Retrospective Analyst runs the post-release review against the brief's success metrics now (limited signal at local/dev). | |

**DN-2 — RESOLVED 2026-06-17 → Option B (`submission-intake`).** Both Phase-0 enablers done;
user selected `submission-intake` (Phase 1 Catalog) as the next feature (D2). Activated into
Stage `1-define`, handed to Product Analyst.

**DN-1 — RESOLVED 2026-06-17 → Option A (skip).** `interest-taxonomy` Stage-6 retrospective
skipped; feature closed-out, outcome review deferred & reopenable (mirrors identity-accounts).

---

## Decisions Made (recently)

A short, human-readable digest. Full rationale lives in [DECISIONS.md](DECISIONS.md)
(global) or `features/<slug>/DECISIONS.md` (local).

- **Release-SI (2026-06-18)** — `submission-intake` **released to local/dev**. [RELEASE_NOTES.md](features/submission-intake/RELEASE_NOTES.md) written (changes, downstream D-6 action, operator rollout, gate-based promotion, success-metric→signal→alert map, known limits). Rollout→rollback **rehearsed on a throwaway Postgres DB**: migrate → 4 `catalog_*` tables + shared `citext` → `check` clean → `migrate catalog zero` reverses to 0 tables (`citext` retained) → re-apply (reversible). **315 tests / ruff / check / no-drift** re-verified. Live-metrics window deferred (no consumer/prod target). Advanced to `6-post-release`; **DN-3** raised (run Stage 6 now vs skip, as DN-1).
- **Build-SI (2026-06-18)** — `submission-intake` **built (T-01…T-14), 131 new tests / 315 total green**, ruff clean, no migration drift, reversibility rehearsed. New app `apps/catalog` (4 tables; fixed 5-floor gate enum, no "other"; single write/read paths; ACCEPTED-only D-6 catalogue substrate; developer+review API and pages; decision emails; admin inspection). Reused accounts gate + taxonomy D-5 + core as-is; added 2 media tunables + Pillow + MEDIA_ROOT. CODEMAP + README + .env.example + [TEST_PLAN.md](features/submission-intake/TEST_PLAN.md) (AC1–AC9) done; global **D-6** confirmed. Stage-4 deviations logged **SI-8…SI-11** in [features/submission-intake/DECISIONS.md](features/submission-intake/DECISIONS.md). Advanced to `5-release` / Release Engineer.
- **Plan-SI (2026-06-17)** — `submission-intake` [TASKS.md](features/submission-intake/TASKS.md) **complete** (14 ordered S/M tasks, no `L`). Risk-first per DESIGN §13: gate no-"other" enum (T-02), write-service invariants (T-05), decision atomicity + lifecycle (T-06), accepted-only catalog/D-6 (T-07) all precede the HTTP/UI tasks. Write path / HTTP surface / pages each split to stay off `L`. Full DESIGN-element + AC1–AC9 coverage table. Advanced to Stage 4; handed to Senior Engineer.
- **Design-SI (2026-06-17)** — `submission-intake` [DESIGN.md](features/submission-intake/DESIGN.md) **approved**. New Django app `apps/catalog/` reusing the accounts gate + taxonomy `is_valid_tag`/`resolve_tag` (D-5) + core email/observability/config (no new stack). Gate = fixed 5-floor code enum with **no "other"** → taste rejection (R1/AC6) unrepresentable; lifecycle state machine; FIFO queue, zero pay/tier/priority fields (AC3). Recorded global **[D-6](DECISIONS.md)** (catalogued-app contract: accepted `App.id` read only via `list_catalogued_apps`/`get_catalogued_app`). OQ-2/OQ-3 resolved in the design. Advanced to Stage 3; handed to Planner.
- **A-SI (2026-06-17)** — `submission-intake` brief **approved**; the 7 confirmation calls logged as **SI-1…SI-7** in [features/submission-intake/DECISIONS.md](features/submission-intake/DECISIONS.md) (web-only app=URL; human/admin checklist gate with no MVP automation; rejection non-terminal; individual ownership; offline founding-catalog recruitment → closes OQ-1; metadata-correction in / versioned-updates out; media=screenshots aligned to `app-pages`). Advanced to Stage 2; handed to Software Architect.
- **Release (2026-06-17)** — `interest-taxonomy` **released to local/dev**. [RELEASE_NOTES.md](features/interest-taxonomy/RELEASE_NOTES.md) written; rollout→rollback **rehearsed on a scratch DB** (migrate → seed 11/67 → check exit 0 → idempotent re-seed → `migrate taxonomy zero` drops 3 tables, keeps shared `citext`). 184 tests / ruff / check / no-drift re-verified. Live-metrics window deferred (no consumer/prod target yet). Stage-6 retrospective awaiting **DN-1** (run-now vs skip, as identity-accounts did). Advanced to `6-post-release`.
- **Build (2026-06-17)** — `interest-taxonomy` **built (T-01…T-10), 76 new tests / 184 total green**. Stage-4 deviations logged in [features/interest-taxonomy/DECISIONS.md](features/interest-taxonomy/DECISIONS.md): **ITX-9** (unauth read = `403` not `401`; DESIGN §5c corrected), **ITX-10** (PyYAML dep for the seed file), **ITX-11** (added `update_tag`/`update_cluster` sync setters; DESIGN §5b), **ITX-12** (founding size band 11 clusters / 67 tags, closes OQ-3). Handed to Release Engineer.
- **A5 (2026-06-17)** — `interest-taxonomy` [DESIGN.md](features/interest-taxonomy/DESIGN.md) **approved** (flat tags + named clusters via M2M; UUID stable identity; soft-retire + read-time `resolve_tag`; seed-file/command/admin management). Decomposed into [TASKS.md](features/interest-taxonomy/TASKS.md); advanced to Stage 4.
- **A4 (2026-06-17)** — `interest-taxonomy` brief **approved**; the 5 confirmation calls logged as **ITX-1…ITX-5** (closed/curated vocabulary; clusters in MVP, adjacency deferred not precluded; shape left to Stage 2 under AC8; English-only at MVP; vocabulary+lifecycle here, rich curation UI in `editorial-curation-tools`).
- **A3 (2026-06-17)** — `identity-accounts` DESIGN.md **approved**; decomposed into [TASKS.md](features/identity-accounts/TASKS.md) (18 S/M tasks).
- **R1 (2026-06-17)** — *"deploying locally, still mid development"* → **Option A**: `identity-accounts` released to local/dev (migrations apply, `/health` green, 108 tests). Production promotion + live-metrics deferred.
- **A2 (2026-06-14)** — stack chosen: **Python / Django + PostgreSQL**. Logged as global [D-4](DECISIONS.md).
- **A1 (2026-06-14)** — `identity-accounts` brief approved with role direction: one access method, role-based actions (user/developer/admin + future). Revised [D-3](DECISIONS.md).
- **D1** — beachhead niche = **"vibecoded webapps"** (small web apps from solo/tiny-team devs, often AI-assisted). Global [D-1](DECISIONS.md).
- **D2** — first feature = `identity-accounts`, chosen by dependency order (deepest Phase-0 root); `signal-capture` postponed (needs deeper cross-platform/privacy design).
- **D3** — no hard constraints up front; start small, scale as we go. Global [D-2](DECISIONS.md).
- **DL-1 / DL-2** — signup is open self-serve (every account gets base **user** role); role assignment is developer self-serve, admin granted (never self-assigned). Feature-local, [identity-accounts/DECISIONS.md](features/identity-accounts/DECISIONS.md).
- **PL-1 (2026-06-17)** — founding-vocabulary sizing (T-09/OQ-3) authored against the niche definition + app archetypes, not a real catalog (none exists pre-`submission-intake`). App-coverage validation deferred & reopenable; not a Stage-4 blocker. Recorded in [TASKS.md](features/interest-taxonomy/TASKS.md) T-09.

---

## Activity Log

Newest first. One line per session. **Keep the most recent ~10 rows here**; older rows
live in [process/activity-archive.md](process/activity-archive.md). The per-feature
folders remain the full record either way.

| Date       | Stage           | Summary                                                                 |
|------------|-----------------|-------------------------------------------------------------------------|
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
| 2026-06-17 | `2-design`      | **Architect** — wrote [DESIGN.md](features/interest-taxonomy/DESIGN.md): flat tags + named clusters via M2M (adjacency deferred, AC8); UUID stable identity; soft-retire + `resolve_tag`; seed.yaml + `seed_taxonomy` + Django admin (no custom UI). Logged global **D-5** + ITX-6/7/8. Awaiting A5. |
| 2026-06-17 | `1-define`→`2-design` | **Product Analyst** (handoff) — brief **approved (A4)**, 5 calls logged as ITX-1…ITX-5; carried shape/retire/size open items to the Architect. Handed off to Software Architect. |
| 2026-06-17 | `1-define`      | **Product Analyst** — wrote [interest-taxonomy/FEATURE_BRIEF.md](features/interest-taxonomy/FEATURE_BRIEF.md): the single shared controlled vocabulary (tags + clusters). 6 stories, 8 criteria, 6 metrics. Deferred taxonomy shape to Stage 2 under AC8; fixed stable identity (AC7) + safe rename/retire (AC6). Awaiting A4. |
| 2026-06-17 | `0-coordinator` | **Coordinator** — user skipped identity-accounts Stage 6; selected next feature by dependency order: **`interest-taxonomy`** (Phase-0, no deps). Activated into `1-define`. Handed off to Product Analyst. |
| 2026-06-17 | `5-release`     | **Release Engineer** — wrote [RELEASE_NOTES.md](features/identity-accounts/RELEASE_NOTES.md): gate-based rollout, **rehearsed rollback** on a scratch Postgres DB, metric→alert mapping. Re-verified 108 tests / `ruff` / `check` / no migration drift. Surfaced R1 → user chose Option A (local/dev release). Handed off to Stage 6. |
| 2026-06-17 | `4-build`→`5-release` | **Senior Engineer** — built `identity-accounts` from TASKS.md (T-01…T-18): Django/DRF/PostgreSQL scaffold, shared core, data model (UUID PKs, citext, 3 role groups), fail-closed role gate, risk-first magic-link (double-spend test), all endpoints + pages, mgmt commands, security hardening, docs, [TEST_PLAN.md](features/identity-accounts/TEST_PLAN.md). **108 tests pass**. Logged DL-5. Handed off to Release Engineer. |

> Older rows (through `identity-accounts` Stage 3 and earlier) live in
> [process/activity-archive.md](process/activity-archive.md).
