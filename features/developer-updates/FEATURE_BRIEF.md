# FEATURE_BRIEF — developer-updates

*Stage 1 artifact (Product Analyst). Status: **APPROVED (DN-20, 2026-06-24 — brief + DN-20.a/b/c all approved as recommended)**.*

## Coordinator scope seed (source: signal-capture SC-7/SC-8, OQ-4 — net-new, not in the breakdown)

> Facts carried over for traceability. The Product Analyst owns the brief below; this block
> is context, not the brief.

- **Layer / build phase:** Developer-facing · Phase 3 (Dev value)
- **Purpose:** Give a developer a channel to **communicate with their subscribed users** —
  post updates, offer **early-access** — so the platform becomes the developer's **front
  page** even when they already have their own website. The developer-side **reason to use
  the platform**, which (paired with subscriptions) generates the on-platform engagement
  `signal-capture` records.
- **MVP slice:** A developer posts an update / early-access note to an app's subscribers;
  subscribers see it in their followed-apps feed and are pulled back to the platform to
  engage. Builds the *surface*; `signal-capture` records the resulting return / re-engagement.
- **Proves (hypothesis):** H2 (developers reach and engage their audience on-platform)
- **Depends on:** app-subscriptions (needs subscribers to post to), app-pages, signal-capture
- **Vision design ref:** §6 Dev-facing, §5.6 (milestone announcements to followers), §8
- **Provenance:** Spawned at signal-capture's Stage-1 review (2026-06-18). SC-7 made the
  corpus depend on on-platform engagement; SC-8 held the engagement *surfaces* out of
  `signal-capture` (OQ-4). This is the developer-side half. **Pairs with / depends on**
  `app-subscriptions` (the user side — there must be subscribers before a developer can
  address them).
- **Source:** [signal-capture/OPEN_QUESTIONS.md](../signal-capture/OPEN_QUESTIONS.md) OQ-4;
  [signal-capture/DECISIONS.md](../signal-capture/DECISIONS.md) SC-7/SC-8.

---

## Brief (Product Analyst — Stage 1)

### Problem statement

A developer who ships an app on the platform has **no way to talk to the people who already
care** about it. `app-subscriptions` lets users *follow* an app, and it deliberately shipped
an **empty-until-producer notice region** in the followed-apps feed (AS-3) — a "reason to
come back" slot with no one authoring into it. So today a follow is a one-way street: the
user opts in, and then nothing ever arrives. The developer's own changelog lives on their
external website, off-platform, where it generates no on-platform engagement and gives no
one a reason to return *here*.

Why now: subscriptions (the audience), app-pages (the destination to return to), and
signal-capture (the corpus that records returns) are all built and released. The producer
for AS-3 is the only missing piece between "users can follow apps" and "following an app
does something." Without it, H2 ("developers reach and engage their audience on-platform")
cannot be tested at all.

### Goal

Let a developer broadcast an **update** or **early-access** note about an app they own to
that app's **existing followers**, who see it in their followed-apps feed and are pulled back
to the app to engage — reaching only the audience that already opted in, never buying new
reach.

### Domain terms

- **Notice** — one published item about an app: an *update* or an *early-access* note. The
  render contract is **already pinned** by `app-subscriptions` as
  [`apps/subscriptions/notices.py::Notice`](../../apps/subscriptions/notices.py)
  (`app_id`, `kind` ∈ {`"update"`, `"early_access"`}, `title`, `summary`, `published_at`).
- **Update** — a notice telling followers what changed / what's new (a changelog post).
- **Early-access note** — a notice inviting followers to be first to try a new release.
  At MVP this is an *announcement* (a notice kind), **not** an entitlement/access-gating
  mechanism (see Out of scope).
- **Audience / followers** — the users who **currently** follow the app, i.e. the
  `subscriptions_subscription` rows for that `app_id` (the user-side `app-subscriptions`
  store; D-6 soft ref to the accepted catalog app).
- **Followed-apps feed** — the existing `app-subscriptions` surface that renders a user's
  follows plus the AS-3 notice region. developer-updates becomes its **producer** by
  repointing the single seam `notices_for_apps(app_ids)`.
- **Owner** — the developer who owns the app, per
  [`catalog.get_owned_app`/`list_owned_apps`](../../apps/catalog/selectors.py) (D-6).
- **Return / re-engagement** — a follower coming back from a notice and acting; recorded by
  `signal-capture` through its **existing** event kinds (an `APP_PAGE` impression /
  `page_reengagement`), not by anything this feature emits.

### User stories

1. **As a developer**, I want to post an **update** about an app I own, so that my followers
   learn what changed and have a reason to return.
2. **As a developer**, I want to post an **early-access** note about an app I own, so that my
   followers can be first to try a new release.
3. **As a developer**, I want to **see and withdraw** the notices I've posted for an app, so
   that I can keep the app's channel current and correct.
