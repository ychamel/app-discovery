# DECISIONS — interest-taxonomy

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

These were the five "For confirmation at approval" calls in
[FEATURE_BRIEF.md](FEATURE_BRIEF.md); the user **approved all five (A4, 2026-06-17)** in
[CONTROL.md](../../CONTROL.md). Recorded here so the Architect treats them as settled
inputs rather than re-litigating them at Stage 2.

## ITX-1 — Closed / editorially-curated vocabulary (not a folksonomy)

**Decision:** The vocabulary is **controlled and closed**: users and developers *choose
from* the tag set; they do **not** coin new tags by free text. The set changes only
through editorial curation (admin role, D-3).
**Rationale:** Grounded in breakdown §4.1 ("controlled vocabulary") + vision §5.4
(editorial curation). A shared matching language only works if both sides draw from one
fixed dictionary.
**Rejected:** open/user-generated tags (folksonomy), user tag-suggestion, auto-generated
tags — all listed Out of Scope.
**Binds:** AC2, Constraints. Consuming features must reject off-vocabulary values.

## ITX-2 — Clusters in MVP; cluster adjacency deferred but not precluded

**Decision:** Named **clusters ship in the MVP** (every tag in ≥1 cluster, AC5).
**Cluster-to-cluster adjacency** (the substrate of ring-based expansion, vision §2.2) is
**post-MVP** — out of scope as a deliverable, but the MVP design must **not preclude** it.
**Rationale:** Clusters are the day-one anchor for adjacency; deferring adjacency avoids
over-building while AC8 guards against a painful future re-tag/migration.
**Rejected:** shipping full adjacency/rings now (over-scope, R3); shipping a bare tag list
with no grouping (precludes the matching fallback and future rings).
**Binds:** AC5 (deliverable), AC8 (Stage-2 design-review exit gate).

## ITX-3 — Taxonomy shape (flat vs shallow hierarchy) left to Stage-2 design

**Decision:** The Analyst **deliberately does not pick** the data-model shape (flat tag
list vs. shallow hierarchy). It is a Stage-2 (Architect) decision, **constrained by AC8**
(adjacency addable later without destructive migration).
**Rationale:** Picking the model now would lock architecture before the problem is
designed — outside the Analyst mandate. Resolves breakdown §7 Q5 by *constraining* rather
than *answering* it.
**Rejected:** the Analyst fixing flat-vs-hierarchy in the brief.
**Binds:** OPEN_QUESTIONS Q5 / OQ-1; handed to the Architect.

## ITX-4 — Single language (English) tag labels at MVP

**Decision:** Tag labels are **English only** at MVP; localization / multilingual labels
deferred.
**Rationale:** Single beachhead niche, single language keeps the MVP vocabulary tight;
localization is a later concern with no current requirement.
**Rejected:** multilingual labels at MVP (speculative, no named need).
**Binds:** Constraints (was [unverified] → now confirmed), Out of Scope.

## ITX-5 — This feature owns the vocabulary + lifecycle rules; rich curation UI is `editorial-curation-tools`

**Decision:** `interest-taxonomy` owns the **vocabulary and its lifecycle rules** (add /
rename / retire, stable identity, clusters). An **elaborate curation UI** belongs to
`editorial-curation-tools`. A **minimal authoritative way to seed/maintain** the set is in
scope here; the exact seed-vs-UI boundary is a Stage-2 design call (OQ-1).
**Rationale:** Mirrors identity-accounts (admin *role* there, admin *tooling* elsewhere) —
keeps this feature's surface area focused on the substrate.
**Rejected:** building the full editorial management UI inside this feature (over-scope).
**Binds:** In/Out of Scope; OQ-1 handed to the Architect.
