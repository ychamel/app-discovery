# FEATURE_BRIEF — app-subscriptions

*Stage 1 artifact (Product Analyst). Status: **awaiting approval** (DN-13). Anchored to
vision §3.1 / §5.2 / §5.4 / §6 and the `signal-capture` SC-7/SC-8 / OQ-4 origin.*

> **Domain terms** (defined once, used throughout):
> - **Follow** (user-facing) / **subscribe** (the [D-7](../../DECISIONS.md) signal kind):
>   a signed-in user marking an accepted app ([D-6](../../DECISIONS.md)) as one they want to
>   keep track of. The two words name the same act; "follow" is the UI verb, `subscribe` is
>   the reserved D-7 `EngagementEvent` kind it emits.
> - **Followed-apps feed** — a personal on-platform surface listing the apps a user follows.
>   It is the **return surface**: the reason a user comes back.
> - **Update / early-access notice** — a piece of news about a followed app (a shipped
>   update, or early-access availability). Its *content* is produced by the developer-side
>   feature `developer-updates` (Phase 3, not built); this brief concerns only whether and
>   how app-subscriptions *surfaces* such notices.
> - **Return signal** — the behavioral evidence (return-to-platform @3d/@14d, on-page
>   re-engagement) that the Quality Score consumes (vision §3.1). app-subscriptions does not
>   compute it; it *causes* it (by giving users a reason to return) and relies on
>   `signal-capture` ([D-7](../../DECISIONS.md)) to record it.

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
- **Depends on:** app-pages ✓, identity-accounts ✓, signal-capture ✓ (all closed out)
- **Vision design ref:** §3.1 (return rate / retention family), §5.4
- **Provenance:** Spawned at signal-capture's Stage-1 review (2026-06-18). The SC-7 pivot
  made the corpus depend on on-platform engagement actually occurring; SC-8 held the
  engagement *surfaces* out of `signal-capture` and raised them as new features (OQ-4). This
  is the user-side half. **Pairs with** `developer-updates` (the developer-side half).
- **Source:** [features/signal-capture/OPEN_QUESTIONS.md](../signal-capture/OPEN_QUESTIONS.md) OQ-4;
  [features/signal-capture/DECISIONS.md](../signal-capture/DECISIONS.md) SC-7/SC-8.

---

## Brief (Product Analyst — Stage 1)

### Problem statement

The platform can now show an app (`app-pages` ✓) and record behavior when it happens
(`signal-capture` ✓), but **nothing pulls a user back after their first visit.** This is a
load-bearing gap: the Quality Score's *primary* inputs are behavioral and earned over time —
**return rate @3d/@14d** and **retention** (vision §3.1) — and the whole `signal-capture`
pivot (SC-7) was predicated on measuring on-platform engagement *that actually occurs*. With
no follow loop, the corpus fills with first-visit click-throughs and little else; the most
important, hardest-to-fake signals are starved, and the platform cannot measure quality —
its entire premise (vision §1, the one-line test in §8).

**Who:** signed-in users, who currently have no durable relationship with any app and no
reason to return; and, transitively, the platform itself, whose ranking engine has no
return/retention signal to consume.

**Why now:** the three prerequisites are all live and closed out — `app-pages` (the surface
to follow *from*), `identity-accounts` (who follows — D-3), and `signal-capture` (the
recorder — D-7, which already **reserves the `subscribe` event kind**). The follow loop is
the smallest missing piece that turns a one-shot catalogue view into a returning audience.

### Goal

Let a signed-in user **follow apps they care about and return to a personal surface of
those apps**, so the platform generates and records the on-platform return/re-engagement
signal the Quality Score depends on — without letting that signal be bought (vision §4).

### User stories

1. **As a signed-in user, I want to follow an app from its page, so that I can keep track of
   apps I care about.**
2. **As a signed-in user, I want to unfollow an app I no longer care about, so that I
   control what I follow.**
3. **As a signed-in user, I want a personal feed of the apps I follow, so that I have a
   reason to return to the platform.**
4. **As a platform operator, I want every follow (and the returns it drives) recorded as
   behavioral signal, so that the Quality Score has the return/retention input it depends
   on (vision §3.1) — recorded raw, never scored here.**
5. **As a signed-in user, I want my followed-apps feed to show news (updates / early-access)
   about an app when such news exists, so that I have a concrete reason to come back** —
   noting the *producer* of that news (`developer-updates`) is not built yet (see AC5 / R1 /
   AS-3).

### Acceptance criteria

> Format: Given / When / Then. Each story has ≥1 criterion.

- **AC1 (story 1 — follow).** *Given* a signed-in user viewing an accepted app's page that
  they do not yet follow, *When* they follow it, *Then* the app becomes one of their
  followed apps and the page reflects the followed state; following an app they already
  follow is a no-op (idempotent — the follow state is single, never duplicated).
- **AC2 (story 1 — auth boundary).** *Given* an anonymous visitor (no D-3 session), *When*
  they attempt to follow an app, *Then* the follow is refused (anonymous users cannot
  follow) and they are prompted to sign in; the app page itself still renders for them.
