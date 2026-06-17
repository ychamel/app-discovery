# OPEN_QUESTIONS — interest-taxonomy

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

- **Taxonomy shape (breakdown §7 Q5):** flat tag list vs. shallow hierarchy with
  adjacency? Design for future rings without over-building now.
- Content (which tags) is gated by repo decision **D1** (beachhead niche) in
  [CONTROL.md](../../CONTROL.md).

## Stage 1 — Product Analyst (2026-06-17)

- **Q5 (taxonomy shape) — handled, not answered here.** The brief deliberately does **not**
  pick flat-vs-hierarchy — that is a Stage-2 **design** (data-model) decision, outside the
  Analyst's mandate. The brief instead fixes the *product constraints* the shape must
  satisfy: clusters present at MVP (AC5), and **adjacency addable later without destructive
  migration** (AC8). → **For the Architect to resolve in DESIGN.md against AC8.**
- **OQ-1 — Management-surface boundary (for the Architect).** This brief scopes the
  *vocabulary + its lifecycle rules* to `interest-taxonomy`, and the *rich curation UI* to
  `editorial-curation-tools` (mirroring identity-accounts: admin role here, admin tooling
  elsewhere). The exact line — how editors **seed and maintain** the set at MVP (e.g. an
  authoritative data source / management command vs. a minimal in-app screen) before
  `editorial-curation-tools` exists — is left to Stage-2 design. Flagged so it isn't
  dropped between the two features.
- **OQ-2 — Retired-tag reference rule (for the Architect).** AC6 fixes the *requirement*
  (a retired tag's existing references must be handled by a defined rule — kept, remapped,
  or flagged — never silently dropped) but not the *mechanism*. The Architect picks the
  rule and where remapping (if any) lives.
- **OQ-3 — Tag-set size band.** The brief sets size as an editorial call, not a fixed
  number. The concrete initial count/band should be decided when the founding catalog is
  in view (App-coverage metric), likely at Stage 2/4 with editorial input.

## Stage 2 — Software Architect (2026-06-17) — resolutions

*Resolved in [DESIGN.md](DESIGN.md) (pending design approval A5). Logged so the open items
above are closed against concrete decisions.*

- **Q5 / OQ-1 (taxonomy shape) — RESOLVED.** Flat tags + named clusters joined by a
  many-to-many membership (no tag→tag hierarchy). Adjacency (AC8) is a future
  cluster-to-cluster table over existing clusters — additive, no re-tag. Global
  [D-5](../../DECISIONS.md); DESIGN §7. *(was breakdown §7 Q5.)*
- **OQ-1 (management surface) — RESOLVED.** Editable `seed/vocabulary.yaml` + idempotent
  `manage.py seed_taxonomy` + `is_staff`/admin-gated Django admin; no custom curation UI
  (rich UI stays in `editorial-curation-tools`). Feature-local **ITX-7**; DESIGN §6.
- **OQ-2 (retired-tag rule) — RESOLVED.** Soft-retire (`status=retired`, row kept) +
  optional `replaced_by` successor; non-destructive read-time resolution via `resolve_tag`,
  never rewriting downstream references. Feature-local **ITX-6**; DESIGN §7.
- **OQ-3 (size band) — DEFERRED to Stage 4 by design.** No number fixed; the band is
  authored editorially against the real founding catalog when `seed/vocabulary.yaml` is
  written, measured by App-/User-coverage. Feature-local **ITX-8**; DESIGN §12.

### New cross-feature note handed downstream (DESIGN §11 / D-5)

- **Tag-reference contract for consumers.** `interest-profile`, `submission-intake`, and the
  matcher must store the `Tag.id` (UUID, never the label/slug), validate input with
  `is_valid_tag(id)` at their write boundary, and resolve with `resolve_tag(id)` at read.
  Flagged so a consumer does not store labels or coin off-vocabulary tags.

## Stage 4 — Senior Engineer (2026-06-17)

- **OQ-3 (size band) — CLOSED for MVP, with a deferral.** Founding vocabulary authored in
  `seed/vocabulary.yaml`: **11 clusters / 67 tags** for the single beachhead niche
  (vibecoded webapps). Editorial size band recorded as **ITX-12**; a guard-rail test
  (`test_founding_vocabulary.py`) keeps it in the 6–16 cluster / 40–90 tag range.
- **OQ-4 (app-coverage validation) — DEFERRED & reopenable (PL-1).** DESIGN §12 sizes against
  "the real founding catalog", but **no app catalog exists yet** — it arrives with
  `submission-intake` (downstream of this Phase-0 foundation, D2). The vocabulary was
  therefore authored against the **niche definition + representative app archetypes**;
  measuring AC4 App-coverage against a *real submitted catalog* is deferred, exactly as
  `identity-accounts` deferred live metrics (R1). **Re-validate when `submission-intake`
  lands.** This deferral does not block Stage 4 (surfaced in CONTROL).
