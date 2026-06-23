# OPEN_QUESTIONS — developer-dashboard

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped directly._ Note: every metric shown here is sourced from
[signal-capture](../signal-capture/OPEN_QUESTIONS.md) and
[ratings-reviews](../ratings-reviews/OPEN_QUESTIONS.md), so their open questions
(attribution method, privacy posture, curated-gate definition) constrain what this
dashboard can honestly report. Add ambiguities here as the feature enters the pipeline.

## Stage 1 (Product Analyst, 2026-06-23) — bundled into DN-19 (approval)

- **OQ-DD-1 — Curated/open reach split in MVP?** Report curated (`DIGEST`) vs open
  (`APP_PAGE`) reach separately, per the **D-8** gate? *Brief recommends **yes*** (AC3/AC4 —
  it is the H2 story). **Status: OPEN — DN-19.a.**
- **OQ-DD-2 — Reporting window set.** Which bounded windows does the dashboard offer (S5)?
  *Brief recommends* a fixed config set (last 7d / 30d / all-time), no custom ranges.
  **Status: OPEN — DN-19.b.**
- **OQ-DD-3 — Per-review weight-eligibility shown to the owner?** Does the developer see
  which incoming reviews are weight-eligible (curated)? *Brief recommends **no** at MVP*
  (D-8 §AC7 keeps the flag internal; gaming-manual line, vision Open Q5). **Status: OPEN — DN-19.c.**

## Stage 2 (carried for the Architect)

- **OQ-DD-4 (from brief C7/R4) — where does the curated/open reach split live?** `app_funnel`
  counts all surfaces together; a per-`Surface` split needs either a new surface-aware read in
  `signals.selectors` (preserving D-7: nothing reads `signals_*` directly) or a dashboard-side
  read through an extended selector. **Design call — must NOT be solved by a direct `signals_*`
  read.** Resolve in DESIGN.md once DN-19.a lands.
