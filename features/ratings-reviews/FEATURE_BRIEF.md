# FEATURE_BRIEF — ratings-reviews

*Stage 1 artifact (Product Analyst). Status: **APPROVED** (2026-06-20, DN-11) — the
curated gate is resolved to **DIGEST-impression-only** (RR-2 option a); "anyone signed-in
may rate" confirmed. Sources: the Coordinator scope seed below, [curated-app-platform-design.md](../../curated-app-platform-design.md)
§3.1/§4.1/§4.3/§5.3, [mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md)
§4.2/§7 Q2, and the upstream contracts [D-6](../../DECISIONS.md) (catalogued app),
[D-7](../../DECISIONS.md) (behavioral events / impression evidence), [D-5](../../DECISIONS.md)
(tags), [D-3](../../DECISIONS.md) (identity/roles), [D-1](../../DECISIONS.md) (web-only niche),
plus the `app-pages` **AP-1** reviews-slot boundary it fills.*

## Coordinator scope seed (source: breakdown §4.2)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** User-facing · Phase 2 (User loop)
- **Purpose:** Capture explicit signal **and** enforce the curated-rating gate.
- **MVP slice:** Rate + review on an app page; **record whether the rater was curated to
  that app** so the gate is enforceable now and weightable later.
- **Proves (hypothesis):** H1, H3
- **Depends on:** `app-pages`, `signal-capture`
- **Vision design ref:** §3.1, §4.1
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.2

---

## Domain terms (defined / linked)

- **Rating** — an explicit, numeric score a signed-in user assigns to one app (vision §3.1,
  the *explicit* secondary signal, as opposed to the *behavioral* events of [D-7](../../DECISIONS.md)).
- **Review** — the optional free-text comment that may accompany a rating, surfaced to other
  readers (vision §3.1).
- **Catalogued app** — an `accepted` `catalog.App`, read **only** through the
  [D-6](../../DECISIONS.md) selectors (`get_catalogued_app` / `list_catalogued_apps`); the
  unit a rating attaches to, referenced by **`App.id`** (UUID), never by URL or name.
- **The curated-rating gate** — vision §4.1: *anyone* may find, access, **and rate** any
  app, but **only users to whom the app was organically curated may affect its score.**
  Outside (non-curated) ratings are accepted and displayed for other readers, but
  **unweighted**. This feature **records** which side of the gate each rating falls on; it
  does **not** compute any score (see RR-1).
- **Curated to app X** — the property that decides a rating's weight-eligibility. Its
  precise MVP definition is the central open decision of this brief (**OQ-1 → DN-11**); the
  candidate definitions all rest on [D-7](../../DECISIONS.md) impression evidence (was the
  app *shown* to this user on a curated surface).
- **Weight-eligible / not-weight-eligible** — the recorded determination, per rating, of
  whether it would count toward the app's score. "Recorded, not computed" (RR-1): the
  Quality Score that *uses* this is a downstream consumer (vision §3), out of scope here.
- **Curated surface** — a [D-7](../../DECISIONS.md) `Surface` on which an impression
  constitutes organic curation. The schema today defines `DIGEST` (the curated weekly
  digest) and `APP_PAGE` (an open/direct page view — **not** curation). No `DIGEST` emitter
  exists yet (`weekly-digest` / `editorial-curation-tools` unbuilt) — the source of R3.
- **Behavioral event** — an append-only [D-7](../../DECISIONS.md) signal (impression,
  click-through, share…). Ratings are **explicit**, not behavioral, signal; this feature
  *reads* D-7 impression evidence for the gate and references apps by `App.id`, but the
  rating store itself is a Stage-2 concern (OQ-4).

---

## 1. Problem statement

**Who:** users in the vibecoded-webapps niche ([D-1](../../DECISIONS.md)) who want to voice
and read opinions on apps; developers who need real audience reaction; and the platform
itself, whose entire fairness premise depends on bought/farmed ratings **not** counting.

**What problem:** `app-pages` ([AP-1](../app-pages/DECISIONS.md)) ships a uniform public
page with an **empty reviews slot** — there is nowhere for a user to rate or review an app,
and nowhere readers can see what others thought. More fundamentally, the platform's
single most important integrity rule — **the curated-rating gate** (vision §4.1: only
organically-curated users may affect a score) — has **no implementation**. Without it, the
explicit-signal channel is wide open to the cheapest, most common attack: paying a bot farm
or review mill to rate an app up (or bomb it down, §4.3). The Quality Score (vision §3) and
`developer-dashboard` both depend on a corpus of ratings *tagged with whether each one is
allowed to count*; that corpus does not exist until this feature captures it.

