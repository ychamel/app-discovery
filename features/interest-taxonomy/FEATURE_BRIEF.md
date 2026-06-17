# FEATURE_BRIEF — interest-taxonomy

*Stage 1 artifact (Product Analyst). Status: **APPROVED 2026-06-17 (A4)** — all 5
"For confirmation at approval" calls confirmed (see [DECISIONS.md](DECISIONS.md)
ITX-1…ITX-5); handed off to Stage 2 (Software Architect). Sources:
[docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.1 + §7 Q5,
[curated-app-platform-design.md](../../curated-app-platform-design.md) §2.2 / §5.4 / §6,
global [DECISIONS.md](../../DECISIONS.md) D-1/D-2, and this feature's
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).*

## Coordinator scope seed (source: breakdown §4.1)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Foundation · Phase 0 (build first — see breakdown §5)
- **Purpose:** The controlled vocabulary of interest tags + cluster structure that
  everything matches against.
- **MVP slice:** A curated flat-to-shallow tag set for the *one* beachhead niche (not a
  universal ontology).
- **Proves (hypothesis):** enabler
- **Depends on:** —
- **Vision design ref:** §2.2, §6 User-facing
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.1
- **Coordinator note:** Foundational and easy to under-scope. The full "interest space"
  with adjacency for rings is post-MVP; design cleanly now to avoid a painful migration
  when rings arrive. Its content is gated by repo decision **D1** (beachhead niche).

---

## Glossary (no undefined domain terms)

- **Interest tag** — a single named unit of interest in the platform's vocabulary (e.g.
  *recipe manager*, *habit tracker*). It is the atomic label both a **user's interests**
  and an **app's subject matter** are expressed in.
- **Interest taxonomy** — the whole curated set of interest tags **plus** the cluster
  structure over them. This feature *is* the taxonomy; it is the single shared dictionary
  every matching surface reads from.
- **Controlled (closed) vocabulary** — the set of valid tags is **fixed and editorially
  curated**: users and developers *choose from* it, they do not invent new tags by free
  text. (Contrast: an open *folksonomy* where anyone coins tags — out of scope, see below.)
- **Cluster** — a named grouping of related tags (e.g. *productivity tools* groups
  *to-do app*, *note-taking*, *habit tracker*). Clusters are the unit the matching layer
  and, later, ring expansion reason about. (Vision §2.2 "interest clusters".)
- **Adjacency** — the relation describing which clusters *neighbour* which, used by
  **ring-based expansion** (vision §2.2) to grow an app outward. Adjacency data is
  **post-MVP**; the MVP taxonomy must not *preclude* it (see Risks R3).
- **Tag identity** — a tag's **stable internal reference**, distinct from its displayed
  label, so a tag can be renamed or retired without invalidating things already tagged
  with it.
- **Beachhead niche** — the single launch vertical, **vibecoded webapps** (small,
  often AI-assisted web apps from solo/tiny-team devs); global [D-1](../../DECISIONS.md).
  It scopes the *content* of the taxonomy (which tags exist), not its structure.
- **Platform editor** — an account holding the **admin** role (from `identity-accounts`,
  [D-3](../../DECISIONS.md)) who is authorized to curate the vocabulary.

---

## Problem statement

The platform's entire value rests on **matching** — putting an app in front of the users
most likely to want it (vision §2.2, §8 one-line test). Matching is only possible if a
user's declared interests and an app's subject matter are written in the **same language**.
Today there is no such language: `interest-profile` has nothing for a user to pick their
interests *from*, `submission-intake` / editorial curation has nothing to *label* an app
*with*, and the (human, at MVP) matcher has no shared vocabulary to compare the two. Free
-text on either side would never line up — "to-do list" vs "todo" vs "task manager" — so
matches would be missed and the digest's quality (the whole user-side promise) would
collapse.

This is needed **now** because it is a Phase-0 foundation with no dependencies and several
dependents: `interest-profile` (users declare interests *from* it), `submission-intake`
and `editorial-curation-tools` (apps are tagged *from* it), and the future matching engine
all read this one vocabulary. It is also, per the Coordinator note, **easy to get wrong by
under- or over-scoping**, which is exactly why the product boundaries belong in a brief
before anyone designs a schema.

## Goal

Provide a single, editorially-curated, **shared controlled vocabulary** of interest tags —
grouped into clusters and scoped to the beachhead niche — that both users and apps are
described in, with stable tag identities and a safe path to evolve, so every matching
surface in the MVP can compare interests to apps in one common language.

