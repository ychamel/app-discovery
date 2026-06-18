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
- **SC-3 — Off-platform open/return = best-effort secondary proxy (revised by SC-7).**
  Given web-only (D-1), native install attribution is already out. The click-through-and-return
  proxy is retained **only as a secondary, best-effort** signal — it is no longer the spine.
  The brief scopes the *behaviors* and leaves the proxy *mechanism* (deep-link vs. return-ping
  vs. …) as the Stage-2 design fork (OPEN_QUESTIONS); the brief does **not** pre-decide it.
  *(Brief C2, AC7, OQ-1.)*
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
  but unresolved) and breakdown §7 Q4 — confirm or adjust before Stage 2. *(Brief A4 / AC10 /
  R3; OQ-2 "behavioral-data privacy posture".)*

## Pivot decided with the user (Stage 1 review, 2026-06-18)

- **SC-7 — Measured spine = on-platform engagement; off-platform open/return demoted to
  best-effort secondary. CONFIRMED by the user.** Original draft centered the funnel on an
  off-platform spine (impression → click-through → off-platform open → off-platform return →
  share), mitigated by the click-through-and-return proxy — which forced the brief's single
  highest risk (R1, High/High) to apologize for a lossy load-bearing signal. The user observed
  that we cannot track off-platform behavior, and that rather than chase it we should measure
  the engagement we *can* see and incentivize users/developers onto the platform. This is also
  **more faithful to vision Open Q #4** ("behavioral signals are easy for web apps … return
  visits via the platform"; off-platform installs are the *mobile/desktop* case, out at MVP per
  D-1). **Decision:** the captured spine is now impression → click-through → **return-to-platform
  (3d/14d)** → **subscribe/follow** → **on-page re-engagement** → share, all directly observable;
  off-platform open/return is kept only as a flagged secondary proxy (SC-3), never required for
  funnel completeness (AC7). R1 drops to High/**Low**. *Rejected:* (a) keep the off-platform
  spine as-is — leaves a lossy signal load-bearing; (b) hybrid co-primary — two spines, more
  schema, keeps R1 top. *(User confirmation 2026-06-18; Brief Goal / stories / AC4–AC8 / R1;
  spawns OQ-4.)*
- **SC-8 — Incentive surfaces are OUT of signal-capture; raised as new candidate features.
  CONFIRMED by the user.** The mechanisms that *generate* on-platform engagement — subscription
  / notification UX, **developer↔user communication**, **early-access programs** — are product
  surfaces that emit the events SC-7 captures; they are **not** built here (CLAUDE.md §6.4,
  single-responsibility measurement spine). They are logged as **OQ-4** for the Coordinator to
  scope as new backlog feature(s); folding them in was explicitly rejected by the user.
  *(Brief out-of-scope, A6, R6; OQ-4.)* **Logged 2026-06-18 as two backlog features:**
  `app-subscriptions` (Phase 2, user-side: follow apps + update/early-access notices) and
  `developer-updates` (Phase 3, developer-side: post updates / early-access / talk to
  subscribers). Folders scaffolded; [INDEX.md](../INDEX.md) rows added; OQ-4 resolved.

## Decided at Stage 2 (Software Architect, 2026-06-18) — feature-local

> The repo-wide event-schema decision is recorded as global **[D-7](../../DECISIONS.md)**, not
> here. The two items below are feature-local design calls within that schema, made in
> [DESIGN.md](DESIGN.md); both are flagged to revisit once real usage/posture data exists.

- **SC-9 — Return-to-platform @3d/@14d is *derived at read*, not a stored event.** A return is a
  relationship between a stored `Impression` and stored `PlatformVisit` activity (a per-user-per-day
  idempotent retention tick); the read path (`selectors.app_funnel`) computes "returned within N
  days" as *∃ a visit in (impression, +N]*. Chosen because a materialized return-event table cannot
  represent the *not-returned* outcome (an absence) the brief's metric requires ("returned vs. not,
  per window"), would need a scheduled job, and would risk drift — whereas derivation is exact and
  **needs no backfill** (AC4/AC8). *Rejected:* (a) a stored `return` event row + a daily job that
  materializes the windows — invents the absence problem + batch infra; (b) deriving returns from
  raw page-view/session firehose — over-collects; the per-day visit tick is all the windows need.
  Scale: one indexed `EXISTS`-aggregate per app at MVP; a materialized per-app/per-window projection
  is the named 100× growth path (DESIGN §9). *(DESIGN §4/§5b/§6/§13; brief AC4/AC8.)*
- **SC-10 (PRIVACY) — Account deletion anonymizes, does not purge, the corpus.**
  `accounts.delete_account` hard-deletes the `Account` row; signal-capture sets the event `user`
  FKs (`Impression`/`EngagementEvent`) to **`SET_NULL`**, so a deleted user's behavioral facts
  **survive as anonymized corpus rows** (person unlinked) — respecting the deletion right *and* the
  no-auto-purge H3 corpus rule (SC-6/A3). `PlatformVisit.user` is **`CASCADE`** (an unlinked daily
  tick is pure noise once it can't join to a live user's impressions). This **resolves the
  account-deletion interaction `submission-intake` DESIGN §13 explicitly deferred "when
  signal-capture keys signals to apps."** *Rejected:* (a) CASCADE all signals — purges the corpus
  H3 depends on; (b) hard-block deletion while signals exist — violates the user's deletion right.
  **Confirm-with-data nuance:** whether "anonymize-and-retain behavioral data about a deleted user"
  is the desired posture is the one item to revisit with real cohort/legal input — flagged, not
  silently assumed. *(DESIGN §10/§13; brief AC10/A4, SC-6.)*
