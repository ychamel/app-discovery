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
