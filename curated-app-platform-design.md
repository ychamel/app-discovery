# Curated App Discovery Platform — High-Level Design

*Working title: TBD · Status: Concept / Pre-MVP · Last updated: 2026-06-26*

---

## 1. Vision

AI has collapsed the cost of building software. The result is a flood of new web, mobile, and desktop apps — most of which die in obscurity, not because they're bad, but because discovery is dominated by marketing budgets, ad spend, and store-ranking games.

**This platform is a discovery and distribution layer where visibility is earned through quality, not bought.** Think of what Steam did for game distribution, applied to apps across web, mobile, and desktop — but with a ranking system deliberately designed so money cannot buy position.

**For users:** a trusted, personalized feed of genuinely good apps matched to their interests — an antidote to app-store noise.

**For developers:** a fair launchpad. Build a good product, get it in front of a real audience, and let the audience's reaction — not your ad budget — determine your growth. Marketing becomes something the platform does *for* you.

---

## 2. The Core Mechanic: Impression Budget Economy

The unit of fairness on this platform is the **impression** — one instance of an app being shown in a user's curated feed. Apps don't buy impressions; they earn them.

### 2.1 Lifecycle of an app

1. **Submission & intake.** Developer submits the app with metadata, interest tags, media, and platform targets. A lightweight quality gate (see §6) filters spam and broken submissions — it does *not* judge taste.

2. **Launch boost.** Every accepted app receives the same standardized launch allocation — e.g., shown to *N* curated users per day for the first evaluation window (numbers illustrative throughout). Every app, from a solo dev's weekend project to a studio release, gets the identical starting deal.

3. **Evaluation window.** During the first week(s), the platform measures how curated users respond: installs/opens, return visits, retention, and explicit ratings/reviews.

4. **Earned growth (or decay).** After the window, the app's daily impression allocation is recalculated from its **Quality Score** (§3). Strong reception → more impressions and expansion into adjacent audience clusters. Weak reception → reduced impressions, but never zero (§5.3).

5. **Continuous re-evaluation.** Allocation is recalculated on a rolling basis. Quality is a living signal, not a launch-day verdict.

### 2.2 Ring-based audience expansion

Growth doesn't mean "more random impressions." It means **expanding outward through interest space, ring by ring:**

- **Ring 0 — Core:** users whose interest profile most closely matches the app's tags. The launch boost targets this ring exclusively.
- **Ring 1 — Adjacent:** users in neighboring interest clusters (e.g., a D&D campaign manager expands from *tabletop RPG* into *board games* and *worldbuilding tools*).
- **Ring 2+ — Broad:** progressively wider audiences, unlocked only by sustained strong performance in inner rings.

This solves the **niche vs. broad problem**: a niche app that delights its small core audience is a success *within its rings* and isn't punished for having a small ceiling, while a mass-market app must prove itself ring after ring to reach everyone. Apps compete primarily against the expectations of their own audience, not against apps in unrelated categories.

---

## 3. The Quality Score

The Quality Score converts user response into impression allocation. Design goals: hard to fake, low-friction for users, fair to different app types.

### 3.1 Inputs (weighted blend)

**Behavioral signals (primary — high weight, hard to fake, zero user effort):**
- **Curated conversion:** of users shown the app, how many engaged (clicked through, installed, opened)?
- **Return rate:** of users who tried it, how many came back after 3 days? 14 days?
- **Retention curve shape:** does usage persist or spike-and-die?
- **Organic sharing:** users sending the app's page to others (a strong, costly-to-fake endorsement).

**Explicit signals (secondary — qualitative richness):**
- **Ratings** from curated users only (§4).
- **Reviews**, surfaced to other users and to the developer as feedback.

**Why behavior leads:** most users never rate anything, so a ratings-only engine runs on a thin, noisy, gameable signal. Whether a real curated user *kept using the app a week later* is far harder to manufacture than a 5-star click, and it captures the silent majority.

