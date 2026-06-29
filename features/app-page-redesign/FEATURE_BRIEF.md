# FEATURE_BRIEF.md — app-page-redesign

*Stage 1 (Product Analyst) — **awaiting user approval***

> Upstream inputs read: the user's request + Coordinator brainstorm in
> [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md); the scope decisions [APR-D-1 / APR-D-2](DECISIONS.md);
> the vision ([../../curated-app-platform-design.md](../../curated-app-platform-design.md) §1
> vision, §4 integrity, §5.4 the developer wedge, §6 app pages); the live page
> ([../../apps/pages/templates/pages/app_page.html](../../apps/pages/templates/pages/app_page.html))
> and the [`CatalogApp`](../../apps/catalog/selectors.py#L53) read-model.

---

## Problem statement

**Who.** Developers shipping a single app onto the platform (the wedge audience, [D-10](../../DECISIONS.md)),
and the visitors they bring with them.

**What problem.** The app page today renders **six fixed slots** — name, category tags, follow,
screenshots, a single plain description paragraph, a try-it button, share, reviews
([app_page.html](../../apps/pages/templates/pages/app_page.html)). The only content fields a developer
can fill are `name`, `description`, `url`, soft tags, and screenshots ([`CatalogApp`](../../apps/catalog/selectors.py#L53)).
It works as a **directory listing** but not as a **launch page**: there is no hook (no short
pitch, no in-action demo), no structured way to convey what *kind* of app it is at a glance
(genre, modality, platform, pricing, maturity), no room for depth without cluttering the top,
and nothing that makes the page feel like the **developer's hub** (their identity, their other
apps, signs the app is alive). The single free-text `description` carries an entire launch
page's worth of communication.

**Why now.** The vision makes the app page **the developer's marketing landing page and the
bring-your-own-audience face of the wedge** (§5.4; [D-10](../../DECISIONS.md)). The live staging
deploy and founding-developer recruitment are sequenced to come *after* this redesign
([APR-D-2](DECISIONS.md)) — precisely so the wedge debuts on a compelling page rather than a
stale listing. A weak page undersells every developer we recruit.

## Goal

**One sentence:** Turn the app page from a uniform *listing* into a uniform, compelling
*launch page + developer hub* — a stronger hook, structured at-a-glance facts, room for depth,
and a sense of the developer behind it — **without ever letting richness be unlocked by tier,
payment, or identity** (every accepted app gets the same slots, filled by its own content).

## Domain terms

- **Slot** — a fixed content zone on the page (e.g. "media gallery", "reviews"). The page is a
  fixed ordered set of slots; this feature adds slots, it does not make slots conditional on
  who owns the app.
- **Typed / faceted tags** — structured classification along named dimensions (genre, modality,
  platform/access, pricing model, maturity), as distinct from today's flat soft tags
  ([D-5](../../DECISIONS.md)). *Whether these become taxonomy clusters or first-class fields is a
  Stage-2 architecture call — see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q1; this brief only requires the
  capability.*
- **Pitch line / tagline** — a short hook (target ≤ ~300 characters) summarizing the app,
  doubling as the SEO/share meta-description.
- **Deep dive ("show more")** — a richer, expandable long-form description below the hook, for
  visitors the hook has already earned.
- **Devlog** — the existing [`developer-updates`](../developer-updates/) changelog feed, surfaced
  read-only on the page.
- **Uniformity guardrail** — every accepted app renders the **same slots in the same order**;
  **no slot is unlocked by tier, payment, brand, or owner identity** (vision §4 / §6; the
  [template contract](../../apps/pages/templates/pages/app_page.html#L4-L9)).

## User stories

1. **US-1 (pitch).** As a developer, I want a short pitch line at the top of my page, so a
   visitor instantly understands what my app does before scrolling.
2. **US-2 (in-action media).** As a developer, I want to show my app *in action* (screenshots
   plus an inline looping product-demo clip as a peer to images), so visitors see how it works,
   not just how it looks.
3. **US-3 (typed facets).** As a developer, I want to classify my app along structured facets
   (genre, modality, platform/access, pricing model, maturity), so a visitor can tell at a
   glance what kind of app it is and whether it fits them.
4. **US-4 (deep dive).** As a developer, I want a richer expandable "show more" description
   below the hook, so interested visitors get the full story (features, how-it-works, plans)
   without cluttering the first impression.
5. **US-5 (developer hub).** As a developer, I want a developer-identity block ("an app by ___"
   plus my other apps), so the page builds my presence and visitors can discover my other work.
6. **US-6 (alive).** As a developer, I want my recent updates surfaced on the page as a devlog,
   so visitors and followers can see the app is actively maintained.
7. **US-7 (compelling, visitor side).** As a visitor, I want the page to read as a compelling
   launch page rather than a stale listing, so I'm intrigued enough to try the app.

## Acceptance criteria

Each criterion is tagged **[agent-verifiable]** (checkable by an automated test / inspection) or
**[human-judgment]** (requires a person's eye, signed off like [premium-frontend](../premium-frontend/)'s PS-3).

- **AC-1 (US-1).** **[agent-verifiable]** *Given* an accepted app whose developer has set a pitch
  line, *When* the app page renders, *Then* the pitch line appears above the deep-dive
  description and is emitted as the page's meta-description; *And* an app with no pitch line set
  renders the page without error (graceful empty/fallback, no broken slot).
- **AC-2 (US-2).** **[agent-verifiable]** *Given* an app with a looping demo clip and
  screenshots, *When* the media gallery renders, *Then* the demo clip appears as a peer media
  item alongside screenshots, every media item carries alt/textual description (A4), and the
  clip is muted and requires no hosted-video infrastructure (it is treated as a media item — see
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q2; full hosted video stays deferred, [APR-D-1](DECISIONS.md)).
- **AC-3 (US-3).** **[agent-verifiable]** *Given* an app with facet values set, *When* the page
  renders, *Then* the facets display as an at-a-glance fact strip; *And* facets are
  *informational only* — pricing facet values (free/paid/subscription) describe the app and do
  **not** create a store/checkout, gate any slot, or affect ranking.
- **AC-4 (US-4).** **[agent-verifiable]** *Given* an app with a deep-dive description, *When* the
  page renders, *Then* the deep dive is present and reachable; *And* its content is reachable
  **without JavaScript** (the no-JS path is the source of truth — "show more" is progressive
  enhancement only, [D-13](../../DECISIONS.md)).
- **AC-5 (US-5).** **[agent-verifiable]** *Given* an app with an owner, *When* the page renders,
  *Then* a developer-identity block shows the developer and links to their other accepted apps;
  *And* it exposes no PII beyond what the developer's public profile already exposes.
- **AC-6 (US-6).** **[agent-verifiable]** *Given* an app whose developer has published updates,
  *When* the page renders, *Then* recent updates appear as an on-page devlog read **through the
  existing [`developer-updates`](../developer-updates/) read path**, preserving the no-PII / widget
  firewall posture (no new `signals` emission added to satisfy this slot; M5=0 invariant intact).
- **AC-7 (uniformity guardrail — applies to every story).** **[agent-verifiable]** *Given* any
  two accepted apps, *When* both pages render, *Then* they expose the **same set of slots in the
  same order**; *And* no slot's presence, order, or richness is a function of tier, payment,
  brand, or owner identity (the read-model carries no such field — structurally true, as today).
- **AC-8 (US-7, overall feel).** **[human-judgment]** *Given* the redesigned page on web and
  mobile, *When* the user reviews it, *Then* they sign off that it reads as a **compelling launch
  page / developer hub, not a stale listing** (the premium-frontend PS-3 sign-off precedent).
- **AC-9 (no regression).** **[agent-verifiable]** *Given* the redesigned page, *When* it
  renders, *Then* the existing slots and contracts still hold: the canonical edit-stable URL
  (current AC4), the try-it action emitting its D-7 `app_page` impression, share, follow, and
  reviews inclusion tags all still function; full suite green, no migration drift unless a
  Stage-2 schema decision deliberately introduces one (see Constraints).

## Success metrics

Structural metrics are checkable now; product metrics require the live deploy ([APR-D-2](DECISIONS.md))
and are recorded here as the post-deploy targets (no prod data exists yet — consistent with the
standing closed-out pattern of deferring live metrics).

- **M1 (structural, now).** 100% of accepted app pages render the identical slot set in identical
  order, regardless of owner — verified by test (AC-7).
- **M2 (structural, now).** Each new content capability (pitch, demo clip, facets, deep dive,
  identity block, devlog) renders correctly when filled **and** degrades to a graceful empty
  state when unfilled — no legacy app produces a broken or worse-looking page than today.
- **M3 (structural, now).** Firewall invariant **M5=0** preserved: surfacing the devlog adds no
  new score-affecting signal emission (AC-6).
- **M4 (adoption, post-deploy).** Among founding developers, the share who fill ≥1 new field
  (pitch / facets / demo clip / deep dive) within their first session — target a majority.
- **M5 (engagement, post-deploy).** App-page → try-it click-through rate is **no lower** than the
  current page's, with the hypothesis it improves (the page emits the click as a D-7 signal
  already).
- **M6 (qualitative, at release).** User sign-off on AC-8 (compelling launch page / hub).

## In scope

- A restructured app page with: a **pitch line / tagline**, a **media gallery** that treats an
  **inline looping demo clip** as a peer to screenshots, **typed/faceted tags** (genre ·
  modality · platform/access · pricing · maturity), a **richer "show more" deep-dive**
  description, a **developer-identity block** ("an app by ___" + other apps by the same dev), and
  an **on-page devlog** surfacing the existing developer-updates feed.
- Whatever read-model / authoring changes are needed for developers to set the new content
  (the *mechanism* is a Stage-2 design call; the *capability* is in scope).
- Responsive, server-rendered, no-build presentation consistent with [D-4](../../DECISIONS.md) /
  [D-13](../../DECISIONS.md) and the premium-frontend design system.
- Preserving every existing slot/contract on the page (AC-9).

## Out of scope

- **Hosted trailer/video infrastructure** (storage, transcoding, bandwidth, self-host-vs-embed)
  — deferred to its own future feature ([APR-D-1](DECISIONS.md)). v1's demo media is a looping clip
  treated as a media item only.
- **Follow-the-developer** (a developer-scoped subscription, distinct from the existing
  app-scoped follow in [`app-subscriptions`](../app-subscriptions/)) — deferred ([APR-D-1](DECISIONS.md)).
- **Community Q&A / comments** — deferred; needs its own integrity design outside the
  curated-rating gate (vision §4.1) ([APR-D-1](DECISIONS.md)).
- Any monetization, paid placement, or store/checkout behavior — pricing facets are
  informational labels only (§5.6; [D-9](../../DECISIONS.md)).
- Changes to ranking, the Quality Score, or impression allocation.
- The live staging deploy itself ([DN-PS-DEPLOY](../../CONTROL.md)) — sequenced after this feature.

## Constraints & assumptions

- **C1 — Uniformity guardrail (load-bearing).** Every accepted app renders the same slots in the
  same order; no slot is unlocked by tier/payment/brand/identity. **[verified]** against the
  current [template contract](../../apps/pages/templates/pages/app_page.html#L4-L9) and vision §4/§6.
- **C2 — Stack.** Server-rendered Django templates ([D-4](../../DECISIONS.md)), no-build token CSS
  ([D-13](../../DECISIONS.md)), responsive shell, HTMX as light progressive enhancement only; the
  no-JS path is the source of truth. **[verified]**
- **C3 — Firewall / privacy.** Surfacing the devlog must reuse the existing developer-updates
  read path and preserve M5=0 and the no-PII posture; no new score-affecting signal. **[verified]**
  the invariant exists; **[unverified]** the cheapest way to embed it (Stage-2, OQ4).
- **C4 — Schema posture.** New content fields likely require schema/read-model changes. If a
  Stage-2 decision introduces a migration, that is acceptable for a **Feature Track** item (this
  is why it is not a patch); it must be deliberate and recorded. **[unverified]** — the
  taxonomy-vs-columns choice (OQ1) and field shapes (OQ3) are explicit Stage-2 calls.
- **C5 — Accessibility.** Every media item carries a textual description (A4 holds today); "show
  more" and facet strips must be keyboard- and screen-reader-accessible without JS. **[verified]**
  as a requirement.
- **C6 — Existing integrations.** The page already hosts inclusion tags from
  [`ratings-reviews`](../ratings-reviews/), [`app-subscriptions`](../app-subscriptions/), and emits
  D-7 `app_page` impressions; these must keep working. **[verified]**
- **A1 — Assumption.** Developers will invest the effort to fill richer fields because the page
  is their marketing face (§5.4). **[unverified]** — measured by M4 post-deploy.
- **A2 — Assumption.** A looping muted demo clip delivers most of the "in-action" punch of a
  hosted trailer at a fraction of the cost. **[unverified]** — drives the APR-D-1 deferral.

## Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | Scope bleeds into the deferred heavy bets (hosted video, dev-follow, Q&A), turning v1 into a mega-feature that fights the pipeline. | Med / High | Hold the [APR-D-1](DECISIONS.md) line; out-of-scope list is explicit; escalate via OPEN_QUESTIONS if a story can't ship without a deferred bet. |
| R2 | A new slot quietly becomes a richness-by-identity unlock (e.g. only "verified" devs get the demo clip), breaking the fairness guardrail. | Low / Critical | AC-7 is a hard, tested invariant; the read-model must carry no tier/payment/identity field (Architect preserves C1). |
| R3 | New slots make legacy / sparsely-filled apps look *worse* than today's listing (empty holes). | Med / Med | M2 requires every new slot to degrade to a graceful empty state; AC-1/AC-2 require no-error rendering when unfilled. |
| R4 | Embedding the devlog leaks PII or adds a score-affecting signal, breaking the firewall. | Low / High | AC-6 + C3: reuse the existing developer-updates read path only; assert M5=0. |
| R5 | "Compelling / intriguing" is subjective and unfalsifiable, so the feature can't be called done. | Med / Med | AC-8 is an explicit human-judgment sign-off gate (PS-3 precedent) on top of the agent-verifiable structural ACs. |

## Vision alignment

Serves **§1** (a Steam-for-apps launch surface where money buys no position), **§5.4 / [D-10](../../DECISIONS.md)**
(the app page is the developer-wedge's face — strengthen it before recruiting), and **§6** (the
uniform app page / polished press-kit profile). The uniformity guardrail (C1/AC-7) directly
upholds **§4** integrity: richness is offered equally to every app, never bought or unlocked.
