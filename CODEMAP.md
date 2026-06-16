# CODEMAP.md — Shared Code Index

**This is the durable channel for code reuse.** Before writing any shared helper,
type, or service, an agent checks here for one that already exists. After adding or
changing shared code, it records it here. This is the third durable channel alongside
[CONTROL.md](CONTROL.md) (process state) and [DECISIONS.md](DECISIONS.md) (rationale).

## Why this exists

Agents work one task at a time and cannot see what other sessions built. Left alone,
they re-create helpers that already exist — because **you cannot grep for a function
whose name you never thought of.** Surveying the whole codebase every session is also
expensive. A small, curated index solves both: it is cheap to read (one file) and it
surfaces reusable code you didn't know to search for.

## What belongs here

Only the **shared, reusable surface** — code meant to be used across features:

- Utility / helper functions (formatting, parsing, validation, math).
- Shared types, schemas, and constants (the canonical shape of a domain concept).
- Cross-cutting services and clients (data access, caching, auth, logging, config).
- Shared UI components, if any.

**What does NOT belong here:** feature-private code used in exactly one place, generated
code, or test fixtures. If it is not meant to be reused, it stays out of the index — a
bloated map is as useless as none.

## Convention: where shared code lives

Shared code lives under a single, known root (set when the stack is chosen in Stage 2 —
e.g. `shared/`, `lib/`, or `src/utils/`, recorded in [DECISIONS.md](DECISIONS.md)).
This keeps placement consistent so even a targeted search is scoped. The chosen root is
named here once it exists.

> Shared-code root: **`apps/`** — every feature is a Django app under it; cross-cutting
> reusable code lives in `apps/core/`, the canonical account/role surface in
> `apps/accounts/`. Set by `identity-accounts` Stage 2 (global [D-4](DECISIONS.md)).

## Format

One line per item, grouped by area. Keep entries to a signature/name, a one-line
purpose, and a path. Detail lives in the code, not here.

```
<name / signature> — <one-line purpose> — <path>
```

## Index

_No code exists yet — entries are added by the Engineer (Stage 4) as code is written._

**Planned shared surface (from [identity-accounts DESIGN.md](features/identity-accounts/DESIGN.md), pending Stage 4):**
- `Account` — canonical identity model (UUID id, email, display_name, roles) — `apps/accounts/models.py`
- `USER` / `DEVELOPER` / `ADMIN` — role-name constants — `apps/accounts/roles.py`
- `HasRole(role)` / `require_role(role)` — the one role-gate (DRF permission + view decorator) — `apps/accounts/permissions.py`
- `EmailSender.send(to, template, context)` — shared email interface (digest reuses) — `apps/core/email.py`

<!-- Example of the shape this takes once code exists:

### Utilities
- `formatRelativeDate(date) -> string` — "3d ago" style relative time — `shared/date.ts`
- `slugify(text) -> string` — URL-safe slug from arbitrary text — `shared/text.ts`

### Domain types
- `QualityScore` — canonical quality-score shape — `shared/ranking/types.ts`

### Services
- `fetchCatalog(niche) -> Catalog` — cached catalog read — `shared/catalog/service.ts`
-->

## Maintenance rules

- **The Engineer (Stage 4) keeps this current** — it is part of definition-of-done.
  Adding or changing shared code without updating this index is an incomplete task.
- **A stale index is worse than none.** Keep it to the shared surface only, so it stays
  small enough to trust.
- **The Retrospective Analyst (Stage 6) reconciles it against reality** at feature close,
  removing entries for deleted code and adding any shared helper that slipped through.
- When this file grows beyond comfortable reading, **partition it by area** (one map per
  top-level package) and keep this file as the index of indexes — mirroring how
  `features/` scales by folder.
