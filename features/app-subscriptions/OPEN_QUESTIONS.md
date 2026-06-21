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

- **OQ-3 — Does *unfollow* need a corpus representation?** D-7 reserves a `subscribe`
  `EngagementEvent` kind but **no `unfollow` kind**. The durable follow *state* (mutable,
  this feature's store — AS-4) clearly captures the current relationship; whether the
  append-only corpus should also record an unfollow *fact* (for retention/churn analysis) is
  a Stage-2 design question. D-7 is additive-only by design, so adding a kind is possible but
  is a global-contract change — flag, don't pre-decide. *(Brief AS-4.)*
- **OQ-4 — Where exactly does the follow control live on the app page?** AS-2 assumes the
  `app-pages` slot / inclusion-tag pattern (as `ratings-reviews` used for AP-1). The precise
  slot, fail-soft behavior, and interaction with the ratings slot are Stage-2 design.
