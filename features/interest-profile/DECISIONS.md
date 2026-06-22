# DECISIONS — interest-profile

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 — Product Analyst (DN-15 resolved 2026-06-21)

The brief's assumptions. **DN-15 approved the brief as written and confirmed IP-1 and
IP-2** (the two forks); IP-3/IP-4/IP-5 carry as working assumptions into Stage 2. Reuses
**D-3** (account/role), **D-5** (tag reference) — **no new global decision** at Stage 1.

- **IP-1 — Stored unit = tag, clusters are a selection aid (AS-1). [RESOLVED — DN-15]** A
  profile stores taxonomy `Tag.id`s; clusters group/expand selection in the picker but are
  not stored as profile entries. *Why:* the matcher matches app **tags** to user tags for
  Ring-0; cluster adjacency/rings are the matcher's job over the D-5 cluster anchor (vision
  §2.2), not a stored user choice. *Rejected:* storing cluster-level interests too
  (ambiguous to match against app tags, duplicates state the matcher derives).
- **IP-2 — Declaration is optional / non-gating at onboarding (AS-2). [RESOLVED — DN-15]**
  New users are prompted but may skip; an empty profile is a valid, handled state (AC6).
  *Why:* no digest consumer exists yet to make declaration load-bearing; a hard gate would
  block signup for zero present payoff. *Rejected:* mandatory picker before first feed
  (premature friction). **Revisit when `weekly-digest` ships.**
- **IP-3 — No hard min/max declared tags at MVP (AS-3).** Any "pick a few" nudge is a
  tunable config value, not a validation floor. *(Working assumption → Stage 2.)*
- **IP-4 — Profile is mutable user state, removed on account deletion (AS-4).** Mirrors
  `app-subscriptions` follow-state posture; distinct from the D-7/SC-10 anonymize-not-purge
  rule, which governs already-emitted behavioral events, not user-declared preferences.
  *(Working assumption → Stage 2.)*
- **IP-5 — Declaring/changing interests emits no D-7 event (AS-5).** It is preference
  state, not an impression/engagement. A future "interest changed" signal would be an
  additive D-7 decision later, not built now. *(Working assumption → Stage 2; not contested
  in DN-15.)*

## Stage 2 — Software Architect (DESIGN.md, pending DN-16, 2026-06-22)

Reuses **D-3/D-4/D-5** as-is — **no new global ADR** (mirrors `app-subscriptions`/`ratings`).
Working assumptions IP-3/IP-4/IP-5 are all **committed by the design**: IP-3 → a config
*nudge*, not a floor (`interest_suggested_minimum`); IP-4 → **CASCADE** user FK (removal on
deletion, no `accounts` edit); IP-5 → the app **does not import `signals.capture`** (the
cleanest proof of no-emit).

- **IP-DESIGN-1 — Membership-only store, no parent `Profile` row.** The interest profile is
  the **set** of a user's `interests_interest` rows (`(user, tag_id)`, `unique(user, tag_id)`,
  CASCADE user FK). *Why:* makes **empty profile the structural default** (AC6) — no row to
  create/check, no second source of truth; nothing profile-level to store at MVP. *Rejected:*
  a `Profile` parent + `ProfileTag` children (adds a lifecycle + an "is it empty?" check for
  no benefit; onboarding "seen/skipped" is deliberately not tracked — §14-A/§17). *Sacrifice:*
  no place to hang a future profile-level field — an additive table/column if ever needed.
- **IP-DESIGN-2 — Set-replace with preserve-on-edit (the AC4 × AC7 seam, §7).** A save
  set-replaces the declared set, **but** preserves any stored id that `resolve_tag` maps to a
  **non-active** tag (a *no-successor* retired tag the active-only picker cannot show). *Why:*
  `retire_tag(replaced_by=None)` is a verified, reachable D-5 state; a naive set-replace would
  silently drop that ref on the next save → violates AC7/M5≠0. This is the minimal rule that
  satisfies AC4 (exact set over what the user can see) and AC7 (never silently dropped)
  together. *Rejected:* naive "new set = exactly submitted" (drops un-showable refs). The full
  clear (`clear_interests`, AC9) deliberately bypasses preserve (explicit "none at all").
- **IP-DESIGN-3 — No D-7 emit; pure preference state (commits IP-5).** `apps/interests` does
  **not** import `signals.capture`. *Why:* declaration is preference, not behavior — emitting
  would couple to the corpus and pollute it with non-impression events. *Rejected:* an
  `interest_declared` D-7 kind (named later path if a churn consumer ever needs it; additive).
- **IP-DESIGN-4 — Onboarding via a fail-soft inclusion tag on the profile landing, not an
  auth-flow edit.** `{% interest_prompt %}` (reads only `has_declared_interests`) renders a
  gentle nudge via **one content line** in `accounts/profile.html` (the existing
  `verify`→profile landing). *Why:* the house pattern is a fail-soft inclusion tag in another
  feature's **template** (ratings/subscriptions → `app_page.html`), never a behavioral change
  to another feature's **view**; satisfies AC3 (encouraged, non-gating) with zero edit to auth
  logic. *Rejected:* redirecting `verify` to the picker (couples accounts→interests, changes
  the auth flow, harder rollback). The single content line is the 2nd half of the activation
  switch (§16).

The cross-feature **read contract** the future matcher consumes is
`interests.selectors.declared_tag_ids(user) -> frozenset[UUID]` (resolved current `Tag.id`s,
AC8) — additive-only, published in [CODEMAP.md](../../CODEMAP.md) at build, **not** a new ADR
(it consumes D-5, it does not amend it).