## User stories (6)

- **US1 — Curate the vocabulary.** As a **platform editor**, I want to define and maintain
  the controlled set of interest tags for the beachhead niche, so that users and apps can
  be described in one shared, consistent language rather than free text.
  *(traces: breakdown §4.1 "controlled vocabulary"; vision §5.4 editorial curation)*
- **US2 — Offer interests to users.** As a **discoverer**, I want to pick my interests from
  a clear, finite list of tags (presented to me by `interest-profile`), so that I can tell
  the platform what I like in terms it understands. *(traces: vision §6 "interest profile";
  selection/storage owned by `interest-profile`, the vocabulary by this feature)*
- **US3 — Offer labels to apps.** As an **app submitter / editor**, I want to tag an app
  from the same controlled vocabulary (via `submission-intake` / editorial tooling), so
  that the app's subject matter is recorded in terms directly comparable to user interests.
  *(traces: vision §2.1 "interest tags"; tagging act owned by `submission-intake`)*
- **US4 — Group tags into clusters.** As a **platform editor**, I want related tags grouped
  into named clusters, so that the matching layer (and, later, ring-based expansion) can
  reason about neighbourhoods of interest rather than only exact-tag hits.
  *(traces: vision §2.2 "interest clusters")*
- **US5 — Evolve the vocabulary safely.** As a **platform editor**, I want to add, rename,
  or retire tags as the niche evolves **without breaking** apps or user profiles already
  tagged, so that the taxonomy can grow without churning everything downstream.
  *(traces: Coordinator note "avoid a painful migration"; data-minimization of churn)*
- **US6 — Give downstream a stable reference.** As a **consuming feature**
  (`interest-profile`, `submission-intake`, matching), I want every tag to have a stable
  identity independent of its display label, so that interests and app labels I stored stay
  valid when a tag is renamed. *(traces: cross-feature contract; Risk R4)*

## Acceptance criteria (Given / When / Then)

- **AC1 (US1).** *Given* the beachhead niche, *when* a platform editor curates the
  vocabulary, *then* a single authoritative set of interest tags exists for that niche, and
  it is the **only** source of valid tags (no two competing vocabularies). *And given* a
  proposed tag that duplicates an existing one (same meaning), *when* it is added, *then*
  the duplication is preventable/visible to the editor (the set stays non-redundant).
- **AC2 (US1, closed set).** *Given* the controlled vocabulary, *when* any consumer
  (user via `interest-profile`, or app via `submission-intake`) supplies an interest/label,
  *then* it is accepted **only if it is a tag that exists in the vocabulary**; an arbitrary
  free-text value that is not in the vocabulary is rejected, not silently coined as a new
  tag. *(The set changes only through editorial curation, US1.)*
