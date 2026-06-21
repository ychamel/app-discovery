# DECISIONS — ratings-reviews

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

> **RR-2 resolved (DN-11, 2026-06-20):** "curated to app X" = a `Surface.DIGEST` D-7
> impression of the app. See RR-2 below. It must agree with
> [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).

> **Built (Stage 4-build, 2026-06-21):** RR-4 and RR-5 are **implemented** in `apps/ratings/`,
> and global **[D-8](../../DECISIONS.md)** (APPROVED) is implemented as `gate.CURATED_SURFACES
> = frozenset({Surface.DIGEST})` — the single source of "what counts as curation". The
> eligibility determination is frozen on each `ratings_rating` row (`weight_eligible` +
> `eligibility_basis` + `eligibility_determined_at`, all NOT NULL) and stamped by the single
> write path on every write. The gate reads evidence through the new factual
> `signals.selectors.has_impression` (additive D-7 read surface) and **fails closed + loud**.
> **Named-not-built growth levers** (per DESIGN §4.2/§5b/§14): a `recompute_eligibility`
> management path (re-derive determinations when a `DIGEST` emitter ships or the gate
> definition changes) and a stronger review-text **purge**-on-account-deletion posture (today
> the row is `SET_NULL`-anonymized, text retained as "a former user"). See
> [TEST_PLAN.md](TEST_PLAN.md) for per-AC verification.

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

## RR-4: Own mutable store; eligibility frozen-on-the-row and re-derivable (OQ-4)
- **Date:** 2026-06-20
- **Stage / feature:** `2-design` / ratings-reviews (Software Architect)
- **Decision:** Ratings live in this feature's **own table** `ratings_rating` (one row per
  `(user, app_id)`, **mutable** — editable/removable), distinct from the append-only D-7
  behavioral tables (A5). The curated-eligibility determination is **frozen on the row** at
  write time — a non-null `weight_eligible` boolean plus an `eligibility_basis` reason
  (`curated_digest_impression` / `no_curated_impression` / `curation_unverified`) and the
  `eligibility_determined_at` instant — yet **re-derivable**, since every input (rater, app,
  timestamp) is retained and the impression corpus is append-only.
- **Why:** **AC5 mandates** the determination be *stored and present on 100% of ratings,
  queryable later* — a derive-at-read-only model would leave it absent until something asks.
  Freezing satisfies AC5; re-derivability preserves the R1 "record as data, correctable"
  property at zero extra cost. A rating is *explicit, mutable* opinion, so an own mutable store
  is the faithful shape — folding it into the append-only, no-score-column signals schema (D-7)
  would violate that contract.
- **Alternatives rejected:** (a) **Store ratings as a new `signals` `EngagementEvent` kind** —
  breaks D-7's append-only + no-score invariants (a rating carries a score, free text, and is
  editable). (b) **Derive eligibility at read only** — leaves AC5's determination absent;
  rejected. (c) **Soft-delete on remove** — unneeded for AC8 ("retracted from display");
  hard-delete is simpler and design-for-deletion.
- **Consequences:** account deletion `SET_NULL`-anonymizes the rating (retain-for-H3, unlink
  the person — SC-10 posture); a stronger purge-the-review-text posture is a noted, unbuilt
  deletion-hook addition. A `recompute_eligibility` management path is the documented growth
  lever for when a `DIGEST` emitter ships — noted, not built.

## RR-5: The AP-1 slot is filled by a ratings inclusion tag (one-line, fail-soft)
- **Date:** 2026-06-20
- **Stage / feature:** `2-design` / ratings-reviews (Software Architect)
- **Decision:** ratings-reviews fills the empty `app-pages` AP-1 reviews slot via a Django
  **inclusion template tag** (`{% app_reviews app %}` from `apps.ratings.templatetags.ratings_tags`),
  changing **only the content** of `app_page.html` slot 6 (the `<section aria-label="Reviews">`,
  its heading, and its position are unchanged). The tag is **fail-soft** — a display-selector
  error renders a degraded slot and never raises into the page render (preserving app-pages
  AC5/AP-1). The gate evidence is read through a **new factual `signals.selectors.has_impression`**
  selector (a pure `EXISTS`, D-7-compliant) — never a direct `signals_*` read; the curation
  *judgement* (`CURATED_SURFACES = {DIGEST}`) stays in `ratings.gate`, keeping signals neutral.
- **Why:** the inclusion tag confines the integration to one template line in the slot app-pages
  *designed to be fillable* ("adding reviews later is not a uniformity-breaking change"), keeping
  the closed-out pages view ignorant of ratings internals. Reading impression evidence through a
  signals selector honors D-7 ("nothing reads `signals_*` directly past the selector surface").
- **Alternatives rejected:** (a) **pages view fetches ratings data and passes it to the template**
  — couples the pages view to this feature's data shape. (b) **`ratings` queries `Impression`
  directly** — violates D-7. (c) **put the DIGEST-=-curation judgement in `signals`** — leaks
  integrity semantics into the neutral raw store. All rejected.
- **Consequences:** the only edits outside `apps/ratings/` are one slot's content in
  `app_page.html`, one `config/urls` include, a few `apps/core` config/metric additions, and one
  additive reversible index on `signals.Impression`. Rollback restores the one slot line.

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
