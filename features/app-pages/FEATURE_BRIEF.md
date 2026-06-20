# FEATURE_BRIEF — app-pages

*Stage 1 artifact (Product Analyst). Status: **draft — awaiting approval** (CONTROL.md
DN-9). Sources: the Coordinator scope seed below, [curated-app-platform-design.md](../../curated-app-platform-design.md)
§1/§4.1/§5.6/§6, [mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.2,
and the upstream contracts [D-6](../../DECISIONS.md) (catalogued app), [D-5](../../DECISIONS.md)
(tags), [D-7](../../DECISIONS.md) (behavioral events), [D-1](../../DECISIONS.md) (web-only niche).*

## Coordinator scope seed (source: breakdown §4.2)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** User-facing · Phase 1 (get the catalog presentable — see breakdown §5)
- **Purpose:** Uniform public page per app (identical slots for solo dev & studio).
  Doubles as the dev's web home / press kit.
- **MVP slice:** Static template: media, description, platform links/downloads, reviews block.
- **Proves (hypothesis):** H1, H2
- **Depends on:** submission-intake
- **Vision design ref:** §6 User/Dev-facing
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.2

---

## Domain terms (defined / linked)

- **Catalogued app** — an `accepted` `catalog.App`, the unit app-pages renders. Read
  **only** through the [D-6](../../DECISIONS.md) selectors (`get_catalogued_app` /
  `list_catalogued_apps`), which return accepted apps only and expose `{App.id (UUID),
  name, description, url, resolved tags, ordered media}`. A `pending` / `rejected` /
  `withdrawn` app is **not** a catalogued app.
- **App.id** — the stable UUID handle for an app ([D-6](../../DECISIONS.md)); the only
  thing app-pages keys a page or a signal to (never URL or name).
- **Tag** — an interest-vocabulary tag referenced by `Tag.id` and rendered via
  `taxonomy.resolve_tag` ([D-5](../../DECISIONS.md)); follows renames/merges at read time.
- **Behavioral event** — an append-only signal (impression, click-through, share,
  on-page re-engagement) written **only** through `signals.capture.*` per
  [D-7](../../DECISIONS.md); app-pages is a named emitter, never a direct writer of
  `signals_*`.
- **Curated-rating gate** — vision §4.1: anyone may find and access any app, but only
  users to whom the app was *organically curated* may affect its score. app-pages
  realizes the **open-access** half (anyone can reach any page); the gate itself is
  owned downstream by `ratings-reviews`.
- **Uniform template** — one page structure with identical slots used for **every**
  accepted app, with no slot, size, or field that varies by the developer's identity,
  team size, or paid status (vision §1, §5.6).
- **Press kit / web home** — the public app page itself, with a stable shareable link,
  used as the app's home on the web for press and users (vision §6 Dev-facing).

---

## 1. Problem statement

**Who:** developers of accepted apps (solo devs and tiny teams in the vibecoded-webapps
niche, [D-1](../../DECISIONS.md)) and the users/visitors who decide whether to try an app.

**What problem:** `submission-intake` ([D-6](../../DECISIONS.md)) has produced a catalog
of accepted apps, but that catalog has **no public face**. There is nowhere a user can
land to see an app — its media, what it does, how to try it — and nowhere a developer can
point press or an audience. Without a page, an accepted app cannot be shown, clicked
through, shared, or reviewed, so neither H1 ("a scarce, curated surface makes users *try*
apps") nor H2 ("a $0-marketing app reaches a real audience") can be tested: the digest
(`weekly-digest`), open browse (`open-search-browse`), and reviews (`ratings-reviews`)
that follow all need an app *page* to point at.

**Why now:** app-pages is the first Phase-1 surface that turns the accepted-app substrate
into something a human can see, and it is the **widest downstream unblock** — every later
user/dev surface depends on it (CONTROL.md DN-8). It must also be the place where the
platform's fairness premise becomes visible: a solo dev's page is structurally identical
to a studio's, and it is openly reachable by anyone (vision §4.1, §5.6).

## 2. Goal

*Every accepted app has one openly-accessible, structurally-uniform public page that
presents its media, description, and a way to try it — identical for a solo dev and a
studio — usable as the app's web home, with visitor interactions captured as behavioral
signal.*

## 3. User stories

1. **As a user or anonymous visitor,** I want to view an app's page — its media,
   description, categories, and a clear way to try it — so that I can decide whether the
   app is for me.
2. **As a developer,** I want every one of my accepted apps to have a page whose
   structure is identical to every other app's, so that my $0-marketing app gets the same
   presentation as a well-funded studio's (visibility is earned, never bought).
3. **As a developer,** I want my app's page to serve as its public home / press kit at a
   stable, shareable link, so that I can point press and users to it without building my
   own site.
4. **As any visitor,** I want to reach any accepted app's page via a direct link with no
   account required, so that the catalog is openly accessible (the open-access half of the
   integrity premise).
5. **As a visitor,** I want clicking through to the app or sharing its page to be recorded
   as behavioral signal, so that my genuine engagement contributes to the app's earned
   reception (feeds H1/H3) — without me having to do anything extra.
6. **As a visitor,** I want a page for an app that is not accepted (pending, rejected, or
   withdrawn) to clearly *not* be presented as a live catalog entry, so that I never
   mistake a non-catalogued app for a curated one.

## 4. Acceptance criteria

Each criterion is `Given / When / Then`. "Renders via D-6" means the data comes only
through `get_catalogued_app` / `list_catalogued_apps`.

- **AC1 (story 1 — view).** *Given* an accepted app with media, a description, resolved
  tags, and a try-it URL, *when* a visitor opens its page, *then* the page displays the
  app's name, description, ordered media (the 1–8 images per [D-6](../../DECISIONS.md)),
  its categories (each tag rendered via `resolve_tag`), and a clearly-labelled action that
  links out to the app's URL.
- **AC2 (story 1 — empty/partial data).** *Given* an accepted app missing an optional
  element (e.g. only one image, or no tags), *when* its page is opened, *then* every slot
  still renders in the uniform layout with a defined empty/absent state — no broken slot,
  no error, and no slot collapses the layout differently than another app's.
- **AC3 (story 2 — uniformity).** *Given* any two accepted apps, *when* both pages are
  rendered, *then* they use the **same template with the same slots in the same order**,
  and **no** slot, media allowance, ordering, badge, or styling differs based on the
  developer's identity, team size, or any paid/subscription status. *(Structural: the page
  has no input for developer paid status.)*
- **AC4 (story 3 — press kit / stable link).** *Given* an accepted app, *when* its page is
  loaded, *then* it is reachable at a **stable, shareable URL** that does not change when
  the developer edits the app's mutable metadata (name, description, URL), and the page is
  self-contained enough to serve as the app's public home (media + description + try-it +
  categories, no login wall).
