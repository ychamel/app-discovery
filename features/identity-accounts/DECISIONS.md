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

### DL-3: Auth mechanism — passwordless email magic-link
- **Date:** 2026-06-14
- **Stage / feature:** `2-design` / `identity-accounts` (Software Architect)
- **Decision:** Authentication is **passwordless**: register/sign-in collects an email,
  the platform emails a **single-use, TTL-bounded magic link** (32 random bytes, stored
  only as a SHA-256 hash, default 15-min expiry), and clicking it confirms email control,
  sets `email_confirmed_at` on first use, and creates a Django session. There is no
  password. This satisfies the single-access-method contract (D-3) — every role signs in
  the same way.
- **Why:** One mechanism covers AC1 (confirm control = clicking the link), AC2
  (undeliverable email ⇒ no link ⇒ never digest-eligible, surfaced), AC3 (sign-in is the
  same path), and AC4 (no credential to lose, so recovery is inherent — re-auth via the
  registered email always returns the same account + roles). No password is stored, which
  honors the brief's data-minimization posture and removes the password-breach surface.
- **Alternatives rejected:** (a) **Passwords** — adds credential storage, a breach
  surface, a separate reset/recovery subsystem, and contradicts data minimization. (b)
  **OAuth/SSO/MFA** — explicitly out of scope per the brief (post-MVP hardening).
- **Sacrifices / consequences:** Users with flaky email access are dependent on email —
  accepted because the core product value (the digest) is itself email, so a non-receiving
  account has no value anyway; OAuth is the post-MVP escape hatch. The duplicate-
  registration message reveals an email is registered (enumeration) — an accepted MVP
  trade-off (D-2 sets no security ceiling), flagged for revisit with the integrity system.

### DL-4: Authorization — Django Groups as roles, one fail-closed gate, two grant paths
- **Date:** 2026-06-14
- **Stage / feature:** `2-design` / `identity-accounts` (Software Architect)
- **Decision:** Roles are **Django `Group`s** (`user`, `developer`, `admin`, seeded;
  extensible by adding a row). Enforcement is a **single** point — `HasRole(role)` (DRF
  permission) / `require_role(role)` (view decorator) — that **fails closed** (unknown
  role or lookup error ⇒ deny). Two grant paths only: (1) **self-serve** adds exactly the
  `developer` role to the caller's own account (`POST /me/roles/developer`); (2)
  **admin-granted** roles (`admin` and any future privileged role) go through
  `POST/DELETE /admin/accounts/{id}/roles`, which requires the caller to **already hold
  `admin`** and records an immutable `RoleGrant` audit row. The first admin is bootstrapped
  out-of-band by a `create_admin` management command.
- **Why:** Groups are the boring, built-in, well-understood RBAC primitive (CLAUDE.md
  §5.5) and are extensible without touching the auth path (AC10). A single fail-closed gate
  is the one place authorization lives (cross-cutting concern placed once) and the source
  of the role-gate-correctness metric. Restricting self-serve to `developer` and routing
  all privileged grants through an existing admin closes the privilege-escalation hole
  (brief R6, DL-2, AC9); the management-command bootstrap means there is no self-grant path
  even for the first admin.
- **Alternatives rejected:** (a) **Custom Role/Permission tables** — reinvents Django
  Groups for no benefit. (b) **Per-capability boolean flags on the account** — exactly the
  non-extensible shape D-3 moved away from (a new capability = a schema + auth change).
- **Sacrifices / consequences:** Couples the authorization model to Django Groups; accepted
  because Groups also carry Permissions, so finer-grained gates later are additive within
  the same model. Admin grant/revoke has no rich UI in this feature — the contract is
  provided for `editorial-curation-tools` to build the tooling.

### DL-5: `issue_login_link` takes an Account + injected base_url/sender (build-stage refinement)
- **Date:** 2026-06-17
- **Stage / feature:** `4-build` / `identity-accounts` (Senior Engineer)
- **Decision:** The internal magic-link issuer is implemented as
  `issue_login_link(account, purpose, *, base_url, email_sender=None)` rather than the
  `issue_login_link(email, purpose)` sketched in DESIGN §3. Account *existence* (and the
  enumeration policy that depends on it) is resolved by the caller: registration passes the
  freshly-created account; sign-in looks the account up and, when absent, simply skips
  issuing while still returning the generic 202 (DESIGN §10). `base_url` and `email_sender`
  are injected for configurability and testability.
- **Why:** Keeps the issuer single-purpose (mint + deliver a token for a known account) and
  puts the "does this account exist / what do we reveal" decision where it belongs — the
  view. Injecting `base_url`/`email_sender` removes hidden coupling to settings/global state
  and makes the component testable in isolation (CLAUDE.md §5.3/§5.4). No HTTP contract (§5)
  or schema changes; the cross-feature surface is unchanged.
- **Alternatives rejected:** Keep `(email, purpose)` and look the account up inside — pushes
  enumeration policy into the issuer and forces it to silently no-op for unknown emails,
  conflating two responsibilities.
- **Sacrifices / consequences:** None material; DESIGN §3 updated to match.

> **Related global decision:** the account + role model (one account, one access method,
> extensible role-based authorization: user / developer / admin) is repo-wide — recorded as
> **[D-3](../../DECISIONS.md)** (revised 2026-06-14 per user A1), not here, because other
> features must not contradict it.
