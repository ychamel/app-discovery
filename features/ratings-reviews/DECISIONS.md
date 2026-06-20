# DECISIONS — ratings-reviews

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

> **RR-2 resolved (DN-11, 2026-06-20):** "curated to app X" = a `Surface.DIGEST` D-7
> impression of the app. See RR-2 below. It must agree with
> [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).

## RR-1: The gate is recorded, not computed
- **Date:** 2026-06-20
- **Stage / feature:** `1-define` / ratings-reviews (Product Analyst)
- **Decision:** ratings-reviews captures the rating + optional review + a **curated-
  eligibility determination** at capture time, stored **raw**. It computes **no** score,
  weight, rank, average-as-quality, per-reviewer calibration, or reviewer reputation. The
  curated-rating gate is realized as *recorded eligibility data* ("enforceable now,
  weightable later"), not as a quality verdict.
- **Why:** The vision separates the *explicit signal* (this feature, §3.1) from the
  *Quality Score* that consumes it (§3.2), and the [D-7](../../DECISIONS.md) principle is
  that all scoring/normalization is a downstream consumer's job — capturing raw keeps the
  H3 backtest corpus uncontaminated. The breakdown §4.2 slice is explicitly "record
  whether the rater was curated… so the gate is enforceable now and weightable later."
- **Alternatives rejected:** Compute and display a weighted quality average here — couples
  this surface to the unbuilt scoring engine, bakes a scoring choice into the capture
  layer, and contaminates the raw corpus (R2). Rejected.
- **Consequences:** This feature stores facts (rating + eligibility flag); a visible
  app-level quality number is owned downstream. At MVP the eligibility flag may skew almost
  entirely *not-eligible* (R3) — that is correct, not a defect.

## RR-2: Curated-eligibility = a DIGEST-surface impression
- **Date:** 2026-06-20 (**resolved — DN-11**)
- **Stage / feature:** `1-define` / ratings-reviews (Product Analyst)
- **Decision:** A rating is **weight-eligible** iff its author has a **`Surface.DIGEST`**
  [D-7](../../DECISIONS.md) impression of that app (the curated weekly digest). An
  `APP_PAGE` (open/direct) view never confers eligibility. Eligibility is **recorded per
  rating** (AC5); the score that *uses* it is downstream (RR-1).
- **Why:** Faithful to vision §4.1 — "only users to whom the app was *organically curated*
  may affect its score"; the digest is the curated surface, an open page view is not.
  Forward-compatible with no contract change: it reads the existing D-7 `Surface` enum, and
  becomes meaningful automatically when `weekly-digest`/`editorial-curation-tools` emit
  `DIGEST` impressions.
- **Alternatives rejected:** (b) *any* impression incl. `APP_PAGE` — an open/self-driven
  view is not curation, contradicts §4.1. (c) record raw evidence and defer the verdict —
  more deferral than needed once the rule is this clear (raw D-7 impressions persist anyway,
  so a re-derivation path remains; OQ-4). (d) editorial assignment — couples to the unbuilt
  `editorial-curation-tools`; a `DIGEST` impression is the surface-level proxy that any
  curation mechanism produces.
- **Consequences:** At MVP, with no `DIGEST` emitter yet, ~all ratings record
  *not-eligible* (R3) — correct, and the §5 gate-split metric makes it visible. **For the
  Architect:** consider whether "curated = DIGEST impression" should be promoted to a
  **global ADR** — `editorial-curation-tools` (must produce DIGEST impressions) and
  `developer-dashboard` ("reach = curated users") both depend on this same semantic
  (breakdown §4.2 says ratings-reviews + editorial-curation-tools must agree).

## RR-3: Anyone authenticated may rate; the gate governs weight, not permission
- **Date:** 2026-06-20
- **Stage / feature:** `1-define` / ratings-reviews (Product Analyst)
- **Decision:** Any **signed-in** account may rate/review any accepted app; whether a rating
  is **weight-eligible** is the gate's job, **not** whether it is allowed to be posted.
  Outside (non-curated) ratings are accepted and displayed for other readers, recorded as
  not-weight-eligible. **Anonymous** visitors cannot rate (the page still renders
  anonymously — AC3).
- **Why:** Vision §4.1 — "outside visitors can rate and review for the benefit of other
  readers, displayed but unweighted." Per-reviewer calibration (§3.2) and one-per-user
  identity both require an attributable account, so anonymous rating is incoherent.
- **Alternatives rejected:** (a) Only curated users may rate at all — contradicts §4.1's
  open participation and discards readable outside feedback. (b) Allow anonymous ratings —
  unattributable, un-calibratable, trivially farmable. Both rejected.
- **Consequences:** A sign-in prompt appears on the rating action only (AC3), preserving
  `app-pages` anonymous render (AP-1).
