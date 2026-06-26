# OPEN_QUESTIONS — widget-conversion-attribution

_Ambiguities, deferrals, and escalations. Any persona may add; resolutions are logged in
[DECISIONS.md](DECISIONS.md)._

| ID | Question | Raised by / stage | Status |
|----|----------|-------------------|--------|
| OQ-WCA-1 | **Inherited from [OQ-EUW-5](../embeddable-update-widget/OPEN_QUESTIONS.md) (the reason this feature exists).** Per-account conversion attribution (M3): linking a *new account/follow* to the specific widget click-through that led to it — needs a widget-source token carried through an anonymous click → app page → sign-up (cookie consent + cross-domain identity + no-PII posture). The [embeddable-update-widget DESIGN §11](../embeddable-update-widget/DESIGN.md) deferred this; defining it is this feature's Stage-1 job. | Coordinator seed / pre-1 | **OPEN** — the core problem; the Product Analyst scopes it in [FEATURE_BRIEF.md](FEATURE_BRIEF.md). |

> The widget already ships **reach** (impressions + click-through counts, AC9) via the
> `apps/widget`-owned `widget_reach_count` rollup, which by design **imports nothing from
> `signals`** (the AC6 firewall, structural by absence). Any attribution mechanism here
> must preserve that firewall (no widget interaction may confer D-8 curated-rating
> eligibility — M5=0) and the no-PII posture. These are upstream constraints, not yet
> design decisions.
