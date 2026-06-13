# DECISIONS — signal-capture

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Flagged for the Architect (Stage 2) — repo-wide, near-irreversible

> Per breakdown §4.5: the **event schema** here is the spine of the whole platform. The
> Quality Score, rings, and integrity system are later *consumers* of this data. If it is
> modeled well now (clean event schema; per-user / per-app / per-impression keys; category
> tags for future per-category baselines) those systems are consumers, not rewrites; if
> modeled badly, the north-star architecture inherits the debt.
>
> **Action:** the Software Architect must treat the event schema as a repo-wide decision
> and record it in the global [/DECISIONS.md](../../DECISIONS.md), not here.

_No feature-local decisions recorded yet._
