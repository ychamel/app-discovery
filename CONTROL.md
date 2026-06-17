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
| **Stage**          | `5-release`                                                      |
| **Persona**        | Release Engineer (see [phase-5-release-engineer.md](process/personas/phase-5-release-engineer.md)) |
| **Folder**         | [features/interest-taxonomy/](features/interest-taxonomy/)       |
| **Last updated**   | 2026-06-17 (build complete — T-01…T-10, 76 new tests, 184 total green; handed to Release Engineer) |

> **`identity-accounts` closed out 2026-06-17** at user request — Stage 6 (retrospective)
> skipped. Build/release artifacts stand (108 tests green, released local/dev basis);
> live-metric measurement + outcome report remain deferred (R1, reopenable).

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 4-build → 5-release | Feature: interest-taxonomy | Persona: Senior Engineer (handoff)
Done: Built apps/taxonomy from TASKS.md (T-01…T-10): new Django app; data model (Tag/Cluster
      + M2M, UUID PKs, citext slugs, functional unique index for normalized-label dedup,
      reversible 0001 that keeps the shared citext extension); single write path services.py
      (≥1-cluster, dedupe, soft-retire + successor validation, +update_tag/update_cluster sync
      setters); cycle-guarded selectors.py (is_valid_tag/resolve_tag, config step-limit);
      3-endpoint JSON read API; seed/vocabulary.yaml + idempotent seed_taxonomy (PyYAML);
      check_taxonomy integrity gate; services-routed Django admin; founding vocabulary
      (11 clusters / 67 tags, vibecoded-webapps niche); README + .env.example + CODEMAP + D-5.
      Wrote TEST_PLAN.md mapping AC1–AC8.
Verified by: 76 new taxonomy tests (full repo 184) green; ruff clean; makemigrations --check
      no drift; manage.py check clean; on dev DB: migrate→seed_taxonomy (11/67)→check_taxonomy
      exit 0, idempotent re-seed, reversible migration verified.
Blocked/Deferred: OQ-4/PL-1 — AC4 app-coverage against a REAL catalog deferred & reopenable
      (no catalog pre-submission-intake). identity-accounts Stage 6 outcome report deferred.
Decisions needed: none blocking. Stage-4 deviations logged: ITX-9 (unauth read=403 not 401,
      DESIGN §5c corrected), ITX-11 (added update_tag/update_cluster, DESIGN §5b), ITX-12
      (size band), ITX-10 (PyYAML dependency).
Next: Release Engineer plans rollout per DESIGN §12 (migrate → seed_taxonomy → check_taxonomy),
      writes RELEASE_NOTES.md, re-verifies the gate.
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

**None blocking.** The Planner's founding-catalog deferral (PL-1, T-09) is logged under
*Decisions Made* for visibility — speak up if you'd rather pause T-09 until real app data
exists, otherwise the Senior Engineer proceeds against the niche definition.

---

## Decisions Made (recently)

A short, human-readable digest. Full rationale lives in [DECISIONS.md](DECISIONS.md)
(global) or `features/<slug>/DECISIONS.md` (local).

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
| 2026-06-17 | `4-build`→`5-release` | **Senior Engineer** — built `apps/taxonomy` from TASKS.md (T-01…T-10): data model (UUID/citext/normalized-label unique index, reversible migration), single write path with all invariants + cycle-guarded `resolve_tag`, 3-endpoint read API, idempotent `seed_taxonomy` (PyYAML) + founding vocabulary (11 clusters / 67 tags), `check_taxonomy` gate, services-routed admin, docs/CODEMAP/D-5. **76 new tests, 184 total green**; ruff clean; no migration drift. Logged ITX-9/10/11/12. Wrote [TEST_PLAN.md](features/interest-taxonomy/TEST_PLAN.md). Handed off to Release Engineer. |
| 2026-06-17 | `3-plan`→`4-build` | **Planner** — A5 approved → decomposed [DESIGN.md](features/interest-taxonomy/DESIGN.md) into [TASKS.md](features/interest-taxonomy/TASKS.md): 10 ordered S/M tasks, risk front-loaded (write-service invariants + `replaced_by` cycle guard in T-03/T-04), full DESIGN/AC coverage. Flagged deferral PL-1. Handed off to Senior Engineer. |
| 2026-06-17 | `2-design`      | **Architect** — wrote [DESIGN.md](features/interest-taxonomy/DESIGN.md): flat tags + named clusters via M2M (adjacency deferred, AC8); UUID stable identity; soft-retire + `resolve_tag`; seed.yaml + `seed_taxonomy` + Django admin (no custom UI). Logged global **D-5** + ITX-6/7/8. Awaiting A5. |
| 2026-06-17 | `1-define`→`2-design` | **Product Analyst** (handoff) — brief **approved (A4)**, 5 calls logged as ITX-1…ITX-5; carried shape/retire/size open items to the Architect. Handed off to Software Architect. |
| 2026-06-17 | `1-define`      | **Product Analyst** — wrote [interest-taxonomy/FEATURE_BRIEF.md](features/interest-taxonomy/FEATURE_BRIEF.md): the single shared controlled vocabulary (tags + clusters). 6 stories, 8 criteria, 6 metrics. Deferred taxonomy shape to Stage 2 under AC8; fixed stable identity (AC7) + safe rename/retire (AC6). Awaiting A4. |
| 2026-06-17 | `0-coordinator` | **Coordinator** — user skipped identity-accounts Stage 6; selected next feature by dependency order: **`interest-taxonomy`** (Phase-0, no deps). Activated into `1-define`. Handed off to Product Analyst. |
| 2026-06-17 | `5-release`     | **Release Engineer** — wrote [RELEASE_NOTES.md](features/identity-accounts/RELEASE_NOTES.md): gate-based rollout, **rehearsed rollback** on a scratch Postgres DB, metric→alert mapping. Re-verified 108 tests / `ruff` / `check` / no migration drift. Surfaced R1 → user chose Option A (local/dev release). Handed off to Stage 6. |
| 2026-06-17 | `4-build`→`5-release` | **Senior Engineer** — built `identity-accounts` from TASKS.md (T-01…T-18): Django/DRF/PostgreSQL scaffold, shared core, data model (UUID PKs, citext, 3 role groups), fail-closed role gate, risk-first magic-link (double-spend test), all endpoints + pages, mgmt commands, security hardening, docs, [TEST_PLAN.md](features/identity-accounts/TEST_PLAN.md). **108 tests pass**. Logged DL-5. Handed off to Release Engineer. |
| 2026-06-17 | `3-plan`→`4-build` | **Planner** — A3 approved → decomposed into [TASKS.md](features/identity-accounts/TASKS.md): 18 ordered S/M tasks, risk front-loaded (magic-link T-07), full coverage table. Handed off to Senior Engineer. |
| 2026-06-14 | `2-design`      | **Architect** — stack chosen (**A2**) → global **D-4**. Wrote [DESIGN.md](features/identity-accounts/DESIGN.md): components, data model, 10 endpoint contracts, traceability (all 10 ACs). Resolved DL-3 (magic-link) + DL-4 (Groups-as-roles + fail-closed gate). Awaiting A3. |
| 2026-06-14 | `1-define`→`2-design` | **Product Analyst** — **A1** answered → revised brief to single access method + extensible role model (user/developer/admin). Revised **D-3**; logged **DL-2**. Resolved editorial/admin escalation. Handed off to Software Architect. |
