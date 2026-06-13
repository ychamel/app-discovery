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

### D-2: No hard launch constraints at MVP — start small, scale as we go
- **Date:** 2026-06-14
- **Stage / feature:** `0-coordinator` (resolving CONTROL.md D3)
- **Decision:** No fixed deadline, budget, platform, or compliance/privacy ceiling is imposed up front. The guiding posture is to build the smallest honest slice first and grow capacity (data, users, infra) incrementally.
- **Why:** The MVP's job is to validate H1–H3 cheaply (breakdown §1). Premature hard constraints would over-specify non-functional targets before we have real load or a chosen stack.
- **Alternatives rejected:** Fixing a launch deadline / infra budget now — rejected because there is nothing yet to size against; it would be guesswork that later features would be wrong to treat as binding.
- **Sacrifices / consequences:** Non-functional targets (scale, latency, retention/consent specifics) are **deferred to each feature's Stage 1–2**, not given globally. "Scale as we go" is a posture, **not** a licence to ship hacks — CLAUDE.md §5.2 (designs must still work at 100×, or document the bounded trade-off) still binds. Privacy/compliance posture for behavioral data remains an explicit open design fork (breakdown §7 Q4), now un-gated but unresolved.

### D-1: Beachhead niche is "vibecoded webapps"
- **Date:** 2026-06-14
- **Stage / feature:** `0-coordinator` (resolving CONTROL.md D1)
- **Decision:** The single launch vertical is **vibecoded webapps** — small web applications built rapidly (often AI-assisted / "vibe coding") by solo developers and tiny teams.
- **Why:** The design mandates a sequenced narrow launch with one beachhead niche (vision §5.4, breakdown §2). This niche is rich in exactly the platform's target persona — unknown solo devs with $0 marketing shipping real apps — making it the cheapest honest test of the one-line north star (breakdown §1).
- **Alternatives rejected:** Indie productivity tools / indie games on a single platform (the breakdown's example niches) — rejected in favour of vibecoded webapps because web apps need no app-store gatekeeper or per-platform install flow, lowering the bar for both submission and the cross-platform attribution prototype.
- **Sacrifices / consequences:** Scopes the **content**, not the component structure (components are niche-agnostic, breakdown §6). Directly shapes `interest-taxonomy` (tag vocabulary), `submission-intake` (what "an app" is + the objective gate), and the founding catalog. Web-only at MVP means native-install attribution is out of scope for now; if the platform later expands beyond web, `signal-capture` attribution must be revisited.
