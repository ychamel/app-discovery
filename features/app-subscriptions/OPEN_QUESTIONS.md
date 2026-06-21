# OPEN_QUESTIONS — app-subscriptions

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded at scaffold (from signal-capture OQ-4)

- **Subscription vs. the weekly digest** — `weekly-digest` is editor-chosen push; this is
  user-chosen following of specific apps. The two notification channels must not collide or
  double-notify; the boundary is a Stage-1/Stage-2 question for this feature.
- **Which events feed `signal-capture`** — this surface emits subscribe / on-page
  re-engagement / return-to-platform events; the exact set and the capture-contract call are
  to be pinned against `signal-capture`'s schema (its Stage 2 / global event-schema decision).

## Resolved / refined at Stage 1 (Product Analyst, 2026-06-21)

- **OQ-1 — RESOLVED: "subscription vs. the weekly digest" boundary.** MVP delivers an
  **on-platform followed-apps feed only**; notification *delivery channels* (email / push /
  the editor-chosen weekly digest) are **out of scope** ([FEATURE_BRIEF.md](FEATURE_BRIEF.md)
  out-of-scope). So the two cannot collide or double-notify at MVP — `weekly-digest` is
  editor-chosen *push*; app-subscriptions is user-chosen *pull* on a personal surface. If a
  future feature adds cross-channel delivery, the de-dup boundary is its concern, not this
  one's.
- **OQ-2 — RESOLVED at Stage 1, exact set pinned: emit only `subscribe` here; reuse seams for
  the rest.** Of the three behaviors the scaffold named, **only the `subscribe` event is
  newly emitted by this feature** (one per follow, through `signals.capture.*` — D-7 AS-1).
  **On-page re-engagement (`page_reengagement`) and return-to-platform (`PlatformVisit`
  ticks) are *caused* by this feature but *captured* by the existing `signal-capture` seams**
  — app-subscriptions must not re-implement them (brief AC6, R3; single source of truth,
  D-7). *(Refines the scaffold's "which events feed signal-capture".)*

## Raised at Stage 1 (Product Analyst, 2026-06-21) — for Stage 2

- **OQ-3 — RESOLVED at Stage 2 (Software Architect, 2026-06-21): NO `unfollow` corpus kind at
  MVP.** D-7 reserves `subscribe` but **no `unfollow` kind**, and we do not add one. The mutable
  follow store (AS-4) is the source of truth for the *current* relationship; unfollow is an
  *absence*, which D-7 models by read-time derivation (like "did-not-return"), never a stored
  row; M6 (unfollow rate) is read from the `SUBSCRIPTION_UNFOLLOWED` metric; no consumer needs
  unfollow-as-corpus yet (building it = speculative abstraction, CLAUDE.md §5.5). Stays additively
  reversible — a future churn consumer can add the `EventKind` without touching this feature.
  *(See [DESIGN.md](DESIGN.md) §8 + [DECISIONS.md](DECISIONS.md) OQ-3.)*
- **OQ-4 — RESOLVED at Stage 2 (Software Architect, 2026-06-21): a fail-soft `{% app_follow app %}`
  inclusion tag in a new app-page Follow slot, immediately after the header.** Mirrors the
  `ratings` AP-1 slot pattern; viewer-state-driven (anonymous → "Sign in to follow"; signed-in →
  Follow/Unfollow), so app-page uniformity holds; fail-soft so a subscriptions fault never 500s
  the page; one-section rollback; independent of the ratings slot. *(See [DESIGN.md](DESIGN.md)
  §5f + [DECISIONS.md](DECISIONS.md) OQ-4.)*
