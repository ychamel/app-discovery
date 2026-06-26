# FEATURE_BRIEF — widget-conversion-attribution

*Stage 1 (Product Analyst). Single source of truth for what & why.*
***Status: APPROVED** (DN-WCA-BRIEF, 2026-06-26) — brief + scoping calls WCA-1/2/3
approved as recommended. WCA-1/2/3 → RESOLVED; advanced to Stage 2-design (Software
Architect). The token-carry mechanism (OQ-WCA-2…4) is the Architect's to resolve under
the AC4 no-PII + AC5 firewall envelope.*

## Origin

This feature picks up the **deferred M3 / OQ-EUW-5** work from
[embeddable-update-widget](../embeddable-update-widget/). The shipped widget delivers
**reach** — impressions + click-throughs attributed to the widget, visible on the
developer dashboard (AC9) — but explicitly **deferred** *which new account/follow came
from which widget click-through*, because that requires carrying a widget-source token
through an **anonymous** click → app page → conversion, entangling cookie consent,
cross-domain identity, and the no-PII posture
([embeddable-update-widget/DESIGN.md §11](../embeddable-update-widget/DESIGN.md)). This
brief defines that downstream-payoff measurement from scratch; the above is upstream
context, not a pre-decided design.

---

## 1. Problem statement

**Who:** a developer who has embedded the "what's new" widget inside their own app
(the [D-10](../../DECISIONS.md) developer wedge — the widget is the mechanism that drags
their existing audience onto the platform).

**What problem:** the developer can see *reach* (how many people saw the widget and
clicked through to the platform) but **cannot see whether that reach converted** — how
many of those click-throughs became platform follows of their app or new accounts. The
funnel stops at the click. Reach without conversion can't answer the only question that
justifies keeping the widget: *is the audience I'm sending over actually sticking?*

**Why now:** the widget is shipped and counting click-throughs (the honest "reached the
platform from the widget" measure). The next, named step (deferred deliberately as
EUW-10 / OQ-EUW-5) is to close the funnel: attribute the downstream **conversion** to
the widget click that caused it — the payoff the wedge was built to produce.

## 2. Goal

A developer can see how many platform **conversions** (new follows of their app; new
accounts) are attributable to **their widget**, completing the funnel
**impression → click-through → conversion** — without collecting personal data and
without the widget ever earning ranking position.

## 3. Domain terms

- **Widget click-through** — an end user clicking the widget's "view on platform" link:
  `GET /widget/<app_id>/view` → 302 to the app's page
  ([apps/widget/views.py](../../apps/widget/views.py)). Today it carries **no source
  token**; the visitor is anonymous (logged out by default).
- **Conversion** — a downstream platform action the click-through can be credited with:
  a **new follow** of the app (`subscriptions.services.follow_app` returning `created`,
  [apps/subscriptions/services.py](../../apps/subscriptions/services.py)) and/or a **new
  account registration** (`accounts` register view,
  [apps/accounts/views.py](../../apps/accounts/views.py)). Exact set = **WCA-1**.
- **Attribution** — crediting a conversion to the specific widget click-through that
  preceded it, within a bounded **attribution window**, under a stated **touch model**
  (first-touch vs last-touch) = **WCA-2**.
- **Source token** — whatever opaque marker carries "this visit originated from app X's
  widget" through the anonymous click → app page → conversion. It identifies the
  **widget source**, never the **person**. *How* it is carried (cookie / storage /
  cross-domain handoff / consent) is **Stage-2 design** (OQ-WCA-2…4), not decided here.
- **Reach vs conversion** — *reach* (already shipped: impressions + click-throughs in
  `widget_reach_count`) is "how many were exposed/clicked." *Conversion* (this feature)
  is "how many of those became follows/accounts." Distinct facts, distinct counts.
- **The AC6 firewall** — no widget interaction may confer [D-8](../../DECISIONS.md)
  curated-rating eligibility; widget interactions contribute **0** to any curated
  surface (`ratings.gate.CURATED_SURFACES = {DIGEST}`); structurally, `apps/widget`
  imports nothing from `signals`. Carried in from the widget (EUW-4), **binding here**.
- **No-PII posture** — the [D-7](../../DECISIONS.md) AC10 stance: the widget surface
  collects no personal data, no IP/device/referrer, no cross-site profile of a person.
  Carried in, **binding here**.
- **M5 = 0** — the firewall's measurable form: widget-attributed reach **and**
  conversion contribute zero curated-rating eligibility.

## 4. User stories (3–7)

- **S1** — As a **developer**, I want to see how many platform conversions (new follows
  of my app, new accounts) are attributable to my embedded widget, so that I can judge
  whether the widget is worth keeping — the payoff beyond raw reach.
- **S2** — As a **developer**, I want each conversion credited to the specific widget
  click-through that led to it within a bounded window, so that the number reflects
  plausible causation, not coincidence.
