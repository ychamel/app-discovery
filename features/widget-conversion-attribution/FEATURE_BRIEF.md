# FEATURE_BRIEF — widget-conversion-attribution

*Stage 1 (Product Analyst). Single source of truth for what & why. **Status: pending.***

_pending — to be authored by the Product Analyst._

## Origin

This feature was scaffolded by the Coordinator (2026-06-26) to pick up the **deferred
M3 / OQ-EUW-5** work from [embeddable-update-widget](../embeddable-update-widget/): the
shipped widget delivers **reach** (impressions + click-throughs, AC9) but explicitly
**deferred per-account conversion attribution** — *which new account/follow came from
which widget click-through* — because it requires carrying a widget-source token through
an **anonymous** click → app page → sign-up, across sessions/domains, entangling cookie
consent, cross-domain identity, and the no-PII posture
([embeddable-update-widget/DESIGN.md §11](../embeddable-update-widget/DESIGN.md)).

The Product Analyst defines the scope here from scratch — the above is upstream context,
not a pre-decided design.
