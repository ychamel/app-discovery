# OPEN_QUESTIONS — widget-conversion-attribution

_Ambiguities, deferrals, and escalations. Any persona may add; resolutions are logged in
[DECISIONS.md](DECISIONS.md)._

| ID | Question | Raised by / stage | Status |
|----|----------|-------------------|--------|
| OQ-WCA-1 | **Inherited from [OQ-EUW-5](../embeddable-update-widget/OPEN_QUESTIONS.md) (the reason this feature exists).** Per-account conversion attribution (M3): linking a *new account/follow* to the specific widget click-through that led to it — needs a widget-source token carried through an anonymous click → app page → sign-up (cookie consent + cross-domain identity + no-PII posture). The [embeddable-update-widget DESIGN §11](../embeddable-update-widget/DESIGN.md) deferred this; defining it is this feature's Stage-1 job. | Coordinator seed / pre-1 | **SCOPED (Stage 1)** — the problem is defined in [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1–AC6, M1–M6); the *what/why/privacy-envelope* is fixed there, the *how* splits into OQ-WCA-2…4 below for Stage 2. |
| OQ-WCA-2 | **The token-carry mechanism.** How does an opaque, no-PII **source** marker travel from a third-party-hosted widget click → app page → conversion (follow/register)? Cookie vs query param vs storage; what survives the anonymous→authenticated transition. The brief's central [unverified] assumption (§8). | Product Analyst / Stage 1 | **OPEN for Stage 2 (Architect).** Must hold AC4 (no-PII) + AC5 (firewall, no `signals` import). |
| OQ-WCA-3 | **Cross-domain identity.** If the widget host and the platform are different origins, how is the source carried across that boundary without a tracking cookie that breaches the no-PII posture (WCA-3)? | Product Analyst / Stage 1 | **OPEN for Stage 2 (Architect).** |
| OQ-WCA-4 | **Consent envelope.** Given WCA-3's *aggregate-only* recommendation (no personal data → no consent banner), confirm in design that the chosen mechanism actually processes no personal data; if it can't, the consent obligation returns to the user as a decision (do not silently relax). | Product Analyst / Stage 1 | **OPEN for Stage 2 (Architect).** |

> The widget already ships **reach** (impressions + click-through counts, AC9) via the
> `apps/widget`-owned `widget_reach_count` rollup, which by design **imports nothing from
> `signals`** (the AC6 firewall, structural by absence). Any attribution mechanism here
> must preserve that firewall (no widget interaction may confer D-8 curated-rating
> eligibility — M5=0) and the no-PII posture. These are upstream constraints, not yet
> design decisions.
