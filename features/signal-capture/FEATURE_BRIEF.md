# FEATURE_BRIEF — signal-capture

*Stage 1 artifact (Product Analyst). Status: **DRAFT — awaiting approval**. Entered
`1-define` on 2026-06-18.*

## Coordinator scope seed (source: breakdown §4.5)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Measurement (the spine) · Phase 0 (schema first — see breakdown §5)
- **Purpose:** The instrumentation layer that records every behavioral signal the future
  Quality Score will consume.
- **MVP slice:** Event capture for: impression shown → click-through → install/open →
  return visit (3d/14d) → share. Includes the **cross-platform attribution prototype**
  (deep-link / "clicked through then returned to rate" proxy).
- **Proves (hypothesis):** **H3** (and feeds H1, H2)
- **Depends on:** identity-accounts
- **Vision design ref:** §3.1, §3.2, Open Q #4
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.5
- **Coordinator note:** The technical heart of the MVP and the breakdown's recommended
  first feature for **D2**. Cross-platform install/engagement tracking is the one piece of
  hard tech that must **not** be deferred (breakdown §3). The event schema is a repo-wide,
  near-irreversible decision — see [DECISIONS.md](DECISIONS.md).

---

## Brief (Product Analyst — Stage 1)

### Problem statement

The platform's differentiating machinery — the Quality Score, ring-based expansion, the
impression allocator — **cannot run without a corpus of real behavioral signal** (vision
§3, §5.4). The MVP deliberately defers that machinery and lets humans do the matching, but
that only de-risks the future algorithm **if the signals it will one day consume are
recorded from the very first impression** (breakdown §1 H3, §2).

Today nothing records behavior. The moment the weekly digest sends its first issue, every
*impression shown*, *click-through*, *app open*, *return visit*, and *share* that isn't
captured is signal lost forever — and an evaluation window we can never reconstruct. Worse,
this is **Phase-0 schema-first** work: every later surface (digest, app-pages,
ratings-reviews, developer-dashboard) either emits or reads these events, so modeling them
late means retrofitting every consumer and inheriting near-irreversible debt in the
north-star architecture (breakdown §4.5).

