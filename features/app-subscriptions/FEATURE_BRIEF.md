# FEATURE_BRIEF — app-subscriptions

*Stage 1 artifact (Product Analyst). Status: **backlog** — folder scaffolded by the
Coordinator; not yet entered Stage 1.*

## Coordinator scope seed (source: signal-capture SC-7/SC-8, OQ-4 — net-new, not in the breakdown)

> Facts carried over for traceability. The Product Analyst owns the brief below; this block
> is context, not the brief.

- **Layer / build phase:** User-facing · Phase 2 (User loop)
- **Purpose:** Let a user **follow / subscribe to** apps they like and receive notices of
  updates / early-access — the user-side **reason to return** to the platform. This is the
  engagement loop that makes the on-platform behavioral signal actually *happen* (so
  `signal-capture` has something to record).
- **MVP slice:** Follow / unfollow an app from its page; a notification or feed of
  subscribed-app activity that pulls the user back. Emits **subscribe / follow**,
  **on-page re-engagement**, and **return-to-platform** events into `signal-capture` via its
  capture contract — this feature builds the *surface*, `signal-capture` records the events.
- **Proves (hypothesis):** H1 (and feeds H3 — supplies the return/retention signal the corpus needs)
- **Depends on:** app-pages, identity-accounts, signal-capture
- **Vision design ref:** §3.1 (return rate / retention family), §5.4
- **Provenance:** Spawned at signal-capture's Stage-1 review (2026-06-18). The SC-7 pivot
  made the corpus depend on on-platform engagement actually occurring; SC-8 held the
  engagement *surfaces* out of `signal-capture` and raised them as new features (OQ-4). This
  is the user-side half. **Pairs with** `developer-updates` (the developer-side half).
- **Source:** [features/signal-capture/OPEN_QUESTIONS.md](../signal-capture/OPEN_QUESTIONS.md) OQ-4;
  [features/signal-capture/DECISIONS.md](../signal-capture/DECISIONS.md) SC-7/SC-8.

## Brief (Product Analyst — Stage 1)

_pending_ — to be written when this feature enters `1-define`. See
[phase-1-product-analyst.md](../../process/personas/phase-1-product-analyst.md) for the
required sections.
