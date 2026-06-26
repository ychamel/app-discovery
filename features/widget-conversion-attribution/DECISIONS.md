# DECISIONS — widget-conversion-attribution

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 0 — Coordinator (feature created, 2026-06-26)

**Choice:** Scaffold `widget-conversion-attribution` as a follow-up feature to pick up
the deferred **M3 / OQ-EUW-5** per-account conversion attribution from
[embeddable-update-widget](../embeddable-update-widget/) (DESIGN §11, EUW-10). The widget
shipped **reach** (impressions + click-throughs); *which signup came from which click* was
deferred because it is a materially harder problem (anonymous token-carry across
sessions/domains, cookie consent, cross-domain identity, no-PII posture).

**Why:** User-directed (Coordinator decision, 2026-06-26) — with the developer wedge
([D-10](../../DECISIONS.md)) complete, deepening the just-shipped widget's measurement is
the chosen next step over activating the density-gated network features or starting the
D-9 monetization surface. The deferral was logged traceably (OQ-EUW-5), so this is the
named follow-up, not new scope invented out of nowhere.

**Rejected (this turn):** activating `weekly-digest` / `editorial-curation-tools` (held
until per-niche density, D-10); starting `D-9` promotion-placements monetization (the
other live option — deferred, not dropped).

**Constraints carried in (not yet decisions — for the Product Analyst / Architect):**
- Must preserve the **AC6 firewall** — no widget interaction may confer D-8 curated-rating
  eligibility (M5=0); `apps/widget` imports nothing from `signals`, structural by absence.
- Must preserve the **no-PII posture** of the widget surface.

No new global ADR at scaffold time. Stage advanced to `1-define`; handed to the Product
Analyst to author [FEATURE_BRIEF.md](FEATURE_BRIEF.md).
