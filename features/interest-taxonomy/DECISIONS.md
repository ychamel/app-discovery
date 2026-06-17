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

---

*Stage-2 (Software Architect) decisions, 2026-06-17. Made in [DESIGN.md](DESIGN.md);
**pending design approval (A5)**. The cross-feature shape + reference contract is global
[D-5](../../DECISIONS.md); the finer mechanism choices below are feature-local.*

## ITX-6 — Retire rule: soft-retire + optional successor, non-destructive (resolves OQ-2)

**Decision:** A retired tag is **kept** (`status=retired`, row stays, `retired_at` set) and
stops being offered for new selection/labelling; existing references still resolve. When a
tag is retired *because it merges into* another, the editor sets an optional `replaced_by`
successor, and `resolve_tag` returns the active successor. Remapping is **read-time only** —
it never rewrites references stored by `interest-profile`/`submission-intake`.
**Rationale:** Guarantees reference-break-rate = 0 (AC6/AC7, R4) without touching data this
feature doesn't own; "what a tag means now" stays in one place (`resolve_tag`).
**Rejected:** hard-delete on retire (breaks references); rewriting downstream references on
merge (touches non-owned tables, momentarily breaks references).
**Binds:** AC6, OQ-2. See [DESIGN.md](DESIGN.md) §7/§10.

## ITX-7 — Management surface: seed file + `seed_taxonomy` command + Django admin (resolves OQ-1)

**Decision:** MVP seed/maintain = an editable, version-controlled `seed/vocabulary.yaml`
applied idempotently (upsert-by-`slug`) by `manage.py seed_taxonomy`, plus the `is_staff`/
admin-gated Django admin for ad-hoc edits — **no custom curation UI**. All writes route
through `services.py` (the single mutate path). Retirements are explicit; the seeder never
deletes a tag that drops out of the file.
**Rationale:** Mirrors identity-accounts (admin role here, admin *tooling* in
`editorial-curation-tools`); vocabulary is *data*, so it lives in a re-runnable seed file,
not a data migration.
**Rejected:** building the rich curation UI here (over-scope, ITX-5); baking the vocabulary
into a data migration (couples editorial content to schema migrations).
**Binds:** OQ-1, In/Out of Scope. See [DESIGN.md](DESIGN.md) §6.

## ITX-8 — Tag-set size band deferred to Stage 4, authored against the founding catalog (OQ-3)

**Decision:** No fixed tag count is set in the design. The concrete initial size/band is an
**editorial Stage-4 call** made while authoring `seed/vocabulary.yaml` against the **real
founding catalog**, measured by the App-coverage / User-coverage metrics (R1/R2).
**Rationale:** Sizing in the abstract risks under/over-scoping; the catalog is the only
honest yardstick.
**Rejected:** fixing a number now (guesswork before the catalog is in view).
**Binds:** OQ-3, Metrics (tag-set size band). See [DESIGN.md](DESIGN.md) §12.

---

*Stage-4 (Senior Engineer) implementation notes, 2026-06-17.*

## ITX-9 — Unauthenticated read returns **403**, not 401 (DESIGN §5c correction)

**Decision:** The three read endpoints return **403** (not the `401` written in DESIGN
§5c) for an unauthenticated request. DRF's `SessionAuthentication` — the project-wide
default fixed by [D-4](../../DECISIONS.md) — issues no `WWW-Authenticate` challenge, so
the framework returns `403 Forbidden`. DESIGN §5c was updated to match.
**Rationale:** This is the established platform behavior; `identity-accounts` asserts the
same `403` for unauthenticated API access ([test_developer_role.py:39](../../apps/accounts/tests/test_developer_role.py)).
Forcing a `401` would require diverging from the platform auth default for no real benefit
(the contract intent — reject the unauthenticated — is met by `403`).
**Rejected:** a custom authenticator/exception handler to coerce `401` (inconsistent with
the rest of the platform; added complexity, no benefit).
**Binds:** DESIGN §5c auth posture; the read-API tests (T-05).

## ITX-10 — Seed file parsed with PyYAML

**Decision:** `seed_taxonomy` (T-06) parses `seed/vocabulary.yaml` with **PyYAML**
(added to `pyproject.toml` dependencies), using `yaml.safe_load`.
**Rationale:** DESIGN §6 specifies a human-editable YAML vocabulary file; PyYAML is the
boring, universal YAML parser. A hand-rolled parser would be a maintenance liability
(CLAUDE.md §5.2). The seed format stays isolated behind the command (DESIGN §3 coupling
check), so the dependency is contained.
**Rejected:** a bespoke YAML/JSON parser (reinventing a solved problem); switching the
file format to JSON (less readable for a hand-curated vocabulary).
**Binds:** T-06 implementation, `pyproject.toml`.

## ITX-11 — Added `update_tag` / `update_cluster` sync setters to the write service (DESIGN §5b)

**Decision:** Added two functions to the write service: `update_tag(tag, *, label,
clusters, definition="")` and `update_cluster(cluster, *, name, description="")`. Each
applies the same dedupe/≥1-cluster guards as `add_*` and is a **no-op when nothing
changed**. DESIGN §5b was updated to list them.
**Rationale:** DESIGN §6 requires `seed_taxonomy` to "update labels/definitions/membership
for existing ones" through `services.py` only, but §5b's enumerated functions had no
idempotent-sync setter for definition/description. These realize §6 (rather than changing
intent) and make a re-seed of an unchanged file a true no-op (T-06 DoD). `rename_tag`/
`rename_cluster` remain the focused AC6 "safe rename" verbs for admin use.
**Rejected:** the seeder writing the ORM directly (bypasses invariants — forbidden by §6);
overloading `rename_*` to also carry definition/description (muddies the AC6 rename verb).
**Binds:** DESIGN §5b, T-06/T-08.

## ITX-12 — Founding size band: 11 clusters / 67 tags (closes OQ-3)

**Decision:** The founding `seed/vocabulary.yaml` for the beachhead niche (vibecoded
webapps, D-1) holds **11 clusters and 67 tags**. A guard-rail test pins the band at
**6–16 clusters / 40–90 tags** — wide enough to grow, tight enough to catch synonym bloat
(R2) or collapse.
**Rationale:** Enough breadth for users to declare interests (AC3) and to distinguish apps
(AC4) across the archetypes a solo/AI-assisted web app tends to be (productivity, dev
tools, AI, content, finance, health, education, social, commerce, data, lifestyle), without
near-duplicate tags. Sized editorially per DESIGN §12 (no fixed number was set there).
**Rejected:** a tiny set (under-covers app subject matter, AC4); a sprawling set (synonym
bloat, harms the closed-vocabulary matching quality, R2).
**Binds:** OQ-3, AC3/AC4/AC5. **Caveat — app-coverage deferral (PL-1):** authored against
the niche definition + representative archetypes, not a real submitted catalog (none exists
pre-`submission-intake`); App-coverage (AC4) re-validation is **deferred & reopenable** —
see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-4.
