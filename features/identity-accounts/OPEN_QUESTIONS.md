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
