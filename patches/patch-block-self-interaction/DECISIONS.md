# DECISIONS.md — patch-block-self-interaction

Local decisions for this patch (choice + rationale + rejected alternatives). Repo-wide
decisions go in the top-level [DECISIONS.md](../../DECISIONS.md) instead.

- **Bundling Q-002 + Q-003 into one patch (Coordinator, 2026-06-29).** Both resolve to the
  same shape — an owner guard that suppresses a public-page interaction control and rejects
  its mutation server-side — over the same surface and the same owner-identity source.
  Splitting them would duplicate the guard plumbing; one patch is the readable, non-redundant
  unit. Rejected: two separate patches (more overhead, same code touched twice).

- **BSI-D-1 — Pre-existing owner rating / follow: allow Remove/Unfollow, no retroactive deletion (Maintenance Engineer, 2026-06-29).** Owners may remove a pre-existing rating (`remove_rating`) or unfollow their own app (`unfollow_app`) that was created before this patch. The Remove and Unfollow controls remain visible in the slot for such owners. No retroactive deletion is performed — the guard blocks only the *create* path (`submit_rating` / `follow_app`); the *delete* paths are left unrestricted for cleanup. Rejected: retroactive deletion (surprising, out of scope for Patch Track), disabling Remove/Unfollow for owners (traps stale data with no cleanup path).
