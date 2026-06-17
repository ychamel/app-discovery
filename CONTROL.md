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
| **Active feature** | `interest-taxonomy`                                            |
| **Stage**          | `4-build`                                                     |
| **Persona**        | Senior Engineer (see [phase-4-engineer.md](process/personas/phase-4-engineer.md)) |
| **Folder**         | [features/interest-taxonomy/](features/interest-taxonomy/)     |
| **Last updated**   | 2026-06-17 (A5 approved → TASKS.md written; handed to Senior Engineer for build) |

> **`identity-accounts` closed out 2026-06-17** at user request — Stage 6 (retrospective)
> **skipped**. Build/release artifacts stand (108 tests green, released local/dev basis);
> live-metric measurement + outcome report remain deferred (R1). Reopen Stage 6 later if
> an outcome review is wanted.

> Canonical stage values: `0-coordinator` · `1-define` · `2-design` · `3-plan` ·
> `4-build` · `5-release` · `6-post-release` · `done`. See the routing table in
> [CLAUDE.md](CLAUDE.md) §2.

### Latest session status (CLAUDE.md §6.7 — overwritten each session)

```
Stage: 3-plan → 4-build | Feature: interest-taxonomy | Persona: Planner / Tech Lead (handoff)
Done: A5 approved → decomposed DESIGN.md into features/interest-taxonomy/TASKS.md: 10 ordered,
      independently verifiable tasks (all S/M, no L) in build order — scaffold (T-01) → models +
      migration (T-02) → write service + invariants + 3 error types (T-03) → cycle-guarded
      selectors/resolve_tag (T-04) → JSON read API (T-05) → seed file + seed_taxonomy (T-06) →
      check_taxonomy (T-07) → Django admin via services (T-08) → author founding vocabulary +
      size band (T-09) → docs/CODEMAP/D-5 (T-10). Risk front-loaded: the two sharpest edges from
      DESIGN §13 (write-service invariants ≥1-cluster/dedupe/safe-retire, and the cycle-guarded
      replaced_by resolution) are T-03/T-04, tested in isolation before any HTTP/admin surface.
      Each task has a DoD, declared files (no collisions), deps, and DESIGN/AC refs. Coverage table
      maps every DESIGN element (§2–§14) + all 8 ACs to ≥1 task. Reuses apps/core (observability/
      config/middleware) + accounts admin gate by name; modifies no existing component.
Verified by: n/a (Stage 3 — planning only, no code). TASKS.md coverage table is the exit-criterion check.
Blocked/Deferred: (1) FOUNDING-CATALOG (T-09) — DESIGN §12 sizes the vocabulary against "the real
      founding catalog," but no app catalog exists yet (it comes from submission-intake, downstream of
      this Phase-0 root). Planner decision: author T-09 against the niche definition + app archetypes;
      app-coverage validation vs a real catalog is DEFERRED until submission-intake lands (mirrors the
      R1 live-metrics deferral). Surfaced below — does NOT block Stage 4. (2) identity-accounts Stage 6
      outcome report + live metrics (deferred, reopenable).
Decisions needed: none blocking. The founding-catalog deferral is flagged for visibility (Decisions
      Made), not as a gate — say so if you'd rather pause T-09 until real app data exists.
Next: Senior Engineer (4-build) executes TASKS.md T-01→T-10, produces code + TEST_PLAN.md covering
      AC1–AC8, keeps CODEMAP current. Start at T-01 (scaffold).
```

> **Handoff (2026-06-17):** Planner / Tech Lead → **Senior Engineer (`4-build`)**. A5 approved;
> TASKS.md complete (10 tasks, all S/M, full DESIGN/AC coverage, risk front-loaded). Build executes
> T-01→T-10 in order; each leaves the system working and releasable.

> **Planner deferral flagged (2026-06-17):** the founding-vocabulary sizing (T-09 / OQ-3) is authored
> against the **niche definition + representative app archetypes**, not a real submitted app catalog
> (none exists pre-`submission-intake`). App-coverage validation vs a real catalog is **deferred and
> reopenable**, exactly as `identity-accounts` deferred live metrics (R1). Recorded in TASKS.md T-09;
> not a Stage-4 blocker.

---

## Decisions Needed From You

The agent is blocked on these. Answer inline (edit the **Answer** cell), then the agent
proceeds.

**None blocking.** A5 resolved below; the Planner's founding-catalog deferral (T-09) is logged
under *Decisions Made* for visibility — speak up if you'd rather pause T-09 until real app data
exists, otherwise the Senior Engineer proceeds against the niche definition.

