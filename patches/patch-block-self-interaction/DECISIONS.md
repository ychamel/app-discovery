# DECISIONS.md — patch-block-self-interaction

Local decisions for this patch (choice + rationale + rejected alternatives). Repo-wide
decisions go in the top-level [DECISIONS.md](../../DECISIONS.md) instead.

- **Bundling Q-002 + Q-003 into one patch (Coordinator, 2026-06-29).** Both resolve to the
  same shape — an owner guard that suppresses a public-page interaction control and rejects
  its mutation server-side — over the same surface and the same owner-identity source.
  Splitting them would duplicate the guard plumbing; one patch is the readable, non-redundant
  unit. Rejected: two separate patches (more overhead, same code touched twice).
