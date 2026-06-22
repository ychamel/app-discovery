# OPEN_QUESTIONS — interest-profile

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded from the breakdown (§7)

_None mapped directly._ Note: this feature consumes the tag set defined by
[interest-taxonomy](../interest-taxonomy/OPEN_QUESTIONS.md), whose **taxonomy shape**
(breakdown §7 Q5) constrains the onboarding tag-picker. Add ambiguities here as the
feature enters the pipeline.

## Stage 1 — Product Analyst (2026-06-21)

Raised as **DN-15** in [CONTROL.md](../../CONTROL.md) (brief approval + the assumption
forks below). Working positions are in the brief / [DECISIONS.md](DECISIONS.md); these are
not blockers to drafting but should be confirmed before/at Stage 2.

- **OQ-IP-1 — Stored unit: tags only, or tags + cluster-level interests?** **RESOLVED
  (DN-15): tags only**, clusters as a selection aid (IP-1). The matcher reads `Tag.id`s.
- **OQ-IP-2 — Onboarding: optional or required?** **RESOLVED (DN-15): optional/non-gating**
  (IP-2); empty profile is a valid handled state. Revisit when a digest consumer exists.
- **OQ-IP-3 — Empty-profile semantics for the future digest (deferred to the consumer).**
  When a profile is empty, what should the (unbuilt) matcher/digest do — broad/editorial
  fallback, or nothing? Out of scope here (matcher owns it); flagged so the consumer
  feature resolves it. Not a DN.
- **OQ-IP-4 — Interest intensity (deferred).** Flat declared set at MVP (out of scope). If
  "love vs like" weighting is ever wanted, it is an additive change to this feature, named
  not built. Not a DN.

## Stage 2 — Software Architect (2026-06-22, DESIGN.md pending DN-16)

No new blockers raised; the design resolves the Stage-1 working assumptions (IP-3/4/5 — see
[DECISIONS.md](DECISIONS.md) IP-DESIGN-*). Re-affirmed as out-of-scope, not blockers:

- **OQ-IP-3 — empty-profile digest semantics** — still owned by the **future matcher**; the
  design only guarantees an empty profile is a representable, handled state here (AC6). No DN.
- **OQ-IP-4 — interest intensity** — additive later (a per-row strength column + a richer read
  selector); named, not built. No DN.

Design-surfaced note (not a blocker): the picker's set-replace must **preserve a stored
reference the active-only picker cannot show** — a *no-successor* retired tag (`retire_tag`
allows `replaced_by=None`, verified) — to keep AC7/M5 true across edits. Resolved in-design by
the §7 preserve-on-edit rule (IP-DESIGN-2), not escalated.
