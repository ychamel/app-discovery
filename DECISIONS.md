# DECISIONS.md — Global Decision Log (ADRs)

**This is the durable channel for repo-wide rationale.** It records decisions that
outlive any single feature — the ones a future feature's Architect must not have to
re-derive or accidentally contradict.

## Global vs. per-feature decisions

- **Here (global):** the tech stack, the shared-code root, the ranking algorithm, the
  beachhead niche, data-store choice, auth model, cross-cutting conventions — anything
  that constrains *more than one* feature.
- **In `features/<slug>/DECISIONS.md` (local):** choices scoped to one feature that no
  other feature needs to know about.

Rule of thumb: **if a later feature would be wrong to contradict it, it belongs here.**
A global decision buried in one feature's folder is invisible to the next feature — that
is exactly the drift this file prevents.

## Format (one ADR per entry, newest first)

```
### D-<n>: <short title>
- **Date:** YYYY-MM-DD
- **Stage / feature:** <where it was made>
- **Decision:** <what was chosen>
- **Why:** <the reasoning>
- **Alternatives rejected:** <≥1 genuinely different option + why not>
- **Sacrifices / consequences:** <what this costs us>
```

A confirmed global decision is also summarized in [CONTROL.md](CONTROL.md)
*Decisions Made (recently)* as a one-line, human-readable digest.

## Decisions

### D-5: Interest-taxonomy shape & cross-feature tag-reference contract
- **Date:** 2026-06-17
- **Stage / feature:** `2-design` / `interest-taxonomy` (Software Architect) — **pending design approval (A5)**
- **Decision:** The shared interest vocabulary is modeled as **flat tags + named clusters joined by a many-to-many membership** (no tag→tag hierarchy; a tag may belong to one *or more* clusters). The **stable cross-feature reference to a tag is its UUID `id`** — never its display label and never its (internal, immutable) `slug`. Every feature that records an interest/label (**`interest-profile`, `submission-intake`, the matcher, `editorial-curation-tools`**) must: **store the `Tag.id`**; **validate** supplied values at its write boundary with the taxonomy's `is_valid_tag(id)` (reject off-vocabulary input — no tag coining); and **resolve** at read with `resolve_tag(id)` (which transparently follows renames and retire/merge successors, and never drops a reference). **Clusters are first-class from day one** so that future **cluster-to-cluster adjacency** (ring-based expansion, vision §2.2) is a purely additive table over existing clusters — **no re-tagging, no destructive migration** (AC8). Tags are **retired (soft), never hard-deleted**, so stored references stay valid (reference-break-rate = 0).
- **Why:** Matching only works if both sides speak one language drawn from one closed dictionary (brief). A label-independent UUID reference is the only thing that keeps stored interests/app-labels valid across editorial renames and merges (R4, AC6/AC7). Making clusters first-class now is the cheap insurance against the Coordinator's named future change (rings) without over-building adjacency today (ITX-2, AC8). This is global because **more than one later feature would be wrong to contradict it** (store-by-label, coin off-vocabulary tags, or hard-delete tags would each break the substrate).
- **Alternatives rejected:** (a) **Single-cluster FK on each tag** — simpler, but the brief requires "one *or more* clusters" and it forecloses a tag spanning clusters. (b) **Arbitrary tag→tag hierarchy** — over-scope (R2); adjacency is a *cluster*-level relation, so a tag tree buys nothing AC8 needs and adds traversal cost. (c) **Hard-delete on retire / rewrite downstream references on merge** — both break stored references (reference-break-rate > 0) and the merge-rewrite touches tables this feature does not own; rejected for non-destructive read-time resolution. (d) **Reference tags by label/slug string** — defeats safe rename; rejected. Full rationale in [features/interest-taxonomy/DESIGN.md](features/interest-taxonomy/DESIGN.md) §7/§13.
- **Sacrifices / consequences:** Downstream features take a per-dereference `resolve_tag` lookup (vs caching) — accepted at MVP scale, with a cached projection as the documented growth path. The "≥1 cluster per active tag" invariant cannot be a single DB constraint, so it is enforced at the one write path + a `check_taxonomy` check rather than in the schema. No dedicated audit table ships here (lifecycle state on rows + observability + Django-admin LogEntry); a rich audit lands with `editorial-curation-tools`. The contract published here (`Tag.id`, `is_valid_tag`, `resolve_tag`, `list_active_tags`, cluster membership) is the stable cross-feature surface and is additive-only by design.