**Who has the problem:** the platform/data team (needs the corpus to backtest a future
score — H3); developers (their dashboard can only show reception if reception was recorded
— H2); end users (their behavior is what's captured, so the privacy posture is theirs).
**Why now:** the digest goes live next phase; capture must exist *before* the first
impression, and its event model is the most expensive thing in the MVP to get wrong.

### Goal

Every behavioral interaction in the curated loop — an app being **shown** to a user,
**clicked through**, **opened**, **returned to** (3-day / 14-day), and **shared** — is
recorded as a clean event keyed to *user × app × impression* and tagged with the app's
interest categories at capture time, so a future Quality Score can be **backtested against
editorial judgement without any re-instrumentation**.

### Domain terms

- **Impression** — one instance of a specific app being shown to a specific user in a
  curated surface (the digest at MVP). The atomic unit of fairness (vision §2). Each
  impression has its own identity so everything downstream attributes to *that* shown
  instance.
- **Click-through** — a user following a curated impression to the app's page / to the app
  itself. The first conversion step (vision §3.1 "curated conversion").
- **App open** — the user reaching the actual (off-platform, web) app after click-through.
- **Return visit** — the user coming back to the app after **3 days** and after **14 days**
  (vision §3.1 "return rate") — the hardest-to-fake, highest-weight behavioral signal.
- **Share** — a user sending an app's page to someone else; a costly-to-fake organic
  endorsement (vision §3.1).
- **Click-through-and-return proxy** — for web apps (the niche, D-1), opens/returns happen
  off-platform and cannot be observed directly; the measurable proxy is "the user clicked
  through, then came back to the platform" (vision Open Q #4 / breakdown §7 Q3). This brief
  scopes the *behaviors to capture*; the exact attribution *mechanism* is a Stage-2 design
  fork (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)).
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
3. **As the platform/data team,** I want app-open and return-visit signal captured at the
   **3-day and 14-day** marks via the click-through-and-return proxy, so that **return
   rate / retention-curve** signal exists for web apps despite opens being off-platform.
   *(H3; vision §3.1, Open Q #4)*
4. **As a user,** I want sharing an app's page recorded as an organic-share signal tied to
   the app, so that this costly-to-fake endorsement is part of the corpus. *(H3; vision §3.1)*
5. **As the platform/data team,** I want the captured events to be queryable so that, for
   any app over any evaluation window, the full funnel
   *(impressions → click-throughs → opens → returns@3d → returns@14d → shares)* can be
   reconstructed without re-instrumentation — the literal H3 backtest. *(H3; breakdown §1)*
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
- **AC4 (story 3 — open):** *Given* a click-through, *When* the user reaches the app and
  returns to the platform, *Then* an app-open signal is recorded against that
  impression/app via the click-through-and-return proxy.
- **AC5 (story 3 — returns):** *Given* a user who opened an app, *When* they return after
  ~3 days and again after ~14 days, *Then* a return-visit signal is recorded for each window,
  distinguishable by window, against that app for that user.
- **AC6 (story 4 — share):** *Given* a user on an app's page, *When* they share it, *Then* a
  share event is recorded tied to the `App.id` and the sharing user.
- **AC7 (story 5 — funnel reconstruction):** *Given* a chosen app and a chosen date range,
  *When* the data team queries the captured events, *Then* the complete funnel
  (impressions, click-throughs, opens, returns@3d, returns@14d, shares) is reconstructable
  from stored data alone, with no field requiring backfill.
- **AC8 (story 6 — developer readability):** *Given* a developer's app, *When* a consumer
  (e.g. developer-dashboard) requests its reception, *Then* the raw funnel counts are
  readable through a defined read path — **raw only, never scored or normalized here.**
- **AC9 (story 7 — privacy posture):** *Given* the MVP privacy posture once confirmed (see
  Constraints A6), *When* an event is captured, *Then* it records only the
  posture-permitted fields, and what-is-recorded / why / retention is stated in a
  human-readable place. *(Contingent on the A6 confirmation call.)*
- **AC10 (correctness — fail loud):** *Given* a capture attempt that cannot be completed,
  *When* it fails, *Then* the failure surfaces (logged/alertable) and the completeness
  metric reflects it — capture is **never silently best-effort** (CLAUDE.md §5.4).

### Success metrics

Measurable signals; targets are illustrative (D-2 sets no global non-functional ceiling).

- **Impression-capture completeness** — recorded impression events ÷ apps actually shown in
  digests. Target ≈ 100%; this is the corpus's foundation.
- **Click-through attribution rate** — click-through events successfully linked to an
  originating impression ÷ all click-throughs. Target high; unlinked clicks are weak signal.
- **Open/return proxy coverage** — the share of click-throughs for which the proxy can
  resolve an open/return, reported honestly (the proxy will under-count; see Risk R1).
- **Event loss / capture-error rate** — failed or dropped captures ÷ attempts. Target near
  0; a lossy corpus invalidates H3.
- **H3 backtest readiness (gate, qualitative→binary):** for ≥1 app over a full evaluation
  window, the team can answer *"would a score computed from these signals have matched the
  editorial pick?"* using stored data alone. This is the feature's reason to exist.
- **Per-app reception availability** — every catalogued app that received ≥1 impression has
  readable funnel counts (feeds H2 / developer-dashboard).

### In scope

- Capturing the defined event types: **impression, click-through, app-open, return-visit
  (3d & 14d), share** — in the curated MVP surfaces.
- Per-event **user × `App.id` × impression** keys, and **capture-time category tags**
  (`Tag.id`, resolved per D-5) on impressions, for future per-category baselines.
- The **cross-platform attribution prototype for web apps**: the click-through-and-return
  proxy (the only viable open/return signal given web-only D-1).
- A **read path** that exposes raw funnel counts per app for downstream consumers
  (dashboard, future score, editorial) — raw, unscored.
- A stated, minimal **MVP privacy posture** for behavioral data (pending the A6 confirmation).
- **Fail-loud** capture with a completeness/error signal.

### Out of scope

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
  explicitly deferred until the platform expands beyond web.
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
| C2 | Niche = vibecoded webapps, **web-only at MVP** ([D-1](../../DECISIONS.md)) → native-install attribution out; the web click-through-and-return proxy is the attribution model. | **verified** |
| C3 | Depends on `identity-accounts`: events key to the one `Account.id` ([D-3](../../DECISIONS.md)). | **verified** |
| C4 | Apps are referenced by `App.id` via the [D-6](../../DECISIONS.md) selectors; tags by `Tag.id` via [D-5](../../DECISIONS.md). Events must adopt both contracts. | **verified** |
| C5 | No global hard non-functional ceiling ([D-2](../../DECISIONS.md)); targets are per-feature. Capture must still be **non-blocking** to the user surface and **not silently lossy** (CLAUDE.md §5.2/§5.4). | **verified (posture)** |
| A1 | Curated surface at MVP is the **weekly digest only**; capture must not assume a browsable feed exists yet (breakdown §3). | unverified |
| A2 | Return windows are **3 days and 14 days** (vision §3.1). Exact tolerance ("~3d") is a design detail. | unverified |
| A3 | Events are stored **for the full MVP duration with no auto-purge**, because the H3 backtest requires the historical corpus. | unverified — see A6 |
| A4 | **MVP privacy posture (proposed):** record only pseudonymous, in-platform behavioral events keyed to `Account.id`; purpose = future-score backtest (H3); consent via the signup ToS (no separate per-event opt-in) given the small, hand-recruited, trusted cohort; retention per A3. | **unverified — confirmation call A6** |
| A5 | A single, reusable **capture contract** (one write path the emitting surfaces call) is preferable to each surface writing events ad hoc — so the schema/keys/fail-loud rule live in one place (CLAUDE.md §5.3). Design's call to realize; flagged as the intent. | unverified |

### Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | The click-through-and-return proxy **under-counts** opens/returns: a user who clicks through to an off-platform web app and never comes back is invisible. | High / High (biases H3 signal) | Scope the proxy honestly; capture every on-platform return that *is* observable; report proxy coverage as a metric; record the gap as a known limitation; leave a design seam for a stronger return signal later — do **not** over-engineer attribution now. |
| R2 | The **event schema is modeled badly** → near-irreversible debt inherited by the whole north-star architecture (breakdown §4.5). | Medium / Very High | Brief mandates *user × app × impression* keys + capture-time category tags + raw-not-scored; the schema is escalated to a **global** Stage-2 decision, not made implicitly. |
| R3 | **Privacy posture wrong or unstated** → capture data we shouldn't, or erode the trust the platform sells (§5.6). | Medium / High | Define a minimal MVP posture here (A4); confirm via A6 before Stage 2; state what/why/retention in a human-readable place (AC9). |
| R4 | **Silent event loss** corrupts the corpus → the H3 backtest is invalid but looks fine. | Medium / High | Fail-loud capture (AC10) + completeness/error metrics; capture is never best-effort-silent. |
| R5 | **Scope creep toward the Quality Score** — capturing slides into normalizing/scoring "while we're here." | Medium / Medium | Hard out-of-scope line: store raw, score later (breakdown §2/§3); AC8 says the read path is raw-only. |

### Vision alignment

Serves vision **§3.1 / §3.2** (this *is* the behavioral-signal layer the Quality Score
consumes, with per-impression keys and per-category tags for the fairness normalizations),
and the MVP's core discipline **§5.4 / breakdown §2** ("measure now, score later"). It
directly proves **H3** (de-risk the algorithm before building it) and feeds **H1** (digest
conversion) and **H2** (developer-visible reception). Most fundamentally it upholds the
prime principle — *visibility is earned through quality, not bought* — by making
**behavioral primacy** (the hard-to-fake signal that real users kept using an app)
recordable, so that one day **money can buy tools, never position**.

---

*Open questions are tracked in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md); confirmation calls
flagged for the user are logged in [DECISIONS.md](DECISIONS.md). This brief is **awaiting
approval** before hand-off to the Software Architect (Stage 2).*
