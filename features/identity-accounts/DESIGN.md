# DESIGN — identity-accounts

*Stage 2 artifact (Software Architect). Status: **approved 2026-06-17 (A3)** — handed off to
Stage 3 (Planner → [TASKS.md](TASKS.md)). Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md),
global [DECISIONS.md](../../DECISIONS.md) (D-1/D-2/D-3, and new D-4 set here),
feature [DECISIONS.md](DECISIONS.md), [CODEMAP.md](../../CODEMAP.md) (empty — greenfield),
vision [§6](../../curated-app-platform-design.md). Produced by the 14-step protocol in
[phase-2-architect.md](../../process/personas/phase-2-architect.md).*

---

## 0. Reasoning trace (14-step protocol — condensed)

The protocol is the method; §1–§12 below are its output. Only the non-obvious steps are
recorded here; the rest are realized in the contract sections.

1. **SCOPE.** Give every person one email-based identity, signed in one way, whose
   permitted actions are governed by extensible roles — the foundation every other MVP
   feature keys off. Lifespan = **platform** (cross-feature substrate); effort is sized
   accordingly. OUT: auth UI richness, OAuth/MFA, admin *tooling*, behavioral data.
2. **REQUIREMENTS.** Functional = the 10 ACs. Non-functional = D-2 (no hard targets, but
   must hold at 100× or document the bounded trade-off). Key **unverified** assumptions
   carried from the brief and resolved here: *auth mechanism* (→ §8 magic-link),
   *email-delivery dependency* (→ §6 pluggable interface, concrete provider is ops config),
   *role mechanics* (→ §3/§5 Django Groups + two grant paths).
3. **CONTEXT.** Greenfield — no code, empty CODEMAP. This feature **sets** the stack
   (D-4), the shared-code root, and the cross-feature account+role contract. Nothing to
   reuse; everything written here becomes the thing later features reuse.
9. **TRADE-OFFS.** Two genuine forks decided below: stack (Django vs TS full-stack vs
   framework-light TS — §7 / D-4, user chose Django) and auth mechanism (magic-link vs
   passwords — §8 / DL-3). The chosen design **sacrifices** a rich SPA frontend now
   (server-rendered pages) and accepts a modular-monolith (documented bounded trade-off).
13. **SELF-CRITIQUE.** See §13 — enumeration trade-off, first-admin bootstrap, and the
    cross-feature account-deletion contract are the three sharp edges; each is resolved or
    explicitly handed downstream.

---

## 1. Current-state summary

The repository is **greenfield**: no source code, no chosen stack, an empty
[CODEMAP.md](../../CODEMAP.md), and no shared-code root. The only fixed inputs are the
global decisions (D-1 niche, D-2 no-hard-constraints, D-3 one-account/one-access-method/
role-based authorization) and this feature's brief. Therefore this design does not modify
existing components — it **establishes** them: the tech stack (→ global D-4), the project
layout and shared-code root, and the canonical *Account + Role* contract that
`submission-intake`, `signal-capture`, `interest-profile`, `developer-dashboard`, and
`editorial-curation-tools` will all build on.

---

## 2. Tech stack & project layout  *(global decision — see D-4)*

