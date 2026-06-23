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

## Stage 2 (carried for the Architect)

- **OQ-DD-4 (from brief C7/R4; widened by DN-19.a) — where does the surface-aware, time-bucketed
  reach read live?** `app_funnel.impressions` counts all surfaces collapsed and is not
  time-bucketed; both the **per-source breakdown** (AC3) and the **over-time trend** (AC10)
  need a new read that (a) groups impressions by `Surface` and (b) buckets by time over the
  selected window. It **must** live in `signals.selectors` (preserving D-7: nothing reads
  `signals_*` directly) — never a dashboard-side raw-table read. Design the bucket granularity
  per window and ensure the breakdown enumerates the `Surface` vocabulary (new surfaces appear
  automatically). **Design call** — resolve in DESIGN.md. *(Verified gap:
  [apps/signals/selectors.py](../../apps/signals/selectors.py) has no per-surface or
  time-bucketed read; [apps/signals/kinds.py](../../apps/signals/kinds.py) `Surface` = DIGEST,
  APP_PAGE today, documented extensible.)*
