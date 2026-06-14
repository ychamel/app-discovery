# FEATURE_BRIEF — identity-accounts

*Stage 1 artifact (Product Analyst). Status: **revised per user role direction (A1) —
role model added; awaiting final go before Stage-2 handoff**. Sources:
[docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.1,
[curated-app-platform-design.md](../../curated-app-platform-design.md) §6, global
[DECISIONS.md](../../DECISIONS.md) D-1/D-2/D-3, and this feature's
[DECISIONS.md](DECISIONS.md).*

## Coordinator scope seed (source: breakdown §4.1)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Foundation · Phase 0 (build first — see breakdown §5)
- **Purpose:** Accounts, auth, sessions for both users and developers.
- **MVP slice:** Email-based sign-in, two roles (user / developer), basic profile.
- **Proves (hypothesis):** enabler (no hypothesis directly; everything depends on it)
- **Depends on:** —
- **Vision design ref:** §6 (all surfaces)
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.1

> **Brief note:** the user's A1 direction supersedes the seed's "two roles" line — the
> identity model is now a **single access method with extensible role-based
> authorization** (roles: **user**, **developer**, **admin**, plus future roles). See
> global [D-3](../../DECISIONS.md) (revised) and the role-model entries below.

---

## Glossary (no undefined domain terms)

- **Account holder** — a person with a single registered identity on the platform.
- **Single access method** — every account holder signs in the **same way** regardless of
  which roles they hold; roles change *what you can do*, never *how you sign in*. There is
  no separate login or portal per role (e.g. no separate admin login).
- **Role** — a named set of actions an account is permitted to perform. An account holds
  **one or more** roles. The MVP defines three (see below); the set is **extensible** so
  later roles can be added without a new access method or an auth redesign.
  - **user** — the **base** role every account holds: discover apps and receive/open the
    curated digest (this is the former "reader" capability).
  - **developer** — submit and own apps. **Self-serve**: any account may take this role
    ([DECISIONS.md](DECISIONS.md) DL-1).
  - **admin** — privileged internal role for editorial/operations work (e.g. digest send
    controls, curation). **Not self-serve**: granted only to authorized staff. This
    feature provides the *role and its gate*; the admin *tooling* is owned by
    `editorial-curation-tools`.
- **Session** — an authenticated period during which an account holder can act without
  re-authenticating, ending at sign-out or expiry.
- **Beachhead niche** — the single launch vertical, **vibecoded webapps** (small,
  often AI-assisted web apps from solo/tiny-team devs); global [D-1](../../DECISIONS.md).
- **Data minimization** — collecting only the identity data the platform actually needs,
  and no more (the privacy posture adopted by this brief).

---

## Problem statement

The platform has no surface — for users, developers, or its own editors — that can exist
without a stable, trustworthy identity. The curated digest must be addressed to *someone*;
an app must be *owned* by a developer; every behavioral signal the future Quality Score
consumes must be keyed to *a specific account*; the curated-rating gate (§4.1) is
meaningless unless a rating can be tied to a real, single identity; and privileged
editorial/operations actions must be performed by *authenticated, authorized* people.
**Without accounts, nothing else in the MVP can be built or measured.** This is needed
*now* because it is the deepest Phase-0 dependency: `signal-capture`, `submission-intake`,
`interest-profile`, `developer-dashboard`, and `editorial-curation-tools` all key off an
account — and a role on that account — that does not yet exist.

In the beachhead niche (vibecoded webapps, D-1), the same person is frequently both a
discoverer and a builder — so the identity model must let one person hold several roles on
one identity, behind one sign-in, without maintaining separate logins.

## Goal

Let any person create one email-based account, sign in and out reliably through a single
access method, hold one or more **roles** (user, developer, admin, or future roles) that
govern which actions they may perform, manage a basic profile, and delete the account —
providing the stable, role-aware identity key every other MVP feature depends on.

## User stories (7)

- **US1 — Register.** As a visitor, I want to create an account with my email address, so
  that I can use the platform. *(traces: breakdown §4.1; open self-serve, [DECISIONS.md](DECISIONS.md))*
- **US2 — Sign in.** As a returning account holder, I want to sign in with my email, so
  that I can resume access without re-registering. *(traces: §4.1)*
- **US3 — Sign out.** As an account holder, I want to end my session, so that my account
  stays secure on shared or public devices. *(traces: §4.1 "sessions")*
- **US4 — Hold roles on one account.** As an account holder, I want to hold one or more
  roles (e.g. user and developer) on a single account behind one sign-in, so that I can
  perform exactly the actions my roles permit without a second identity or a separate
  login. *(traces: global D-3 (revised); user A1 direction; breakdown §4.1 "two roles")*
- **US5 — Basic profile.** As an account holder, I want to view and edit a basic profile
  (a display name), so that my identity is presented consistently across the platform's
  surfaces. *(traces: §4.1 "basic profile"; vision §6)*
- **US6 — Delete account.** As an account holder, I want to delete my account, so that I
  can remove my identity and data when I choose. *(traces: data-minimization constraint below)*
- **US7 — Privileged (admin) role.** As the platform operator, I want certain accounts to
  hold an **admin** role that grants privileged actions and is not self-assignable, so
  that editorial/operations work is done by authenticated, authorized people through the
  same access method — without a parallel identity system. *(traces: user A1 direction;
  global D-3 (revised); resolves the editorial/admin escalation in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Admin **tooling** is owned by `editorial-curation-tools`, not this feature.)*

## Acceptance criteria (Given / When / Then)

- **AC1 (US1).** *Given* a visitor with no account, *when* they register with an email
  address and the platform confirms they control that email, *then* an active account
  exists for that email, holds the base **user** role, and they are signed in. *And given*
  an email that already has an account, *when* they attempt to register, *then* registration
  is refused with a clear message (no duplicate accounts per email).
- **AC2 (US1, deliverability).** *Given* registration, *when* the email cannot be
  confirmed (typo / undeliverable / not owned), *then* the account is **not** treated as
  active for digest delivery, and the failure is surfaced to the person — not swallowed.
- **AC3 (US2).** *Given* an existing account holder, *when* they authenticate with their
  email, *then* a valid session is established. *And given* a failed/invalid attempt,
  *when* it occurs, *then* access is denied and no session is created.
- **AC4 (US2, recovery).** *Given* an account holder who has lost access, *when* they
  re-authenticate through their registered email, *then* they regain access to the same
  account **with the same roles** (no identity or role grant is orphaned by a forgotten
  credential).
- **AC5 (US3).** *Given* an active session, *when* the account holder signs out, *then*
  the session is ended and protected actions require re-authentication.
- **AC6 (US4, role-gated actions).** *Given* an account holder, *when* they take an action,
  *then* it is permitted only if one of their roles allows it and refused otherwise. *And
  given* an account with the base **user** role that takes the (self-serve) **developer**
  role, *when* they then perform a developer action, *then* it succeeds on the **same**
  account with no second identity or second login required.
- **AC7 (US5).** *Given* an account holder, *when* they set or change their display name,
  *then* the new value is saved and shown wherever their identity appears.
- **AC8 (US6).** *Given* an account holder, *when* they request deletion and confirm,
  *then* their account, credentials, roles, and profile data are removed, and the account
  can no longer sign in. *(Behavioral-signal records are owned by `signal-capture`; this
  brief does not specify their deletion — see Open Questions.)*
- **AC9 (US7, admin role).** *Given* an account **without** the admin role, *when* it
  attempts an admin-gated action, *then* the action is refused. *And given* an account, *when*
  it tries to grant itself the admin role, *then* the request is refused (admin is not
  self-serve). *And given* an account that has been granted admin by an authorized grant,
  *when* it performs an admin-gated action, *then* it succeeds — through the same sign-in as
  any other account. *(How admin is granted is a Stage-2 mechanism; the product rule
  "admin is granted, never self-assigned" is fixed here.)*
- **AC10 (US4/US7, single access method + extensibility).** *Given* any two accounts with
  different role sets, *when* each signs in, *then* both authenticate through the **same**
  access method (no role-specific login). *And given* a new role is later introduced and
  granted to an account, *when* that account acts, *then* it gains exactly that role's
  actions through the existing access method, and accounts' other roles are unaffected.

## Success metrics

This feature is an **enabler** — it proves no H1/H2/H3 hypothesis directly. Its metrics
are therefore operational reliability signals (the bar is "it works and is trustworthy"),
plus one niche-health indicator:

- **Registration completion rate** — visitors who start signup → active confirmed account
  (detects friction / email-confirmation drop-off).
- **Sign-in success rate / auth error rate** — successful authentications ÷ attempts;
  target an auth-error rate near zero for legitimate users.
- **Unexpected-logout rate** — sessions ending without a sign-out or expiry event (should
  be ~0; surfaces session bugs).
- **Developer-role adoption** — share of accounts that hold the **developer** role in
  addition to the base user role (validates D-3 / the niche assumption that builders are
  also discoverers).
- **Role-gate correctness** — rate of actions correctly allowed/refused against the acting
  account's roles; unauthorized-action leakage should be ~0 (surfaces authorization bugs).
- **Deletion fulfilment** — account-deletion requests that complete successfully (privacy
  posture is honored; no hard SLA imposed per D-2, but completion must be observable).

## In scope

- Email-based **account creation** (open self-serve for everyone — [DECISIONS.md](DECISIONS.md)).
- **Email-ownership confirmation** sufficient for the account to be active for digest
  delivery (the *capability* of confirming control of the email; the *mechanism* is Stage 2).
- **Sign-in, sign-out, and session lifecycle** (establish, end, expire) through a **single
  access method** for all roles.
- **Account recovery** via the registered email (so a lost credential never orphans an
  identity or its role grants).
- **Single account, role-based authorization** model (D-3, revised): an account holds one
  or more roles — **user** (base), **developer** (self-serve), **admin** (granted, not
  self-serve) — and the role set is **extensible** for future roles.
- **Role-gated action enforcement**: each action is permitted only if one of the acting
  account's roles allows it; the **admin** role exists, is restricted to authorized grants,
  and gates privileged actions (the admin *tooling* itself is owned by `editorial-curation-tools`).
- **Basic profile**: a display name the account holder can view and edit.
- **Account deletion** of identity/credential/role/profile data on request (data minimization).
- **Data-minimization posture** for identity data (see Constraints).

## Out of scope

- The **auth mechanism** itself (magic-link vs. password vs. other), token/session
  storage, and verification flow — these are Stage-2 **design** decisions, not product scope.
- The **role-assignment mechanics** — *how* a role (especially admin) is granted/revoked,
  and any admin-management UI — are Stage-2 design. The brief fixes only the product rules
  (developer = self-serve, admin = granted not self-assigned, set is extensible).
- **Admin / editorial tooling** (digest send controls, curation surfaces) — this feature
  provides the **admin role and its gate**; the privileged *tooling* is owned by
  `editorial-curation-tools`.
- **Social / OAuth / SSO login** and **multi-factor authentication** (post-MVP hardening).
- **Developer-role gating / approval** — taking the developer role is open; the *quality
  gate* on what a developer submits lives in `submission-intake` (§5.5), not here.
- **Interest tags / preferences** (owned by `interest-profile`).
- **Behavioral / engagement tracking and its retention** (owned by `signal-capture`;
  cross-feature privacy posture deferred there per breakdown §7 Q4).
- **Monetization, paid tiers, supporter membership, developer subscription** (§5.6 — all
  free at MVP; no paid account state exists, and no role confers paid status).
- **User/developer reputation or early-supporter badges** (§3.2, §5.4 step 5 — deferred).
- **Team / organization accounts** (tiny-team niche noted, but MVP accounts are individual).

## Constraints & assumptions

*(Each marked **[verified]** = grounded in a recorded decision/source, or
**[unverified]** = a proposal this brief makes that the user/Architect should confirm.)*

- **Platform: web.** The niche is vibecoded webapps; identity is web-based. **[verified — D-1]**
- **No hard non-functional targets up front** (deadline/budget/scale/latency); start
  small, scale as we go — but the design must still hold at 100× or document the bounded
  trade-off (CLAUDE.md §5.2). **[verified — D-2]**
- **Identity model:** one account, **one access method**, **role-based authorization**
  with an **extensible** role set (user / developer / admin + future). **[verified — global D-3, revised per user A1]**
- **Role-assignment rules:** the **developer** role is self-serve; the **admin** role is
  **not** self-serve and is granted only to authorized staff; new roles can be added
  without a new access method. **[verified — user A1 / D-3 revised]**
- **Signup access:** open self-serve for everyone (every new account gets the base **user**
  role). **[verified — feature [DECISIONS.md](DECISIONS.md) / user decision]**
- **Data collected (minimization):** email address, display name, role assignments, and
  account lifecycle timestamps (created / last sign-in) — and nothing more in this
  feature. No behavioral, interest, or payment data is collected here. **[verified — set by this brief]**
- **Retention:** identity data is kept while the account is active and removed on deletion
  request; behavioral-data retention is explicitly deferred to `signal-capture`. **[unverified — proposes the posture D-2 left un-gated]**
- **Email ownership is confirmed** because the core user value (the weekly digest) is
  delivered to that email; an unconfirmed email yields no value. **[verified as a requirement; mechanism deferred to Stage 2]**
- **Dependency — email delivery:** registration confirmation (and later the digest)
  assume a shared email-sending capability exists; this feature consumes it, does not
  build the digest. **[unverified — shared infra not yet decided]**
- **Fairness:** all accounts are uniform with respect to ranking; **no role** (including
  admin) and no account attribute confers any ranking or visibility advantage now or by
  design — roles grant *actions*, never *position*. **[verified — vision §5.6]**

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | The identity/account model locks in poorly; downstream features (`signal-capture`, `submission-intake`, `developer-dashboard`, `editorial-curation-tools`) inherit the debt. | Med | High | Account + role model decided up front and recorded as global **D-3** (revised); Architect treats it as a stable cross-feature contract. |
| R2 | Email deliverability fails → users never receive the digest (the entire user value). | Med | High | Confirm email ownership at signup (AC2); treat email delivery as an explicit shared dependency to resolve in design. |
| R3 | Open self-serve signup invites fake/farmed accounts that later pollute signal and the rating gate. | Med | Med | Email confirmation raises the floor; the integrity system is deliberately deferred (breakdown §3) and the curated-rating gate already blunts fake influence — revisit if abuse appears. |
| R4 | Identity-data privacy/retention posture stays undecided and forces rework when `signal-capture` lands. | Low–Med | Med | Adopt data minimization now (collect 4 fields incl. role assignments, delete on request); explicitly hand the behavioral-data posture to `signal-capture`. |
| R5 | Account recovery is overlooked → a lost credential orphans an identity and its role grants. | Med | Med | Recovery via registered email is **in scope** (AC4); flagged for the Architect to design alongside the auth mechanism. |
| R6 | The admin role becomes a privilege-escalation hole (self-grant, or admin actions leaking to non-admins) given open signup. | Low–Med | High | Product rule fixed now: admin is **granted, never self-assigned** (AC9); role-gate correctness is a tracked metric; the *grant mechanism* is escalated to the Architect to design safely. |

## Vision alignment

Serves vision **§6 (all surfaces)** as the foundational enabler — every user-, developer-,
and editor-facing surface, and every internal signal, keys off the account and its roles
that this feature creates. It also upholds **§5.6 / the one-line test**: accounts are
uniform with respect to ranking and **roles grant actions, never position** — even an
admin cannot buy or push visibility — so *money buys tools, never position* holds at the
identity layer, and a single fair identity is what lets "an unknown solo dev with $0
marketing" participate on equal footing.