| Concern        | Choice                                                                 |
|----------------|-----------------------------------------------------------------------|
| Language       | Python 3.12+                                                           |
| Web framework  | Django 5.x (server-rendered pages for this feature's surfaces)         |
| API layer      | Django REST Framework (DRF) — JSON contracts for downstream consumers  |
| Database       | PostgreSQL 15+ (Django ORM + migrations)                               |
| Auth model     | **Passwordless magic-link** + Django server-side sessions (see §8/DL-3)|
| Authorization  | **Django Groups as roles** + one DRF permission class (see §5/DL-4)    |
| Email delivery | Pluggable `EmailSender` over Django's email backend (see §6)           |

Rationale, alternatives, and sacrifices are recorded in global **[D-4](../../DECISIONS.md)**.

**Project layout** (shared-code root = `apps/`, recorded in CODEMAP):

```
config/                  ← Django project: settings, root urls, asgi/wsgi
apps/                    ← SHARED-CODE ROOT (every feature is a Django app here)
  core/                  ← cross-cutting shared surface (not feature-specific)
    email.py             ← EmailSender interface + default backend impl  (shared)
    config.py            ← typed access to tunables (TTLs, limits)        (shared)
  accounts/              ← THIS feature
    models.py            ← Account (custom User), LoginToken, RoleGrant
    roles.py             ← role-name constants: USER, DEVELOPER, ADMIN    (shared)
    permissions.py       ← HasRole DRF permission + require_role decorator (shared)
    auth_backend.py      ← magic-link token issue/verify
    views.py / urls.py   ← endpoints (§5) + server-rendered pages (§9)
    templates/accounts/  ← register, check-email, verify, profile pages
    management/commands/
      create_admin.py     ← first-admin bootstrap (cold start, §10)
      purge_expired_tokens.py
manage.py
pyproject.toml
```

The four items marked **(shared)** are the cross-feature reusable surface this feature
publishes; they are registered in [CODEMAP.md](../../CODEMAP.md) (entries added by the
Engineer in Stage 4 when the code exists).

---

## 3. Proposed architecture (components & responsibilities)

Each component has one responsibility, is testable in isolation, and depends only toward
more stable components (models ← services ← views). Roles are modeled as **Django
`Group`s**, so "add a role" never touches the auth path (AC10).

| Component | Owns (single responsibility) | Exposes | Hides |
|-----------|------------------------------|---------|-------|
| **Account model** (`accounts.models.Account`) | The canonical identity: email, display name, confirmation + lifecycle timestamps. Custom `AbstractBaseUser`; `USERNAME_FIELD = email`; **no password** (`set_unusable_password`). | `Account` ORM model; `email`, `display_name`, `email_confirmed_at`, `is_active`; `groups` (roles) via `PermissionsMixin`. | Storage details, password machinery (unused). |
| **Role service** (`accounts.roles` + `permissions`) | Mapping roles→Groups, the role constants, and the **one** enforcement point. | `USER/DEVELOPER/ADMIN` constants; `HasRole(role)` DRF permission; `require_role(role)` view decorator; `grant_role()/revoke_role()` (records audit). | Group internals; gate decisions **fail closed**. |
| **Magic-link auth** (`accounts.auth_backend` + `LoginToken`) | Issue, deliver, and verify single-use email tokens; create sessions on success. | `issue_login_link(email, purpose)`, `verify_token(raw) -> Account`. | Token hashing, TTL, single-use consumption. |
| **Session** (Django sessions) | Authenticated period lifecycle (establish/end/expire). | Standard Django session middleware + `login()/logout()`. | Cookie + server-side store details. |
| **Profile** (within `accounts.views`) | View/edit the display name (AC7). | `GET/PATCH /me`. | — |
| **Account deletion** (`accounts` service) | Hard-remove identity/credentials/roles/profile on confirmed request (AC8). | `DELETE /me`. | Transaction + session teardown. |
| **EmailSender** (`core.email`) | Cross-cutting send capability (registration link now, digest later). | `EmailSender.send(to, template, context)`. | Concrete provider (SMTP/SES/Postmark) — ops config. |
| **Admin grant path** (`accounts.views`, admin-gated) | Authorized grant/revoke of non-self-serve roles, recorded in `RoleGrant`. | `POST/DELETE /admin/accounts/{id}/roles`. | Requires requester already holds `admin`. |

**Coupling check:** every component is replaceable behind its exposed surface (the
EmailSender provider, the token store, even the session backend can swap with no caller
changes). Cross-cutting concerns are each defined **once**: authorization in
`permissions.py`, email in `core.email`, config tunables in `core.config`, errors via
DRF exception handling, auth in `auth_backend`.

---

## 4. Data design

One source of truth per fact. UUID primary keys (no sequential enumeration; distribution-
safe at scale). Email is stored case-insensitive (Postgres `citext`) and unique.

### `accounts_account`  (custom User — owns identity)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | Stable cross-feature key everything else references. |
| `email` | citext, **unique**, indexed | One account per email (AC1). |
| `display_name` | varchar(80) | Profile (AC7); validated, non-empty. |
| `email_confirmed_at` | timestamptz, nullable | NULL ⇒ unconfirmed ⇒ **not digest-eligible** (AC2). |
| `is_active` | bool, default true | Django sign-in gate; set false / row deleted on AC8. |
| `date_joined` | timestamptz | Lifecycle (Django). |
| `last_login` | timestamptz, nullable | Lifecycle (Django). |
| roles | M2M → `auth_group` | Roles held (PermissionsMixin `groups`). |

### `auth_group`  (roles — Django built-in)
Seeded rows: `user`, `developer`, `admin`. Adding a future role = inserting a row +
applying `HasRole('new-role')` to new actions. No schema or auth change (AC10).

### `accounts_logintoken`  (owns the credential-of-the-moment)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `account_id` | FK → account, on_delete CASCADE | |
| `token_hash` | char(64), **unique**, indexed | SHA-256 of a 32-byte random token; **raw token never stored**. |
| `created_at` | timestamptz | |
| `expires_at` | timestamptz | created_at + `LOGIN_TOKEN_TTL` (default 15 min). |
| `consumed_at` | timestamptz, nullable | Single-use marker (see concurrency). |

### `accounts_rolegrant`  (audit — owns attributability for grants/revokes)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `target_account_id` | FK → account | Who received/lost the role. |
| `role` | varchar | Role name. |
| `action` | enum(`grant`,`revoke`) | |
| `granted_by_id` | FK → account, **nullable** | NULL only for the cold-start bootstrap (§10). |
| `created_at` | timestamptz | Immutable audit row (never updated/deleted). |

**Lifecycle.** Account: *created (unconfirmed)* → *confirmed* (first successful verify) →
*deleted (hard)*. Token: *issued* → *consumed* | *expired* (purged by
`purge_expired_tokens`). RoleGrant rows are append-only.

**Crash/restart.** Sessions and tokens are DB-backed, so they survive process restarts;
no in-memory auth state. **Concurrency.** (a) Duplicate-registration race → resolved by
the `email` unique constraint (`IntegrityError` → 409). (b) Token double-spend → consumed
atomically via `UPDATE logintoken SET consumed_at=now() WHERE id=? AND consumed_at IS
NULL` and acting only if one row changed — idempotent and race-free.

**Migration/retention.** First migration creates the schema and seeds the three groups.
Retention = data-minimization: only the four identity facts are kept while active; AC8
**hard-deletes** the account, its tokens (CASCADE), and its group memberships.
`RoleGrant` audit rows reference accounts that may be deleted → `granted_by_id` and
`target_account_id` use `on_delete=SET_NULL` so the audit trail survives a deletion
without blocking it.

---

## 5. Interface contracts

Transport: HTTP. State-changing form posts use Django CSRF; JSON variants are DRF
endpoints for downstream consumers. All errors are explicit (never silent). Tunables come
from `core.config`, never hardcoded.

| # | Endpoint | Auth | Request | Success | Errors |
|---|----------|------|---------|---------|--------|
| 1 | `POST /auth/register` | none | `{email, display_name}` | `202` link-sent | `400` invalid email/name · `409` email already has an account (clear message + sign-in link) · `429` rate-limited · `503` email send failed (AC2) |
| 2 | `POST /auth/login` | none | `{email}` | `202` link-sent | `400` invalid · `404`→treated as `202` for *generic* path (see §10 enumeration) · `429` |
| 3 | `GET /auth/verify?token=` | none | token in query | `302`→profile, session created; sets `email_confirmed_at` if first time | `410` expired/consumed/invalid (clear resend CTA) |
| 4 | `POST /auth/logout` | session | — | `204`, session flushed (AC5) | — |
| 5 | `GET /me` | session | — | `200 {id,email,display_name,roles[],email_confirmed}` | `401` |
| 6 | `PATCH /me` | session | `{display_name}` | `200` updated (AC7) | `400` invalid · `401` |
| 7 | `DELETE /me` | session | `{confirm:true}` | `204`, account hard-deleted, session ended (AC8) | `400` missing confirm · `401` |
| 8 | `POST /me/roles/developer` | session | — | `200` developer role added to self (AC6 self-serve) | `401` |
| 9 | `POST /admin/accounts/{id}/roles` | session + **admin** | `{role}` | `200` role granted, `RoleGrant` recorded (AC9) | `401` · `403` not admin · `404` target · `400` unknown role |
| 10| `DELETE /admin/accounts/{id}/roles/{role}` | session + **admin** | — | `204` revoked, `RoleGrant` recorded | `401` · `403` · `404` |

**Invariants (illegal states made unrepresentable / enforced at the boundary):**
- One account per email — DB unique constraint.
- Every account holds ≥ the `user` role — assigned in the same transaction as creation.
- A non-admin can **never** obtain `admin` — there is *no* code path that adds a
  non-self-serve role except endpoint #9, which requires the caller to already hold
  `admin` (AC9, R6). Self-serve is limited to exactly the `developer` role (#8).
- Roles grant **actions, never ranking position** — no role is ever read by any future
  ranking/allocation code path (fairness, vision §5.6); enforced by convention + review.
- Magic-link tokens are single-use and TTL-bounded; the raw token exists only in the
  email and the request, never at rest.

**Evolution without breaking consumers:** the cross-feature contract downstream features
depend on is intentionally small — `Account.id`, `Account.email`,
`HasRole(role)`/`require_role(role)`, and the role constants. New roles and new endpoints
are additive; the `/me` and `/admin` shapes are versionable (URL prefix) if ever needed.

---

## 6. Email-delivery dependency

The brief flagged this as an unresolved shared dependency. Resolution: define the
**interface here**, defer the **provider to ops config** (design-for-change).

```python
class EmailSender(Protocol):
    def send(self, to: str, template: str, context: dict) -> None: ...
```

- Default implementation wraps Django's email backend; the concrete transport (console in
  dev, SMTP/SES/Postmark in prod) is selected by `EMAIL_BACKEND` env config — **not**
  hardcoded.
- `core.email` is the single shared send point; the future `weekly-digest` reuses it.
- **Failure handling (AC2):** a send failure raises loudly → endpoint #1 returns `503`
  with a retry CTA, the account stays *unconfirmed* (never silently marked active for
  digest), and the failure is logged + counted (`email_send_failure`). Transient failures
  retry with bounded backoff; the user always learns if the link could not be sent.

---

## 7. Tech-stack decision

Recorded in full as global **[D-4](../../DECISIONS.md)** (the persona requires the stack,
shared-code root, and rejected alternatives to live in the repo-level log because they
constrain every later feature). Summary: **Django + DRF + PostgreSQL**, chosen by the user
for Python familiarity and as the strongest base for the later data/ML-heavy ranking &
integrity engine; batteries-included auth/sessions/groups/ORM/migrations minimize
hand-rolled, security-sensitive code. Shared-code root = `apps/`.

---

## 8. Authentication mechanism — passwordless magic-link  *(see DL-3)*

The brief left the mechanism to Stage 2. Chosen: **passwordless email magic-link**.

**Flow.** Register/sign-in collects an email → a single-use token (32 random bytes,
stored only as a SHA-256 hash, TTL 15 min) is emailed as a link → clicking it
(`/auth/verify`) consumes the token, sets `email_confirmed_at` on first use, and creates a
Django session.

**Why it fits the ACs with one mechanism:**
- **AC1 + AC2** — clicking the link *is* proof of email control; an undeliverable email
  yields no link, so the account never becomes digest-eligible and the failure surfaces.
- **AC3** — sign-in is the same issue-then-verify path.
- **AC4 (recovery)** — there is **no password to lose**: re-authenticating via the
  registered email always returns the same account with the same roles. Recovery is
  inherent, not a separate subsystem.
- **Data minimization** — no password is ever stored, eliminating the password-breach
  surface entirely.

Alternatives rejected (logged in DL-3): passwords (adds storage, breach surface, a
separate reset flow, and contradicts minimization), OAuth/SSO/MFA (explicitly out of
scope per the brief; post-MVP hardening).

---

## 9. UX flow (server-rendered pages)

For this feature the surfaces are simple, so Django-rendered pages are the boring,
low-wiring choice; a richer SPA is deferred until a surface needs it (OPEN_QUESTIONS).

- **Register** — form (email, display name). States: *idle → submitting → "check your
  email"*; errors: *email taken* (→ message + one-click sign-in link), *send failed* (→
  retry), *invalid input* (inline). 
