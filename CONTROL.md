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
| **Stage**          | `2-design`                                                     |
| **Persona**        | Software Architect (see [phase-2-architect.md](process/personas/phase-2-architect.md)) |
| **Folder**         | [features/identity-accounts/](features/identity-accounts/)     |
| **Last updated**   | 2026-06-14                                                     |

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 2-design | Feature: identity-accounts | Persona: Software Architect (handed off this session)
Done: User answered A1 with role direction → applied it to the brief and revised global D-3 from
      "dual capability (reader+developer)" to "one account, ONE access method, extensible ROLE-based
      authorization" (roles: user[base]/developer[self-serve]/admin[granted, not self-serve]+future).
      Updated FEATURE_BRIEF.md (now 7 stories incl. US7 admin role; 10 G/W/T criteria incl. AC9 admin
      + AC10 single-access/extensibility; role-aware metrics, scope, constraints; new R6 escalation
      risk). Resolved the editorial/admin escalation (editors auth THROUGH this feature via admin role;
      tooling stays in editorial-curation-tools). Logged DL-2 (role-assignment rules). Approved brief
      and handed off to the Software Architect.
Verified by: n/a (Stage 1 produces a document — no code/tests). Exit gate (user approval of brief) met
      via A1 answer + applied role direction.
Blocked/Deferred: Auth mechanism, shared email-delivery dependency, and now ROLE-assignment/enforcement
      mechanics (esp. safe admin grant — brief R6) deferred to Stage 2. Behavioral-data retention
      deferred to signal-capture.
Decisions needed: None pending. (A1 resolved.)
Next: Software Architect reads the revised FEATURE_BRIEF.md + D-3/DL-2 and produces DESIGN.md —
      must design the single-access-method, extensible role model and a safe admin-grant path.
```

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

_None pending._

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
| 2026-06-14 | `1-define`→`2-design` | **Product Analyst** — user answered **A1** with role direction. Revised the brief to a **single access method + extensible role model** (user/developer/admin+future): 7 stories (added US7 admin), 10 G/W/T criteria (added AC9 admin-grant + AC10 single-access/extensibility), role-aware metrics/scope/constraints, new R6. Revised global **D-3** accordingly; logged **DL-2** (developer self-serve, admin granted). **Resolved** the editorial/admin escalation (editors auth via admin role through this feature; tooling stays in `editorial-curation-tools`). Approved → **handed off to Software Architect (2-design)**. |
| 2026-06-14 | `1-define`      | **Product Analyst** wrote [identity-accounts/FEATURE_BRIEF.md](features/identity-accounts/FEATURE_BRIEF.md) (6 stories, 8 G/W/T criteria, metrics, scope, 5 risks). Resolved 2 forks via user → **D-3** (one account, dual capability, global) + **DL-1** (open self-serve signup, local). Adopted data-minimization posture; escalated editorial/admin-account gap. **Awaiting brief approval** (A1) before Stage-2 handoff. |
| 2026-06-14 | `0-coordinator` | Resolved D1–D3. Logged niche (D-1) + no-constraints posture (D-2) in global [DECISIONS.md](DECISIONS.md); un-gated the identity-accounts privacy open question. **Activated `identity-accounts` into `1-define`** (by dependency order; signal-capture postponed). Handed off to Product Analyst — did not run Stage 1 (one persona per session). |
| 2026-06-13 | `0-coordinator` | Transformed [docs/mvp-component-breakdown.md](docs/mvp-component-breakdown.md) §4 into 11 scaffolded feature folders (7 artifacts each, briefs/open-questions seeded with breakdown facts + §7 questions); registered all in [features/INDEX.md](features/INDEX.md) as `backlog` in dependency-build order. No feature activated — that is D2 (user's call). |
| 2026-06-13 | `0-coordinator` | Decomposed the vision doc into separately-designable MVP components → [docs/mvp-component-breakdown.md](docs/mvp-component-breakdown.md). Recommends `signal-capture` as the first feature (informs D2); no decision taken. |
| 2026-06-13 | `0-coordinator` | Migrated `chain-of-thought.md` (14-step protocol → Architect persona) and `Design-strategy.md` (determinism rule + release-level DoD → CLAUDE.md §2/§6) into the personas/manual, then deleted both source files; personas are now self-contained specs. |
| 2026-06-13 | `0-coordinator` | Added `CODEMAP.md`, global `DECISIONS.md`, `features/INDEX.md`; wired code-reuse + global-decision tracking into the personas and CLAUDE.md. |
| 2026-06-13 | `0-coordinator` | Set up persona pipeline (CLAUDE.md, personas, folders). Awaiting D1–D3. |