### D-4: Tech stack — Django + DRF + PostgreSQL; shared-code root `apps/`
- **Date:** 2026-06-14
- **Stage / feature:** `2-design` / `identity-accounts` (Software Architect)
- **Decision:** The platform is built on **Python 3.12+ / Django 5.x** with **Django REST Framework** for JSON APIs and **PostgreSQL 15+** as the datastore (Django ORM + migrations). Authentication is **passwordless email magic-link** over **Django server-side sessions**; authorization uses **Django `Group`s as roles** enforced through a single permission point. Email delivery is a **pluggable interface** (`apps/core/email.py`) whose concrete provider is ops/env config, not code. The **shared-code root is `apps/`**: every feature is a Django app under it, with cross-cutting reusable code in `apps/core/` and the canonical account/role surface in `apps/accounts/`. For this feature the UI is **server-rendered Django templates**; a richer SPA frontend is deferred until a surface needs one (not chosen here).
- **Why:** Chosen by the user for Python familiarity and as the strongest base for the later **data/ML-heavy** internal engine (Quality-Score pipeline, matching/ring computation, integrity graph analysis — all §3/§4/§6 of the vision), which lives most naturally in Python. Django's batteries-included auth, sessions, groups/permissions, ORM, migrations, and admin minimize hand-rolled, security-sensitive code (CLAUDE.md §5.4 fail-loud, §5.5 boring-and-well-understood). PostgreSQL covers relational identity now and the relational/analytic needs of later features.
- **Alternatives rejected:** (a) **TypeScript full-stack** (Next.js + Auth.js + Postgres) — viable and lower-wiring for the web surfaces, but the user preferred Python and JS is a weaker base for the ML/graph internal engine. (b) **Framework-light TS API** (Fastify + separate SPA) — cleanest boundaries but requires hand-built auth/session glue (more security surface to get wrong) for no MVP benefit. Both logged so a later feature does not re-litigate the stack.
- **Sacrifices / consequences:** Two languages once a rich SPA frontend is added (Python backend + JS frontend); accepted because identity-accounts needs no SPA yet. Django's monolith-first shape means we accept a **modular monolith** now — the documented growth path is extracting services at scale, a deliberate bounded trade-off (D-2 / CLAUDE.md §5.2). The account+role contract published here (`Account.id`, `Account.email`, `HasRole`/`require_role`, role constants) is the stable cross-feature API every later feature builds on; it is additive-only by design.