4. **As a follower**, I want updates from apps I follow to **appear in my followed-apps
   feed**, so that I'm pulled back to the app to engage.
5. **As the platform**, I want a developer's posts to reach **only that app's current
   followers** and emit **no new score-bearing signal**, so that money buys tools, not
   position (vision §8) and the channel can't become a "gaming manual" (Open Q #5).

### Acceptance criteria

**AC1 — owner + role gated (Story 1/2/3).**
*Given* a developer with the `developer` role who **owns** app X
([`require_role(DEVELOPER)`](../../apps/accounts/permissions.py) + `get_owned_app`),
*When* they post a notice to X, *Then* it is created and attributed to X.
*Given* a user who is **not** the owner of X (or lacks the role), *When* they attempt to
post to X, *Then* the attempt is rejected and **no notice is created** — the non-owner case
is indistinguishable from "app does not exist" (no ownership oracle).

**AC2 — post an update (Story 1).**
*Given* an owner of X submits an update with a `title` and `summary`, *When* it is saved,
*Then* a notice of kind `"update"` with a `published_at` is recorded and **honors the pinned
`Notice` contract** (`app_id`, `kind`, `title`, `summary`, `published_at`).

**AC3 — post early-access (Story 2).**
*Given* an owner of X submits an early-access note, *When* it is saved, *Then* a notice of
kind `"early_access"` with the same contract is recorded.

**AC4 — producer of the AS-3 feed seam (Story 4).**
*Given* a user follows X and the owner has posted a notice, *When* the user views their
followed-apps feed, *Then* the notice appears (newest-first) because `notices_for_apps`
now returns real notices for followed apps — the empty-until-producer seam is live.
*Given* no notices exist for the user's follows, *Then* the region shows its existing empty
state (behavior unchanged).

**AC5 — audience-scoped; buys no reach (Story 5).**
*Given* an owner posts to X, *When* the notice is distributed, *Then* it is visible **only
to users who currently follow X** — posting injects **no** digest/launch impression and
buys **no** new reach or ranking position. *(Integrity audit M5: notice reach beyond
current followers = 0.)*

**AC6 — only genuine returns count; no manufactured signal (Story 5).**
*Given* a follower returns from a notice and engages, *When* `signal-capture` records the
visit, *Then* the corpus reflects the **user's own** return via existing kinds; *and* the
**act of posting a notice emits no score-bearing / curated signal** a developer can trigger
at will (a notice is content, not an impression or an engagement event).

**AC7 — manage / withdraw (Story 3).**
*Given* an owner has posted a notice for X, *When* they view X's channel, *Then* they see
the notices they posted (newest-first). *When* they withdraw a notice, *Then* it no longer
appears in any follower's feed, and a feed that referenced it does **not** error (mirrors
the AS-3 "silently dropped" tolerance for withdrawn apps).

**AC8 — anti-spam rate limit (Story 5).**
*Given* an owner posts repeatedly within a short window, *When* they exceed the configured
per-developer/per-app posting limit, *Then* further posts are rejected with a clear message
and nothing is created — so the channel can't be used to spam followers or manufacture
attention. *(Limit is config-driven, not hardcoded — CLAUDE.md §5.2.)*

### Success metrics

- **M1 — adoption:** % of developers with ≥1 accepted app who post ≥1 notice within their
  first N days of having a follower.
- **M2 — reach:** median number of current followers a posted notice reaches (audience size).
- **M3 — return rate:** % of a notice's reached followers who return to the app within the
  post window (genuine re-engagement, measured via `signal-capture`).