**Why now:** the gate must be **recorded from the very first rating**, exactly as
`signal-capture` had to capture behavioral signal before the first impression — a rating
stored today without its curated-eligibility determination is a fact lost forever, and the
H3 backtest corpus is contaminated. `app-pages` left the slot; this feature fills it and
makes the §4.1 premise real (enforceable now, weightable when the score and a curated
surface exist).

## 2. Goal

*Any signed-in user can rate and review any accepted app from its page; every rating is
stored raw together with a recorded determination of whether its author was curated to
that app — so the curated-rating gate is enforceable now and the score can weight it later
— and reviews are displayed to all readers in the app-pages reviews slot, with no scoring
performed in this layer.*

## 3. User stories

1. **As a signed-in user,** I want to leave a rating (and an optional written review) on an
   accepted app's page, so that I can share my opinion and contribute explicit signal.
2. **As any visitor (signed in or not),** I want to read other users' reviews and the app's
   rating summary on its page, so that I can judge the app from real user feedback.
3. **As the platform (integrity),** I want every rating to record whether its author was
   curated to that app at the time, so that the curated-rating gate is enforceable now and
   the score can weight it later — and bought/farmed ratings never silently count.
4. **As a signed-in user,** I want to edit or remove my own rating/review, so that I can
   correct or retract my opinion — with one active rating per app, not many.
5. **As an outside (non-curated) user,** I want my rating/review to still be accepted and
   displayed for other readers, so that the platform stays openly participatory even though
   my rating does not affect the app's score (vision §4.1).

## 4. Acceptance criteria

Each criterion is `Given / When / Then`. "Accepted app" means resolved via
[D-6](../../DECISIONS.md) `get_catalogued_app`. The curated determination follows the
definition resolved in **DN-11**.

- **AC1 (story 1 — submit).** *Given* a signed-in user on an accepted app's page who has
  not yet rated it, *when* they submit a rating within the allowed scale (with optional
  review text within length limits), *then* the rating + review is stored keyed to their
  account × `App.id` and is reflected on the page.
- **AC2 (story 1 — validation / fail-loud).** *Given* a submission with an out-of-range or
  missing required rating, or over-length review text, or for a non-existent app, *when* it
  is submitted, *then* it is rejected with a clear validation error and **nothing is
  stored** (validated at the trust boundary, CLAUDE.md §5.4).
- **AC3 (story 1 — auth required).** *Given* an anonymous visitor, *when* they attempt to
  rate or review, *then* they are required to sign in first; the rating action is
  unavailable without an account, while the app page itself still renders anonymously
  (preserving `app-pages` AC5 / AP-1).
- **AC4 (story 2 — display + empty state).** *Given* an accepted app with ≥1 review, *when*
  any visitor (signed in or not) opens its page, *then* the reviews slot displays the
  reviews and a rating summary; *given* an app with 0 reviews, *then* the slot shows a
  defined empty state (filling the `app-pages` AP-1 empty slot — no broken layout).
- **AC5 (story 3 — gate recorded for every rating).** *Given* a rating is stored, *when*
  it is written, *then* the record carries a determination of whether its author was
  curated to that app at capture time, and this determination is present for **100%** of
  stored ratings (the gate is *data*, queryable later — never absent).
- **AC6 (story 3 — no scoring in this layer).** *Given* any rating/review, *when* it is
  stored or displayed, *then* **no** weight, score, rank, average-as-quality, reviewer
  reputation, or per-reviewer calibration is computed here; ratings are stored raw beside
  the eligibility determination (the Quality Score is a downstream consumer — vision §3,
  the [D-7](../../DECISIONS.md) raw-not-scored principle).
- **AC7 (story 5 — outside ratings displayed but marked).** *Given* a user who is **not**
  curated to the app submits a rating, *when* it is stored, *then* it is still accepted and
  displayed for other readers (vision §4.1) but recorded as **not-weight-eligible** — never
  silently dropped and never silently counted.
- **AC8 (story 4 — one active rating, editable).** *Given* a user who has already rated an
  app, *when* they submit again, *then* their existing rating is **updated** (one active
  rating per user × `App.id`, no duplicate), and *when* they remove it, *then* it is
  retracted from display; how eligibility is treated on edit follows DN-11 / design.
- **AC9 (stories 1–2 — accepted apps only).** *Given* an app that is `pending`, `rejected`,
  `withdrawn`, or non-existent, *when* a rating is attempted or its reviews are requested,
  *then* it is rejected / not presented (consistent with [D-6](../../DECISIONS.md)
  accepted-only and `app-pages` AC8) — a non-catalogued app is never rated or shown as
  reviewed.

