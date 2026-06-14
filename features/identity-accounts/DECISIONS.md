# DECISIONS — identity-accounts

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

### DL-1: Signup access — open self-serve for everyone
- **Date:** 2026-06-14
- **Stage / feature:** `1-define` / `identity-accounts` (Product Analyst)
- **Decision:** Anyone can create an account with an email; the developer capability is
  available to any account. Account creation is **not** gated by invite or approval.
- **Why:** Matches the platform's open-access integrity premise (vision §4.1 — anyone can
  access any app). Spam/quality control belongs at *submission* (the objective gate in
  `submission-intake`, §5.5), not at account creation, so gating signup would add surface
  area without protecting anything the score depends on.
- **Alternatives rejected:** (a) Invite-only during cold start — keeps the early cohort
  trusted but adds an invite mechanism to build and contradicts open access; (b) open for
  readers, gated for developers — extra approval surface for no MVP benefit since the
  submission gate already filters what developers publish.
- **Sacrifices / consequences:** Open signup admits fake/farmed accounts (brief R3);
  accepted because the integrity system is deliberately deferred (breakdown §3) and the
  curated-rating gate blunts fake influence. Revisit if abuse appears.

### DL-2: Role-assignment rules — developer self-serve, admin granted (not self-serve)
- **Date:** 2026-06-14
- **Stage / feature:** `1-define` / `identity-accounts` (Product Analyst)
- **Decision:** Under the single access method and role-based model ([D-3](../../DECISIONS.md), revised),
  the **developer** role is **self-serve** (any account may take it — consistent with DL-1's
  open-access premise), while the **admin** role is **never self-assignable** and is granted
  only to authorized staff. New roles can be introduced without a new access method.
- **Why:** Developer access is open because quality control lives at *submission*, not at
  role-taking (DL-1). Admin grants privileged editorial/operations actions, so allowing
  self-assignment under open signup would be a direct privilege-escalation hole (brief R6) —
  the privilege must be conferred, not claimed.
- **Alternatives rejected:** (a) Admin self-serve like developer — rejected: open signup
  would let anyone seize platform control. (b) Admins live in a separate out-of-band system —
  rejected: duplicates auth + account model and contradicts the single-access-method decision (D-3).
- **Sacrifices / consequences:** Introduces an asymmetry between roles (some self-serve,
  some granted) that Stage 2 must encode in the grant mechanism. The *how* of granting/revoking
  admin (and enforcing gates) is deferred to the Architect; only the rules are fixed here.

> **Related global decision:** the account + role model (one account, one access method,
> extensible role-based authorization: user / developer / admin) is repo-wide — recorded as
> **[D-3](../../DECISIONS.md)** (revised 2026-06-14 per user A1), not here, because other
> features must not contradict it.
