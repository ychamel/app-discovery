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
| **Active feature** | `identity-accounts`                                            |
| **Stage**          | `4-build`                                                      |
| **Persona**        | Senior Engineer (see [phase-4-engineer.md](process/personas/phase-4-engineer.md)) |
| **Folder**         | [features/identity-accounts/](features/identity-accounts/)     |
| **Last updated**   | 2026-06-17                                                     |

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 3-plan | Feature: identity-accounts | Persona: Planner / Tech Lead
Done: A3 approved (DESIGN.md accepted) → ran Stage 3. Decomposed the approved design into TASKS.md:
      18 ordered, independently verifiable tasks (all S/M — no L remains), in build order
      scaffold → shared core (config/email/rate-limit) → data model+seed → role gate → magic-link →
      API+UI slices (register, sign-in/verify/session, logout, profile, developer self-serve, deletion,
      admin grant/revoke) → mgmt commands → security settings → observability → docs/deploy runbook.
      Risk front-loaded: magic-link token logic (T-07) built and tested in isolation early. Each task
      carries a concrete definition-of-done, declared files/areas (no collisions), dependencies, and a
      DESIGN.md/AC reference. Added a coverage table proving every design element (§2–§14) and all 10
      ACs map to ≥1 task; CODEMAP-update is in each shared task's DoD.
Verified by: n/a (Stage 3 produces a document — no code/tests). Exit-criteria self-check passed:
      full design coverage, every task has a DoD, zero L tasks.
Blocked/Deferred: none new. (Carried from design: concrete prod email provider + rich SPA frontend —
      ops/later feature, not MVP. Cross-feature account-deletion cascade handed downstream.)
Decisions needed: none — Stage 4 (build) is unblocked.
Next: Senior Engineer executes TASKS.md starting at T-01 (project scaffold), then T-02/T-03 (shared
      core), per the dependency overview; produce code + TEST_PLAN.md covering AC1–AC10.
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

_None — Stage 4 (build) is unblocked. Newly resolved items are summarized below._

> **A3 — resolved 2026-06-17.** You **approved** `identity-accounts` DESIGN.md. The
> Planner decomposed it into [TASKS.md](features/identity-accounts/TASKS.md) (18 ordered
> S/M tasks, full coverage) and handed off to **Stage 4 (Senior Engineer)**.
>
> **A2 — resolved 2026-06-14.** Stack chosen by the user: **Python / Django + PostgreSQL**
> (over TypeScript full-stack and framework-light TS). Logged as global [D-4](DECISIONS.md).
>
> **A1 — resolved 2026-06-14.** You approved the `identity-accounts` brief with role
> direction: *one access method, different roles perform different actions (user,
> developer, admin, + future roles)*. Applied — see *Decisions Made* below and the
> revised brief. Feature handed off to Stage 2 (Software Architect).

---

## Decisions Made (recently)

A short, human-readable digest. Full rationale lives in [DECISIONS.md](DECISIONS.md)
(global) or `features/<slug>/DECISIONS.md` (local).

- **D1 → beachhead niche = "vibecoded webapps"** (small web apps from solo/tiny-team devs, often AI-assisted). Repo-wide; logged as [D-1](DECISIONS.md). Scopes taxonomy, submission, founding catalog.
- **D2 → first feature = `identity-accounts`.** Chosen by dependency order ("go by dependencies"); it is the deepest Phase-0 root (signal-capture, submission-intake, interest-profile all depend on it). `signal-capture` deliberately **postponed** despite the breakdown's recommendation — it needs deeper design choices (cross-platform attribution + privacy fork).
- **D3 → no hard constraints up front; start small, scale as we go.** Repo-wide; logged as [D-2](DECISIONS.md). Non-functional targets deferred per-feature; CLAUDE.md §5.2 still binds.
- **D-3 (revised) → identity model = one account, one access method, extensible role-based authorization.** Roles: **user** (base), **developer** (self-serve), **admin** (granted, not self-serve), + future roles; one sign-in for all. Revised 2026-06-14 per user A1 (was "dual capability reader+developer"). Repo-wide; logged as [D-3](DECISIONS.md). Other features gate actions on roles, key off one account, and authenticate every surface (incl. admin) through this feature.
- **DL-1 → signup = open self-serve for everyone** (account creation un-gated; every new account gets the base **user** role; quality control lives at submission, not signup). Feature-local; logged in [features/identity-accounts/DECISIONS.md](features/identity-accounts/DECISIONS.md).
- **DL-2 → role-assignment rules: developer self-serve, admin granted (never self-assigned).** Prevents privilege escalation under open signup (brief R6). Feature-local; logged in [features/identity-accounts/DECISIONS.md](features/identity-accounts/DECISIONS.md).

---

## Activity Log