- **Check-email** — confirmation screen with a resend control (rate-limited).
- **Verify landing** (`/auth/verify`) — *loading → success* (redirect to Profile) or
  *expired/invalid* (clear message + resend form).
- **Sign-in** — email-only form → same check-email → verify landing.
- **Profile** — view/edit display name (*view → editing → saved*, error inline); shows
  roles held; **"Become a developer"** self-serve button (#8); **"Delete account"** →
  confirm dialog → *deleted* state. Empty/loading/error states all specified.
- **Admin grant** — *no rich UI in this feature.* During cold start, grants are performed
  via the `create_admin` command and Django's built-in admin site (staff only); the
  product-facing admin tooling is owned by `editorial-curation-tools` (brief scope). The
  contract (#9/#10) is provided here so that tooling has an API to call.

---

## 10. Non-functional handling

**Performance / scale.** Every access path is an indexed point lookup (unique `email`,
unique `token_hash`, FK indexes); auth is O(1). A single Postgres node comfortably handles
MVP and ~100× via connection pooling and read replicas — a **deliberate, bounded
single-node trade-off** (D-2): horizontal sharding is unnecessary now and documented as
the growth path. No O(n²) or in-memory state anywhere.

**Security (threat model).**
- *Privilege escalation (R6):* the only self-serve role is `developer`; `admin` and any
  future privileged role require endpoint #9 with the caller already holding `admin`. Role
  gates **fail closed** (unknown/error ⇒ deny). Every grant/revoke is an immutable
  `RoleGrant` row (attributable). **First-admin bootstrap:** the very first admin is
  seeded out-of-band by `manage.py create_admin <email>` (records a `RoleGrant` with
  `granted_by = NULL`); no self-grant endpoint exists, so the chain of trust starts there.
- *Account enumeration:* the duplicate-registration message (AC1) does reveal an email is
  registered; the sign-in path (#2) uses a **generic "if an account exists, we sent a
  link"** response to avoid leaking. The registration leak is an **accepted MVP trade-off**
  (D-2 sets no security ceiling; integrity is deferred per breakdown §3, brief R3) and is
  noted for revisit when the integrity system lands.
- *Token theft / replay:* tokens are hashed at rest, single-use, short-TTL; verify
  consumes atomically.
- *Email/link bombing:* request endpoints (#1/#2) are rate-limited — default **5/email/hr,
  20/IP/hr** (config, not hardcoded).
- *Sessions:* cookies `HttpOnly` + `Secure` + `SameSite=Lax`; CSRF on all form posts
  (Django built-in); HTTPS enforced.
- *PII:* the only PII is email + display name, encrypted in transit (TLS) and protected at
  rest at the DB layer; logs record the account **UUID**, never the raw email.

**Observability.** Structured logs carry a request id + account UUID. Metrics map 1:1 to
the brief's success metrics: `registration_completion`, `signin_success_rate` /
`auth_error_rate`, `unexpected_logout_rate`, `developer_role_adoption`,
`role_gate_decisions{result=allow|deny}`, `email_send_failure`, `deletion_fulfilment`. A
health endpoint checks DB + email reachability. **Actionable alerts only:** auth-error
spike, email-send-failure rate, and **any** admin grant/revoke.

**Rollback.** As the foundational substrate there is nothing to feature-flag *off*;
safety comes from **reversible migrations** and a documented deploy order (§12). A bad
release is rolled back by reverting the deploy and, if needed, the last migration.

---

## 11. Failure modes (detection → response, never silent)

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| EmailSender | provider down/slow | exception/timeout | `503` to user + retry CTA; account stays unconfirmed; bounded-backoff retry; alert (AC2). |
| Database | down / constraint hit | exception | Fail loud (`500`); account creation is one transaction (no partial state); duplicate email → `409`. |
| LoginToken | expired / reused / forged | hash miss / `consumed_at`/`expires_at` check | `410` + resend CTA; **no session** issued. |
| Session store | unavailable | middleware error | Fail **closed** — deny access; never default-allow. |
| Role gate | role lookup error / unknown role | exception in `HasRole` | **Deny** the action (closed); log; never leak the action (R6). |
| Admin grant | non-admin caller / bad target | permission + existence check | `403` / `404`; nothing mutated; no `RoleGrant` written. |

---

## 12. Rollout strategy

First feature, so no backward-compat burden — but its outputs are the stable cross-feature
contract, so they ship deliberately:

1. Apply migrations (create schema, seed `user`/`developer`/`admin` groups).
2. Bootstrap the first admin: `manage.py create_admin <email>` (cold start, §10).
3. Configure `EMAIL_BACKEND` for the environment; verify deliverability via the health
   check.
4. Enable registration/sign-in.
5. Schedule `purge_expired_tokens`.

No phased flag is required (nothing pre-existing to protect); rollback = revert deploy +
last migration. **Cross-feature note (handed downstream):** features that later own data
referencing an account (e.g. apps owned by a developer) must define their own
account-deletion behavior (cascade or reassign) when AC8 hard-deletes an account — this
feature deletes only identity data and cannot know their tables. Logged in OPEN_QUESTIONS.

---

## 13. Self-critique & alternatives

**Attacks on the design and resolutions:**
- *"Magic-link locks out users with flaky email."* Accepted for MVP — email is the core
  delivery channel (the digest *is* email), so an account that can't receive email has no
  product value anyway (brief assumption). OAuth is the post-MVP escape hatch (out of scope).
- *"Enumeration via the duplicate message."* Acknowledged and bounded (§10); integrity is
  deliberately deferred; revisit with the integrity system.
- *"First-admin is a bootstrap hole."* Closed: the only way to mint the first admin is a
  server-side management command run by an operator; there is no self-grant path.
- *"Groups-as-roles is too coarse for fine-grained actions later."* Django Groups carry
  Permissions too, so finer gates are additive within the same model — no redesign (AC10).
- *Simplification pass:* dropped a separate "email-confirmation token" type (the login
  token already proves control), dropped a custom Role table (Groups suffice), dropped any
  speculative org/team modeling (out of scope). Nothing remains that isn't tied to an AC.

**Alternatives considered (full rationale in DECISIONS.md):**
- *Stack:* TypeScript full-stack / framework-light TS API — rejected per user choice and
  the Python advantage for the later ML/graph engine (D-4).
- *Auth:* password-based — rejected (storage + breach surface + reset flow + violates
  minimization) (DL-3).
- *RBAC:* custom Role/Permission tables or per-capability boolean flags — rejected; flags
  are exactly the non-extensible shape D-3 moved away from; Groups are the boring built-in
  (DL-4).

**What the chosen design sacrifices:** a rich SPA frontend now (server-rendered pages
instead); a modular-monolith rather than services (documented bounded trade-off);
acknowledged registration-enumeration until integrity lands.

---

## 14. Traceability — every acceptance criterion maps to a design element

| AC | Design element(s) |
|----|-------------------|
| **AC1** Register + no duplicates | Endpoint #1; `email` unique constraint; `user` group assigned in creation txn; §8 flow |
| **AC2** Email confirmation / deliverability | §6 EmailSender failure handling; `email_confirmed_at`; §8; #1 `503` |
| **AC3** Sign in / deny invalid | Endpoints #2/#3; §8 verify; failure table (#11 LoginToken) |
| **AC4** Recovery, same account+roles | §8 (no credential to lose); roles persist on the account row |
| **AC5** Sign out | Endpoint #4; Django session flush |
| **AC6** Role-gated actions + self-serve developer | `HasRole`/`require_role` (§3/§5); endpoint #8 |
| **AC7** Profile display name | Endpoints #5/#6; Profile page (§9) |
| **AC8** Delete account | Endpoint #7; hard-delete txn (§4); CASCADE tokens; downstream-cascade note (§12) |
| **AC9** Admin role granted, never self-assigned | Endpoints #9/#10; admin-gated; `RoleGrant` audit; bootstrap (§10) |
| **AC10** Single access method + extensibility | One magic-link path for all roles (§8); roles = Groups, additive (§3/§4) |

Every component's failure behavior is documented in §11; no contract above contains "TBD".
