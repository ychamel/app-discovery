# OPEN_QUESTIONS — identity-accounts

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

- **Behavioral-data privacy posture (breakdown §7 Q4)** partially touches this feature
  (what identity data we record, retention, consent). Primary owner is
  [signal-capture](../signal-capture/OPEN_QUESTIONS.md); flag the auth/profile slice here.
- ~~Gated by repo decision **D3**~~ — **resolved 2026-06-14:** D3 set *no hard
  constraints* (no compliance/privacy ceiling imposed up front; see
  [/DECISIONS.md](../../DECISIONS.md) D-2). The privacy posture for identity/profile data
  is therefore **un-gated but still undecided** — the Product Analyst (Stage 1) should
  define the auth/profile data we collect + retention as a constraint in the brief, and
  defer the cross-feature behavioral-data posture to `signal-capture`.
  - ~~**Resolved 2026-06-14 (Stage 1):**~~ [FEATURE_BRIEF.md](FEATURE_BRIEF.md) adopts a
    **data-minimization** posture: collect only email, display name, capability flags,
    and lifecycle timestamps; delete on request. Behavioral-data retention deferred to
    `signal-capture`. Marked *unverified* in the brief — confirm at approval.

## Stage 1 (Product Analyst) — resolved forks

- ~~**Account/role model**~~ — **resolved (revised 2026-06-14 per user A1):** one account,
  **one access method**, **role-based authorization** with an **extensible** role set —
  roles **user** (base), **developer** (self-serve), **admin** (granted, not self-serve),
  plus future roles. Supersedes the earlier "dual capability (reader + developer)" wording.
  Recorded as global [D-3](../../DECISIONS.md) (revised).
- ~~**Signup access**~~ — **resolved:** open self-serve for everyone (every new account
  gets the base **user** role). Recorded as [DL-1](DECISIONS.md).

## Deferred to Stage 2 (Architect) — RESOLVED 2026-06-14

- ~~**Auth mechanism**~~ — **resolved:** passwordless **email magic-link** + Django
  sessions (single-use hashed token, 15-min TTL); recovery is inherent (no credential to
  lose). See [DESIGN.md](DESIGN.md) §8 and [DL-3](DECISIONS.md).
- ~~**Shared email-delivery dependency**~~ — **resolved:** a pluggable `EmailSender`
  interface at `apps/core/email.py` (shared, the digest reuses it); concrete provider is
  ops/env config, not code. Send failures fail loudly (AC2). See DESIGN.md §6, [D-4](../../DECISIONS.md).
- ~~**Role-assignment & enforcement mechanics**~~ — **resolved:** roles = Django Groups;
  one fail-closed gate (`HasRole`/`require_role`); two grant paths (developer self-serve;
  admin/privileged via an existing admin, audited in `RoleGrant`); first admin bootstrapped
  by a management command. See DESIGN.md §3/§5/§10 and [DL-4](DECISIONS.md).

## New — raised in Stage 2, handed downstream

- **Cross-feature account-deletion cascade.** AC8 hard-deletes an account but this feature
  deletes only *identity* data. Any later feature that owns account-referencing data (e.g.
  apps owned by a developer in `submission-intake`, signals in `signal-capture`) must define
  its own on-delete behavior (cascade or reassign) when an account is deleted. See DESIGN.md §12.
- **Concrete email provider** for production (SMTP/SES/Postmark) — an ops/config choice, not
  a code decision; the interface is fixed (DESIGN.md §6).
- **Rich SPA frontend** — deferred until a surface needs more than server-rendered pages
  (developer dashboard / feed are likely first). Not chosen at MVP (D-4).

## Escalations — resolved

- ~~**Internal editorial / admin accounts.**~~ **Resolved 2026-06-14 (user A1):** editors
  authenticate **through this feature** via an **admin** role under the single access
  method — *not* out-of-band and *not* a parallel identity system. This feature provides
  the admin **role and its gate** (AC9); the admin **tooling** (digest send controls,
  curation surfaces) remains owned by `editorial-curation-tools`. The admin role is
  **granted, never self-assigned**; the *grant mechanism* is deferred to Stage 2 (below).