> **A5 — resolved 2026-06-17.** User **approved** the `interest-taxonomy`
> [DESIGN.md](features/interest-taxonomy/DESIGN.md) as written (shape = flat tags + named clusters
> via M2M; UUID stable identity; soft-retire + read-time `resolve_tag`; seed-file/command/Django-admin
> management; OQ-3 size band left to Stage 4). The Planner decomposed it into
> [TASKS.md](features/interest-taxonomy/TASKS.md) (10 ordered S/M tasks, full DESIGN/AC coverage,
> risk front-loaded) and handed off to **Stage 4 (Senior Engineer)**.
>
> **A4 — resolved 2026-06-17.** User **approved** the `interest-taxonomy`
> [FEATURE_BRIEF.md](features/interest-taxonomy/FEATURE_BRIEF.md) — all 5 "For confirmation at
> approval" calls confirmed (closed/curated vocabulary; clusters-in-MVP + adjacency-deferred-not-
> precluded; taxonomy shape left to Stage-2 under AC8; English-only at MVP; vocabulary+lifecycle here
> / rich curation UI in `editorial-curation-tools`). Logged as feature-local **ITX-1…ITX-5** in
> [features/interest-taxonomy/DECISIONS.md](features/interest-taxonomy/DECISIONS.md). Advanced to
> **Stage 2 (Software Architect)**.
>
> **R1 — resolved 2026-06-17.** User: *"we're only deploying locally at the moment, since
> we're still mid development."* → **Option A.** Release artifacts accepted as the
> deliverable; identity-accounts is released to the **local/dev** target (migrations apply,
> `/health` green, 108 tests). **Production promotion + live-metrics monitoring window are
> deferred** until the platform approaches launch (RELEASE_NOTES §5). Advanced to
> **Stage 6 (Retrospective Analyst)** — its outcome review runs against ACs / build quality
> / release readiness, with live-metric measurement explicitly deferred to the future prod
> promotion.
>
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
- **PL-1 (Planner deferral, 2026-06-17) → founding-vocabulary sizing is authored against the niche definition + app archetypes, not a real catalog.** DESIGN §12 sizes the vocabulary (OQ-3) against "the real founding catalog," but no app catalog exists yet — it is produced by `submission-intake`, downstream of this Phase-0 root. The Senior Engineer authors T-09 from the niche definition (D-1) + representative app archetypes; **app-coverage validation against a real submitted catalog is deferred and reopenable** (same pattern as the identity-accounts R1 live-metrics deferral). Flagged for visibility; not a Stage-4 blocker. Recorded in [TASKS.md](features/interest-taxonomy/TASKS.md) T-09.
- **ITX-1…ITX-5 → `interest-taxonomy` brief calls, approved at A4 (2026-06-17).** Closed/editorially-curated vocabulary (not folksonomy); clusters in MVP, adjacency deferred but not precluded (AC8); **taxonomy shape left to the Architect** under AC8; English-only at MVP; this feature owns vocabulary+lifecycle, rich curation UI lives in `editorial-curation-tools`. Feature-local; logged in [features/interest-taxonomy/DECISIONS.md](features/interest-taxonomy/DECISIONS.md).

---

## Activity Log

Newest first. One line per session. **Keep the most recent ~10 rows here**; when it
grows past that, move older rows to `process/activity-archive.md` so this dashboard
stays quick to scan. The per-feature folders remain the full record either way.