- **M4 — engagement lift:** re-engagement events in a post window vs the no-post baseline.
- **M5 — integrity audit:** notice reach beyond current followers = **0** (the
  money-can't-buy-position invariant; structural, not just measured).
- **M6 — spam control:** notices rejected by the rate limit / notices per developer per
  period (channel-health guardrail).

### In scope

- An owner posts **update** and **early-access** notices on apps they own (role + owner gated).
- The notice honors the **pinned AS-3 `Notice` contract**; developer-updates becomes the
  **single producer** — `notices_for_apps` is repointed to real data.
- Notices surface in the **existing in-platform followed-apps feed**, newest-first.
- An owner can **list and withdraw** the notices they've posted for an app.
- **Rate-limiting** posts (config-driven) to prevent follower spam.

### Out of scope

- **Email / push / any external notification delivery** — MVP distribution is the in-platform
  followed-apps feed only (the AS-3 seam). External channels are a later feature.
- **Update re-boosts / fresh impression allocation** (vision §5.2) — no allocation lever
  exists at MVP; that is the impression economy, not this communication tool.
- **Early-access *entitlement* enforcement** — gating actual access to a pre-release build /
  key. MVP ships the *announcement* (a notice kind), not access control (per OQ).
- **Two-way messaging** — comments, replies, dev↔user threads, surveys. MVP is one-way
  broadcast. ("Ask about needs/problems" from the seed is deferred to a later iteration.)
- **Paid-tier gating / billing** — no billing system exists; §5.6's paid framing is deferred.
  Posting is free at MVP (free tier "always sufficient to grow", vision §5.6).
- **Showing reception / analytics here** — that is `developer-dashboard`; the boundary stays
  clean (this feature *acts*, the dashboard *shows*; seeded OQ).
- **Rich media / formatting beyond text** `title` + `summary` (matches the pinned contract).
- **A new D-7 `EventKind` or `Surface`** for "notice viewed" — reuse the existing return
  signals; a dedicated notice surface is a named future seam, not built now.
- **Scheduling / drafts** of notices (post is immediate at MVP).

### Constraints & assumptions

| # | Constraint / assumption | Status |
|---|--------------------------|--------|
| C1 | The **AS-3 producer seam** is `apps/subscriptions/notices.py` — `Notice` DTO + `notices_for_apps(app_ids)->[]`; this feature is the single repoint point; the feed renders `Notice`s unchanged. | **verified** (read the file) |
| C2 | **Owner-scoping** via `catalog.get_owned_app(owner, app_id)` / `list_owned_apps(owner)` (D-6); only the owner posts about an app. | **verified** |
| C3 | **Dev-role gate** via `accounts.roles.DEVELOPER` + `accounts.permissions.require_role` (D-3). | **verified** |
| C4 | **Audience store** is `subscriptions_subscription (user, app_id)`. It supports a reverse "who currently follows X" read via `filter(app_id=…)`, but **no reverse selector exists today** — `is_following`/`followed_apps` are user-scoped. A new **additive, bounded** owner/audience read on `apps/subscriptions` is needed (see OQ-DU-1). | **verified** (gap confirmed) |
| C5 | **Returns are already captured.** `signal-capture` records genuine returns/re-engagement through existing kinds (`APP_PAGE` impression / `page_reengagement`); `signals.kinds` has **no** notice-specific kind, and none is needed at MVP. | **verified** |
| C6 | **Stack** = Django + PostgreSQL (D-4). Notices must be persisted, so this feature likely **owns a table** (unlike the model-less `apps/pages`/`apps/discovery`/`apps/dashboard` consumers) — but model-vs-not is a **Stage-2** call, not the brief's. | verified (stack); design owns the shape |
| A1 | The in-platform feed alone is a sufficient "notification" for the MVP slice (no email/push infra). | **unverified** — confirm via DN-20.b |
| A2 | Posting is free at MVP (no billing exists; §5.6 paid framing deferred). | assumption |

### Risks

| # | Risk | L / I | Mitigation |
|---|------|-------|------------|
| R1 | **"Gaming manual" (vision Open Q #5).** A dev→follower channel feeding the same corpus the Quality Score trusts could help *manufacture* engagement signal. | M / **H** | Posting emits **no** score-bearing signal (AC6); only the follower's own genuine return is counted; posts are rate-limited (AC8). The exact transparency line must be **settled in Stage-2 design** before ship — flagged OQ-DU-2. |
| R2 | **Notification spam** erodes follower trust / triggers unfollows. | M / M | Per-developer/per-app rate limit (AC8, config), one-way only, withdraw (AC7). Watch M6 + the `app-subscriptions` `SUBSCRIPTION_UNFOLLOWED` metric. |
| R3 | **Audience fan-out N+1** at scale (a post to many followers; the feed read across many posts). | M / M | Design must keep the reverse-audience and feed reads **bounded/independent of follower count** (mirror the existing `followed_apps` two-query pattern). OQ-DU-1. |
| R4 | **Scope merge with `developer-dashboard`** into one over-scoped surface. | L / M | Explicit out-of-scope: no reception/analytics display here (seeded OQ). |
| R5 | **Early-access ambiguity** (announcement vs real entitlement) expands scope. | L / M | MVP = the announcement notice kind only; entitlement enforcement explicitly out of scope (DN-20.a). |

### Vision alignment

Serves **§6 Dev-facing** (the publish-changelogs / "Update & re-boost manager" half — the
*publish* half; re-boost is out of scope), **§5.6** (milestone announcements to followers,
shipped as a free tool at MVP), and **§8** (developers spend less time on marketing because
the platform carries the dev→audience relationship).

**Money-buys-position test → PASS.** A notice reaches **only** users who already chose to
follow the app; it injects no impression and buys no reach or ranking (AC5, M5 = 0). It is a
*tool* for talking to an audience you already earned — never a lever to acquire one.

---

## Decisions raised for approval

See `CONTROL.md` → **DN-20** (approve this brief + three bundled scoping calls **DN-20.a/b/c**).
Proposed decisions are logged in [DECISIONS.md](DECISIONS.md) (DU-1…DU-3, **PROPOSED**);
open items for Stage 2 in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) (OQ-DU-1, OQ-DU-2).
**No Stage advance until the user approves.**
