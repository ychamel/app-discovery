# OPEN_QUESTIONS — ratings-reviews

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Open (Stage 1 — Product Analyst)

- **OQ-1 — "Curated to app X" definition — ✅ RESOLVED (DN-11, 2026-06-20): option (a),
  `DIGEST`-impression only** (see RR-2). A rating is weight-eligible iff its author has a
  `Surface.DIGEST` D-7 impression of the app; `APP_PAGE` views never count. *Architect
  follow-up (Stage 2): ✅ DONE — **promoted to proposed global [D-8](../../DECISIONS.md)***
  (pending DN-12). The gate semantic is repo-wide (`editorial-curation-tools` /
  `developer-dashboard` / the Quality Score consumer all share it); the curated-surface set
  lives in one place (`apps.ratings.gate.CURATED_SURFACES`); impression evidence is read via
  the new factual `signals.selectors.has_impression` (D-7-compliant), not a direct corpus read.
  The candidate set considered:
  - **(a) DIGEST-impression only** — curated iff the user has a `Surface.DIGEST` impression
    of the app. Clean and forward-compatible, but ~always *not-eligible* at MVP (no `DIGEST`
    emitter yet — R3).
  - **(b) Any platform impression** — includes `APP_PAGE`. *Contradicts §4.1* (an open page
    view is not organic curation); would let self-driven page views confer eligibility.
  - **(c) Record raw evidence, defer the verdict** — store *which* impressions (surfaces,
    times) the user had for the app at rating time; let the downstream scorer decide what
    "curated" means. Most [D-7](../../DECISIONS.md)-faithful (capture facts, not verdicts),
    but pushes the definition to the score consumer.
  - **(d) Editorial assignment** — a user is curated to X iff a human editor
    (`editorial-curation-tools`) assigned X to them. Most faithful to the MVP's
    human-stand-in (vision §5.4), but couples to an unbuilt feature.
  Must agree with [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).

- **OQ-2 — Rating shape — ✅ RESOLVED (Stage 2, DESIGN §5/§10/§15).** Numeric
  **1..`rating_scale_max()`** (default 5) + **optional** `review_text` ≤
  `review_text_max_length()` (default 4000 chars); the slot shows `reviews_display_limit()`
  (default 20) most-recent reviews. Scale/limits are `apps/core/config` tunables (no magic numbers).

- **OQ-3 — Abuse/moderation scope — ✅ CONFIRMED OUT (Stage 2, DESIGN §7/§15).** Review-bomb/
  anomaly detection (§4.3), reviewer reputation/calibration (§3.2), profanity/abuse-reporting
  are **OUT** at MVP (later integrity system). This feature ships authenticated-only +
  one-per-user (structural volume cap) + the gate (outside brigades land unweighted); request
  rate-limiting is available (`apps/core/ratelimit`) but unwired given the structural cap.

- **OQ-4 — Storage & eligibility freezing — ✅ RESOLVED (Stage 2, DESIGN §4/§11; [RR-4](DECISIONS.md)).**
  Ratings live in this feature's **own mutable table** `ratings_rating`, distinct from the
  append-only D-7 tables (A5). The curated-eligibility determination is **frozen on the row**
  (a non-null `weight_eligible` + `eligibility_basis` + `eligibility_determined_at` — AC5
  needs it present on 100% of ratings) **and re-derivable** (all inputs + the append-only
  impression corpus are retained — R1). Derive-at-read-only (DN-11 option c) was rejected
  because it leaves the AC5 determination absent until something asks.

## Seeded from the breakdown (§7) — folded into OQ-1

- **"Curated" definition for the gate (breakdown §7 Q2):** what exactly marks a user as
  "curated to app X" so a rating is weight-eligible? Now tracked as **OQ-1 / DN-11**;
  must agree with
  [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).
