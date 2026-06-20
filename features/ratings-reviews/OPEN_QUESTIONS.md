# OPEN_QUESTIONS — ratings-reviews

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Open (Stage 1 — Product Analyst)

- **OQ-1 — "Curated to app X" definition — ✅ RESOLVED (DN-11, 2026-06-20): option (a),
  `DIGEST`-impression only** (see RR-2). A rating is weight-eligible iff its author has a
  `Surface.DIGEST` D-7 impression of the app; `APP_PAGE` views never count. *Architect
  follow-up:* whether to promote this to a global ADR (`editorial-curation-tools` /
  `developer-dashboard` share the semantic). The candidate set considered:
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

- **OQ-2 — Rating shape.** Numeric scale (1–5? 1–10?), and is a written review optional or
  required? Brief assumes 1–5 + optional text (A1); exact scale/limits set at Stage 2.

- **OQ-3 — Abuse/moderation scope.** Confirm review-bomb/anomaly detection (§4.3), reviewer
  reputation/calibration (§3.2), profanity/abuse-reporting are **OUT** at MVP (later
  integrity system); this feature ships authenticated-only + one-per-user + the gate (A3,
  R4).

- **OQ-4 — Storage & eligibility freezing (Stage 2).** Ratings live in this feature's own
  store, distinct from D-7 behavioral-event tables (A5). Open for design: is the
  curated-eligibility determination **frozen at capture** (a stored flag, like the D-7
  frozen tag snapshot) or **re-derived at read** (like D-7's return-@3d/@14d)? Interacts
  with DN-11 option (c).

## Seeded from the breakdown (§7) — folded into OQ-1

- **"Curated" definition for the gate (breakdown §7 Q2):** what exactly marks a user as
  "curated to app X" so a rating is weight-eligible? Now tracked as **OQ-1 / DN-11**;
  must agree with
  [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).
