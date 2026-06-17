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

_Built by `identity-accounts` Stage 4. Entries are added as each shared item ships._

### Configuration (`apps/core/config.py`)
- `login_token_ttl() -> timedelta` — magic-link token lifetime (default 15 min) — `apps/core/config.py`
- `rate_limit_per_email_per_hour() -> int` — auth-request cap per email (default 5) — `apps/core/config.py`
- `rate_limit_per_ip_per_hour() -> int` — auth-request cap per client IP (default 20) — `apps/core/config.py`
- `taxonomy_resolve_max_steps() -> int` — max replaced_by hops `resolve_tag` follows before bailing on a cycle (default 16) — `apps/core/config.py`
- `validate_all()` — evaluate all tunables at startup (fail loud) — `apps/core/config.py`

### Email (`apps/core/email.py`)
- `EmailSender` (Protocol) / `DefaultEmailSender` — pluggable, fail-loud email send (digest reuses) — `apps/core/email.py`
- `get_email_sender() -> EmailSender` — factory seam for the configured sender — `apps/core/email.py`
- `EmailSendError` — raised when a send cannot be handed to the transport — `apps/core/email.py`

### Rate limiting (`apps/core/ratelimit.py`)
- `rate_limited` (decorator) — enforce per-email + per-IP hourly limits, `429` over cap (no-op on safe methods) — `apps/core/ratelimit.py`

### Observability (`apps/core/observability.py`, `apps/core/middleware.py`)
- `increment(metric, **tags)` — emit a counter event (pluggable; logs today) — `apps/core/observability.py`
- metric name constants (`REGISTRATION_COMPLETION`, `SIGNIN_SUCCESS`, `AUTH_ERROR`, `ROLE_GATE_DECISION`, `EMAIL_SEND_FAILURE`, `DELETION_FULFILMENT`, `DEVELOPER_ROLE_ADOPTION`, `ADMIN_ROLE_CHANGE`, `SIGNOUT`) — `apps/core/observability.py`
- taxonomy metric constants (`TAXONOMY_TAG_ADDED`, `TAXONOMY_TAG_RENAMED`, `TAXONOMY_TAG_RETIRED`, `TAXONOMY_REFERENCE_BREAK`, `TAXONOMY_INTEGRITY_VIOLATION`) — `apps/core/observability.py`
- `check_health() -> dict` — DB + email reachability (backs `/health`) — `apps/core/observability.py`
- `RequestContextFilter` + `RequestContextMiddleware` — inject request id + account UUID into logs — `apps/core/observability.py`, `apps/core/middleware.py`

### Identity model (`apps/accounts/models.py`)
- `Account` — canonical cross-feature identity (UUID id, citext email, display_name, roles via groups; passwordless) — `apps/accounts/models.py`
- `Account.objects.create_account(email, display_name)` — the one account-creation path (sets unusable password) — `apps/accounts/managers.py`
- `LoginToken` — single-use magic-link credential (hash only) — `apps/accounts/models.py`
- `RoleGrant` — append-only grant/revoke audit row (SET_NULL FKs survive deletion) — `apps/accounts/models.py`

### Roles & authorization (`apps/accounts/`)
- `USER` / `DEVELOPER` / `ADMIN` / `BASE_ROLE` / `SELF_SERVE_ROLES` — role-name constants & policy — `apps/accounts/roles.py`
- `account_roles(account) -> list[str]` — role names an account holds — `apps/accounts/roles.py`
- `account_has_role(user, role) -> bool` — the one fail-closed gate decision — `apps/accounts/permissions.py`
- `HasRole(role)` — DRF permission class factory — `apps/accounts/permissions.py`
- `require_role(role)` — Django view decorator (raises 403 when denied) — `apps/accounts/permissions.py`
- `grant_role` / `revoke_role` — audited role change (writes RoleGrant atomically) — `apps/accounts/services.py`
- `UnknownRoleError` — raised for a role with no group (→ 400) — `apps/accounts/services.py`

### Interest vocabulary — model (`apps/taxonomy/models.py`)
- `Tag` — one vocabulary unit; UUID `id` is the stable cross-feature reference, `slug`/`label`/`status`/`replaced_by`/`clusters` — `apps/taxonomy/models.py`
- `Cluster` — a named grouping of related tags (anchor for future adjacency) — `apps/taxonomy/models.py`
- `CanonicalLabel` — SQL Func for a label's case/whitespace-insensitive duplicate-detection form — `apps/taxonomy/models.py`

### Interest vocabulary — write surface (`apps/taxonomy/services.py`, admin-only single mutate path)
- `add_tag` / `rename_tag` / `retire_tag` — tag lifecycle (≥1 cluster, dedupe, soft-retire + successor) — `apps/taxonomy/services.py`
- `update_tag` — idempotent sync of an existing tag's label/definition/membership (seed path; no-op when unchanged) — `apps/taxonomy/services.py`
- `add_cluster` / `rename_cluster` / `update_cluster` / `assign_to_cluster` / `remove_from_cluster` — cluster + membership writes (refuses to orphan an active tag) — `apps/taxonomy/services.py`
- `check_integrity() -> IntegrityReport` — scan for orphan active tags, empty clusters, duplicate labels — `apps/taxonomy/services.py`
- `DuplicateTagError` / `OrphanTagError` / `RetireSuccessorError` — loud write-service failures — `apps/taxonomy/errors.py`

### Interest vocabulary — read surface (`apps/taxonomy/selectors.py`, the cross-feature substrate — D-5)
- `list_active_tags()` / `list_clusters()` — active vocabulary with membership prefetched (no N+1) — `apps/taxonomy/selectors.py`
- `get_tag(id) -> Tag | None` — fetch a tag of any status — `apps/taxonomy/selectors.py`
- `is_valid_tag(id) -> bool` — closed-set validator: True only for an active tag (consumers enforce at their write boundary, AC2) — `apps/taxonomy/selectors.py`
- `resolve_tag(id) -> Tag | None` — follow `replaced_by` to current meaning; keeps retired refs, cycle-guarded (AC6/AC7) — `apps/taxonomy/selectors.py`

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