- **AC5 (story 4 — open access).** *Given* a visitor with **no account / not signed in**,
  *when* they open any accepted app's page by direct link, *then* the full page renders
  with no authentication required.
- **AC6 (story 5 — signal capture).** *Given* a visitor on an app's page, *when* they click
  the try-it action or share the page, *then* the interaction is recorded as a behavioral
  event **through `signals.capture.*`** ([D-7](../../DECISIONS.md)) keyed to the page's
  `App.id` — and the page **never** writes `signals_*` directly. *(How an interaction with
  no originating impression — a direct/search visit — is attributed is a design fork; see
  OPEN_QUESTIONS OQ-2.)*
- **AC7 (story 5 — capture is non-blocking to viewing).** *Given* the signal-capture path
  is unavailable or errors, *when* a visitor opens or interacts with a page, *then* the
  page still renders and the try-it/share actions still work; the failed capture is
  surfaced per the [D-7](../../DECISIONS.md) fail-loud-but-counted contract, not hidden,
  and does not block the visitor.
- **AC8 (story 6 — only accepted apps).** *Given* an app that is `pending`, `rejected`, or
  `withdrawn` (or an `App.id` that does not exist), *when* its page URL is requested,
  *then* the page is **not** presented as a live catalog entry (it returns a
  not-available / not-found response) — a non-accepted app is never rendered as if
  catalogued.
