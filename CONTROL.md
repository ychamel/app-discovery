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
| **Active feature** | `interest-taxonomy`                                              |
| **Stage**          | `6-post-release`                                                 |
| **Persona**        | Retrospective Analyst (see [phase-6-retrospective-analyst.md](process/personas/phase-6-retrospective-analyst.md)) |
| **Folder**         | [features/interest-taxonomy/](features/interest-taxonomy/)       |
| **Last updated**   | 2026-06-17 (released local/dev — [RELEASE_NOTES.md](features/interest-taxonomy/RELEASE_NOTES.md) written, rollout→rollback rehearsed on scratch DB, 184 tests green; handed to Retrospective Analyst) |

> **`identity-accounts` closed out 2026-06-17** at user request — Stage 6 (retrospective)
> skipped. Build/release artifacts stand (108 tests green, released local/dev basis);
> live-metric measurement + outcome report remain deferred (R1, reopenable).

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 5-release → 6-post-release | Feature: interest-taxonomy | Persona: Release Engineer (handoff)
Done: Re-verified the Stage-4 build and shipped interest-taxonomy to local/dev. Wrote
      RELEASE_NOTES.md (what changed, who's affected, operator rollout, gate-based promotion,
      rehearsed rollback, metric→alert mapping, known limitations). Rehearsed the full
      rollout→rollback on a THROWAWAY Postgres DB: migrate taxonomy (3 tables) → seed_taxonomy
      (11 clusters / 67 tags) → check_taxonomy exit 0 → idempotent re-seed (no writes) →
      migrate taxonomy zero reverses to 0 taxonomy_* tables while KEEPING the shared citext
      extension. Updated features/INDEX.md (→ 6-post-release, released local/dev).
Verified by: full repo suite 184 tests green; ruff clean; manage.py check clean;
      makemigrations --check no drift; scratch-DB rollout→rollback rehearsal (above).
Blocked/Deferred: live-metrics monitoring window deferred (no live consumer / no production
      target yet — local/dev only, consistent with identity-accounts R1). OQ-4/PL-1 — AC4
      app-coverage vs a REAL catalog deferred & reopenable (no catalog pre-submission-intake).
Decisions needed: DN-1 below — run the Stage-6 retrospective now or skip it (as
      identity-accounts did), given outcomes can't be measured until a consumer + real
      catalog exist. No code/scope change pending.
Next: Retrospective Analyst — measure outcomes against the brief OR (user's call, DN-1) skip
      Stage 6 and mark interest-taxonomy closed-out with the outcome review reopenable.
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

**DN-1 — Run the `interest-taxonomy` Stage-6 retrospective now, or skip it?** The feature is
released to local/dev and verified. Stage 6 measures live outcomes against the brief — but
the headline metrics (app/user coverage, reference-break rate) need a *live consumer* and a
*real submitted catalog*, neither of which exists yet (OQ-4/PL-1). For `identity-accounts`
you chose to **skip** Stage 6 and keep the outcome review reopenable. Same call here?

| Option | Meaning | **Answer** |
|--------|---------|------------|
| **A — Skip** (mirrors identity-accounts) | Mark `interest-taxonomy` closed-out; defer the outcome report until a consumer + catalog exist (reopenable). Then return to Coordinator to pick the next feature. | skip for now |
| **B — Run it now** | Retrospective Analyst writes the outcome report against what *can* be measured today (integrity gate, vocabulary size/redundancy, the design's AC8 future-proofing), flagging coverage as not-yet-measurable. | _ |

> Not blocking the release (already shipped). It only decides whether the next session runs
> Stage 6 or moves on. Default if unanswered: hold at `6-post-release` awaiting your call.

---

## Decisions Made (recently)

A short, human-readable digest. Full rationale lives in [DECISIONS.md](DECISIONS.md)
(global) or `features/<slug>/DECISIONS.md` (local).

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
