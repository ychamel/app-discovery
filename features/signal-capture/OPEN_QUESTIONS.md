# OPEN_QUESTIONS — signal-capture

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

- **Cross-platform attribution method (breakdown §7 Q3):** deep-link, optional SDK, or
  click-through-and-return proxy? The single biggest design fork for this feature
  (vision Open Q #4).
- **Behavioral-data privacy posture (breakdown §7 Q4):** what we record, retention,
  consent. Gates repo decision **D3** and this feature.

## Flagged for design (breakdown §4.5)

- The **event schema** is a repo-wide, near-irreversible decision and must be logged in
  the global [/DECISIONS.md](../../DECISIONS.md). See [DECISIONS.md](DECISIONS.md).

## Raised at Stage 1 (Product Analyst, 2026-06-18)

- **OQ-1 — Attribution proxy mechanism (web-only).** The brief scopes the *behaviors*
  (open/return via the click-through-and-return proxy) but leaves the *mechanism* to Stage 2:
  deep-link/redirect attribution vs. a return-to-platform ping vs. tying opens to the next
  observed on-platform action. The single biggest design fork (vision Open Q #4 / breakdown
  §7 Q3). Native install/SDK attribution is **closed** by D-1 (web-only) — out of scope.
- **OQ-2 — Behavioral-data privacy posture.** Proposed minimal MVP posture is logged as
  confirmation call **SC-6** in [DECISIONS.md](DECISIONS.md) (pseudonymous in-platform
  events, ToS consent, no auto-purge for the H3 backtest). Gated by breakdown §7 Q4 / D-2;
  needs user confirmation before Stage 2; retention specifics also touch any future
  data-deletion/account-deletion path.
- **OQ-3 — Proxy under-count is a known limitation, not a bug (R1).** A user who clicks
  through and never returns is invisible to the proxy. Stage 2 should document the gap and
  leave a seam for a stronger return signal later — without over-building attribution now.
