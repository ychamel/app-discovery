# DECISIONS — developer-updates

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 — Product Analyst (PROPOSED, pending DN-20)

These are the scoping calls bundled into the brief-approval decision **DN-20** (CONTROL.md).
Each becomes **RESOLVED** when the user approves; until then the brief is `DRAFT`.

### DU-1 (DN-20.a) — Early-access is a notice *kind*, not an entitlement mechanism
**Choice:** At MVP, "early-access" is one **kind** of notice (an announcement), matching the
already-pinned AS-3 contract (`kind ∈ {"update", "early_access"}`). Gating actual access to a
pre-release build/key is **out of scope**.
**Why:** The render contract `app-subscriptions` pinned already enumerates `early_access` as a
notice kind — honoring it is the minimum honest surface (CLAUDE.md §5.5, no speculative
machinery). Entitlement enforcement is a separate, larger problem (auth to a build, keys,
revocation) with no upstream dependency built.
**Rejected:** A third dedicated feature for early-access (the Stage-1 review already chose not
to split — revisit only if it grows); building access-gating now (speculative).

### DU-2 (DN-20.b) — Distribution at MVP = the in-platform followed-apps feed only
**Choice:** Notices are delivered by repointing the AS-3 `notices_for_apps` seam so they
render in the **existing followed-apps feed**. **No email/push** at MVP.
**Why:** The seam, DTO, and single call site already ship (AS-3 = option A); this is the
exact surface `app-subscriptions` built developer-updates to fill. Email/push is new infra
(deliverability, templates, opt-out, queues) the MVP slice doesn't need to prove H2.
**Rejected:** Email/push delivery at MVP (deferred, out of scope); a brand-new standalone
notices page divorced from the follow graph (the feed *is* the follow graph's surface).

### DU-3 (DN-20.c) — Posting emits no score-bearing signal; posts are rate-limited
**Choice:** The act of posting a notice emits **no** curated/weighted D-7 signal. The only
corpus entries are the followers' **own genuine returns**, recorded by `signal-capture`
through existing kinds. Posting is **rate-limited** (config-driven).
**Why:** Directly answers the "gaming manual" risk (vision Open Q #5 / seeded OQ): a
developer must not be able to manufacture engagement signal by posting. A notice is *content*,
not an impression/event. This must hold because it feeds the same corpus the Quality Score
will trust. The rate limit caps follower-spam and trivial-bump abuse (vision §5.2 spirit).
**Rejected:** Emitting a "notice published" engagement event (would let posting move the
corpus — gameable); unlimited posting (spam + signal-manufacture vector).

> **Global ADRs:** none proposed. This feature **reuses D-3** (role gate), **D-6** (owner
> scoping / accepted catalogue), **D-7** (the signal corpus — consumed, not extended), and
> the **AS-3** producer contract from `app-subscriptions`. Whether developer-updates owns a
> table is a **Stage-2** decision, not recorded here.