### D-3: Identity model — one account, one access method, role-based authorization
- **Date:** 2026-06-14 *(revised 2026-06-14 per user A1 direction — generalized from "dual capability (reader + developer)" to an extensible role model; no downstream feature had consumed the prior wording yet)*
- **Stage / feature:** `1-define` / `identity-accounts` (Product Analyst)
- **Decision:** A person has a **single account** and a **single way to sign in**, regardless of what they are allowed to do. What an account may do is governed by the **roles** it holds. The MVP defines three roles — **user** (the base role every account has: discover apps, receive/open the curated digest), **developer** (submit and own apps), and **admin** (privileged internal/editorial/operations actions) — and the model is **extensible** so future roles can be added without a new access method or a redesign of authentication. An account may hold more than one role (e.g. user + developer). The **developer** role is self-serve (any account may take it — DL-1); the **admin** role is **not** self-serve and is granted only to authorized staff.
- **Why:** The beachhead niche is vibecoded webapps (D-1), where the same solo/tiny-team person is routinely both a discoverer and a builder, so one identity avoids fragmented logins and keeps a person's history unified. Modelling permitted actions as roles (rather than a fixed reader/developer pair) is the simpler, more scalable choice (CLAUDE.md §5.2): the platform already needs privileged editorial/operations access, and a single extensible role system absorbs that — and any later role — without a second identity system or a separate admin login.
- **Alternatives rejected:** (a) Separate user and developer accounts — forces the niche's core persona to maintain two identities and splits their signal/history. (b) A fixed two-capability flag (the prior D-3 wording) — would have required a *second* identity/access mechanism the first time the platform needed admins or any third role, contradicting "design for change" (§5.2). (c) A separate out-of-band admin login — duplicates the auth surface and the account model for no benefit.
- **Sacrifices / consequences:** Cross-feature contract: `submission-intake`, `signal-capture`, `interest-profile`, `developer-dashboard`, and `editorial-curation-tools` must key off one account whose permitted actions are gated on **roles** (not on a separate account type or login). Every privileged surface authenticates through this one feature and checks an `admin` role; `editorial-curation-tools` builds the admin *tooling*, not a parallel identity system. Role *assignment* mechanics (how a role is granted, especially admin) are a Stage-2 design concern. Team/organization accounts remain out of scope at MVP. The added generality is a deliberate, bounded cost justified by an already-known need (admin) plus a named likely change (future roles), not speculation (§5.5).

### D-2: No hard launch constraints at MVP — start small, scale as we go
- **Date:** 2026-06-14
- **Stage / feature:** `0-coordinator` (resolving CONTROL.md D3)
- **Decision:** No fixed deadline, budget, platform, or compliance/privacy ceiling is imposed up front. The guiding posture is to build the smallest honest slice first and grow capacity (data, users, infra) incrementally.
- **Why:** The MVP's job is to validate H1–H3 cheaply (breakdown §1). Premature hard constraints would over-specify non-functional targets before we have real load or a chosen stack.
- **Alternatives rejected:** Fixing a launch deadline / infra budget now — rejected because there is nothing yet to size against; it would be guesswork that later features would be wrong to treat as binding.
- **Sacrifices / consequences:** Non-functional targets (scale, latency, retention/consent specifics) are **deferred to each feature's Stage 1–2**, not given globally. "Scale as we go" is a posture, **not** a licence to ship hacks — CLAUDE.md §5.2 (designs must still work at 100×, or document the bounded trade-off) still binds. Privacy/compliance posture for behavioral data remains an explicit open design fork (breakdown §7 Q4), now un-gated but unresolved.

### D-1: Beachhead niche is "vibecoded webapps"
- **Date:** 2026-06-14
- **Stage / feature:** `0-coordinator` (resolving CONTROL.md D1)
- **Decision:** The single launch vertical is **vibecoded webapps** — small web applications built rapidly (often AI-assisted / "vibe coding") by solo developers and tiny teams.
- **Why:** The design mandates a sequenced narrow launch with one beachhead niche (vision §5.4, breakdown §2). This niche is rich in exactly the platform's target persona — unknown solo devs with $0 marketing shipping real apps — making it the cheapest honest test of the one-line north star (breakdown §1).
- **Alternatives rejected:** Indie productivity tools / indie games on a single platform (the breakdown's example niches) — rejected in favour of vibecoded webapps because web apps need no app-store gatekeeper or per-platform install flow, lowering the bar for both submission and the cross-platform attribution prototype.
- **Sacrifices / consequences:** Scopes the **content**, not the component structure (components are niche-agnostic, breakdown §6). Directly shapes `interest-taxonomy` (tag vocabulary), `submission-intake` (what "an app" is + the objective gate), and the founding catalog. Web-only at MVP means native-install attribution is out of scope for now; if the platform later expands beyond web, `signal-capture` attribution must be revisited.
