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

| Field            | Value                                                            |
|------------------|------------------------------------------------------------------|
| **Active feature** | _none yet_                                                     |
| **Stage**          | `0-coordinator` (no feature in the pipeline)                   |
| **Persona**        | Coordinator (see [CLAUDE.md](CLAUDE.md) §4)                    |
| **Folder**         | _n/a_                                                          |
| **Last updated**   | 2026-06-13                                                     |

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds. These are seeded from the open questions in the vision doc (§7) — the first
one gates everything downstream.

| #  | Decision                                                                                          | Why it matters                                                            | Answer |
|----|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|--------|
| D1 | **Beachhead niche** — which single vertical launches first (e.g. indie productivity, indie games on platform X)? | Drives cold-start strategy, founding catalog, and the first feature set.  | _TBD_  |
| D2 | What is the **first feature** to run through the pipeline (e.g. weekly digest, submission/intake, quality-score v1)? | Determines which `features/<slug>/` folder we create and enter Stage 1.   | _TBD_  |
| D3 | Any hard constraints up front — **deadline, budget, platform, compliance/privacy** scope?         | Shapes the brief and the architecture's non-functional targets.           | _TBD_  |

When all blocking items are answered, the agent moves D1–D3 into the relevant
`FEATURE_BRIEF.md` / `DECISIONS.md` and clears them here.

---

## Decisions Made (recently)

_None yet. Confirmed decisions are logged per-feature in `features/<slug>/DECISIONS.md`;
this section is a short, human-readable digest of the latest few._

---

## Activity Log

Newest first. One line per session. **Keep the most recent ~20 rows here**; when it
grows past that, move older rows to `process/activity-archive.md` so this dashboard
stays quick to scan. The per-feature folders remain the full record either way.

| Date       | Stage           | Summary                                                                 |
|------------|-----------------|-------------------------------------------------------------------------|
| 2026-06-13 | `0-coordinator` | Decomposed the vision doc into separately-designable MVP components → [docs/mvp-component-breakdown.md](docs/mvp-component-breakdown.md). Recommends `signal-capture` as the first feature (informs D2); no decision taken. |
| 2026-06-13 | `0-coordinator` | Migrated `chain-of-thought.md` (14-step protocol → Architect persona) and `Design-strategy.md` (determinism rule + release-level DoD → CLAUDE.md §2/§6) into the personas/manual, then deleted both source files; personas are now self-contained specs. |
| 2026-06-13 | `0-coordinator` | Added `CODEMAP.md`, global `DECISIONS.md`, `features/INDEX.md`; wired code-reuse + global-decision tracking into the personas and CLAUDE.md. |
| 2026-06-13 | `0-coordinator` | Set up persona pipeline (CLAUDE.md, personas, folders). Awaiting D1–D3. |
