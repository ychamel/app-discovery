# DECISIONS — developer-dashboard

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 (Product Analyst, 2026-06-23) — PROPOSED, pending DN-19 approval

These are the brief's recommendations on the three bundled scoping calls. They become
RESOLVED on DN-19 approval (or are revised by the user's answer).

### DD-1: Split reach into curated (`DIGEST`) vs open (`APP_PAGE`) — PROPOSED (DN-19.a)
- **Decision (proposed):** The MVP reports **reach as two figures** — *curated reach*
  (impressions on `Surface.DIGEST`, the **D-8** organic-curation gate) and *open reach*
  (`Surface.APP_PAGE` / self-driven), shown distinctly (brief AC3/AC4).
- **Why:** The curated half *is* the H2 demo ("shown to N *matched* users"); a single
  collapsed "reach" number hides exactly what proves H2 and contradicts the D-8 gate's point.
- **Rejected:** (a) one combined reach number — hides the matched-audience story; (b) curated
  reach only — discards the live open-reach signal that is non-zero at MVP.
- **Cost:** needs a surface-aware read (brief C7 / OQ-DD-4) — a Stage-2 design item, **not** a
  direct `signals_*` read (D-7 boundary).

### DD-2: Fixed config window set, no custom ranges — PROPOSED (DN-19.b)
- **Decision (proposed):** Offer a small **fixed** set of windows driven by config — *last
  7 days / last 30 days / all-time* — satisfying S5/AC7; arbitrary per-developer custom date
  ranges are deferred.
- **Why:** Bounded reads, simple UI, covers "current vs cumulative" without an unbounded
  query surface.
- **Rejected:** arbitrary custom ranges (unbounded, more UI/query surface for no MVP need);
  single all-time-only window (fails S5 — can't tell current from cumulative).

### DD-3: Per-review weight-eligibility hidden from the owner at MVP — PROPOSED (DN-19.c)
- **Decision (proposed):** The developer sees review **content + distribution**, **not** which
  reviews are weight-eligible (curated).
- **Why:** Consistent with D-8 §AC7 (the gate flag is internal substrate, off `ReviewRow`);
  exposing "which reviews count" approaches the gaming-manual line (vision Open Q5) and adds
  nothing until a Quality Score consumes the gate.
- **Rejected:** show eligibility now — premature transparency on an integrity-sensitive field
  with no score yet to make it meaningful.

> **No new global ADR proposed.** The feature reuses **D-3/D-5/D-6/D-7/D-8 as-is** (the
> dashboard is a read-only consumer of existing selector surfaces).
