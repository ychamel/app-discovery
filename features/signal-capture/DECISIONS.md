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

## Confirmation calls flagged by the Product Analyst (Stage 1, 2026-06-18)

> Defensible MVP-scoped calls made while drafting [FEATURE_BRIEF.md](FEATURE_BRIEF.md), so
> the brief is complete and reviewable. Each is the brief's working assumption; approving
> the brief confirms them, or the user adjusts. **A6 is the one with privacy implications**
> (CLAUDE.md §6.5) — surfaced for explicit confirmation, not silently assumed.

- **SC-1 — Curated surface scope.** The only event-emitting surface at MVP is the **weekly
  digest** (no browsable feed yet, breakdown §3). Capture must not presuppose a destination
  feed. *(Brief A1.)*
- **SC-2 — Return windows = 3d & 14d.** Taken directly from vision §3.1; the brief treats
  exact tolerance as a Stage-2 detail. *(Brief A2.)*
- **SC-3 — Attribution model = click-through-and-return proxy.** Given web-only (D-1),
  native install attribution is already out; the brief scopes the *behaviors* and leaves the
  proxy *mechanism* (deep-link vs. return-ping vs. …) as the Stage-2 design fork
  (OPEN_QUESTIONS). The brief does **not** pre-decide the mechanism. *(Brief C2, OQ.)*
- **SC-4 — Raw, not scored.** signal-capture stores raw events and exposes raw funnel
  counts only; all scoring/normalization is a deferred *consumer*. *(Brief AC8, out-of-scope.)*
- **SC-5 — Single reusable capture contract.** The brief states the intent that emitting
  surfaces call one write path (keys + fail-loud in one place); realizing it is design's
  call. *(Brief A5.)*
- **SC-6 (PRIVACY — confirm explicitly) — proposed MVP posture.** Record only pseudonymous,
  in-platform behavioral events keyed to `Account.id`; purpose = future-score backtest (H3);
  **consent via signup ToS, no separate per-event opt-in**, justified by the small,
  hand-recruited, trusted MVP cohort; **retention = full MVP duration, no auto-purge** because
  the H3 backtest needs the historical corpus. This was left an open fork by D-2 (un-gated
  but unresolved) and breakdown §7 Q4 — confirm or adjust before Stage 2. *(Brief A4 / AC9 /
  R3; OQ "behavioral-data privacy posture".)*
