# OPEN_QUESTIONS.md — app-page-redesign

Ambiguities, deferrals, and escalations across all stages. The Coordinator seeds the raw
input + the questions the Product Analyst must resolve; later personas append.

---

## Raw input from the user (verbatim intent, Coordinator capture 2026-06-29)

The user wants to **redesign the app page**. Today it is "very stale" — just a title,
description, screenshots, tags, and reviews. Functionally fine as a basic showcase, but the
goal is for this page to be **the hub for developers and their followers**: interesting,
marketable, and intriguing — showcasing the developer's app to its full potential and making
developers want to use the platform as their **main hub**.

Reference model = **Steam game pages**, adapted to **web apps and any app that has a URL**
(websites, game websites, etc.). Specifically called out:
- a **trailer/video** showcase area;
- a **short pitch** describing the app in **under ~300 characters**;
- a **focused, typed tag list** — genre, controller types, single/multiplayer,
  online/offline, etc.;
- a dedicated **"show more"** area for a richer deep-dive (complex description, plans,
  features) after the hook earns interest.

"Don't shy away from complexity here."

## The Coordinator brainstorm (input for the Product Analyst)

Anatomy proposed, grouped by zone:

- **The hook (above the fold):** hero trailer **or** an autoplaying muted product-demo loop
  (likely converts better than a cinematic trailer for software); a pitch line (<300 chars,
  doubles as SEO/share meta-description); a media carousel (screenshots + video as peers); a
  sticky primary "Try it" CTA; an at-a-glance fact strip from the typed tags.
- **Typed tags (generalize Steam genres):** Category/genre · Modality (single/multi/collab,
  online/offline, real-time/async) · Platform & access (web/PWA/desktop/mobile, signup-needed,
  browser reqs) · Pricing model (free/freemium/paid/subscription — informational, not a store)
  · Maturity (beta/live/early-access — strong fit for vibecoded apps).
- **Deep dive ("show more"):** structured long description (feature list, how-it-works),
  requirements/compatibility, FAQ, pricing detail.
- **Hub dimension:** developer identity block (avatar/bio/links + other apps by this dev);
  on-page **devlog** surfacing the existing [`developer-updates`](../developer-updates/) feed
  (highest-leverage, lowest-new-cost hub feature); follow-the-developer and community Q&A
  (deferred — see below).
- **Expandability to "any app with a URL":** handled by the typed-tag facets, **not** by
  per-type templates — different facet values render the same uniform template.

## The load-bearing guardrail (must hold through all stages)

**Uniformity = fairness (vision §4 / AC3 / the [app_page.html](../../apps/pages/templates/pages/app_page.html#L4-L9)
template contract).** Every accepted app must render the **same slots in the same order**, and
**no slot may be unlocked by tier, payment, brand, or owner identity** — `CatalogApp` carries
no such field today, and that must stay structurally true. Richness is allowed *only* as more
slots offered **equally to every app**, filled by the **developer's own content**. A solo
dev's page must be able to look as good as a studio's. Money buys neither ranking nor a richer
page. The Architect must preserve this when adding any new field/slot.

## Open questions the Product Analyst / Architect must resolve

1. **Typed tags: taxonomy extension vs. first-class `App` fields?** We already have a soft-tag
   taxonomy ([global D-5](../../DECISIONS.md)). Do the new facets become typed
   clusters/tags, or new structured columns on `App`? (Stage-2 architecture call; affects
   schema + the `CatalogApp` read-model.)
2. **Inline demo media format for v1:** muted looping clip (GIF/MP4) treated as a media item,
   vs. waiting for full hosted video (deferred). What's the cheapest demo-media slot that adds
   real punch without the video-hosting infra?
3. **Pitch line + structured description:** new `App` fields (tagline ≤N chars, structured
   long-form)? Confirm character limit and whether "show more" is one rich-text field or
   structured sub-sections.
4. **On-page devlog:** how much of [`developer-updates`](../developer-updates/) to surface on
   the page, and confirm the firewall/no-PII posture is preserved when embedding it.

## Deferred bets (APR-D-1 — to be scoped as their own future features when activated)

- **Hosted trailer/video** — storage, transcoding, bandwidth, and the self-host-vs-embed
  (YouTube/Vimeo) decision. Real infra; deserves its own feature. (v1 may include a *looping
  demo clip* as media instead — see open question 2.)
- **Follow the developer** (vs. the existing app-scoped follow in
  [`app-subscriptions`](../app-subscriptions/)) — a new subscription dimension; the deeper
  "hub for followers" payoff.
- **Community Q&A / comments** — must sit outside the Quality-Score curated-rating gate
  (vision §4.1); needs its own integrity design.
</content>
</invoke>