- **S3** — As a **developer**, I want widget-attributed conversions shown alongside the
  existing impressions + click-throughs on my dashboard, so that I see the whole funnel
  (impression → click → conversion) in one place.
- **S4** — As a **platform operator**, I want widget-attributed conversion to collect no
  personal data and build no per-person cross-site profile, so that the no-PII posture
  holds even as we link anonymous clicks to later conversions.
- **S5** — As a **platform operator**, I want widget interactions and their attributed
  conversions to remain firewalled from the Quality Score, so that attribution can never
  become a ranking-manipulation lever (AC6 / M5 = 0).

## 5. Acceptance criteria (Given / When / Then)

- **AC1 (S1)** — *Given* a developer's app whose widget has produced click-throughs,
  *When* a visitor who clicked through later converts (follows the app and/or
  registers), *Then* the dashboard's widget section shows that conversion in an
  **attributed-conversions** count for that app.
- **AC2 (S2)** — *Given* a visitor clicked a widget and then converts **within** the
  attribution window, *When* attribution runs, *Then* the conversion is credited to that
  widget source. *Given* a conversion with **no** preceding widget click, **or** one
  occurring **after** the window expires, *When* attribution runs, *Then* it is **not**
  credited to the widget (no fabricated links).
- **AC3 (S3)** — *Given* the dashboard widget slot already shows impressions +
  click-throughs (reach), *When* attributed conversions exist, *Then* they appear in the
  same slot as a distinct, clearly-labeled funnel stage **without altering the existing
  reach numbers**.
- **AC4 (S4 — no-PII)** — *Given* any widget-attributed conversion, *When* it is
  recorded, *Then* no personal data about the converting visitor is stored (no identity,
  IP, device fingerprint, or persisted cross-site browsing profile); only aggregate,
  **source-keyed** counts exist, and any transient marker used to carry the source
  identifies the widget, not the person.