- **AC9 (reviews slot boundary).** *Given* the uniform template includes a reviews
  section, *when* a page renders during the app-pages MVP (before `ratings-reviews`
  ships), *then* the reviews slot shows a defined empty state and the page does **not**
  capture, store, or display ratings/reviews itself (that capability is owned by
  `ratings-reviews`; see Out of scope and OQ-1).

## 5. Success metrics

- **Page coverage (H2):** % of accepted apps that have a reachable live page = **100%**
  (every `accepted` app in the [D-6](../../DECISIONS.md) selector resolves to a page; zero
  accepted apps without one).
- **Uniformity (fairness):** number of accepted-app pages whose rendered structure differs
  by developer identity/team/paid status = **0** (target is structural, not statistical).
- **Open-access reachability:** % of accepted-app pages that render fully without
  authentication = **100%**.
- **Click-through (H1):** count and rate of try-it click-through events captured per page
  view (the impression→click-through link of the H1 funnel becomes measurable here; full
  funnel value depends on impressions from `weekly-digest`/`open-search-browse`).
- **Share signal:** count of share events captured per page view.
- **Page render latency:** server-render time within a budget to be set at Stage 2 (no
  global ceiling — [D-2](../../DECISIONS.md)); recorded so regressions are visible.
- **Non-accepted leakage:** number of non-accepted apps ever rendered as a live page = **0**.

## 6. In scope / Out of scope

### In scope
- One **uniform public page** per accepted app, structurally identical for all apps,
  rendering name, description, ordered media, resolved category tags, and a try-it
  action — all read via the [D-6](../../DECISIONS.md) selectors.
- **Open / anonymous access** to any accepted app's page by direct, stable link.
- The page as **press kit / web home** (self-contained, shareable, no login wall).
- **Capturing** try-it click-through and share interactions through `signals.capture.*`
  ([D-7](../../DECISIONS.md)).
- A **reviews section slot** in the template, rendered as an empty state at MVP.
- Correct handling of **non-accepted / missing** apps (not presented as catalogued).
- Empty/partial-data states for every slot (AC2).

### Out of scope
- **Capturing, storing, weighting, or displaying ratings & reviews**, and the curated-
  rating gate — owned by `ratings-reviews` (the slot is here; the content is not).
- **Search, listing, or browse** across apps — owned by `open-search-browse`. app-pages is
  a single-app page reachable by direct link only.
- **Generating impressions** or the curated feed — owned by `weekly-digest` /
  `editorial-curation-tools`. app-pages emits engagement events but is not an impression
  source.
- **Follows / subscribe** actions and update/early-access notices — owned by
  `app-subscriptions` / `developer-updates`.
- **Developer-facing analytics / dashboard** (reach, engagement, retention views) — owned
  by `developer-dashboard`. app-pages produces signal; it does not report it back to devs.
- **Editing app content** from the page — app metadata and media are owned and edited in
  `submission-intake`; app-pages is read-only over the catalog.
- **A separate downloadable press-asset bundle, press-contact field, or embargo controls**
  beyond what submission metadata already provides (see OQ-3).
- **Native-app install / store links and attribution** — web-only niche
  ([D-1](../../DECISIONS.md)); the try-it action is a web URL.
- **Any score, ranking, or quality computation** — never done in this layer
  ([D-7](../../DECISIONS.md)).

## 7. Constraints & assumptions

Each marked **[verified]** (traceable to a decision/contract) or **[unverified]** (a
proposal the reviewer/design should confirm).

**Constraints**
- **C1 [verified — [D-4](../../DECISIONS.md)]** Server-rendered Django templates over the
  existing stack; the page is a public, server-rendered HTML surface (an SPA is not chosen).
- **C2 [verified — [D-6](../../DECISIONS.md)]** Reads the catalog **only** through
  `get_catalogued_app` / `list_catalogued_apps` (accepted-only, by `App.id`); media is the
  ordered 1–8 images (PNG/JPEG/WebP, ≤5 MB) the contract exposes; never reads `catalog_app`
  directly.
