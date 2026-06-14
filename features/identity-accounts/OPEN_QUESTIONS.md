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

## Deferred to Stage 2 (Architect)

- **Auth mechanism** — magic-link vs. password vs. other; session/token storage; the
  email-confirmation and account-recovery *flows*. The brief fixes the *capabilities*
  (confirm email ownership, recover via email); the *mechanism* is a design decision.
- **Shared email-delivery dependency** — registration confirmation and the digest both
  need an email-sending capability. Not yet decided where that lives (shared infra).
- **Role-assignment & enforcement mechanics** — *how* roles are stored, how a role is
  granted/revoked (especially the **admin** grant, which must be safe under open signup),
  and how role gates are enforced at action boundaries. The brief fixes the *rules*
  (developer = self-serve, admin = granted not self-assigned, set extensible); the
  *mechanism* is a Stage-2 design decision (see brief R6).

## Escalations — resolved

- ~~**Internal editorial / admin accounts.**~~ **Resolved 2026-06-14 (user A1):** editors
  authenticate **through this feature** via an **admin** role under the single access
  method — *not* out-of-band and *not* a parallel identity system. This feature provides
  the admin **role and its gate** (AC9); the admin **tooling** (digest send controls,
  curation surfaces) remains owned by `editorial-curation-tools`. The admin role is
  **granted, never self-assigned**; the *grant mechanism* is deferred to Stage 2 (below).
