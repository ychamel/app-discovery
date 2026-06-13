# DECISIONS.md — Global Decision Log (ADRs)

**This is the durable channel for repo-wide rationale.** It records decisions that
outlive any single feature — the ones a future feature's Architect must not have to
re-derive or accidentally contradict.

## Global vs. per-feature decisions

- **Here (global):** the tech stack, the shared-code root, the ranking algorithm, the
  beachhead niche, data-store choice, auth model, cross-cutting conventions — anything
  that constrains *more than one* feature.
- **In `features/<slug>/DECISIONS.md` (local):** choices scoped to one feature that no
  other feature needs to know about.

Rule of thumb: **if a later feature would be wrong to contradict it, it belongs here.**
A global decision buried in one feature's folder is invisible to the next feature — that
is exactly the drift this file prevents.

## Format (one ADR per entry, newest first)

```
### D-<n>: <short title>
- **Date:** YYYY-MM-DD
- **Stage / feature:** <where it was made>
- **Decision:** <what was chosen>
- **Why:** <the reasoning>
- **Alternatives rejected:** <≥1 genuinely different option + why not>
- **Sacrifices / consequences:** <what this costs us>
```

A confirmed global decision is also summarized in [CONTROL.md](CONTROL.md)
*Decisions Made (recently)* as a one-line, human-readable digest.

## Decisions

_None yet. The first entries will come from the first feature's Stage 2 (tech stack,
shared-code root) and from resolving D1–D3 in [CONTROL.md](CONTROL.md)._