- **AC3 (story 2 — unfollow).** *Given* a signed-in user who follows an app, *When* they
  unfollow it, *Then* the app is removed from their followed apps and the page reflects the
  not-followed state; unfollowing an app they do not follow is a no-op.
- **AC4 (story 3 — feed).** *Given* a signed-in user who follows ≥1 app, *When* they open
  their followed-apps feed, *Then* it lists exactly the apps they currently follow (each via
  its D-6 accepted-app data), and *Given* a user who follows none, *Then* the feed renders a
  clear empty state — never an error.
- **AC5 (story 4 — subscribe signal).** *Given* a successful follow (AC1), *When* it is
  recorded, *Then* exactly one D-7 `subscribe` `EngagementEvent` is emitted **through the
  `signals.capture.*` write path** (never a direct `signals_*` write), keyed `user × App.id`;
  *And* the follow surface contains **no score/weight/rank** of any kind (raw per D-7 — the
  Quality Score is a downstream consumer).
- **AC6 (story 4 — return signal, no double-build).** *Given* a user returns to the platform
  via their followed-apps feed or re-engages a followed app's page, *When* that visit
  occurs, *Then* it is captured **through the existing `signal-capture` seams**
  (`PlatformVisit` tick / `page_reengagement`), and app-subscriptions does **not**
  re-implement return/re-engagement capture (single source of truth — D-7).
- **AC7 (story 4 — fail loud).** *Given* the `subscribe` capture fails (AC5), *When* a user
  follows, *Then* the failure is surfaced and counted (`capture_error`, per D-7), not
  silently swallowed; the user-visible follow state must not claim success if the durable
  follow was not stored.
- **AC8 (story 5 — notice surface).** *Given* the followed-apps feed and the working scope
  of AS-3, *When* a user views it, *Then* it renders update/early-access notices for
  followed apps **if any exist**, and a clear empty/"no news yet" state otherwise — and it
  never errors on the (current, MVP-normal) condition that no producer has emitted any
  notice. *(Exact in/out boundary of this AC depends on DN-13 — see AS-3.)*
- **AC9 (privacy — account deletion).** *Given* a user with follows, *When* their account is
  deleted (D-3 / `accounts.delete_account`), *Then* their follow relationships are removed,
  and their already-emitted `subscribe` corpus events are handled per the existing D-7/SC-10
  rule (anonymized, not purged) — the live follow state and the behavioral corpus are
  governed by their respective owners, with no new corpus-deletion behavior invented here.

### Success metrics

Measurable from the D-7 corpus / `signals.selectors.*` and this feature's own follow store.

| # | Metric | What it tells us | Target posture (MVP) |
|---|--------|------------------|----------------------|
| M1 | **Follow adoption** — % of signed-in users who follow ≥1 app | Is the loop used at all? | Establish a baseline; trend up |
| M2 | **Follows per user** (distribution) | Depth of engagement | Observe; no fixed target (D-2) |
| M3 | **Follow-driven return rate @3d/@14d** — of users who follow ≥1 app, % who return in-window, vs. a non-follower baseline | The headline: does following *cause* return (vision §3.1)? | Followers' return rate measurably > non-followers' |
| M4 | **Feed re-engagement** — % of follows that lead to a later app-page re-engagement | Does the feed actually pull users back to apps? | Establish a baseline; trend up |
| M5 | **Subscribe capture integrity** — `subscribe` events emitted == follows recorded; `capture_error` for `subscribe` | Is the corpus complete and the write path healthy (AC5/AC7)? | 1:1; `capture_error` == 0 |
| M6 | **Unfollow rate** — unfollows / follows over a window | Churn of the relationship | Observe; high churn flags weak value |

> M3 is the metric that proves the feature's *reason to exist*. At MVP it may be thin until
> follow adoption grows and (R1) until `developer-updates` supplies notices — expected, made
> visible, not hidden.

### In scope

- Follow an accepted app (D-6) from its app page, signed-in only (D-3); idempotent single
  follow state.
- Unfollow an app.
- A personal **followed-apps feed** (the return surface) listing the user's current follows
  via D-6 accepted-app data, with an empty state.
- Emit exactly one D-7 **`subscribe`** event per follow through `signals.capture.*` (AC5),
  fail-loud (AC7).
- Account-deletion handling of the follow store (AC9), reusing the D-3/SC-10 corpus rule
  as-is for the events.
- Read-only admin visibility of follow relationships (operability).
- *(Pending DN-13 / AS-3)* a forward-compatible **notice surface** in the feed with an
  empty state, ready for `developer-updates` to fill.

### Out of scope

- **Producing/posting** update or early-access *content* — that is `developer-updates`
  (Phase 3, the developer-side half of OQ-4). app-subscriptions never authors notices.
- **Notification delivery channels** (email / push / the weekly digest). MVP is an
  on-platform feed only; cross-channel delivery is `weekly-digest`/future (resolves the
  OQ "subscription vs. the weekly digest" boundary — see OPEN_QUESTIONS).
