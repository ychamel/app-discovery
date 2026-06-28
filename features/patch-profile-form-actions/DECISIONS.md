# DECISIONS.md — `patch-profile-form-actions`

> Local choices + rationale + rejected alternatives. Repo-wide choices go in the
> global [DECISIONS.md](../../DECISIONS.md) instead.

- **2026-06-28 (Coordinator) — routed to Patch Track.** No schema/migration (`display_name`
  + `delete_account` already exist) and the fix lives in the accounts §9 server-rendered
  human-flow, leaving the §5 JSON `/me` API contract untouched. Rationale + the alternative
  (escalate to Feature Track if the `/me` contract must change) recorded in [PATCH.md](PATCH.md).
