# FEATURE_BRIEF — signal-capture

*Stage 1 artifact (Product Analyst). Status: **DRAFT — awaiting approval**. Entered
`1-define` on 2026-06-18. Revised 2026-06-18: spine pivoted to on-platform engagement
(SC-7); off-platform open/return demoted to best-effort secondary.*

## Coordinator scope seed (source: breakdown §4.5)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Measurement (the spine) · Phase 0 (schema first — see breakdown §5)
- **Purpose:** The instrumentation layer that records every behavioral signal the future
  Quality Score will consume.
- **MVP slice:** Event capture for the **on-platform engagement funnel**: impression shown
  → click-through → return-to-platform visit (3d/14d) → subscribe/follow → on-page
  re-engagement → share. The cross-platform (off-platform open/return) attribution proxy is
  retained only as a **best-effort secondary** signal, not the spine — see SC-7.
- **Proves (hypothesis):** **H3** (and feeds H1, H2)
- **Depends on:** identity-accounts
- **Vision design ref:** §3.1, §3.2, Open Q #4
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.5
- **Coordinator note:** The technical heart of the MVP and the breakdown's recommended
  first feature for **D2**. The event schema is a repo-wide, near-irreversible decision —
  see [DECISIONS.md](DECISIONS.md). **Pivot (SC-7):** the breakdown framed cross-platform
  install/engagement tracking as the hard piece that must not be deferred — but that is the
  *mobile/desktop* problem (vision Open Q #4), and the niche is **web-only** (D-1). For web
  apps the high-value signal is directly observable **on-platform**, so the brief centers
  there and treats off-platform attribution as secondary, not load-bearing.

---

## Brief (Product Analyst — Stage 1)

### Problem statement

The platform's differentiating machinery — the Quality Score, ring-based expansion, the
impression allocator — **cannot run without a corpus of real behavioral signal** (vision
§3, §5.4). The MVP deliberately defers that machinery and lets humans do the matching, but
that only de-risks the future algorithm **if the signals it will one day consume are
recorded from the very first impression** (breakdown §1 H3, §2).

Today nothing records behavior. The moment the weekly digest sends its first issue, every
*impression shown*, *click-through*, *return to the platform*, *subscribe*, and *share*
that isn't captured is signal lost forever — and an evaluation window we can never
reconstruct. Worse, this is **Phase-0 schema-first** work: every later surface (digest,
app-pages, ratings-reviews, developer-dashboard) either emits or reads these events, so
modeling them late means retrofitting every consumer and inheriting near-irreversible debt
in the north-star architecture (breakdown §4.5).

**We are structurally blind off-platform — so we measure where we can see.** Our niche is
web apps (D-1). When a user click-throughs to an off-platform web app, opens it, subscribes
there, and reopens it directly later, those are real and valuable behaviors we **cannot
observe** — and chasing them with a lossy attribution proxy would build the corpus on a
signal we have to apologize for. The vision already says the way out (Open Q #4): for web
apps, the hard-to-fake behavioral signal is observable **via the platform** — link clicks
and **return visits to the platform**. So the corpus is built from **on-platform
engagement**: the user returning to the platform, subscribing to / following an app,
re-engaging with its page, and sharing it. Off-platform opens/returns are captured only
when a best-effort proxy can resolve them, and never carry the corpus.

**Who has the problem:** the platform/data team (needs an observable, hard-to-fake corpus
to backtest a future score — H3); developers (their dashboard can only show reception if
reception was recorded — H2); end users (their on-platform behavior is what's captured, so
the privacy posture is theirs). **Why now:** the digest goes live next phase; capture must
exist *before* the first impression, and its event model is the most expensive thing in the
MVP to get wrong.

### Goal

Every **on-platform** behavioral interaction in the curated loop — an app being **shown**
to a user, **clicked through**, **returned to the platform** for (3-day / 14-day),
**subscribed to / followed**, **re-engaged** with on its page, and **shared** — is recorded
as a clean event keyed to *user × app × impression* and tagged with the app's interest
categories at capture time, so a future Quality Score can be **backtested against editorial
judgement without any re-instrumentation**, using directly observed signal rather than an
off-platform proxy.

### Domain terms

- **Impression** — one instance of a specific app being shown to a specific user in a
  curated surface (the digest at MVP). The atomic unit of fairness (vision §2). Each
  impression has its own identity so everything downstream attributes to *that* shown
  instance.
- **Click-through** — a user following a curated impression to the app's page / to the app
  itself. The first conversion step (vision §3.1 "curated conversion").
- **Return-to-platform visit** — the user coming **back to the platform** after an
  impression / click-through, measured at the **3-day** and **14-day** marks (vision §3.1
  "return rate"; Open Q #4 "return visits via the platform"). This is the directly
  observable, hardest-to-fake, highest-weight behavioral signal for web apps — it replaces
  off-platform "return visit" as the spine.
- **Subscribe / follow** — a user opting in to an app on the platform (to follow its
  updates / early-access / changes). An on-platform, costly-to-fake **intent** signal that
  the user wants an ongoing relationship with the app (vision §3.1 retention family).
- **On-page re-engagement** — a user returning to an app's page on the platform and
  interacting with it (e.g. viewing updates the developer posts). Repeat on-platform
  engagement over time is the observable form of vision §3.1's "retention curve shape."
- **Share** — a user sending an app's page to someone else; a costly-to-fake organic
  endorsement (vision §3.1).
- **Off-platform open/return (secondary)** — for web apps the actual app open and any
  off-platform return happen where we cannot observe them; a **best-effort** proxy
  (e.g. the user clicked through then came back) may resolve some of these, but they are a
  **secondary** signal, never required for the funnel (SC-7). This brief scopes the
  *behaviors*; the proxy *mechanism* is a Stage-2 design fork (see
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).
- **Evaluation window** — the first week(s) after an impression during which response is
  measured (vision §2.1). At MVP the funnel must be reconstructable per app over such a
  window.
- **Catalogued app / `App.id`** — the accepted app, referenced only by its UUID `App.id`
  via the [D-6](../../DECISIONS.md) selectors. Events key to `App.id`.
- **`Tag.id`** — an interest tag, referenced by UUID under the [D-5](../../DECISIONS.md)
  taxonomy contract. Captured category tags are `Tag.id`s.

### User stories

> signal-capture is instrumentation — it has few *direct* human users. Stories are framed
> from the perspectives that depend on it: the platform/data team, the end user (whose
> behavior and privacy are at stake), and the developer (the consumer who must eventually
> *see* reception). 3–7 per the persona spec.

1. **As the platform/data team,** I want every impression shown in a curated surface
   recorded with its user, its `App.id`, a unique impression identity, and the app's
   interest tags at that moment, so that every later conversion attributes to a specific
   shown instance and per-category baselines need no backfill. *(H3; vision §3.1/§3.2)*
2. **As the platform/data team,** I want a user's click-through linked back to the
   originating impression, so that **curated conversion** (shown → clicked) is measurable
   per app and per category. *(H1, H3; vision §3.1)*
3. **As the platform/data team,** I want **on-platform engagement** after an impression
   captured — the user **returning to the platform** at the 3-day and 14-day marks,
   **subscribing to / following** an app, and **re-engaging** with its page — so that
   **return rate / retention** signal (vision §3.1) exists for web apps as a *directly
   observed*, hard-to-fake signal rather than an off-platform proxy. *(H3; vision §3.1, Open Q #4)*
4. **As a user,** I want sharing an app's page recorded as an organic-share signal tied to
   the app, so that this costly-to-fake endorsement is part of the corpus. *(H3; vision §3.1)*
5. **As the platform/data team,** I want the captured events to be queryable so that, for
   any app over any evaluation window, the full funnel
   *(impressions → click-throughs → returns@3d → returns@14d → subscribes → re-engagements →
   shares)* can be reconstructed without re-instrumentation — the literal H3 backtest. *(H3; breakdown §1)*
6. **As a developer,** I want the raw reception of my app(s) (the funnel counts above)
   available to be read, so that a later developer-dashboard can show me that a $0-marketing
   app reached and engaged a real matched audience. *(H2; breakdown §4.3)*
7. **As a user,** I want my behavioral data captured under a clear, minimal posture — what
   is recorded, why, and for how long — so that measurement does not betray the trust the
   curated platform depends on. *(privacy; vision §5.6 "auditable fairness")*

### Acceptance criteria

Each criterion is `Given / When / Then`. "Recorded" means durably stored and retrievable;
"linked" means the relationship is queryable, not merely co-present.

- **AC1 (story 1 — impression):** *Given* an app is shown to a user in a curated surface,
  *When* the surface renders/sends, *Then* exactly one impression event is recorded carrying
  the user, the `App.id`, a unique impression id, the capture timestamp, and the app's
  interest `Tag.id`s as of that moment.
- **AC2 (story 1 — keys & category):** *Given* any recorded event, *When* it is read back,
  *Then* it carries stable *user × `App.id` × impression* keys and (for impressions) the
  category tags captured at show-time — never resolved live at read.
- **AC3 (story 2 — click-through):** *Given* a recorded impression, *When* the user clicks
  through from it, *Then* a click-through event is recorded and linked to that impression's
  id (not merely to the app), so shown→clicked is attributable to the instance.
- **AC4 (story 3 — return-to-platform):** *Given* a user who was shown / clicked through an
  impression, *When* they return to the platform after ~3 days and again after ~14 days,
  *Then* a return-visit signal is recorded for each window, distinguishable by window and
  linked to that user × app — derived from directly observed on-platform activity, not a
  proxy.
- **AC5 (story 3 — subscribe & on-page engagement):** *Given* a user on an app's page,
  *When* they subscribe to / follow the app, or re-engage with its page on a later visit,
  *Then* a subscribe event (and, for re-engagement, an on-page engagement event) is recorded
  tied to user × `App.id` (and the originating impression where known).
- **AC6 (story 4 — share):** *Given* a user on an app's page, *When* they share it, *Then* a
  share event is recorded tied to the `App.id` and the sharing user.
- **AC7 (off-platform proxy is secondary):** *Given* a click-through to an off-platform web
  app, *When* a best-effort proxy can resolve an open/return, *Then* it is recorded as a
  **secondary** signal flagged as proxy-derived — and *When* it cannot, *Then* the funnel
  (AC8) is still complete from on-platform signal alone, with no field requiring the proxy.
- **AC8 (story 5 — funnel reconstruction):** *Given* a chosen app and a chosen date range,
  *When* the data team queries the captured events, *Then* the complete on-platform funnel
  (impressions, click-throughs, returns@3d, returns@14d, subscribes, re-engagements, shares)
  is reconstructable from stored data alone, with no field requiring backfill.
- **AC9 (story 6 — developer readability):** *Given* a developer's app, *When* a consumer
  (e.g. developer-dashboard) requests its reception, *Then* the raw funnel counts are
  readable through a defined read path — **raw only, never scored or normalized here.**
- **AC10 (story 7 — privacy posture):** *Given* the MVP privacy posture once confirmed (see
  Constraints A4), *When* an event is captured, *Then* it records only the
  posture-permitted fields, and what-is-recorded / why / retention is stated in a
  human-readable place. *(Contingent on the SC-6 confirmation call.)*
- **AC11 (correctness — fail loud):** *Given* a capture attempt that cannot be completed,
  *When* it fails, *Then* the failure surfaces (logged/alertable) and the completeness
  metric reflects it — capture is **never silently best-effort** (CLAUDE.md §5.4).

### Success metrics

Measurable signals; targets are illustrative (D-2 sets no global non-functional ceiling).

- **Impression-capture completeness** — recorded impression events ÷ apps actually shown in
  digests. Target ≈ 100%; this is the corpus's foundation.
- **Click-through attribution rate** — click-through events successfully linked to an
  originating impression ÷ all click-throughs. Target high; unlinked clicks are weak signal.
- **Return-rate observability** — share of impressed/clicked users for whom a
  return-to-platform outcome (returned vs. not, per window) is determinable from on-platform
  data. Target ≈ 100% — this is now *directly observed*, which is the whole point of the
  pivot (SC-7).
- **Engagement-event capture** — subscribe/follow and on-page re-engagement events recorded
  per app that received impressions (feeds the retention picture).
- **Off-platform proxy coverage (secondary)** — share of click-throughs for which the proxy
  resolves an off-platform open/return, reported **honestly as a secondary** number; it will
  be low by design and is **not** a gate (Risk R1).
- **Event loss / capture-error rate** — failed or dropped captures ÷ attempts. Target near
  0; a lossy corpus invalidates H3.
- **H3 backtest readiness (gate, qualitative→binary):** for ≥1 app over a full evaluation
  window, the team can answer *"would a score computed from these signals have matched the
  editorial pick?"* using stored on-platform data alone. This is the feature's reason to exist.
- **Per-app reception availability** — every catalogued app that received ≥1 impression has
  readable funnel counts (feeds H2 / developer-dashboard).

### In scope

- Capturing the defined **on-platform** event types: **impression, click-through,
  return-to-platform (3d & 14d), subscribe/follow, on-page re-engagement, share** — in the
  curated MVP surfaces.
- Per-event **user × `App.id` × impression** keys, and **capture-time category tags**
  (`Tag.id`, resolved per D-5) on impressions, for future per-category baselines.
- The **off-platform open/return proxy** as a **best-effort secondary** signal only —
  flagged as proxy-derived, never required for funnel completeness (SC-7, AC7).
- A **read path** that exposes raw funnel counts per app for downstream consumers
  (dashboard, future score, editorial) — raw, unscored.
- A stated, minimal **MVP privacy posture** for behavioral data (pending the SC-6 confirmation).
- **Fail-loud** capture with a completeness/error signal.

### Out of scope

- **The incentive product surfaces that *generate* on-platform engagement** — subscription
  / notification UX, **developer↔user communication**, **early-access programs**, and any
  other reason-to-return mechanics. signal-capture **records** the events these surfaces
  emit (subscribe, return, on-page engagement); it does **not build** them. They are new
  candidate features for the Coordinator (logged **OQ-4**), owned elsewhere — folding them
  here would break the single-responsibility measurement spine (CLAUDE.md §6.4).
- **The event-schema design itself** — *what* to capture is defined here; *how* it is
  modeled/stored/exposed is the Stage-2 Architect's near-irreversible, repo-wide decision
  (breakdown §4.5; flagged in [DECISIONS.md](DECISIONS.md) & [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).
- **Quality Score computation** — scoring, per-reviewer calibration, per-category baselines,
  confidence intervals, reputation weighting (vision §3.1/§3.2). These are *consumers* of
  this data, deferred (breakdown §3). signal-capture stores raw signal only.
- **Matching engine / ring computation / impression allocator** (vision §2.2) — humans
  assemble digests at MVP.
- **Integrity / anomaly / graph analysis** (vision §4) — a later consumer of the corpus.
- **Native mobile/desktop install attribution & any SDK** — web-only at MVP (D-1);
  explicitly deferred until the platform expands beyond web. (This is the off-platform-install
  problem the pivot SC-7 deliberately steps away from.)
- **Ratings/reviews capture and the curated-rating gate** — owned by `ratings-reviews`;
  this feature captures *behavioral*, not explicit, signal.
- **Developer-dashboard UI** — owned by `developer-dashboard`; signal-capture only makes the
  data *readable*, it builds no dashboard surface.
- **The digest/app-page surfaces that emit events** — owned by `weekly-digest` / `app-pages`;
  signal-capture defines the capture contract those surfaces call into.

### Constraints & assumptions

| # | Item | Status |
|---|------|--------|
| C1 | Stack is Django / DRF / PostgreSQL, shared root `apps/` ([D-4](../../DECISIONS.md)). | **verified** |
| C2 | Niche = vibecoded webapps, **web-only at MVP** ([D-1](../../DECISIONS.md)) → native-install attribution out; for web apps the return-rate signal is observed **on-platform** (vision Open Q #4), which is the spine. The off-platform proxy is best-effort secondary only. | **verified** |
| C3 | Depends on `identity-accounts`: events key to the one `Account.id` ([D-3](../../DECISIONS.md)). | **verified** |
| C4 | Apps are referenced by `App.id` via the [D-6](../../DECISIONS.md) selectors; tags by `Tag.id` via [D-5](../../DECISIONS.md). Events must adopt both contracts. | **verified** |
| C5 | No global hard non-functional ceiling ([D-2](../../DECISIONS.md)); targets are per-feature. Capture must still be **non-blocking** to the user surface and **not silently lossy** (CLAUDE.md §5.2/§5.4). | **verified (posture)** |
| A1 | Curated surface at MVP is the **weekly digest only**; capture must not assume a browsable feed exists yet (breakdown §3). Subscribe/on-page-engagement events become live as their surfaces ship (see A6). | unverified |
| A2 | Return windows are **3 days and 14 days** (vision §3.1). Exact tolerance ("~3d") is a design detail. | unverified |
| A3 | Events are stored **for the full MVP duration with no auto-purge**, because the H3 backtest requires the historical corpus. | unverified — see A4 |
| A4 | **MVP privacy posture (proposed, SC-6):** record only pseudonymous, in-platform behavioral events keyed to `Account.id`; purpose = future-score backtest (H3); consent via the signup ToS (no separate per-event opt-in) given the small, hand-recruited, trusted cohort; retention per A3. | **unverified — confirmation call SC-6** |
| A5 | A single, reusable **capture contract** (one write path the emitting surfaces call) is preferable to each surface writing events ad hoc — so the schema/keys/fail-loud rule live in one place (CLAUDE.md §5.3). Design's call to realize; flagged as the intent. | unverified |
| A6 | **Engagement events presuppose surfaces that don't exist yet.** `subscribe/follow` and `on-page re-engagement` require an app-page + a subscription/notification surface (owned by `app-pages` and the new incentive features in OQ-4). signal-capture defines their **capture contract** now; the events go live when those surfaces ship. A thin corpus caused by *no engagement happening* is a product-surface gap (R6), not a capture failure. | unverified — dependency |

### Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | The off-platform open/return proxy **under-counts**: a user who clicks through to an off-platform web app and never comes back is invisible. | High / **Low** (down from High after SC-7) | **Structural** mitigation: the spine is now directly observed on-platform signal (return-to-platform, subscribe, on-page engagement, share), so the proxy is a *secondary* number, not the corpus. Report proxy coverage honestly; record the gap as a known limitation; leave a design seam for a stronger return signal later — do **not** over-engineer attribution now. |
| R2 | The **event schema is modeled badly** → near-irreversible debt inherited by the whole north-star architecture (breakdown §4.5). | Medium / Very High | Brief mandates *user × app × impression* keys + capture-time category tags + raw-not-scored; the schema is escalated to a **global** Stage-2 decision, not made implicitly. |
| R3 | **Privacy posture wrong or unstated** → capture data we shouldn't, or erode the trust the platform sells (§5.6). | Medium / High | Define a minimal MVP posture here (A4); confirm via SC-6 before Stage 2; state what/why/retention in a human-readable place (AC10). |
| R4 | **Silent event loss** corrupts the corpus → the H3 backtest is invalid but looks fine. | Medium / High | Fail-loud capture (AC11) + completeness/error metrics; capture is never best-effort-silent. |
| R5 | **Scope creep toward the Quality Score** — capturing slides into normalizing/scoring "while we're here." | Medium / Medium | Hard out-of-scope line: store raw, score later (breakdown §2/§3); AC9 says the read path is raw-only. |
| R6 | **Thin corpus because engagement never happens** — if users have no reason to return/subscribe and developers don't use the platform as a front page, the on-platform signal is sparse. This is the flip side of the pivot. | Medium / High | Out of *this* feature's control by design: capture is correct regardless. The fix is the **incentive surfaces** raised as new candidate features (OQ-4) — escalated to the Coordinator so the engagement loop is built, not silently assumed. signal-capture must not be blamed for, or expanded to solve, a product-surface gap. |

### Vision alignment

Serves vision **§3.1 / §3.2** (this *is* the behavioral-signal layer the Quality Score
consumes, with per-impression keys and per-category tags for the fairness normalizations),
and is **more faithful to vision Open Q #4** by measuring web-app behavior where it is
observable — *return visits via the platform* — instead of an off-platform proxy. It upholds
the MVP's core discipline **§5.4 / breakdown §2** ("measure now, score later"). It directly
proves **H3** (de-risk the algorithm before building it) and feeds **H1** (digest
conversion) and **H2** (developer-visible reception). Most fundamentally it upholds the prime
principle — *visibility is earned through quality, not bought* — by making **behavioral
primacy** (the hard-to-fake signal that real users kept engaging with an app on the platform)
recordable, so that one day **money can buy tools, never position**.

---

*Open questions are tracked in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md); confirmation calls
flagged for the user are logged in [DECISIONS.md](DECISIONS.md). This brief is **awaiting
approval** before hand-off to the Software Architect (Stage 2).*