## 5. Success metrics

- **Coverage capability (H1):** % of accepted-app pages that accept a rating/review from a
  signed-in user = **100%** (every catalogued app is rateable).
- **Gate-determination completeness (integrity):** % of stored ratings carrying a recorded
  curated-eligibility determination = **100%** (AC5 — the core of "enforceable now").
- **Duplicate prevention:** number of users with >1 active rating on the same app = **0**
  (AC8).
- **No-scoring guarantee:** number of score/weight/rank values computed or stored in this
  layer = **0** (AC6 — structural).
- **Gate split (observability, feeds H3):** share of ratings recorded weight-eligible vs
  not. *At MVP this is expected to skew almost entirely **not-eligible** until a curated
  surface (`weekly-digest` / `editorial-curation-tools`) emits `DIGEST` impressions — see
  R3; the metric makes that visible rather than surprising.*
- **Explicit-signal volume & submission rate:** ratings/reviews submitted, and rate per
  page view (vision §5.3 expects this to be sparse — behavior, not ratings, carries growth).
- **Validation-rejection rate:** malformed submissions rejected at the boundary (input
  hygiene, AC2).

## 6. In scope / Out of scope

### In scope
- A **rating** (numeric) + **optional written review** submitted by a **signed-in** user on
  an accepted app's page (AC1–AC3).
- **One active rating per user × app**, **editable and removable** (AC8).
- **Recording the curated-eligibility determination** for every rating at capture time
  (AC5, AC7) — the curated-rating gate as *recorded data* (RR-1).
- **Displaying** reviews + a rating summary in the existing **`app-pages` reviews slot**
  (AP-1), with a defined empty state (AC4).
- **Accepting and displaying outside (non-curated) ratings** as not-weight-eligible (AC7,
  vision §4.1).
- **Boundary validation** and accepted-app-only enforcement via [D-6](../../DECISIONS.md)
  (AC2, AC9).

### Out of scope
- **Any score, weight, rank, average-as-quality, per-reviewer calibration, or reviewer
  reputation** — the Quality Score and its normalizations (vision §3.2) are a downstream
  consumer; this layer is raw-not-scored ([D-7](../../DECISIONS.md) principle, AC6).
- **Anomaly detection / review-bomb defense / sockpuppet & graph analysis / human-review
  queue** (vision §4.2/§4.3) — the integrity system is a separate later internal
  component; this feature only records honest raw signal + the gate flag (see R4, OQ-3).
- **Creating impressions or the curated surface** that *makes* a user "curated"
  (`weekly-digest` / `editorial-curation-tools`) — this feature **reads** curation
  evidence, it does not produce it.
- **Developer feedback inbox / structured feedback views / reply-to-review** — owned by
  `developer-dashboard` (a dev reads reviews here only as a page visitor, story 2).
- **Rating prompts / timing** (e.g. "ask after a return visit", vision §5.3) — a later
  engagement/notification concern, not this capture surface.
- **Moderation tooling, profanity filtering, abuse reporting UI** beyond basic input
  validation — deferred with the integrity system (OQ-3).
- **Changing the `app-pages` template structure or its uniformity** — this feature fills
  the existing AP-1 slot; it does not restyle the page (vision §5.6 uniformity holds).

## 7. Constraints & assumptions

Each marked **[verified]** (traceable to a decision/contract) or **[unverified]** (a
proposal the reviewer/design should confirm).

**Constraints**
- **C1 [verified — [D-4](../../DECISIONS.md)]** Built as a Django app under `apps/`,
  server-rendered, over server-side sessions; the rater is an authenticated
  [D-3](../../DECISIONS.md) account.
- **C2 [verified — [D-6](../../DECISIONS.md)]** App validity only via `get_catalogued_app`
  (accepted-only, by `App.id`); never reads `catalog_app` directly.
- **C3 [verified — [D-7](../../DECISIONS.md)]** The curated determination reads
  **impression evidence** through the `signals` contract (selectors / per D-7); references
  apps by `App.id`; performs **no** scoring; any behavioral event it emits goes through
  `signals.capture.*`.
- **C4 [verified — vision §3 / §4.1]** Ratings/reviews are **explicit secondary** signal,
  stored **raw**; weighting, calibration, and the gate *verdict's use* are downstream.
- **C5 [verified — `app-pages` AP-1]** Reviews render in the existing uniform app-pages
  reviews slot; the page stays structurally uniform and renders anonymously (AC3 — the
  rating *action* requires sign-in, the *page* does not).
- **C6 [verified — vision §1/§4.1/§5.6]** Paid/subscription/identity status is **never** an
  input to whether or how a rating counts (money buys tools, not position).

