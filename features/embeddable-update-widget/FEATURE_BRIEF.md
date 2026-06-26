# FEATURE_BRIEF — embeddable-update-widget

_Status: **DRAFT — awaiting approval** (DN-EUW-BRIEF in [CONTROL.md](../../CONTROL.md)). Stage 1, Product Analyst._

> Activated by the **developer-wedge pivot** ([global D-10](../../DECISIONS.md)). Traces to
> vision **§5.4 (revised)** (developer wedge / bring-your-own-audience cold start) and
> **§5.6 / §4.1** + **[D-9](../../DECISIONS.md)** (money buys attention, never ranking; the
> firewall). Upstream contracts read and grounded in code (see §9).

---

## 1. Problem statement

A developer in the beachhead niche (vibecoded webapps, [D-1](../../DECISIONS.md)) already has
their own users, but the platform is empty — there is no audience here to discover them, and
there won't be until per-niche density exists ([D-10](../../DECISIONS.md) holds the discovery
network back). Two things follow:

- **The developer gets no distribution value yet**, so they have no reason to keep their app
  page and changelog current — the single-player tools alone don't pull their existing users in.
- **The platform cannot fill itself** by acquiring users directly. It needs each adopting
  developer to *bring their own audience*. A shared link does this weakly; nothing currently
  lets a developer surface their platform presence **where their users already are** — inside
  their own running app.

**Why now:** the rest of the wedge is already built (`app-pages`, `developer-updates`,
`app-subscriptions`, `developer-dashboard`, `open-search-browse`). The embeddable widget is the
**one missing load-bearing piece** of the cold-start engine ([D-10](../../DECISIONS.md)): the
mechanism that converts a developer's existing users into platform traffic.

## 2. Goal

A developer can drop a read-only "what's new" widget inside their own app that shows that app's
latest published update notices and links back to its platform page — pulling their existing
users onto the platform — with **zero ability for that widget to buy or confer ranking**.

## 3. Domain terms (defined; no undefined terms downstream)

- **Widget** — an embeddable, read-only UI fragment a developer places inside their own app/site
  that displays that app's recent **published notices** plus a labeled link to the app's
  **platform page**.
- **Host app** — the developer's own application/website where the widget is embedded.
- **End user** — a person using the host app; **not necessarily** a platform account holder.
- **Published notice** — an existing notice authored through `developer-updates`: the AS-3
  [`PublishedNotice`](../../apps/updates/selectors.py) shape — `kind ∈ {update, early_access}`,
  `title`, `summary`, `published_at`. The widget **displays** these; it never authors them.
- **App page** — the public platform page for an ACCEPTED app
  ([apps/pages](../../apps/pages/)), keyed on the stable `App.id` UUID.
- **Capture / click-through** — an end user following the widget's link from the host app to the
  app page, where the platform's existing follow / sign-up paths are reachable.
- **Non-curated surface** — a `Surface` kept **outside** `ratings.gate.CURATED_SURFACES`
  (`= {DIGEST}`); interactions on it **cannot** confer **[D-8](../../DECISIONS.md)**
  curated-rating eligibility and cannot move the Quality Score.

## 4. User stories

- **S1.** As a **developer**, I want to embed a widget inside my own app that shows my app's
  latest update notices, so that my existing users see my changelog without me hand-maintaining one.
- **S2.** As a **developer**, I want the widget to link back to my app's platform page, so that my
  existing users discover and can follow my app on the platform (bring-your-own-audience capture).
- **S3.** As an **end user** of the host app, I want to read the latest updates and click through
  to learn more **without needing a platform account**, so that I stay informed and can choose to
  engage further.
- **S4.** As a **developer**, I want the widget to reflect notices I publish/withdraw through the
  existing update channel, so that I keep **one source of truth** for announcements.
- **S5.** As the **platform**, I want every widget impression and click-through to be a
  non-curated surface, so that embedding the widget can **never** buy or confer ranking /
  curated-rating eligibility (§5.6 / §4.1 firewall).
- **S6.** As a **developer** in the vibecoded niche, I want a drop-in embed with **no platform
  build toolchain**, so that I can adopt the widget without changing how I build my app.

## 5. Acceptance criteria (Given / When / Then)

- **AC1 (S1).** *Given* an ACCEPTED app with ≥1 published notice, *When* its widget renders,
  *Then* it shows that app's most-recent published notices (kind, title, summary, published date),
  newest first, bounded to a configured maximum.
