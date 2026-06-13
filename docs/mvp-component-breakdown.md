# MVP Component Breakdown — Curated App Discovery Platform

*Status: Draft for review · Last updated: 2026-06-13 · Source: [curated-app-platform-design.md](../curated-app-platform-design.md)*

> **Purpose.** This document decomposes the vision doc into **separately designable
> components**, viewed through an MVP lens. It is a planning/reference artifact for the
> Coordinator stage — it is *not* a feature brief. Each component below is a candidate to
> run through the pipeline (Stage 1 → 6) as its own `features/<slug>/` folder.
>
> **Nothing here is final.** The vision is explicitly pre-MVP and up for change. Treat
> every scope line as a proposal and every open question as a real fork.

---

## 1. What the MVP is actually trying to prove

The platform's *differentiating* machinery — the Quality Score, ring-based expansion,
the impression allocator, the integrity system — is also its hardest and riskiest part,
and **by the design's own logic it cannot run without data** (§3, §5.4). So the MVP's
job is not to build that machinery. Its job is to **stand up the smallest end-to-end
loop that produces the data and proves the value**, while humans stand in for the
algorithm.

Three hypotheses to validate (mapped to [§8 Success Criteria](../curated-app-platform-design.md)):

| # | Hypothesis | Whose value | How the MVP shows it |
|---|------------|-------------|----------------------|
| H1 | A curated, scarce digest makes users *try* apps they'd never have found. | **Users** | Digest open rate + impression→click-through→trial conversion. |
| H2 | An app with **$0 marketing** can reach a real, matched audience and grow on reception alone. | **Developers** | A submitted app gets in front of its core ring and produces engagement/retention signal — visible to the dev. |
| H3 | Editorial curation + raw signal capture produces exactly the data a future Quality Score would need — **de-risking the algorithm before we build it.** | **Platform** | We can retroactively ask "would a score computed from these signals have matched editorial judgement?" |

The "one-line test" (§8) is the north star: *a great app from an unknown solo dev with
$0 marketing reliably finds its audience here.* The MVP is the cheapest honest test of
that sentence.

---

## 2. The MVP strategy in one paragraph

Follow the design's **sequenced narrow launch** (§5.4): one beachhead niche, a
hand-curated founding catalog, and a **weekly digest** as the only user surface — *not* a
browsable destination yet. Humans do the matching (editorial tools replace the matching
engine). The Quality Score, rings, and integrity defenses are **deferred** — but the
**signals they will one day consume are captured from day one.** That single discipline
(measure now, score later) is what turns a hand-run MVP into a launchpad for the real
algorithm instead of a throwaway demo.

---

## 3. Scope boundary: what is IN vs. OUT for the MVP

### In scope — the validation loop

Foundation + the thinnest slice of each surface that closes the user↔developer loop and
records signal.

### Deliberately OUT of scope (and why it's safe to defer)

| Deferred component | Why it can wait | What replaces it in the MVP |
|--------------------|-----------------|------------------------------|
| **Automated Quality Score pipeline** (§3) | Needs a corpus of real signal to calibrate; scoring before you have data is guessing. | Editorial judgement + raw signal stored for later backtesting. |
| **Matching engine / ring computation / impression allocator** (§2.2, §6 Internal) | Meaningless at 50–150 apps and a small user base; the interest graph isn't dense enough. | Humans assemble each digest (editorial curation). |
| **Integrity system** — account maturity, behavioral coherence, graph analysis (§4) | At MVP scale (hand-recruited catalog, trusted early users) manipulation isn't yet the threat, and the score it would protect doesn't exist yet. | Capture the behavioral data the future system needs; manual eyeballing suffices for now. |
| **Browsable destination feed** (§5.4 step 4) | The design explicitly graduates to this *after* the digest proves out. | Weekly digest is the hero surface. |
| **Update & re-boost manager** (§5.2, §6 Dev-facing) | Depends on the allocator existing. | Editorial can manually re-feature an updated app. |
| **Collections & follows** (§6 User-facing) | Engagement nicety, not part of the core hypotheses. | — |
| **Developer subscription / monetization** (§5.6) | Free tier must always be enough to launch; no revenue needed to validate. | Everything free during MVP. |
| **Reviewer reputation weighting** (§3.2) | Earned slowly over time; nothing to weight yet. | All curated signal treated equally for now. |

