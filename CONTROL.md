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
| **Stage**          | `5-release`                                                    |
| **Persona**        | Release Engineer (see [phase-5-release-engineer.md](process/personas/phase-5-release-engineer.md)) |
| **Folder**         | [features/identity-accounts/](features/identity-accounts/)     |
| **Last updated**   | 2026-06-17                                                     |

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 4-build | Feature: identity-accounts | Persona: Senior Engineer
Done: Executed all 18 tasks (T-01…T-18). Stood up the Django/DRF/PostgreSQL project (config/ + apps/
      shared root), shared core (typed config, fail-loud EmailSender, rate-limit decorator,
      observability+health), the identity data model (Account/LoginToken/RoleGrant, UUID PKs, citext
      email, three role groups seeded by migration 0001), the single fail-closed role gate
      (HasRole/require_role + audited grant/revoke), risk-first magic-link issue/verify (hash-only,
      atomic single-use), and every endpoint+page: register, sign-in/verify/session, sign-out, profile
      view/edit, self-serve developer, account deletion, admin grant/revoke. Plus create_admin +
      purge_expired_tokens commands, security hardening (HttpOnly/Secure/SameSite cookies, CSRF, HSTS/
      SSL when not DEBUG, UUID-only logs), README + .env.example (every tunable) + deploy runbook, and
      TEST_PLAN.md mapping all 10 ACs.
Verified by: 108 automated tests pass (incl. a real 2-thread token double-spend race); `ruff check`
      clean; `manage.py check` clean; migration applied on a fresh PostgreSQL DB (citext + groups
      confirmed). TEST_PLAN.md shows 100% AC1–AC10 coverage; CODEMAP updated with the shared surface.
Blocked/Deferred: none new. Carried: concrete prod email provider (ops config — EMAIL_BACKEND),
      shared cache for rate limits in multi-worker prod (runbook note), rich SPA frontend (deferred),
      cross-feature account-deletion cascade (handed downstream, noted in runbook).
Decisions needed: none — Stage 5 (release) is unblocked.
Next: Release Engineer follows docs/deploy-identity-accounts.md (§12 order: migrate → create_admin →
      configure/verify email via /health → enable → schedule purge) and produces RELEASE_NOTES.md.
```

> **Deviation logged this session:** DL-5 — `issue_login_link` takes an `Account` (+ injected
> `base_url`/`email_sender`) instead of `(email, purpose)`; DESIGN §3 updated to match. No HTTP
> contract or schema change. See [features/identity-accounts/DECISIONS.md](features/identity-accounts/DECISIONS.md).

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

_None — Stage 5 (release) is unblocked. The build is complete and fully green._

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
| 2026-06-17 | `4-build`→`5-release` | **Senior Engineer** — built the whole feature from TASKS.md (T-01…T-18): Django/DRF/PostgreSQL scaffold; shared core (typed config, fail-loud `EmailSender`, rate-limit decorator, observability + `/health`); data model (`Account`/`LoginToken`/`RoleGrant`, UUID PKs, **citext** email, 3 role groups seeded in migration 0001); the **single fail-closed gate** (`HasRole`/`require_role` + audited `grant_role`/`revoke_role`); **risk-first magic-link** (hash-only, atomic single-use, **2-thread double-spend test**); all endpoints + server-rendered pages (register, sign-in/verify/session, logout, profile, self-serve developer, deletion, admin grant/revoke); `create_admin` + `purge_expired_tokens`; security hardening (cookies/CSRF/HSTS/SSL, UUID-only logs); README + `.env.example` + [deploy runbook](docs/deploy-identity-accounts.md); [TEST_PLAN.md](features/identity-accounts/TEST_PLAN.md) (all 10 ACs). **108 tests pass, ruff clean, `check` clean**, migration verified on fresh Postgres; CODEMAP updated. Logged **DL-5** (issue_login_link signature refinement; DESIGN §3 synced). **Handed off to Release Engineer (5-release).** |
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
