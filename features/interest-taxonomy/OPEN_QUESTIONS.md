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
