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

## Stage 1 — Product Analyst (brief authored, 2026-06-26)

Authored [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (5 stories / AC1–AC6 / M1–M6); grounded
every dependency in code (widget click-through 302, `follow_app`/register conversions,
the `record_subscribe` corpus event, the shipped reach slot, the `signals`-import
firewall). Money-buys-position test → **PASS**. Left the token-carry **mechanism** OPEN
for Stage 2 (OQ-WCA-2…4) — did not guess architecture. Raised **DN-WCA-BRIEF** (approve
brief + the three scoping calls below) in [CONTROL.md](../../CONTROL.md); **stopped at the
gate** (no Stage advance until approved).

The following are **PROPOSED** (not yet ratified — they bind Stage 2 only once
DN-WCA-BRIEF is approved):

- **WCA-1 (PROPOSED) — conversion set.** Count **both** a new **follow** of the
  clicked-through app (primary) and a new **account registration** (secondary), as
  distinct counts. *Rejected for now:* follow-only / account-only (narrower; loses half
  the funnel). Rationale: the wedge's payoff is turning a developer's audience into
  followers, but a brand-new account is the broader platform conversion worth seeing too.
- **WCA-2 (PROPOSED) — attribution model + window.** **Last-touch** within a bounded,
  configurable **~30-day** window. *Rejected for now:* first-touch (credits the wrong
  click when a visitor returns via a later widget click); unbounded window (stale,
  noisy). Rationale: last-touch + a bounded window is the boring, defensible default;
  the value is config (§5.2 design-for-change).
- **WCA-3 (PROPOSED) — privacy/tracking posture.** **Aggregate-only, source-keyed** — no
  per-person cross-site profile, so no PII is processed and no consent banner is required;
  the source marker is transient and identifies the widget, not the person. *Rejected for
  now:* consented per-person attribution (richer, but creates a PII-handling + consent
  surface that contradicts the carried-in no-PII posture). Rationale: holds AC4 / M5 = 0
  by construction. If Stage 2 finds aggregate-only infeasible, it returns as a decision,
  not a silent relaxation.

Reuses D-3/D-4/D-6/D-7/D-8 + the carried-in AC6 firewall — **no new global ADR**.