Newest first. One line per session. **Keep the most recent ~20 rows here**; when it
grows past that, move older rows to `process/activity-archive.md` so this dashboard
stays quick to scan. The per-feature folders remain the full record either way.

| Date       | Stage           | Summary                                                                 |
|------------|-----------------|-------------------------------------------------------------------------|
| 2026-06-17 | `3-plan`→`4-build` | **Planner / Tech Lead** — A3 approved → decomposed the design into [TASKS.md](features/identity-accounts/TASKS.md): **18 ordered, independently verifiable tasks (all S/M, no L)** in build order (scaffold → shared core: config/email/rate-limit → data model+group seed → role gate → magic-link → API+UI slices: register/sign-in/verify/logout/profile/developer self-serve/deletion/admin grant → mgmt commands → security → observability → docs). Risk front-loaded (magic-link T-07 isolated+tested early). Each task has a DoD, declared files (no collisions), deps, and a DESIGN/AC ref. Added a coverage table mapping every design element (§2–§14) + all 10 ACs to ≥1 task. **Handed off to Senior Engineer (4-build).** |
| 2026-06-14 | `2-design`      | **Software Architect** — user chose the stack (**A2**: Django + DRF + PostgreSQL) → logged global **D-4** (stack, auth model, shared-code root `apps/`, rejected TS alternatives). Ran the 14-step protocol and wrote [DESIGN.md](features/identity-accounts/DESIGN.md): components, data model (Account/LoginToken/RoleGrant, UUID PKs), 10 endpoint contracts, UX, non-functional, failure modes, rollout, AC→design traceability (all 10 ACs, no TBD). Resolved the 3 Stage-2 deferrals → **DL-3** (passwordless magic-link), **DL-4** (Groups-as-roles + fail-closed gate + audited admin grant), email = pluggable `EmailSender`. Set CODEMAP shared-code root + planned surface. **Awaiting design approval (A3)** before Stage-3 handoff. |
| 2026-06-14 | `1-define`→`2-design` | **Product Analyst** — user answered **A1** with role direction. Revised the brief to a **single access method + extensible role model** (user/developer/admin+future): 7 stories (added US7 admin), 10 G/W/T criteria (added AC9 admin-grant + AC10 single-access/extensibility), role-aware metrics/scope/constraints, new R6. Revised global **D-3** accordingly; logged **DL-2** (developer self-serve, admin granted). **Resolved** the editorial/admin escalation (editors auth via admin role through this feature; tooling stays in `editorial-curation-tools`). Approved → **handed off to Software Architect (2-design)**. |
| 2026-06-14 | `1-define`      | **Product Analyst** wrote [identity-accounts/FEATURE_BRIEF.md](features/identity-accounts/FEATURE_BRIEF.md) (6 stories, 8 G/W/T criteria, metrics, scope, 5 risks). Resolved 2 forks via user → **D-3** (one account, dual capability, global) + **DL-1** (open self-serve signup, local). Adopted data-minimization posture; escalated editorial/admin-account gap. **Awaiting brief approval** (A1) before Stage-2 handoff. |
| 2026-06-14 | `0-coordinator` | Resolved D1–D3. Logged niche (D-1) + no-constraints posture (D-2) in global [DECISIONS.md](DECISIONS.md); un-gated the identity-accounts privacy open question. **Activated `identity-accounts` into `1-define`** (by dependency order; signal-capture postponed). Handed off to Product Analyst — did not run Stage 1 (one persona per session). |
| 2026-06-13 | `0-coordinator` | Transformed [docs/mvp-component-breakdown.md](docs/mvp-component-breakdown.md) §4 into 11 scaffolded feature folders (7 artifacts each, briefs/open-questions seeded with breakdown facts + §7 questions); registered all in [features/INDEX.md](features/INDEX.md) as `backlog` in dependency-build order. No feature activated — that is D2 (user's call). |
| 2026-06-13 | `0-coordinator` | Decomposed the vision doc into separately-designable MVP components → [docs/mvp-component-breakdown.md](docs/mvp-component-breakdown.md). Recommends `signal-capture` as the first feature (informs D2); no decision taken. |
| 2026-06-13 | `0-coordinator` | Migrated `chain-of-thought.md` (14-step protocol → Architect persona) and `Design-strategy.md` (determinism rule + release-level DoD → CLAUDE.md §2/§6) into the personas/manual, then deleted both source files; personas are now self-contained specs. |
| 2026-06-13 | `0-coordinator` | Added `CODEMAP.md`, global `DECISIONS.md`, `features/INDEX.md`; wired code-reuse + global-decision tracking into the personas and CLAUDE.md. |
| 2026-06-13 | `0-coordinator` | Set up persona pipeline (CLAUDE.md, personas, folders). Awaiting D1–D3. |