- **Following developers** (vision §6 also lists following *developers*); MVP follows *apps*
  only. Developer-follow deferred.
- **Collections / saved lists** beyond a simple follow.
- **Any scoring/weighting/ranking** of follows or derived retention — raw only (D-7); the
  Quality Score is a downstream consumer.
- **Public follower counts / a social graph display** — follow state is private to the user
  at MVP.
- **Re-implementing return / re-engagement / visit capture** — owned by `signal-capture`
  seams (AC6); app-subscriptions reuses them.

### Constraints & assumptions

*Constraints (binding):*
- **C1** — Web-only (D-1); Python/Django server-rendered templates, `apps/` root (D-4).
- **C2** — Signed-in only for follow actions (D-3); anonymous may view app pages but not
  follow (AC2).
- **C3** — Follows reference apps by **`App.id`** and read the catalog only through D-6
  selectors (accepted apps only); tags via D-5 if shown.
- **C4** — All behavioral emission goes through `signals.capture.*` (the single D-7 write
  path); no direct `signals_*` writes; raw, no scoring (D-7).

*Assumptions (✓ verified against the repo / ⧖ to confirm via DN-13):*
- **AS-1 ✓** — D-7 already reserves the **`subscribe`** `EngagementEvent` kind (`kind ∈
  {click_through, subscribe, page_reengagement, share, off_platform_proxy}`), so emitting a
  follow needs **no new global decision** — verified in [/DECISIONS.md](../../DECISIONS.md)
  D-7.
- **AS-2 ✓** — `app-pages` provides the per-app page surface (and an established slot/
  inclusion-tag pattern, used by `ratings-reviews` for AP-1) from which a follow control can
  originate — verified (`apps/pages` closed out 2026-06-20).
- **AS-3 ⧖ (scope fork — confirm in DN-13)** — Update/early-access **notice generation is
  out of scope** (it belongs to the unbuilt `developer-updates`). The open question is
  whether MVP should still ship a **forward-compatible, empty-until-producer notice surface**
  in the feed now (option A — recommended, mirrors the honest-MVP pattern of
  `ratings-reviews` D-8 shipping a gate that's ~always not-eligible until a producer exists),
  or **defer the notice surface entirely** and ship only follow + followed-apps feed now
  (option B — strictly less to test, but the feed alone is a weaker return pull). This
  determines the exact in/out of AC8.
- **AS-4 ⧖** — The durable **follow/unfollow state** is this feature's own **mutable** store
  (one current relationship per user×app), distinct from the append-only `subscribe`
  corpus event (mirrors `ratings-reviews`' mutable `ratings_rating` vs. the D-7 corpus).
  Whether **unfollow** needs its own corpus representation (D-7 has no `unfollow` kind) is a
  Stage-2 design question (logged OQ) — the brief does not pre-decide it.
- **AS-5 ⧖ (privacy)** — Account deletion **removes** a user's follow state (a live
  relationship, not corpus), while the already-emitted `subscribe` events follow the
  existing **SC-10** rule (anonymize, not purge). Surfaced for explicit confirmation per
  CLAUDE.md §6.5 — not silently assumed.

### Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | **No producer for notices at MVP** (`developer-updates` is Phase 3) — the follow loop's strongest pull (news) is absent; the feed alone may drive weak return. | High / Med | Ship follow + feed now (it still gives a return reason *and* generates the `subscribe`/return signal); per AS-3 design the notice surface forward-compatibly so `developer-updates` fills it without rework; measure M3 uplift to validate the loop. |
| R2 | **Low follow adoption** → thin return signal; H1/H3 starved. | Med / High | One-click follow from the app page; measure M1/M3; sparing, well-timed prompts (vision §5.3) — left as a design lever, not over-built now. |
| R3 | **Double-counting / mis-attributed return signal** across `app-pages`, `weekly-digest`, and this feature. | Med / Med | Emit only the `subscribe` event here; reuse existing `PlatformVisit`/`page_reengagement` seams (AC6); one write path (D-7). |
| R4 | **Privacy** — the follow list is personal data; over-exposure (public follower lists) would leak it. | Low / Med | Follow state private to the user at MVP (out-of-scope: public counts); deletion removes follows (AC9). |
| R5 | **Scope creep** into `developer-updates` (authoring notices) or notification infra. | Med / Med | Explicit out-of-scope list; escalate any needed cross-feature work via OPEN_QUESTIONS, don't absorb it. |

### Vision alignment

Serves **§3.1** (return rate / retention — the Quality Score's *primary* behavioral input),
**§5.2** (the user-side of update re-boosts — seeing a followed app's news), **§5.4** (a
reason to return — the cold-start engagement loop), and **§6** (Collections & follows). It
upholds the core premise that **money buys tools, never position** (vision §1/§4): a follow
is earned attention recorded raw, never a purchasable rank. Proves **H1** (impressions
convert to durable engagement) and feeds **H3** (the behavioral corpus the future Quality
Score backtests against).
