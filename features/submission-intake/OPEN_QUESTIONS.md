# OPEN_QUESTIONS — submission-intake

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

- **Founding catalog mechanics (breakdown §7 Q6):** is catalog recruitment a product
  surface or an offline editorial process for MVP? (Likely offline; confirm.) Shared with
  [editorial-curation-tools](../editorial-curation-tools/OPEN_QUESTIONS.md).
- Content (which apps / niche) is gated by repo decision **D1** (beachhead niche) in
  [CONTROL.md](../../CONTROL.md).

## Stage 1 (Product Analyst, 2026-06-17)

- **OQ-1 — Founding-catalog entry path (refines breakdown §7 Q6). RESOLVED 2026-06-17 →
  SI-5.** Confirmed at brief approval: founding apps are **self-submitted** by recruited
  developers through the same form; recruitment is an **offline** editorial activity, *not*
  a product surface in this feature. Reopens scope only if an in-product recruitment/invite
  surface is later wanted. See [DECISIONS.md](DECISIONS.md) SI-5.
- **OQ-2 — Exact gate checklist wording. RESOLVED 2026-06-17 → [DESIGN.md](DESIGN.md) §6.**
  The five floors are a **fixed code enum** (`catalog.gate.Criterion`); their reviewer-facing
  "what to check" wording lives in one place (`gate.CHECKLIST`), editable as a one-file change.
  Crucially there is **no "other"/"quality" criterion** — a taste rejection is unrepresentable in
  the decision shape (AC6/R1, §6b). The concrete wording per floor is a Stage-4 fill-in of
  `CHECKLIST` against the design's intent.
- **OQ-3 — Media slots/limits. RESOLVED 2026-06-17 → [DESIGN.md](DESIGN.md) §4/§9.** MVP media =
  screenshots/images; **1 ≤ count ≤ 8 per app**, formats **PNG/JPEG/WebP**, **≤ 5 MB/file**,
  Pillow-validated at the boundary, stored via Django storage under `MEDIA_ROOT` (limits are
  `apps.core.config` tunables). Published as the contract **[app-pages](../app-pages/) must adopt**
  (recorded here so the two don't diverge); revisit if `app-pages` needs different slots.