- **AC2 (S1).** *Given* an app with no published notices, *When* its widget renders, *Then* it
  shows a neutral empty state (no error) and still offers the link back to the app page.
- **AC3 (S4).** *Given* the developer publishes a new notice or withdraws one through the existing
  `developer-updates` channel, *When* the widget is next loaded, *Then* the displayed notices
  reflect that change — the widget reads the **same published-notice source of truth** and never
  authors or stores notices of its own.
- **AC4 (S2).** *Given* a rendered widget, *When* an end user activates its "view on platform"
  link, *Then* they land on that app's platform app page (keyed on `App.id`), from which the
  existing follow / sign-up paths are reachable.
- **AC5 (S3).** *Given* an end user who is **not** a platform account holder, *When* the widget
  loads in the host app, *Then* the notices and link render without requiring authentication
  (anonymous public read), exposing only the app's already-public notice content + link.
- **AC6 (S5 — the firewall, hard constraint).** *Given* any widget impression or widget
  click-through, *When* signals are evaluated for the curated-rating gate, *Then* that interaction
  is on a surface **outside** `ratings.gate.CURATED_SURFACES` and confers **no** D-8
  weight-eligibility — it cannot move the Quality Score, by construction.
- **AC7 (S6).** *Given* a developer following the documented embed steps, *When* they add the
  widget to their host app, *Then* no platform-specific build toolchain is required (a drop-in
  embed).
- **AC8 (S3 — abuse bound).** *Given* the widget is an unauthenticated public read surface,
  *When* it is requested, *Then* it serves only already-public notice content + the link and the
  surface is rate-limited (no private data, no unbounded read; exact limits set in design).

## 6. Success metrics

| ID | Metric | Why it matters |
|----|--------|----------------|
| **M1** | **Developer adoption:** # / % of accepted niche apps that have embedded the widget. | The wedge working — devs choose to surface the platform inside their app. |
| **M2** | **Capture click-through rate:** widget loads → "view on platform" activations. | The bring-your-own-audience pull is happening. |
| **M3** | **Audience conversion:** new platform accounts / follows attributable to a widget click-through. | The capture engine's payoff — existing users becoming platform users. (Attribution mechanism = Stage 2.) |
| **M4** | **Reach / freshness:** widget loads per embedded app over time. | The changelog is actually being seen by end users. |
| **M5** | **Firewall integrity (target = 0):** curated-rating eligibilities conferred by a widget interaction. | Must be **0 by construction** — the §5.6/§4.1 promise that money/embedding never buys ranking. |
| **M6** | **Reliability:** widget render latency + error rate on the public read. | It sits inside someone else's app; it must be fast and robust or devs remove it. |

## 7. In scope / Out of scope

**In scope**
- A **read-only** embeddable widget that displays an app's recent published notices + a labeled
  link to its platform page.
- An **anonymous / public read** of an ACCEPTED app's own published notices for embedding.
- The **non-curated-surface boundary** for all widget interactions (the hard firewall, AC6).
- A documented **low-friction, drop-in** embed path for the developer (AC7).
- A neutral **empty state** (AC2).

**Out of scope**
- Authoring / editing / withdrawing notices inside the widget — that is `developer-updates`; the
  widget only displays.
- Account creation, follow, or auth UI **inside** the widget — capture happens by click-through to
  the platform's existing app-page / identity paths.
- **Paid promotion placements** ([D-9](../../DECISIONS.md)) — a separate future monetization
  surface. The widget is a **free** single-player tool for a developer's **own** notices, not a
  bought placement.
- Update re-boosts / impression allocation and any discovery-network behavior — held until density
  ([D-10](../../DECISIONS.md)).
- Email / push delivery of notices (also out of `developer-updates`).
- Deep theming / customization beyond minimal branding — MVP is a functional drop-in.
- Cross-app discovery **within** the widget (showing *other* apps) — that is network density,
  held back per [D-10](../../DECISIONS.md).