- **AC5 (S5 — firewall)** — *Given* a widget click-through and its attributed
  conversion, *When* the curated-rating gate / Quality Score is evaluated, *Then* the
  widget interaction and the act of attributing it confer **no D-8 curated-rating
  eligibility** and add **0** to any curated surface (**M5 = 0**); the conversion's own
  legitimate on-platform corpus event (e.g. the follow's `record_subscribe`) is
  **unchanged** — attribution adds nothing to it. The attribution path imports nothing
  from `signals` (structural).
- **AC6 (robustness — fail-soft)** — *Given* the attribution mechanism is unavailable or
  errors, *When* a visitor converts, *Then* the conversion itself (follow / register)
  and the existing reach counts still succeed unaffected; attribution is best-effort to
  the user, **loud to operators**.

## 6. Success metrics

| ID | Metric | Why it matters |
|----|--------|----------------|
| **M1** | Widget-attributed conversions per app per window (follows + accounts, as distinct counts) | The headline payoff — does the widget convert, not just reach? |
| **M2** | Conversion rate = attributed conversions ÷ widget click-throughs | Funnel efficiency; lets a developer compare widgets/periods. |
| **M3** | Attribution coverage = % of relevant conversions for which a source could be determined | Data-quality / mechanism-health signal; guards against silently lossy attribution. |
| **M4** (guardrail) | Curated-surface contribution of widget interactions + attributed conversions = **0** | Proves the AC6 firewall (M5 = 0) holds. |
| **M5** (guardrail) | Count of PII fields stored for attribution = **0** | Proves the no-PII posture holds. |
| **M6** | Attribution-path error / degraded rate | Robustness; attribution is best-effort and must never break a conversion. |

## 7. In scope / Out of scope

**In scope**
- Defining and recording an attributable link from a widget click-through to a
  downstream **conversion** (new follow of the clicked-through app; new account) — the
  conversion set fixed by WCA-1.
- The **attribution window** + **touch model** as product rules (values may be config).
- Surfacing widget-attributed conversion counts on the **developer dashboard** as a
  funnel stage alongside the existing reach (additive to the shipped widget slot).
- Holding the **firewall (M5 = 0)** and **no-PII posture** as binding constraints
  throughout.

**Out of scope**
- The **token-carry mechanism**: cookie vs storage vs cross-domain handoff, the
  cross-domain-identity technique, and any **consent UX** — these are **Stage-2 design**
  (OQ-WCA-2…4). The brief fixes *what* and *the privacy/firewall envelope*, not *how*.
- **Off-platform install attribution** (vision §7 Open Q#4) — adjacent and explicitly
  excluded; this measures on-platform follows/accounts only.
- Any **per-person** tracking, user-level analytics, or cohort/funnel dashboards beyond
  the single attributed-conversion count (subject to WCA-3).
- Attribution for **non-widget sources** (D-9 promo placements, organic) — separate work.
- **Charging** for attribution — it is a free tool (D-9 firewall: money buys no position).
- **Retroactive** attribution of conversions that occurred before this ships.

## 8. Constraints & assumptions

*Verified against code this session unless marked unverified.*

- **[verified]** The widget click-through is `GET /widget/<id>/view` → 302 to
  `pages:app-page`, server-derived, carrying **no source token** today
  ([apps/widget/views.py](../../apps/widget/views.py)).
- **[verified]** Conversions are concrete events: follow =
  `subscriptions.services.follow_app(user, app_id)` (returns `created`); new account =
  the `accounts` register view (`/auth/register`).
- **[verified]** A new follow already emits a legitimate corpus event
  (`signals_capture.record_subscribe`) as part of the follow unit — that is the genuine
  on-platform action and is correct; attribution must **not** add to it.
- **[verified]** Reach is already surfaced on the dashboard widget slot, fed by the
  `apps/widget`-owned `widget_reach_count` rollup, which imports nothing from `signals`.
- **[verified]** Firewall: `ratings.gate.CURATED_SURFACES = {DIGEST}`; `apps/widget`
  imports nothing from `signals` (AST-enforced) — the carried-in AC6 invariant.
- **[verified]** Stack = Python / Django + PostgreSQL ([D-4](../../DECISIONS.md)); the
  widget audience is **anonymous** (logged out) by default.
- **[unverified — the central Stage-2 risk]** That a **no-PII**, source-only token can be
  carried from a third-party-hosted widget through an anonymous click → app page →
  conversion (possibly cross-domain) **without** cookies/consent that would breach the
  posture. Feasibility and the consent envelope are the core design question (OQ-WCA-2…4).
- **Assumption [unverified]** MVP traffic/conversion volume may be low, making counts
  noisy early; the metric's value grows with adoption (R5).

## 9. Risks

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| **R1** | The cross-session identifier needed for attribution drifts into covert per-person tracking (privacy/consent overreach). | Med / **High** | Aggregate, **source-keyed not person-keyed**; no persisted per-person profile (AC4); the consent/tracking posture is decided explicitly (WCA-3) **before** any cross-domain identifier is designed in Stage 2. |
| **R2** | Cookieless cross-domain attribution is technically hard/infeasible without degrading to guesswork. | Med / Med | Treat the mechanism as the central Stage-2 design risk; the acceptable fallback is **lower coverage (M3) reported honestly**, never fabricated links (AC2). |
| **R3** | Wiring conversions to widget source tempts feeding it into the score (firewall erosion). | Low / **High** | Structural firewall — no `signals` import; AC5 + M4 guardrail; the attribution counter lives outside the corpus (the shipped `widget_reach_count` precedent). |
| **R4** | Over-counting / double-attribution (one visitor, multiple widgets or repeat clicks). | Med / Med | Explicit touch model + window + dedupe rules (WCA-2, refined in Stage 2). |
| **R5** | Low conversion volume at MVP density makes the metric noisy / unactionable. | Med / Low | Report raw counts + coverage honestly; it is a measurement feature whose value scales with traffic. |

## 10. Vision alignment

- **§5.4 (the developer wedge, [D-10](../../DECISIONS.md))** — the widget is the capture
  mechanism that drags a developer's audience onto the platform; this feature measures
  whether that capture **converts**, closing the funnel the wedge exists to produce.
- **§5.6 + the money-buys-position test → PASS** — attribution is a **free** measurement
  tool; it confers no ranking advantage, the widget interaction stays outside
  `CURATED_SURFACES`, and **M5 = 0** (firewall, §4.1 / [D-8](../../DECISIONS.md)).
- **§7 Open Q#4 (install attribution)** — explicitly bounded **out**; this stays
  on-platform.
- **No-PII posture ([D-7](../../DECISIONS.md) AC10)** — held as a binding constraint
  (AC4 / M5).

## 11. Decisions needed (raised as DN-WCA-BRIEF in CONTROL.md)

Three bundled scoping calls; logged PROPOSED in [DECISIONS.md](DECISIONS.md). Architecture
(the token-carry mechanism itself) is **not** asked here — it is left OPEN for Stage 2.

- **WCA-1 — What counts as a "conversion"?** *Recommendation:* **both** a **new follow**
  of the clicked-through app (primary — the wedge's whole point is turning the
  developer's audience into followers) **and** a **new account registration**
  (secondary), tracked as **distinct** counts. *Alternatives:* follow-only; account-only.
- **WCA-2 — Attribution model + window.** *Recommendation:* **last-touch** (credit the
  most recent widget click-through before the conversion) within a **bounded window**
  (default ~30 days, config). *Alternatives:* first-touch; a different window length.
- **WCA-3 — Privacy / tracking posture.** *Recommendation:* **aggregate-only,
  source-keyed** — no per-person cross-site profile is built, so no personal data is
  processed and no consent banner is required; the source marker is transient and
  identifies the widget, not the person. *Alternative:* permit **consented per-person**
  attribution (richer data, but adds a consent obligation and PII-handling surface). If
  Stage 2 finds aggregate-only infeasible, that returns here as a decision rather than
  being silently relaxed.