### 3.2 Normalizations (the fairness layer)

- **Per-reviewer calibration.** Ratings are interpreted relative to each user's own rating history. A 4★ from a harsh rater outweighs a 5★ from someone who gives everything 5★. Side effect: farmed accounts that spam max ratings self-neutralize — uniform ratings carry no information.
- **Per-category baselines.** A utility app and an idle game have wildly different natural retention curves. Scores are computed against the norms of the app's category/ring, not a global average.
- **Confidence intervals.** Small sample sizes widen uncertainty; the algorithm expands an app's audience conservatively until the signal is statistically solid (a Wilson-score-like approach rather than raw averages).
- **Reviewer reputation weighting.** Users whose past ratings proved predictive of broader reception gradually carry slightly more weight. Reputation is earned slowly and decays with inactivity — making it expensive to farm.

### 3.3 What the score explicitly ignores

- Total download counts from outside the platform
- Press coverage, social-media following, brand recognition
- Any payment, subscription tier, or partnership status of the developer
- Ratings from non-curated users (see next section)

---

## 4. Integrity: Why This Is Hard to Game

### 4.1 The curated-rating gate

**Anyone can find and access any app** via search and direct links — the platform is open. But **only users to whom the app was organically curated can affect its score.** Outside visitors can rate and review for the benefit of other readers, displayed but unweighted.

This single rule kills the cheapest, most common attack: paying bot farms or review mills to rate an app directly. Their ratings simply don't count.

### 4.2 The remaining attack — pool farming — and defenses

The serious attacker's strategy becomes: *create accounts, make them look interested in my app's category, wait for my app to be curated to them, rate it up.* Defenses, layered:

| Defense | Effect on attacker |
|---|---|
| **Account maturity requirements** — rating power phases in over weeks of genuine activity | Farms must be aged and maintained, raising cost dramatically |
| **Curation unpredictability** — the matching algorithm includes randomness; no account is guaranteed to receive a given app | Attacker must farm many accounts per useful rating; ROI collapses |
| **Behavioral coherence checks** — real users browse, dwell, return irregularly; farms look mechanically uniform | Pattern-detection flags and silently de-weights suspicious cohorts |
| **Per-reviewer calibration (§3.2)** — accounts that only ever praise carry near-zero signal | Farms must rate *other* apps honestly to build weight — which is just… being a real user |
| **Behavioral primacy (§3.1)** — ratings are the minority input; retention is the majority | Faking sustained multi-week usage across aged, organic-looking accounts approaches the cost of just acquiring real users |
| **Graph analysis** — clusters of accounts that disproportionately co-rate the same apps get reviewed | Coordinated rings become visible at exactly the scale where they'd matter |

**Honest framing:** no system is unbeatable. The goal is to make manipulation *more expensive than building a better app* — that's the only equilibrium that matters.

### 4.3 Review bombing (the inverse attack)

