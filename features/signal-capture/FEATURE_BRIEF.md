# FEATURE_BRIEF — signal-capture

*Stage 1 artifact (Product Analyst). Status: **backlog** — folder scaffolded by the
Coordinator from [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md);
not yet entered Stage 1.*

## Coordinator scope seed (source: breakdown §4.5)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Measurement (the spine) · Phase 0 (schema first — see breakdown §5)
- **Purpose:** The instrumentation layer that records every behavioral signal the future
  Quality Score will consume.
- **MVP slice:** Event capture for: impression shown → click-through → install/open →
  return visit (3d/14d) → share. Includes the **cross-platform attribution prototype**
  (deep-link / "clicked through then returned to rate" proxy).
- **Proves (hypothesis):** **H3** (and feeds H1, H2)
- **Depends on:** identity-accounts
- **Vision design ref:** §3.1, §3.2, Open Q #4
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.5
- **Coordinator note:** The technical heart of the MVP and the breakdown's recommended
  first feature for **D2**. Cross-platform install/engagement tracking is the one piece of
  hard tech that must **not** be deferred (breakdown §3). The event schema is a repo-wide,
  near-irreversible decision — see [DECISIONS.md](DECISIONS.md).

## Brief (Product Analyst — Stage 1)

_pending_ — to be written when this feature enters `1-define`. See
[phase-1-product-analyst.md](../../process/personas/phase-1-product-analyst.md) for the
required sections.