- Mobile / desktop SDK install attribution (vision Open Q#4 — a hard problem, not MVP).

## 8. Constraints & assumptions

Each marked **[verified]** (checked against code/docs) or **[unverified]** (needs confirmation or
belongs to a later stage).

- **[verified]** The notice content + shape already exists and is read-bounded: the `apps/updates`
  producer + AS-3 [`PublishedNotice`](../../apps/updates/selectors.py)
  (`published_notices_for_apps(app_ids, limit)`), `kind/title/summary/published_at`.
- **[verified]** The destination app page exists and is keyed on the stable `App.id` UUID
  ([apps/pages/urls.py](../../apps/pages/urls.py)) — a link that survives metadata edits.
- **[verified]** `ratings.gate.CURATED_SURFACES = {DIGEST}` only; `APP_PAGE` and any future widget
  surface are already **outside** it — the firewall is consistent with the existing D-8 gate
  ([apps/ratings/gate.py](../../apps/ratings/gate.py)).
- **[verified]** [D-6](../../DECISIONS.md): only ACCEPTED apps are catalogued / have a public page
  — the widget serves accepted apps only.
- **[verified]** Stack = Python / Django + PostgreSQL ([D-4](../../DECISIONS.md)).
- **[unverified — scoping call, see DN-EUW-BRIEF]** Published notices are intended to be
  **publicly readable by anonymous end users**. Today they surface only in the follower feed; the
  widget makes a developer's **own** notices a public read. The developer authors them, so consent
  is implicit, but exposing them publicly is a deliberate product expansion to confirm.
- **[unverified — Stage 2 design, OQ-EUW-1]** The embedding **mechanism** (script tag / iframe /
  rendered endpoint), cross-origin handling, and caching.
- **[unverified — Stage 2 design, OQ-EUW-2]** Whether a widget click-through **emits** a
  (non-curated) D-7 signal and whether a new `Surface` (e.g. `WIDGET`) is added — and how M2/M3
  attribution is captured. Must stay outside `CURATED_SURFACES` regardless.
- **[unverified — Stage 2 design, OQ-EUW-3]** The exact rate / abuse limits on the unauthenticated
  read surface.

## 9. Upstream grounding (traceability)

| This brief relies on | Source (read) |
|----------------------|---------------|
| Notice content + bounded read | [apps/updates/selectors.py](../../apps/updates/selectors.py) `published_notices_for_apps` |
| The render Notice shape (AS-3) | [apps/subscriptions/notices.py](../../apps/subscriptions/notices.py) |
| The destination page (stable `App.id` link) | [apps/pages/urls.py](../../apps/pages/urls.py) |
| The firewall: curated surfaces = `{DIGEST}` | [apps/ratings/gate.py](../../apps/ratings/gate.py) |
| Wedge / cold start; promotion firewall | vision §5.4 / §5.6; [D-9](../../DECISIONS.md) / [D-10](../../DECISIONS.md) |

## 10. Risks

| ID | Risk | Likelihood / Impact | Mitigation |
|----|------|---------------------|------------|
| **R1** | A widget interaction accidentally confers curated eligibility or moves the Quality Score — breaks the platform's core integrity promise. | Low / **Critical** | Hard AC6 + keep the widget surface outside `CURATED_SURFACES` **by construction**; a structural test in the no-emit precedent of prior consumers. |
| **R2** | The public, unauthenticated read is scraped / DoS'd / exposes more than intended. | Med / Med | Serve only already-public notice content + link; rate-limit the surface (AC8 / OQ-EUW-3). |
| **R3** | Adoption fails because embedding needs a build toolchain — the vibecoded niche won't bother, and the wedge stalls. | Med / **High** | Drop-in, zero-build embed as an acceptance criterion (AC7); mechanism chosen for low friction in Stage 2 (OQ-EUW-1). |
| **R4** | Capture doesn't convert — end users see the widget but don't click through or join. | Med / **High** | Clear, labeled CTA to the app page; the link lands on existing follow/sign-up paths; measure M2/M3 and iterate. |
| **R5** | The widget misbehaves inside arbitrary third-party sites (cross-origin / caching / styling). | Med / Med | Design for cross-origin + bounded caching (Stage 2, OQ-EUW-1); track latency/error rate (M6). |

## 11. Vision alignment

- **§5.4 (revised, [D-10](../../DECISIONS.md))** — the developer wedge / bring-your-own-audience
  cold-start engine. The widget is the **named capture mechanism** that fills the platform without
  acquiring users directly.
- **§5.6 / §4.1 ([D-9](../../DECISIONS.md))** — money buys attention, never ranking. The widget is
  a **free** tool, and its interactions are a **non-curated** surface firewalled from the Quality
  Score.
- **§8 money-buys-position test → PASS.** The widget confers no ranking and no curated-rating
  eligibility (AC6); it only surfaces a developer's **own** public notices + a link. It cannot be
  used to buy position.