Coordinated *negative* campaigns are blunted by the same gate (outside brigades can't touch the score) plus anomaly detection on sudden sentiment shifts among curated users, with human review for flagged cases.

---

## 5. Resolved Design Problems

### 5.1 Niche vs. broad apps
**Problem:** pure rating-driven growth either over-rewards small passionate audiences or buries them.
**Resolution:** ring-based expansion (§2.2) + per-category baselines (§3.2). Apps are judged against their own audience's expectations and grow outward only as far as reception supports.

### 5.2 The one-shot launch problem
**Problem:** Steam's most-criticized dynamic — you get one launch spike, and an app that stumbles in week one is dead forever. This is especially wrong in the AI era, where apps iterate rapidly post-launch.
**Resolution — three mechanisms:**
- **Update re-boosts.** Shipping a major update triggers a partial impression boost to a fresh slice of the core ring — a genuine second chance. Rate-limited (e.g., once per quarter) so it can't be spammed with trivial version bumps.
- **The trickle floor.** No app's allocation ever reaches zero. A small permanent baseline of impressions means a sleeper hit can still catch fire late.
- **Developer reputation carry-over.** A dev whose previous app performed well earns a modest launch-boost multiplier on their next one. Track records matter; budgets don't. (Capped, so success compounds gently rather than creating a new aristocracy.)

### 5.3 Review fatigue & rating sparsity
**Problem:** most users won't rate; the ones who do are unrepresentative.
**Resolution:** behavioral signals carry the growth engine (§3.1); ratings are calibrated per-reviewer (§3.2); rating prompts are sparing and well-timed (e.g., after a return visit, not on first open).

### 5.4 Cold start (chicken-and-egg)
**Problem:** developers won't come without users; users won't come without apps.
**Resolution — a developer wedge first, then turn on the network (revised 2026-06-26, [global D-10](DECISIONS.md)):** don't launch two-sided. Make the product genuinely useful to the *developer* on a completely empty platform, and let each developer bring their own audience — solving the chicken-and-egg by not having one.
1. **Pick one beachhead niche** where the "buried by budgets" pain is sharpest — chosen: **vibecoded webapps** ([D-1](DECISIONS.md)). Depth beats breadth.
2. **Lead with single-player developer value.** The MVP is the easiest way to spin up a beautiful public **app page** + an **update/changelog feed** — plus an **embeddable "what's new" widget** the developer drops inside their own app. A developer uses this *alone*, with zero followers, because it replaces work they already do badly (a hand-maintained landing page, scattered release notes); and every adopter **drags their existing users onto the platform** as a side effect — the widget is the capture mechanism a shared link alone isn't. This is the engine that fills the platform without acquiring users directly.
3. **Validate the wedge in staging before recruiting** ([global D-11](DECISIONS.md), 2026-06-27): stand up a reachable staging environment, deploy the built wedge, and walk it end-to-end as user / developer / admin on **web and mobile** before any founding developer is onboarded — the public app page + embeddable widget *are* the developer's face, so their UX must be validated first. The frontend stays on server-rendered Django templates ([D-4](DECISIONS.md)), polished + responsive; a dedicated SPA is evidence-gated on this walkthrough, not assumed. **Then hand-curate the founding catalog** (50–150 genuinely good apps, recruited personally, white-glove onboarding). Editorial curation substitutes for the algorithm until there's data.
4. **Hold the network back until density.** Discovery, trending, the personalized digest, and cross-app browse are worthless at ten apps and powerful at a few hundred in one niche. Turn them on only once a visitor to one developer's page can stumble onto other apps they'd actually want — that is the moment the value proposition to a new developer flips from "free changelog tool" to "free changelog tool *and* distribution."
5. **Then launch the user-side digest** — a weekly "5 apps picked for you," now backed by real catalog depth. A digest feels premium and **scarcity makes each impression valuable**, the foundation of the impression economy; graduate from there to a browsable destination feed (Steam-discovery-queue style).
6. Founding developers get a permanent "early supporter" badge — status, not algorithmic advantage.

### 5.5 Quality gate vs. gatekeeping
**Problem:** "curated" can slide into elitism, and human taste-gatekeeping doesn't scale.
**Resolution:** the intake gate checks only objective floors — the app works, isn't malware/spam/a duplicate, has honest metadata, meets basic platform policies. *Taste* is decided entirely by the audience through the score. The platform curates the *matching*, not the *merit*.

### 5.6 Sustainability without corruption
**Problem:** most "fair" platforms eventually sell ranking because nothing else pays.
**Resolution (revised 2026-06-26, [global D-9](DECISIONS.md)):** revenue comes from selling *attention*, never *ranking*. Tools and curation are free; money buys a labeled, time-boxed promotional placement that is **firewalled from the Quality Score by construction**.
- **Paid promotion placements (the primary model):** a developer pays to push a clearly-labeled, time-boxed announcement — a **new release**, a **major update**, or a **beta-tester recruitment** call — to gain reach for a bounded period. Because promo placements are a **non-curated surface**, interactions on them **cannot move the Quality Score** (they sit outside the curated-rating gate, §4.1). Ads buy the top of the funnel; **ranking still has to be earned.** The firewall is **per-impression, not per-user** — a promo impression never counts, but a user *acquired* via a promo who later gets the app organically curated and rates it does. This aligns with §4.2's equilibrium: the platform now *sells* the legitimate "just acquire real users" path.
- **Tools and curation stay free.** The dashboard, the update/changelog channel, the app page, and the earned discovery surfaces cost nothing — paying is never required to compete.
- **User supporter membership (possible later):** cosmetic perks, early digest access, a badge. No effect on anyone's score.
- **Possible later:** opt-in transaction/distribution fee if the platform ever handles payments or hosting (Steam's model) — still position-neutral.
- **Structural safeguards:** (a) publish the ranking-inputs list publicly and commit in the ToS that paid status is excluded from it; (b) promotion placements are visually distinct, always labeled, and **bounded as a published fraction of the feed** — a cap locked *before* the revenue exists, because eroding it is exactly how "fair" platforms die. Auditable fairness is a feature.

---

## 6. Platform Components (High Level)

### User-facing
- **Curated feed / digest** — the core surface; daily queue or weekly digest depending on phase.
- **Interest profile** — explicit tags chosen at signup + implicit refinement from behavior.
- **App pages** — uniform template for every app (identical media slots, layout, and visibility mechanics for solo devs and studios alike). Reviews, platform links/downloads.
- **Open search & browse** — full catalog accessible to everyone, including non-members.
- **Collections & follows** — follow developers, save apps, see updates from followed projects.

### Developer-facing
- **Submission & intake pipeline** with the objective quality gate.
- **Dashboard:** impression allocation, ring position, score components, retention curves — *transparent enough to be actionable, abstracted enough to resist reverse-engineering for manipulation.*
- **Feedback inbox:** structured reviews and beta-tester responses.
- **Update & re-boost manager:** publish changelogs, trigger update re-boosts.
- **Press-kit page:** a polished public profile usable as the app's home on the web.

### Internal
- **Matching engine:** interest-cluster model, ring computation, impression allocator.
- **Quality Score pipeline:** signal ingestion, normalization, confidence-weighted scoring.
- **Integrity system:** account-maturity tracking, behavioral coherence, graph analysis, anomaly alerts, human-review queue.
- **Editorial tools** (cold-start phase): manual catalog and digest curation.

---

## 7. Key Open Questions

1. **Beachhead niche:** which single vertical launches first? (Decision drives everything in §5.4.)
2. **Allocation function shape:** how steep is the reward curve from score → impressions? Too steep recreates winner-take-all; too flat fails to reward quality. Needs simulation before launch.
3. **Evaluation window length:** one week vs. one month per ring? Likely category-dependent.
4. **Cross-platform install tracking:** behavioral signals are easy for web apps (link clicks, return visits via the platform) but mobile/desktop installs happen off-platform. Options: deep-link attribution, optional lightweight SDK, or treating "clicked through to store + returned to rate later" as the proxy. This is a genuine technical hard problem to prototype early.
5. **Transparency level for devs:** where exactly is the line between actionable insight and a gaming manual?
6. **Governance:** who adjudicates integrity flags and gate appeals — staff, community jury, or hybrid?

---

## 8. Success Criteria

- **Users:** a meaningful share of curated impressions convert to trials; users report discovering apps they love that they'd never have found elsewhere; digest open rates stay high (scarcity preserved).
- **Developers:** apps with zero external marketing demonstrably reach audiences and grow on reception alone; devs report spending less time on marketing and more on product.
- **Integrity:** manipulation attempts exist (they will) but measurably cost more than legitimate quality improvement.
- **The one-line test:** *a great app built by an unknown solo developer with $0 in marketing reliably finds its audience here.* If that stops being true, the platform has failed its premise.
