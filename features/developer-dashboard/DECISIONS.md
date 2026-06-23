# DECISIONS — developer-dashboard

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 1 (Product Analyst) — RESOLVED by DN-19 (answered 2026-06-24)

The three bundled scoping calls, as answered. DD-1 and DD-2 were **expanded** beyond the
brief's recommendation by the user's answer; DD-3 was taken as recommended.

### DD-1: Reach = combined total + per-source breakdown + curated-line trend — RESOLVED (DN-19.a)
- **Decision:** The MVP presents reach as a **combined impressions total plus a per-source
  breakdown** keyed on the `Surface` vocabulary (Steam-style impressions-by-source) — **curated
  `DIGEST` surfaced first / highlighted** as the most important source, then open `APP_PAGE`
  and any later-added surfaces (search, direct-link, generated-link, feed) — and an
  **impressions-over-time trend** with the **curated (`DIGEST`) series as its own distinguished
  line** (brief AC3/AC4/AC10).
- **Why:** The curated half *is* the H2 demo ("shown to N *matched* users") and the D-8 gate's
  point, so it leads; but the developer also wants to see *where the rest of the reach comes
  from*, source by source. The breakdown enumerates the `Surface` vocabulary so new surfaces
  appear without a dashboard rewrite (CLAUDE.md §5.2 design-for-change).
- **Deferred (user "maybe later"):** a UI to **select which series/subsets** to chart; plotting
  the *funnel* (not just impressions) over time.
- **Rejected:** (a) one combined reach number — hides the matched-audience story and the
  source mix; (b) a hardcoded two-way curated/open split — not extensible to future surfaces.
- **Cost / carry-forward:** needs a **surface-aware AND time-bucketed** read in
  `signals.selectors` (brief C7 / OQ-DD-4) — a Stage-2 design item, **not** a direct
  `signals_*` read (D-7 boundary). `app_funnel` today collapses surfaces and is not bucketed.

### DD-2: Fixed config window set (8 windows), no custom ranges — RESOLVED (DN-19.b)
- **Decision:** Offer a **fixed** config-driven set of windows — **last week / 2 weeks / month
  / 3 months / 6 months / year / 3 years / all-time** — satisfying S5/AC7; arbitrary
  per-developer custom date ranges are deferred.
- **Why:** Bounded reads and a simple selector, covering short-term vs long-term vs cumulative
  reception without an unbounded query surface. The set lives in config (CLAUDE.md §5.2), so
  adding/removing a window is a config change, not a logic change.
- **Rejected:** arbitrary custom ranges (unbounded query surface for no MVP need); a single
  all-time-only window (fails S5 — can't tell current from cumulative).
- **Carry-forward:** bucket granularity for the AC10 trend should be chosen per window in
  Stage 2 (e.g. daily for short windows, monthly for multi-year) — OQ-DD-4.

### DD-3: Per-review weight-eligibility hidden from the owner at MVP — RESOLVED (DN-19.c)
- **Decision:** The developer sees review **content + distribution**, **not** which
  reviews are weight-eligible (curated).
- **Why:** Consistent with D-8 §AC7 (the gate flag is internal substrate, off `ReviewRow`);
  exposing "which reviews count" approaches the gaming-manual line (vision Open Q5) and adds
  nothing until a Quality Score consumes the gate.
- **Rejected:** show eligibility now — premature transparency on an integrity-sensitive field
  with no score yet to make it meaningful.

> **No new global ADR proposed.** The feature reuses **D-3/D-5/D-6/D-7/D-8 as-is** (the
> dashboard is a read-only consumer of existing selector surfaces).
