# DECISIONS.md — app-page-redesign

Feature-local decisions. Repo-wide choices go in the global
[../../DECISIONS.md](../../DECISIONS.md). Each entry: the choice, why, and what was rejected.

---

## APR-D-1 — Phased scope: redesign v1 now, heavy bets queued (Coordinator, 2026-06-29)

**Decision.** Scope this feature as a **focused v1 redesign**: restructure the app page and
add the cheapest high-impact slots. The heavier, higher-cost bets are **deferred to separate
future features**, not bundled here.

- **In v1 (this feature):** a restructured page with — a short pitch line / tagline, a
  media carousel (screenshots + an inline looping product-demo clip as a peer to images),
  typed/faceted tags (genre · modality · platform/access · pricing · maturity), a richer
  structured "deep dive" description ("show more"), a developer-identity block ("an app by
  ___" + other apps by the same developer), and surfacing the existing
  [`developer-updates`](../developer-updates/) feed as an on-page devlog.
- **Deferred to future features (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §Deferred bets):**
  full hosted **trailer/video** (storage/transcoding/bandwidth — real infra), **follow the
  developer** (vs. the existing app-follow), and **community Q&A / comments**.

**Why.** The full reimagined page is plausibly 4–6 features' worth of work; landing it as one
mega-feature fights the staged pipeline (CLAUDE.md §2) and §5.5 simplicity discipline. A
focused v1 ships value before the live deploy (APR-D-2) and lets the heavy infra bets be
scoped on their own merits when activated.

**Rejected.** (a) One ambitious v1 covering everything incl. trailer hosting + dev-follow —
too large for one clean Feature-Track pass. (b) Keep brainstorming without scoping — the user
chose to commit.

**User decision:** AskUserQuestion 2026-06-29 → *"Phased: redesign now, heavy bets later."*

---

## APR-D-2 — Sequence this **before** the live staging deploy (Coordinator, 2026-06-29)

**Decision.** Land the app-page redesign **before** the live staging deploy
([DN-PS-DEPLOY](../../CONTROL.md)) and the founding-developer recruitment that follows it.

**Why.** The app page **is** the developer's marketing landing page and the
bring-your-own-audience face of the wedge ([global D-10](../../DECISIONS.md), vision §5.4).
Recruiting founding developers onto a stale listing-style page undersells the wedge; the
deploy should debut the compelling page. This mirrors the precedent set when
[premium-frontend](../premium-frontend/) was sequenced before the deploy for the same reason.

**Implication.** DN-PS-DEPLOY stays parked (reopenable, artifacts ready) until this feature
closes out — exactly as it stayed parked behind `premium-frontend`.

**Rejected.** Deploy first then redesign with real feedback — the user chose to strengthen the
face first; real-feedback iteration remains available post-deploy regardless.

**User decision:** AskUserQuestion 2026-06-29 → *"Redesign first, then deploy."*
</content>
</invoke>