**Assumptions**
- **A1 [unverified]** A rating is a **numeric scale** (e.g. 1–5) plus an **optional**
  free-text review; the exact scale and length limits are set at Stage 2. See OQ-2.
- **A2 [unverified]** **One active rating per user per app**, editable/removable (AC8).
- **A3 [unverified]** Moderation, review-bomb/anomaly detection, reputation weighting, and
  per-reviewer calibration are **OUT** at MVP (later integrity system / Quality Score). See
  OQ-3.
- **A4 [verified — DN-11, 2026-06-20]** "Curated to app X" = the user has a
  **`Surface.DIGEST`** [D-7](../../DECISIONS.md) impression of that app; an `APP_PAGE`
  (open/direct) view never confers eligibility (vision §4.1). Forward-compatible: ~all MVP
  ratings record *not-eligible* until a `DIGEST` emitter exists (R3 — correct, not a bug).
  See OQ-1 (resolved). *Whether the gate spans `editorial-curation-tools` /
  `developer-dashboard` as a global ADR is flagged for the Architect (RR-2).*
- **A5 [unverified]** Ratings/reviews live in **this feature's own store** (explicit
  signal), distinct from the D-7 behavioral-event tables; whether the eligibility
  determination is **frozen at capture** or **re-derivable** is a Stage-2 design concern.
  See OQ-4.

**Dependencies**
- **`app-pages`** ✓ closed-out — provides the uniform page + the empty **AP-1** reviews
  slot this fills.
- **`signal-capture`** ✓ closed-out — provides [D-7](../../DECISIONS.md) impression evidence
  for the gate and the `signals.capture.*` path.
- **`submission-intake`** ✓ closed-out — provides [D-6](../../DECISIONS.md) accepted-app
  validity.
- **`identity-accounts`** ✓ closed-out — the authenticated account a rating is keyed to
  ([D-3](../../DECISIONS.md)).
- **`interest-taxonomy`** ✓ closed-out — [D-5](../../DECISIONS.md) tags (indirect).

## 8. Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | **Gate definition wrong/ambiguous** — "curated to app X" is undefined (breakdown §7 Q2); the *entire* integrity premise (§4) rests on it. Too loose → review mills count (premise dead); too tight → legitimate raters excluded. | **High** / **High** | Resolve **DN-11** before Stage 2; record the determination as *data*, not an irreversible verdict, so it is correctable/re-derivable (OQ-4); agree the definition with `editorial-curation-tools`. |
| R2 | **Scoring creep** — pressure to show a "quality average" or weight ratings here violates the raw-not-scored principle and contaminates the H3 corpus. | Med / **High** | AC6 structural: store raw rating + eligibility flag only; any aggregation/weighting is a downstream consumer, never in this layer. |
| R3 | **No curated surface at MVP** — no `DIGEST` emitter exists yet, so the eligibility flag is ~always *not-eligible*; the gate can look inert. | Med / Med | Correct behavior, not a bug: the value is the recorded substrate becoming weightable when `weekly-digest`/`editorial-curation-tools` ship. Surfaced via the §5 gate-split metric + DN-11. |
| R4 | **Abuse on an open platform** — review bombing (§4.3), spam, sockpuppets. | Med / Med | Authenticated-only + one-per-user + the gate (outside brigades land *unweighted*); full anomaly/graph defense explicitly **OUT** (later integrity system) — deferred in writing (OQ-3), not silently skipped. |
| R5 | **Anonymous-render vs auth-to-rate friction** — and per-reviewer calibration (§3.2) needs an account history, so anonymous cannot rate. | Low / Med | Page renders anonymously (AP-1 preserved); a sign-in prompt appears only on the rating action (AC3). |

## 9. Vision alignment

Implements the platform's single most important integrity rule — **the curated-rating
gate** (vision §4.1), the rule that "kills the cheapest, most common attack" of bought
ratings — by **recording** weight-eligibility on every rating so a bought rating can never
silently count, while keeping the platform openly participatory (outside ratings displayed,
unweighted). It captures the **explicit secondary signal** (ratings/reviews) the Quality
Score consumes (§3.1), keeps it **raw and uncontaminated** for the H3 backtest (§3 / the
[D-7](../../DECISIONS.md) raw-not-scored principle), and respects review-sparsity by not
forcing ratings to carry growth (§5.3). It blunts review bombing by the same gate (§4.3).
It **proves H1** (explicit user engagement on the surface) and **feeds H3** (the
eligibility-tagged corpus the score is backtested on), and upholds **"money buys tools,
never position"** — paid status is never an input to whether a rating counts (§5.6).