> **The one piece of "hard tech" that must NOT be deferred:** cross-platform install /
> engagement tracking (Open Question #4). The design flags it as *"a genuine technical
> hard problem to prototype early."* It lives in the MVP under **Signal Capture** (§4.5)
> precisely because deferring it would invalidate H2 and H3.

---

## 4. The components (each separately designable)

Grouped by layer. Each is a candidate `features/<slug>/`. The **MVP slice** column is the
thin version; the **proves** column ties it to a hypothesis.

### 4.1 Foundation (cross-cutting — build first)

| Slug | Purpose | MVP slice | Proves | Depends on | Design ref |
|------|---------|-----------|--------|------------|------------|
| `identity-accounts` | Accounts, auth, sessions for both users and developers. | Email-based sign-in, two roles (user / developer), basic profile. | enabler | — | §6 (all surfaces) |
| `interest-taxonomy` | The controlled vocabulary of interest tags + cluster structure that everything matches against. | A curated flat-to-shallow tag set for the *one* beachhead niche (not a universal ontology). | enabler | — | §2.2, §6 User-facing |

> `interest-taxonomy` is foundational and easy to under-scope. The full "interest space"
> with adjacency for rings is post-MVP; the MVP only needs enough tags to (a) let users
> declare interests and (b) let editors match apps to people. Designing it cleanly now
> avoids a painful migration when rings arrive.

### 4.2 User-facing

| Slug | Purpose | MVP slice | Proves | Depends on | Design ref |
|------|---------|-----------|--------|------------|------------|
| `interest-profile` | Explicit interest tags at signup; the input to curation. | Onboarding tag-picker writing to the user profile. (Implicit/behavioral refinement deferred.) | H1 | `identity-accounts`, `interest-taxonomy` | §6 User-facing |
| `weekly-digest` | The hero surface: weekly "N apps picked for you" delivery. | Compose + deliver (email and/or push) a per-user list of editor-chosen apps; track delivery + opens. | H1 | `editorial-curation-tools`, `app-pages`, `signal-capture` | §5.4 step 3, §6 |
| `app-pages` | Uniform public page per app (identical slots for solo dev & studio). Doubles as the dev's web home / press kit. | Static template: media, description, platform links/downloads, reviews block. | H1, H2 | `submission-intake` | §6 User/Dev-facing |
| `ratings-reviews` | Capture explicit signal **and** enforce the curated-rating gate. | Rate + review on an app page; **record whether the rater was curated to that app** so the gate is enforceable now and weightable later. | H1, H3 | `app-pages`, `signal-capture` | §3.1, §4.1 |
| `open-search-browse` | Full catalog findable by anyone (the "open access" half of the integrity premise). | Minimal search/listing so direct links and discovery work outside the digest. | enabler / H3 | `app-pages` | §4.1, §6 User-facing |

### 4.3 Developer-facing

| Slug | Purpose | MVP slice | Proves | Depends on | Design ref |
|------|---------|-----------|--------|------------|------------|
| `submission-intake` | Developer's entry point + the **objective** quality gate (works, not malware/spam/dupe, honest metadata). | Submission form (metadata, tags, media, platform targets) + a checklist gate. Manual review acceptable at MVP volume. | H2 | `identity-accounts`, `interest-taxonomy` | §2.1, §5.5, §6 Dev-facing |
| `developer-dashboard` | The core developer value: transparent, actionable reception. | Read-only view of *reach* (impressions/curated users), *engagement* (click-through, opens, returns), and incoming reviews for the dev's app(s). | **H2** | `signal-capture`, `ratings-reviews` | §6 Dev-facing |

> `developer-dashboard` is where H2 becomes visible to the person who cares most. Even
> with no scoring algorithm, "your app was shown to 80 matched users, 34 tried it, 12
> came back after 3 days" is the demo that sells the platform to developers.

### 4.4 Internal / editorial (the algorithm's human stand-in)

| Slug | Purpose | MVP slice | Proves | Depends on | Design ref |
|------|---------|-----------|--------|------------|------------|
| `editorial-curation-tools` | Let a human do what the matching engine + allocator will later do: pick which apps go to which users this week. | Catalog management + a digest-assembly view (per user or per interest cluster) with send controls. | H1, H3 | `interest-taxonomy`, `submission-intake`, `weekly-digest` | §5.4 steps 2–3, §6 Internal |

### 4.5 Measurement (the spine — invisible but most important)

| Slug | Purpose | MVP slice | Proves | Depends on | Design ref |
|------|---------|-----------|--------|------------|------------|
| `signal-capture` | The instrumentation layer that records every behavioral signal the future Quality Score will consume. | Event capture for: impression shown → click-through → install/open → return visit (3d/14d) → share. Includes the **cross-platform attribution prototype** (deep-link / "clicked through then returned to rate" proxy). | **H3** (and feeds H1, H2) | `identity-accounts` | §3.1, §3.2, Open Q #4 |

> This is the technical heart of the MVP. If it's modeled well now — clean event schema,
> per-user/per-app/per-impression keys, category tags for future per-category baselines —
> then the Quality Score, rings, and integrity system are later *consumers* of this data,
> not rewrites. If it's modeled badly, the whole north-star architecture inherits the debt.
> The Architect (Stage 2) should treat the event schema here as a near-irreversible,
> repo-wide decision and log it in [DECISIONS.md](../DECISIONS.md).

---

## 5. Dependency-ordered build sequence

A suggested order. Arrows are hard dependencies; items on the same line are parallelizable.

```
Phase 0 — Foundation
  identity-accounts ─┬─► interest-taxonomy
                     └─► signal-capture (schema first; it's the spine)

Phase 1 — Get the catalog in and presentable
  submission-intake ─► app-pages ─► editorial-curation-tools

Phase 2 — Close the user loop and start measuring
  interest-profile ─► weekly-digest ─► (impression/click signals flow into signal-capture)
  ratings-reviews   (curated-gate recorded)
  open-search-browse  (minimal; enables open-access + direct-link integrity premise)

Phase 3 — Make developer value visible
  developer-dashboard  (reads everything signal-capture + ratings-reviews collected)
```

**Thinnest end-to-end slice that tests H1+H2+H3 at once:** Phase 0 + Phase 1 +
`weekly-digest` + `signal-capture` + a stub `developer-dashboard`. Everything else
thickens the loop.

---

## 6. How this maps to the open decisions

- **D1 (beachhead niche)** scopes `interest-taxonomy`, `submission-intake`, and the
  founding catalog — but **not** the component structure itself. The components are
  niche-agnostic; the niche fills in their content. So D1 can be resolved in parallel
  with designing the foundation components.
- **D2 (first feature)** is exactly the choice in §5: the dependency graph says the first
  *buildable* feature is in **Phase 0** (`identity-accounts` or `signal-capture` schema),
  because the user-visible features depend on them. The first *demonstrable* slice is the
  Phase 0→2 thin loop above.
- **D3 (constraints)** — platform/compliance scope directly shapes `signal-capture`
  (cross-platform tracking, install attribution, privacy of behavioral data) and
  `identity-accounts`.

> **Recommended first feature for D2:** `signal-capture` (schema + the cross-platform
> attribution prototype), because (a) Open Q #4 calls it out as the hard problem to
> prototype early, (b) it's the highest-risk, highest-leverage decision, and (c) every
> other component depends on it. This is a recommendation, not a decision — D2 is yours.

---

## 7. Open questions surfaced by this breakdown

These extend [§7 of the vision doc](../curated-app-platform-design.md) and should land in
the relevant feature's `OPEN_QUESTIONS.md` when it enters the pipeline:

1. **Digest delivery channel** — email, push, or both? Affects `weekly-digest` and open-rate measurement (H1's primary metric).
2. **"Curated" definition for the gate** — at MVP, with humans assembling digests, what exactly marks a user as "curated to app X" for the rating gate? (`ratings-reviews` + `editorial-curation-tools` must agree on this.)
3. **Cross-platform attribution method** — deep-link, optional SDK, or click-through-and-return proxy? (Open Q #4; the single biggest `signal-capture` design fork.)
4. **Behavioral-data privacy posture** — what we record, retention, consent. Gates D3 and `signal-capture`.
5. **Taxonomy shape** — flat tag list vs. shallow hierarchy with adjacency. Designing for future rings without over-building now.
6. **Founding catalog mechanics** — is catalog recruitment a product surface or an offline editorial process for MVP? (Likely offline; confirm.)

---

## 8. Traceability

Every component above traces to a vision section: foundation/surfaces → §6; the curation
substitution → §5.4; signal capture → §3.1/§3.2; the curated-rating gate → §4.1; the
deferral rationale → §3 and §5.4; the success metrics behind H1–H3 → §8. Components with
*no* vision-doc origin were not invented here — if future work has no traceable origin,
it belongs in an `OPEN_QUESTIONS.md`, per [CLAUDE.md](../CLAUDE.md) §6.3.