| Date       | Stage           | Summary                                                                 |
|------------|-----------------|-------------------------------------------------------------------------|
| 2026-06-17 | `3-plan`→`4-build` | **Planner / Tech Lead** — A5 approved → decomposed [DESIGN.md](features/interest-taxonomy/DESIGN.md) into [TASKS.md](features/interest-taxonomy/TASKS.md): **10 ordered, independently verifiable tasks (all S/M, no L)** in build order — scaffold (T-01) → models+migration (T-02) → **write service + invariants + 3 error types (T-03)** → **cycle-guarded selectors/`resolve_tag` (T-04)** → JSON read API (T-05) → seed file + `seed_taxonomy` (T-06) → `check_taxonomy` (T-07) → Django admin via services (T-08) → author founding vocabulary + size band (T-09) → docs/CODEMAP/D-5 (T-10). **Risk front-loaded** (the DESIGN §13 sharp edges — ≥1-cluster/dedupe/safe-retire invariants and the `replaced_by` cycle guard — land in T-03/T-04, tested in isolation before any HTTP/admin surface). Each task has a DoD, declared files (no collisions), deps, DESIGN/AC refs; coverage table maps every §2–§14 element + all 8 ACs to ≥1 task. **Reuses** `apps/core` (observability/config/middleware) + accounts admin gate by name; modifies no existing component. **Flagged Planner deferral PL-1** — founding-vocabulary sizing (T-09/OQ-3) authored vs the niche definition + app archetypes (no real catalog exists pre-`submission-intake`); app-coverage-vs-real-catalog validation deferred & reopenable (R1 pattern), not a Stage-4 blocker. **Handed off to Senior Engineer (4-build).** |
| 2026-06-17 | `2-design`      | **Software Architect** — ran the 14-step protocol → wrote [DESIGN.md](features/interest-taxonomy/DESIGN.md) for `interest-taxonomy`. Resolved all four handed-down items: **shape** = flat tags + named **clusters** via M2M (no tag hierarchy), adjacency deferred as a future cluster-to-cluster table (additive, **no re-tag** — AC8); **stable identity** = UUID `id` (downstream stores UUID, never label/slug; rename = label-only → 0 broken refs, AC6/AC7); **retire rule (OQ-2)** = soft-retire + optional `replaced_by`, non-destructive read-time `resolve_tag`; **mgmt surface (OQ-1)** = editable `seed/vocabulary.yaml` + idempotent `seed_taxonomy` command + Django admin, **no custom curation UI**; **size band (OQ-3)** deferred to Stage 4 vs the real founding catalog. New app `apps/taxonomy/` **reuses** the stack (D-4), `apps/core` observability/config, and the accounts `admin` gate — no new auth path. Logged global **[D-5](DECISIONS.md)** (shape + cross-feature reference contract) + feature-local **ITX-6/7/8**; closed Q5/OQ-1/OQ-2/OQ-3. All 8 ACs traced; no "TBD". **Awaiting design approval (A5)** — stayed in `2-design` (one persona/session). |
| 2026-06-17 | `1-define`→`2-design` | **Product Analyst** (handoff) — user **approved** the `interest-taxonomy` brief (**A4**), confirming all 5 "For confirmation at approval" calls. Recorded them as feature-local **ITX-1…ITX-5** in [DECISIONS.md](features/interest-taxonomy/DECISIONS.md) (closed/curated vocabulary; clusters-in-MVP + adjacency-deferred-but-not-precluded; **taxonomy shape left to Stage-2 under AC8**; English-only at MVP; vocabulary+lifecycle here / rich curation UI in `editorial-curation-tools`). Marked the brief APPROVED, advanced [INDEX.md](features/INDEX.md) + CONTROL Current State to **`2-design`**, resolved A4. Carried 3 open items to the Architect (Q5/OQ-1 shape + seed/maintain boundary, OQ-2 retired-tag rule, OQ-3 size band). **Handed off to Software Architect (2-design);** did not start Stage-2 design (one persona per session). |
| 2026-06-17 | `1-define`      | **Product Analyst** — wrote [interest-taxonomy/FEATURE_BRIEF.md](features/interest-taxonomy/FEATURE_BRIEF.md). Framed the feature as the **single shared controlled vocabulary** (tags + clusters) that both user interests and app labels are expressed in — explicitly **not** owning user selection (`interest-profile`), app tagging (`submission-intake`), or the matching algorithm. 6 stories, 8 G/W/T criteria, 6 enabler metrics (app/user **coverage**, cluster integrity, non-redundancy, **reference-break-rate = 0**, size band), in/out scope, constraints, 5 risks (under/over-scope, **shape lock-in**, no stable identity, drift). Deliberately **did not pick the taxonomy shape** (flat vs shallow hierarchy — breakdown §7 Q5); left it to Stage-2 design under a hard constraint — **AC8: adjacency addable later without destructive migration** — and fixed **stable tag identity (AC7)** + **safe rename/retire (AC6)** as product requirements. Logged Q5 handling + 3 open questions (mgmt-surface boundary, retired-tag rule, size band) in [OPEN_QUESTIONS.md](features/interest-taxonomy/OPEN_QUESTIONS.md). **Awaiting brief approval (A4)** before Stage-2 handoff; stayed in `1-define` (one persona per session). |
| 2026-06-17 | `0-coordinator` | **Coordinator** — user opted to **skip identity-accounts Stage 6** (retrospective) and move on; closed it out (build/release artifacts stand, outcome review deferred & reopenable). Selected the next feature by dependency order: **`interest-taxonomy`** (Phase-0 Foundation, no deps, enabler for submission-intake / interest-profile / editorial-curation-tools); `signal-capture` stays postponed (D2). Verified its folder is scaffolded (brief still _pending_) and **activated it into `1-define`** — updated CONTROL.md Current State + [INDEX.md](features/INDEX.md). **Handed off to Product Analyst (1-define);** did not run Stage 1 (one persona per session). |
| 2026-06-17 | `5-release`     | **Release Engineer** — worked the release checklist and wrote [RELEASE_NOTES.md](features/identity-accounts/RELEASE_NOTES.md): what changed / who's affected / how to deploy (per [runbook](docs/deploy-identity-accounts.md) + DESIGN §12), **gate-based rollout** (no phased flag — first feature; safety = reversible migration + ordered procedure), **rehearsed rollback**, monitoring→brief-metric mapping (alert on auth-error spikes, `email_send_failure`, **any `admin_role_change`**), and known limitations. Re-verified green: **108 tests**, `ruff`/`check` clean, `makemigrations --check` no drift. **Genuinely rehearsed the rollback** on a throwaway Postgres DB (apply 0001 → 5 tables + citext + 3 groups; `migrate accounts zero` → 0 tables/0 groups, reversible). *(Caught & fixed a self-inflicted slip: an initial rehearsal used the wrong env var and rolled back the dev `identity` DB; restored it immediately, then redid the rehearsal correctly on a scratch DB.)* **Surfaced R1** (no live prod → persona exit criteria can't be met by me); user resolved **Option A** — *"deploying locally, still mid development"*, so released on a **local/dev basis** with prod promotion + live metrics deferred. Updated RELEASE_NOTES §5 with the local-target framing. **Handed off to Stage 6 (Retrospective Analyst).** |
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
