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

## Stage 2 (Software Architect) — RATIFIED by DN-DD-DESIGN (answered 2026-06-24)

The DESIGN decisions, mapping to [DESIGN.md](DESIGN.md). All **RATIFIED** on the
DESIGN-approval decision (DN-DD-DESIGN in [CONTROL.md](../../CONTROL.md)) — binding for Stage 3.
**Resolves OQ-DD-4.** **No new global ADR** — reuses D-3/D-5/D-6/D-7/D-8.

> **Stage 4 status (Senior Engineer, 2026-06-24): DD-DESIGN-1…5 all BUILT** across T-01…T-06,
> as specified, with no contract deviation. Implementation note (no contract change):
> `impression_trend` uses `TruncDay` (not `TruncDate`) for the DAY grain so `ImpressionBucket.
> bucket_start` is uniformly a `datetime` across all three granularities — this *honours* the
> declared DTO type (`bucket_start: datetime`); a bare `TruncDate` would have returned a `date`
> for DAY and broken that uniformity. The two `reception` composition entry points take a
> `ResolvedWindow` (the §4.3 resolved form carrying the `ReportingWindow` + concrete
> `start`/`end`/`granularity`) rather than a bare `ReportingWindow` — these signatures are
> internal (§5.4: the DTOs/composition are template+test only; the irreversible public surface
> is the two URL routes + the two selector signatures, both as designed). Full per-AC
> verification is in [TEST_PLAN.md](TEST_PLAN.md).

### DD-DESIGN-1: New model-less consumer app `apps/dashboard/` — RATIFIED
- **Decision:** The dashboard is a stateless consumer app (mirrors `apps/pages/` +
  `apps/discovery/`) owning **no model, migration, table, or index**. Activation *and* rollback
  = a single `config/urls` include (+ `INSTALLED_APPS` line).
- **Why:** Everything it presents is already a read surface; design-for-deletion by
  construction (remove the include → every dependency untouched). House norm (verified A8).
- **Rejected:** a public HTTP/DRF analytics API (out of scope — server-rendered owner-scoped
  view suffices to prove H2).

### DD-DESIGN-2: Two additive neutral reads on `signals.selectors` — RATIFIED (**resolves OQ-DD-4**)
- **Decision:** Add `impression_breakdown(app, *, start, end)` + `impression_breakdown_for_apps`
  (per-`Surface` counts, **every** `Surface` zero-filled — AC3/AC4) and
  `impression_trend(app, *, start, end, granularity)` (per-`Surface` per-time-bucket — AC10) +
  a `TrendGranularity` enum, to `apps/signals/selectors.py`. **No** model/migration/index
  change (backed by the existing `signals_imp_app_time_idx`).
- **Why:** D-7 forbids reading `signals_*` outside `signals.selectors` (R4), so the
  surface-aware/time-bucketed read *must* be an additive extension there — same precedent as
  ratings' `has_impression`. Signals stays **neutral** (counts per surface; never judges
  "curated"). The breakdown enumerates the `Surface` vocabulary so a new surface appears with
  no dashboard rewrite (§5.2 design-for-change). Invariant `breakdown.total ==
  app_funnel.impressions` keeps reach and funnel consistent.
- **Rejected:** (a) the dashboard reading `signals_*` directly (breaks D-7/R4); (b) deriving
  the breakdown by summing trend buckets (couples totals to chart granularity, can disagree
  with the funnel).

### DD-DESIGN-3: 8 reporting windows + per-window bucket granularity as a code-fixed table — RATIFIED
- **Decision:** `apps/dashboard/windows.py` holds the fixed 8 `ReportingWindow`s (1w/2w/1m/3m/
  6m/1y/3y/all) each with a bucket `granularity` (DAY ≤1m, WEEK 3–6m, MONTH ≥1y + all-time);
  all-time is lower-bounded by an epoch sentinel so the existing range-based selectors are
  reused unchanged (AC7). Unknown/blank `window` → the default key (fail-safe).
- **Why:** A closed vocabulary (like `Surface`/`CHECKLIST`) belongs in code in the feature
  app, not env config; granularity-per-window is the M6/AC9 bound on the trend's bucket count.
- **Rejected:** arbitrary custom date ranges (DN-19.b — unbounded query surface).

### DD-DESIGN-4: Failure split + read-only gating — RATIFIED
- **Decision:** Core reception (signals) read **fails loud** (500 + `DASHBOARD_RECEPTION_DEGRADED`
  — the one alert; a fake-empty dashboard would lie about H2, R1); the reviews slot **fails
  soft** (`available=False`); owner-scope mismatch ⇒ **404 indistinguishable** (AC8/R3);
  `login_required` + `require_role(DEVELOPER)`, **GET-only**, **no `signals.capture` import**
  (AST-enforced) so viewing a dashboard emits no D-7 impression (AC8 structural).
- **Why:** Mirrors discovery's loud-listing / soft-facet split and ratings' soft display; the
  no-capture rule prevents a developer inflating their own reach by viewing it.

### DD-DESIGN-5: Reach split reuses `CURATED_SURFACES`; trend = inline-SVG line — RATIFIED
- **Decision:** The curated/open split and the trend's curated line are composed from
  `ratings.gate.CURATED_SURFACES` (the single D-8 source); the trend renders as a pure-Python
  inline-SVG polyline (total + curated) with a `<table>` fallback.
- **Why:** One source of truth for "curated"; no JS build dependency (D-4 server-rendered
  default); the table fallback is accessible and makes exact per-bucket numbers testable.
- **Rejected:** client-side JS charting (adds a dependency for one MVP line);
  hardcoding `DIGEST` in the dashboard (two sources of truth).
