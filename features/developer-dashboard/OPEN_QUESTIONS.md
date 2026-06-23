# OPEN_QUESTIONS — developer-dashboard

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped directly._ Note: every metric shown here is sourced from
[signal-capture](../signal-capture/OPEN_QUESTIONS.md) and
[ratings-reviews](../ratings-reviews/OPEN_QUESTIONS.md), so their open questions
(attribution method, privacy posture, curated-gate definition) constrain what this
dashboard can honestly report. Add ambiguities here as the feature enters the pipeline.

## Stage 1 (Product Analyst, 2026-06-23) — RESOLVED by DN-19 (2026-06-24)

- **OQ-DD-1 — reach presentation in MVP?** **RESOLVED — DN-19.a.** Not a binary curated/open
  split: a **combined impressions total + per-source breakdown** over the `Surface` vocabulary
  (curated `DIGEST` first/highlighted) **plus an impressions-over-time trend with a
  distinguished curated line** (AC3/AC4/AC10). User-selectable graph series deferred.
- **OQ-DD-2 — Reporting window set.** **RESOLVED — DN-19.b.** Fixed config set: last week /
  2 weeks / month / 3 months / 6 months / year / 3 years / all-time; no custom ranges.
- **OQ-DD-3 — Per-review weight-eligibility shown to the owner?** **RESOLVED — DN-19.c.**
  Hidden at MVP (D-8 §AC7 keeps the flag internal; gaming-manual line, vision Open Q5).

## Stage 2 (Architect) — OQ-DD-4 RESOLVED-in-design (2026-06-24, DESIGN.md §5.1 / DD-DESIGN-2)

- **OQ-DD-4 (from brief C7/R4; widened by DN-19.a) — where does the surface-aware, time-bucketed
  reach read live?** **RESOLVED-in-design** (pending DESIGN approval). Two **additive, neutral**
  reads are added to `apps/signals/selectors.py` (the only D-7-permitted reader of `signals_*`):
  `impression_breakdown[_for_apps]` (per-`Surface` counts, **every** `Surface` zero-filled —
  AC3/AC4) and `impression_trend(…, granularity)` (per-`Surface` per-time-bucket — AC10), plus a
  `TrendGranularity` enum. **No model/migration/index** (backed by the existing
  `signals_imp_app_time_idx`). Bucket granularity is chosen **per window** in
  `apps/dashboard/windows.py` (DAY ≤1m / WEEK 3–6m / MONTH ≥1y + all-time) — the M6/AC9 bound.
  Signals stays neutral (it never judges "curated"); the dashboard composes the curated split
  via `ratings.gate.CURATED_SURFACES`. The breakdown enumerates the `Surface` vocabulary so a new
  surface appears with no dashboard rewrite. See [DESIGN.md](DESIGN.md) §4.2/§4.3/§5.1 and
  [DECISIONS.md](DECISIONS.md) DD-DESIGN-2/3. *(Original verified gap stands:
  [apps/signals/selectors.py](../../apps/signals/selectors.py) had no per-surface/time-bucketed
  read; [apps/signals/kinds.py](../../apps/signals/kinds.py) `Surface` = DIGEST, APP_PAGE,
  documented extensible.)*