- **C3 [verified — [D-5](../../DECISIONS.md)]** Renders tags via `resolve_tag(Tag.id)`;
  never displays a stored tag label.
- **C4 [verified — [D-7](../../DECISIONS.md)]** Emits engagement **only** through
  `signals.capture.*`; references apps by `App.id`; performs no scoring.
- **C5 [verified — [D-1](../../DECISIONS.md)]** Web-only; the try-it target is a URL.
- **C6 [verified — vision §1/§5.6]** The template is structurally uniform; paid/subscription
  status is not an input to the page.

**Assumptions**
- **A1 [verified — vision §4.1]** Pages are intended to be openly accessible (anonymous,
  direct-linkable, and — proposed — indexable so direct discovery works); confirmed by the
  open-access integrity premise.
- **A2 [unverified]** The reviews slot at MVP is an **empty-state placeholder**; the
  reviews content lands with `ratings-reviews` (which depends on app-pages). See OQ-1.
- **A3 [unverified]** "Press kit" at MVP = the public page + a stable link + the media
  already in submission; **no** separate press-asset download, press-contact field, or
  embargo. See OQ-3.
- **A4 [unverified]** Basic accessibility is expected: alt text on media, semantic markup,
  keyboard-reachable actions (WCAG-AA-leaning); exact bar set at Stage 2.
- **A5 [unverified]** A sensible page-render latency budget will be set at Stage 2; no
  global non-functional ceiling exists ([D-2](../../DECISIONS.md)).

**Dependencies**
- **`submission-intake`** ✓ closed-out — provides the [D-6](../../DECISIONS.md) catalogued-app
  selectors app-pages reads.
- **`signal-capture`** ✓ closed-out — provides the [D-7](../../DECISIONS.md) `signals.capture.*`
  write path app-pages emits through.
- **`interest-taxonomy`** ✓ closed-out — provides `resolve_tag` ([D-5](../../DECISIONS.md)).

## 8. Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | **Uniformity erosion** — later pressure to give studios/paying devs richer pages (more media, badges, premium layout) silently breaks the "money buys tools, not position" premise. | Med / **High** | Make uniformity **structural** (AC3): one template, no paid-status/identity input to layout; any per-dev variation is a scope violation logged, not shipped. |
| R2 | **Built before its emitter** — app-pages ships before `weekly-digest`/`open-search-browse` create impressions, so impression-originated click-through attribution (D-7 links `click_through` to an impression) can't be exercised end-to-end here. | Med / Med | Scope the page's interaction points to be **instrumentable** per [D-7](../../DECISIONS.md); treat direct/search-visit attribution as a design fork (OQ-2); verify full attribution when an impression source exists. |
| R3 | **Non-accepted leakage** — a pending/rejected/withdrawn app rendered as a live page contradicts the catalogued-only guarantee. | Low / **High** | Render strictly via [D-6](../../DECISIONS.md) accepted-only selectors (AC8); never query `catalog_app` directly; non-accepted → not-available. |
| R4 | **Reviews-slot scope bleed** — the breakdown's "reviews block" pulls ratings/gate work into app-pages, which `ratings-reviews` owns. | Med / Med | Slot-only at MVP with an empty state (AC9); rating capture/gate explicitly Out of scope and deferred to `ratings-reviews`. |
| R5 | **Open-access misuse / catalog scraping** — public, unauthenticated, indexable pages let anyone enumerate the catalog. | Low / Low-Med | Open access is a deliberate integrity premise (vision §4.1) — nothing secret is on the page; rate-limit/robots posture is a Stage-2 design concern, not a blocker. |

## 9. Vision alignment

Serves the core premise that **visibility is earned through quality, not bought** (vision
§1) by making the app's public face **structurally uniform** for solo dev and studio alike
(§5.6 structural safeguard) and **openly accessible to anyone** (§4.1, the open-access half
of the integrity model). It realizes the **App pages** and **press-kit** components (§6
User-facing and Dev-facing). It **proves H1** (a presentable page is what users click
through to try) and **H2** (a $0-marketing app gets a real, equal public presence), and
**feeds H3** by capturing click-through/share signal through the [D-7](../../DECISIONS.md)
corpus.