- **AC3 (US2, user coverage).** *Given* a typical discoverer in the niche, *when* they are
  shown the tag list to choose interests, *then* the list contains tags that meaningfully
  describe their interests (a low "none of these fit me" rate — see Metrics), and each tag
  is clear enough to choose without guessing (it has a human-readable label and, where the
  meaning isn't obvious, a short definition).
- **AC4 (US3, app coverage).** *Given* an app from the founding catalog, *when* an editor
  tags it, *then* the vocabulary contains tags that adequately capture what the app is
  about (a low "no suitable tag" rate), so the app and interested users end up described in
  comparable terms.
- **AC5 (US4, clustering).** *Given* the curated tag set, *when* the taxonomy is published,
  *then* **every tag belongs to at least one cluster** (no orphan tags), and clusters group
  tags that are genuinely related — so matching can fall back from exact-tag hits to
  same-cluster hits.
- **AC6 (US5, safe evolution).** *Given* a tag already applied to apps and user profiles,
  *when* an editor **renames** it, *then* its display label changes everywhere it appears
  while every existing reference remains valid. *And when* an editor **retires** a tag,
  *then* it stops being offered for new selection/labelling, existing references are handled
  by a defined rule (kept, remapped, or flagged — not silently dropped), and nothing
  downstream breaks. *(The exact retire-rule mechanism is Stage-2 design.)*
- **AC7 (US6, stable identity).** *Given* a tag referenced by a stored user interest or app
  label, *when* its display label later changes, *then* the stored reference still resolves
  to the same tag (references are by stable identity, not by label string).
- **AC8 (US4, future-proofing — design constraint, verified at design review).** *Given*
  the MVP taxonomy ships with clusters but **no** cluster-to-cluster adjacency, *when*
  ring-based expansion (vision §2.2) is added later, *then* adjacency can be introduced over
  the existing clusters **without** redefining tags or re-tagging apps/users (no destructive
  migration). *(Asserts the Coordinator's "design cleanly now" requirement as a checkable
  exit condition for Stage 2, not an MVP deliverable.)*

## Success metrics

This feature is an **enabler** — it proves no H1/H2/H3 hypothesis directly. Its bar is
"matching has a vocabulary good enough to work, and it stays trustworthy as it grows":

- **App coverage rate** — share of founding-catalog apps that can be **adequately tagged**
  using only the vocabulary (editor reports "no suitable tag" for ~0% of apps). Detects
  under-scoping (R1).
- **User coverage rate** — share of niche users who find ≥1 (ideally several) tags that fit
  their interests; a low "none of these fit" rate. Detects under-scoping on the user side.
- **Cluster integrity** — % of tags assigned to ≥1 cluster (target 100%, i.e. zero orphan
  tags) and % of clusters that are non-empty. Surfaces AC5 violations.
- **Vocabulary non-redundancy** — count of near-duplicate/synonym tags (target ≈0); a
  bloated synonym-ridden set both confuses users and degrades matching. Detects over-scoping
  (R2).
- **Reference-break rate on edit** — number of stored user-interest / app-label references
  invalidated by a tag rename or retire (target **0**; this is the core safety property,
  AC6/AC7).
- **Tag-set size** — total active tags, watched as a health band (neither so few apps can't
  be distinguished, nor so many users are overwhelmed); the exact target band is set
  editorially in Stage 2+, not fixed here.

## In scope

- **The single shared controlled vocabulary** of interest tags for the beachhead niche
  (vibecoded webapps, D-1) — the one authoritative source every matching surface reads.
- **Each tag carries:** a human-readable display label, a **stable identity** distinct from
  that label, and (where meaning isn't self-evident) a short definition so editors and
  users apply it consistently.
- **Cluster structure:** every tag grouped into one or more named clusters of related tags
  (vision §2.2), so matching can use exact-tag *and* same-cluster proximity.
- **Lifecycle rules (product level):** add, rename (display), and retire tags **without
  breaking** existing references — including a defined rule for what happens to references
  of a retired tag.
- **Editorial ownership:** the vocabulary is curated by **platform editors** (admin role,
  D-3) — it is *controlled/closed*, changed only through curation, not by end-users.
- **A defined initial tag set** sized "flat-to-shallow" for the niche — enough to (a) let
  users declare interests and (b) let editors match apps — populated as part of delivering
  this feature.

## Out of scope

- **User interest *selection* and its storage** — owned by `interest-profile`. This feature
  supplies the vocabulary; it does not build the signup interest-picker or persist a user's
  chosen interests.
- **App *tagging* during submission** — owned by `submission-intake` / `editorial-curation-tools`.
  This feature supplies the labels; it does not build the submission form or the tagging UI.
- **The matching / ranking algorithm, ring computation, and impression allocation** — owned
  by the matching engine (human/editorial at MVP, vision §5.4). This feature provides the
  *substrate* clusters are read from; it does not decide *how* matches are scored or grown.
- **Cluster-to-cluster adjacency data and ring definitions** (vision §2.2) — **post-MVP**.
  In scope only as a *constraint* that the MVP design must not preclude (AC8), not as a
  deliverable.
- **A universal / multi-niche ontology** — explicitly rejected by the MVP slice; the
  vocabulary is scoped to the one beachhead niche.
- **Open / user-generated tags (folksonomy)**, tag suggestion-by-users, and auto-generated
  tags — the vocabulary is closed and editorially curated at MVP.
- **The rich editorial management UI** for the vocabulary — like `identity-accounts`
  providing the admin *role* but not the admin *tooling*, this feature owns the **vocabulary
  and its lifecycle rules**; an elaborate curation surface belongs to
  `editorial-curation-tools`. (A minimal authoritative way to seed/maintain the set is in
  scope; see Open Questions for the exact boundary.)
- **Localization / multilingual tag labels** (single language at MVP — see Constraints).
- **Per-user or per-app weighting of tags / interest strength** (e.g. "loves" vs "likes") —
  the strength of an interest is `interest-profile`/signal territory, not the vocabulary's.

## Constraints & assumptions

*(Each marked **[verified]** = grounded in a recorded decision/source, or **[unverified]**
= a proposal this brief makes that the user/Architect should confirm.)*

- **Content scope = vibecoded webapps.** Which tags exist is gated by the niche; the
  *structure* is niche-agnostic. **[verified — D-1]**
- **Controlled (closed), editorially-curated vocabulary** — not a folksonomy. **[verified —
  breakdown §4.1 "controlled vocabulary" + vision §5.4 editorial curation]**
- **Shape = flat-to-shallow with clusters; adjacency deferred but not precluded.** Whether
  the structure is a flat tag list or a shallow hierarchy is a **Stage-2 design** choice,
  constrained by AC8 — the Product Analyst does **not** fix the data model. **[verified —
  breakdown §7 Q5 + Coordinator note]**
- **Curation authority = admin role** from `identity-accounts` (D-3); editors authenticate
  through the one access method. **[verified — D-3]**
- **No hard non-functional targets up front** (D-2); but the structure must still hold as
  the platform grows to *many* niches and a far larger tag space later (CLAUDE.md §5.2) —
  the MVP's single-niche set is a deliberate bounded starting point, not a ceiling.
  **[verified — D-2]**
- **Single language (English) tag labels at MVP.** **[unverified — proposal; localization
  deferred]**
- **Tag-set size is "enough to (a) let users declare interests and (b) let editors match
  apps" — neither minimal nor exhaustive.** The exact count is an editorial Stage-2+ call,
  not fixed here. **[verified — breakdown §4.1 note; exact band unverified]**
- **No dependency on other features to exist**; downstream features depend on *it*. It does
  not consume `signal-capture`, `interest-profile`, or `submission-intake`. **[verified —
  breakdown §4.1 "Depends on: —"]**

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Under-scoping** — too few or too coarse tags, so apps can't be distinguished and matches are meaningless (a *productivity* tag that swallows 40 different apps). | Med | High | App-coverage + user-coverage metrics; size the initial set against the real founding catalog, not in the abstract. |
| R2 | **Over-scoping** — chasing a universal ontology / hundreds of synonymous tags, paralysing users and inflating editorial burden, contradicting the MVP slice. | Med | Med | Non-redundancy metric; out-of-scope list rejects multi-niche ontology and folksonomy; flat-to-shallow mandate. |
| R3 | **Shape lock-in** — an MVP model with no path to cluster adjacency forces a painful re-tag/migration when ring expansion arrives (the Coordinator's explicit warning). | Med | High | AC8 makes "adjacency can be added without destructive migration" a Stage-2 design-review exit gate; clusters shipped from day one as the adjacency anchor. |
| R4 | **No stable tag identity** — references stored by label string, so a rename/retire silently invalidates user profiles and app labels downstream. | Med | High | Stable tag identity (AC7) and reference-break-rate = 0 metric are fixed product requirements, flagged to the Architect. |
| R5 | **Inconsistent application / drift** — without clear definitions and single ownership, editors and users apply the same tag to different things, degrading match quality over time. | Med | Med | Per-tag definitions (AC3); single authoritative set + admin-only curation (AC1/AC2); non-redundancy metric. |

## Vision alignment

Serves vision **§2.2** (interest clusters are the substrate of ring-based audience
expansion), **§6 User-facing** (the *interest profile* and *app pages* both speak this
vocabulary), and **§5.4** (editorial curation stands in for the algorithm at MVP — and
needs a shared vocabulary to curate against). It upholds **the one-line test (§8)**: an
unknown solo dev's app "reliably finds its audience" only if app and audience are described
in the same language — this feature *is* that language. It touches ranking not at all, so
*money buys tools, never position* is trivially preserved (a tag confers description, never
visibility).

---

## For confirmation at approval

The brief makes these calls from the source material; flag any you'd decide differently:

1. **Closed/controlled vocabulary** (not user-generated/folksonomy) — grounded in
   "controlled vocabulary" + editorial-curation philosophy. *(Constraints; AC2)*
2. **Clusters are in the MVP; cluster *adjacency* is deferred** but must not be precluded.
   *(AC5 in scope; AC8 as a design constraint)*
3. **Taxonomy shape (flat vs shallow hierarchy) is left to Stage-2 design**, constrained by
   AC8 — the Analyst deliberately does not pick the data model. *(resolves breakdown §7 Q5)*
4. **Single language (English) at MVP**; localization deferred. *(Constraints — [unverified])*
5. **This feature owns the vocabulary + lifecycle rules; the rich curation UI is
   `editorial-curation-tools`** — see Open Questions for the exact seed/maintain boundary.
