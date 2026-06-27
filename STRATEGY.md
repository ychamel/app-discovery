# STRATEGY.md — Living Strategic Picture

> Owned by the **Strategist** ([process/personas/strategist.md](process/personas/strategist.md), CLAUDE.md §4.1).
> A short, current picture of *where the product is going and why*. Durable ratified bets
> are global ADRs in [DECISIONS.md](DECISIONS.md); direction changes also edit the vision
> ([curated-app-platform-design.md](curated-app-platform-design.md)). This file is the basis
> the **Coordinator** (§4) reads when picking the next feature. Keep it short — detail lives
> in the ADRs and the vision.

**Last updated:** 2026-06-27 (Strategist — next bet RATIFIED as **staging-validation-before-live**; frontend = keep templates, evidence-gated → [D-11](DECISIONS.md))

---

## The premise (non-negotiable)

*A great app built by an unknown solo developer with $0 in marketing reliably finds its
audience here.* Money buys **tools and reach, never curated position** (vision §2/§4/§5.6/§8).
Any strategy that erodes this is wrong no matter how lucrative.

## The business model (one paragraph)

Tools (dashboard, changelog/update channel, app page, widget) and curation (the earned
discovery surfaces) are **free** — paying is never required to compete. Revenue comes from
selling **attention, never ranking**: clearly-labeled, time-boxed **promotion placements**
([D-9](DECISIONS.md)) that gain a bounded period of reach and are **firewalled from the
Quality Score by construction** (a non-curated `Surface` outside `ratings.gate.CURATED_SURFACES`).
The firewall is per-impression, not per-user. Revenue is **density-gated** — it earns nothing
until there's an aggregated audience to reach.

## The current wedge ([D-10](DECISIONS.md))

A single-player **developer hub** — a beautiful public **app page** + an **update/changelog
feed** + an **embeddable "what's new" widget** the developer drops in their own app — useful
to a developer with **zero followers on day one**, so each adopter **brings their existing
audience onto the platform** (bring-your-own-audience). This solves the chicken-and-egg by
not having one. The discovery **network** (personalized digest, trending, cross-app browse
beyond open search) is **held back until per-niche density**.

**Build status:** the wedge is **code-complete** — `app-pages`, `developer-updates`,
`app-subscriptions`, `developer-dashboard`, `open-search-browse`, `embeddable-update-widget`,
and now `widget-conversion-attribution` (the full impression → click → conversion funnel) are
all built and **released to local/dev**.

## The bet sequence (sequence is the strategy)

| | Bet | State | Trigger to start |
|--|-----|-------|------------------|
| **Done** | Developer wedge (single-player hub + full attribution funnel) | Built, **local/dev only** | — |
| **NEXT (ratified, [D-11](DECISIONS.md))** | **Staging + full-role UX validation** — stand up a reachable staging env, deploy the wedge, walk it end-to-end as **user / developer / admin on web + mobile**; polish + make the templates responsive. This also exercises the deferred deploy work (hosting, domain, the stubbed D-4 email provider, monitoring). | **Ready to scope now** (Coordinator) | — (the immediate bet) |
| **Then** | **Go live + recruit the founding cohort** — promote staging to a real prod target; white-glove recruit 50–150 real vibecoded-webapp developers (§5.4 step 3) | After staging validation passes | A clean full-role walkthrough on web+mobile |
| **Held** | Network / `weekly-digest` (user-side "5 apps picked for you") | Backlog (D-10) | **Per-niche density** — a page visitor can plausibly stumble onto other apps they'd want |
| **Held** | `editorial-curation-tools` (manual catalog/digest curation) | Backlog (D-10) | Real users **and** apps to match |
| **Held** | D-9 monetization (promotion placements) | Ratified, unbuilt | An **aggregated audience** to sell reach to |

> **Why staging-validation is next and not another feature:** all three held bets are
> density-gated, and density cannot exist until the wedge is reachable by real developers
> pulling real audiences in. But you can't responsibly recruit founding developers onto a
> UI nobody has walked end-to-end or checked on mobile — and the wedge's public face (app
> page + widget) *is* the bring-your-own-audience thesis. So staging + a full-role
> walkthrough is the cheap de-risking step before live, and it doubles as the forcing
> function that decides the frontend on evidence ([D-11](DECISIONS.md)).

## Frontend posture (resolved 2026-06-27, [D-11](DECISIONS.md))

**Keep server-rendered Django templates** for the wedge ([D-4](DECISIONS.md)); polish +
make them mobile-responsive in staging. A split to a dedicated SPA frontend
(Django-as-backend-API) is **deferred and evidence-gated** — undertaken only if the staging
walkthrough shows a specific surface the templates demonstrably can't serve, and then as an
explicit D-4-revisit ADR, never a silent rewrite. Rationale: templates fit content-heavy,
SEO-sensitive public pages + a zero-build embed better than an SPA (which would need SSR to
match), and a rewrite before evidence is speculative (CLAUDE.md §5.5).

## The hard problem still unprototyped

Cross-platform/off-platform attribution (vision §7 Q4) — easy for web (link clicks, return
visits) and now partly addressed by the widget funnel; mobile/desktop installs remain the
genuine open technical problem flagged for early prototyping. Not on the critical path for
the web-only beachhead (D-1), but the named risk for any expansion beyond web.

## Top open strategic questions

1. ~~Go to prod now, or finish the network design first?~~ **RESOLVED ([D-11](DECISIONS.md), 2026-06-27):**
   neither — stand up **staging** and validate the wedge full-role (web+mobile) first, then
   go live; everything else stays density-gated behind real adoption. Frontend stays on
   templates, evidence-gated.
2. **What exactly is the density trigger?** — D-10 names "per-niche density" qualitatively
   ("a few hundred apps in one niche"; "a visitor to one page can stumble onto others they'd
   want"). It is not yet a measurable threshold. Worth making concrete before the network
   features reactivate, so the un-gate is a decision, not a vibe.
3. **Allocation-function shape & evaluation-window length** (vision §7 Q2/Q3) — need
   simulation before the impression economy turns on; not blocking the wedge, blocking the
   network.
