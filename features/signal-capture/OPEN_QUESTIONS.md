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

- **OQ-1 — Off-platform attribution proxy mechanism (web-only, now SECONDARY).** After the
  SC-7 pivot the spine is on-platform engagement; the off-platform open/return proxy is a
  best-effort *secondary* signal (SC-3 / AC7). The brief still leaves its *mechanism* to
  Stage 2 (deep-link/redirect vs. return-to-platform ping vs. tying opens to the next observed
  on-platform action), but it is **no longer the biggest fork** — and Stage 2 must not
  over-build it. Native install/SDK attribution is **closed** by D-1 (web-only) — out of scope.
- **OQ-2 — Behavioral-data privacy posture.** Proposed minimal MVP posture is logged as
  confirmation call **SC-6** in [DECISIONS.md](DECISIONS.md) (pseudonymous in-platform
  events, ToS consent, no auto-purge for the H3 backtest). Gated by breakdown §7 Q4 / D-2;
  needs user confirmation before Stage 2; retention specifics also touch any future
  data-deletion/account-deletion path.
- **OQ-3 — Off-platform proxy under-count is a known limitation, not a bug (R1).** A user who
  clicks through and never returns is invisible to the proxy. Post-SC-7 this only affects the
  *secondary* off-platform number, not the spine, so R1 is now High/Low. Stage 2 should
  document the gap and leave a seam for a stronger return signal later — without over-building
  attribution now.

## Raised at Stage 1 review (Product Analyst + user, 2026-06-18) — FOR THE COORDINATOR

- **OQ-4 — RESOLVED 2026-06-18: two new backlog features created.** The incentive /
  engagement-loop surfaces were logged as **`app-subscriptions`** (Phase 2, user-side) and
  **`developer-updates`** (Phase 3, developer-side, incl. early-access) — folders scaffolded
  and rows added to [INDEX.md](../INDEX.md). They emit into `signal-capture` but are built
  elsewhere (SC-8). Original note retained below for context.
- **OQ-4 (original) — Incentive / engagement-loop surfaces are new candidate features (SC-7 / SC-8).**
  The SC-7 pivot makes the corpus depend on *on-platform engagement actually happening*. The
  surfaces that drive it — **subscription / notification UX**, **developer↔user communication**,
  **early-access programs**, and other reasons-to-return — are out of scope for signal-capture
  (it only records their events, brief A6 / R6) and do not map cleanly onto the existing
  backlog (developer-dashboard and weekly-digest touch only the edges). **Action for the
  Coordinator:** scope one or more new backlog features for the engagement loop and add them to
  [INDEX.md](../INDEX.md). The user has chosen to **log, not build now** (no reordering of the
  current pipeline). Tracked in [CONTROL.md](../../CONTROL.md).
