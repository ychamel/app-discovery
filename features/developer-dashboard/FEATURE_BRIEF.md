# FEATURE_BRIEF — developer-dashboard

*Stage 1 artifact (Product Analyst). Status: **APPROVED** (DN-19, 2026-06-24 — brief approved;
DN-19.a expanded the reach scope to a Steam-style per-source impression breakdown + curated-line
trend; DN-19.b expanded the window set; DN-19.c hidden as recommended). Drafted 2026-06-23,
revised on approval 2026-06-24. Grounds every dependency in code; proposes no new global ADR.*

## Coordinator scope seed (source: breakdown §4.3)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Developer-facing · Phase 3 (make developer value visible — see breakdown §5)
- **Purpose:** The core developer value: transparent, actionable reception.
- **MVP slice:** Read-only view of *reach* (impressions/curated users), *engagement*
  (click-through, opens, returns), and incoming reviews for the dev's app(s).
- **Proves (hypothesis):** **H2** — *an app with $0 marketing can reach a real, matched
  audience and grow on reception alone* (breakdown §1).
- **Depends on:** `signal-capture` (D-7) ✓, `ratings-reviews` (D-8) ✓
- **Vision design ref:** §6 Dev-facing ("Dashboard: … transparent enough to be actionable,
  abstracted enough to resist reverse-engineering for manipulation")
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.3

---

## Brief (Product Analyst — Stage 1)

### Problem statement

**Who:** A developer (D-3 `developer` role) who has submitted an app and had it **accepted**
into the catalogue (D-6).

**What problem:** Once an app is live, the developer has **no way to see how it is being
received.** The platform is already recording everything that matters — every impression,
click-through, return visit, subscribe, share, and incoming review is captured by
`signal-capture` (D-7) and `ratings-reviews` (D-8) — but that corpus is an **internal,
in-process selector surface** with no developer-facing read. The data that *proves H2 to
the person who cares most* exists and is invisible to them.

**Why now:** Both dependencies are built and closed out (D-7 `apps/signals`, 374 tests;
D-8 `apps/ratings`, 486 tests). H2 is the Phase-3 hypothesis the platform must demonstrate,
and per the breakdown this dashboard is *"where H2 becomes visible … 'your app was shown to
80 matched users, 34 tried it, 12 came back after 3 days' is the demo that sells the
platform to developers"* (breakdown §4.3). Nothing else surfaces the captured corpus to a
developer; until it does, the reception data is a backtest substrate (H3) with no
developer-facing payoff (H2).

### Goal

A developer can open a read-only dashboard for an app they own and see its **reception** —
reach, the engagement funnel, and incoming reviews — over a chosen window, sourced
faithfully from the captured D-7 / D-8 corpus, scoped strictly to their own apps.

### Domain terms (defined or linked)

- **Reception** — the platform's record of how an app was received: its *reach*,
  *engagement funnel*, and *incoming reviews*. Read-only; this feature presents it, it does
  not produce or score it.
- **Reach** — how many times / to how many the app was *shown*. Presented as a **combined
  impressions total plus a per-source breakdown** keyed on the `Surface` vocabulary — today
  `DIGEST` and `APP_PAGE`, extensible to future surfaces (search, direct-link, generated-link,
  feed) with no dashboard rewrite (DN-19.a; modelled on Steam's impressions-by-source view).
  **Curated reach** (impressions on an *organic-curation* surface — `Surface.DIGEST`, per the
  **D-8** gate) is surfaced **first / highlighted** as the most important source ("shown to N
  *matched* users" — the H2 story); all other surfaces are **open reach** (`APP_PAGE` and
  self-driven views). A reach **trend over time** plots impressions across the window with the
  **curated (`DIGEST`) series as its own distinguished line** (DN-19.a).
- **Engagement funnel** — the raw per-app counts from `signals.selectors.app_funnel`:
  impressions → click-throughs → returns @ short/long window → subscribes →
  page-reengagements → shares, with the off-platform proxy reported separately (D-7 §5b).
- **Returns** — impressed users who came back within the short / long window
  (config tunables, "3d/14d" illustrative); **derived at read**, never a stored event (D-7).
- **Incoming reviews** — the ratings + review text left on the app, read through
  `ratings.selectors.reviews_for_app` (count + raw score distribution + recent list; **no
  average / score**, by D-8 design).
- **Owner-scoped** — a developer sees reception only for apps they own; another developer's
  app id is indistinguishable from "not found" (`catalog.get_owned_app`, D-6 §AC8).
- **H2** — see Coordinator seed above.

### User stories (5)

- **S1 — My apps' reception list.** As a **developer**, I want a list of my accepted apps
  each with a reception summary, so that I can see at a glance which of my apps are getting
  traction.
- **S2 — Reach for one app.** As a **developer**, I want to see how many times my app was
  shown — a combined total plus a per-source breakdown (curated `DIGEST` first/highlighted,
  then open `APP_PAGE` and any later sources) and a trend over time with a distinguished
  curated line — so that I can tell whether the platform is putting it in front of its core
  ring (H2) and where the rest of my reach is coming from.
- **S3 — Engagement funnel for one app.** As a **developer**, I want the funnel from
  impressions through click-throughs, returns, subscribes, re-engagement and shares, so that
  I can see not just that my app was shown but that people *acted on it and came back*.
- **S4 — Incoming reviews for one app.** As a **developer**, I want to read the ratings and
  reviews left on my app, so that I get the qualitative feedback the audience is giving me.
- **S5 — Choose the reporting window.** As a **developer**, I want to view reception over a
  bounded recent window (and all-time), so that I can tell *current* reception from
  cumulative history.

### Acceptance criteria (Given / When / Then)

- **AC1 (S1) — owner-scoped my-apps list.** *Given* a signed-in developer who owns two
  accepted apps (and another developer owns a third), *When* they open the dashboard, *Then*
  they see exactly their two apps with a reception summary each, and never the third app or
  its data.
- **AC2 (S1) — non-developer / non-owner is denied.** *Given* a signed-in account that owns
  no apps (or is not in the `developer` role), *When* it requests the dashboard or any app's
  reception view, *Then* it is shown an empty/own-nothing state (own-nothing) or denied, and
  no other developer's reception is ever returned.
- **AC3 (S2) — reach is a combined total + per-source breakdown.** *Given* an app with 5
  `DIGEST` and 20 `APP_PAGE` impressions in the window, *When* the developer views its reach,
  *Then* they see a **combined total of 25** plus a per-source breakdown — **`DIGEST` = 5**
  (curated, shown **first / highlighted**) and **`APP_PAGE` = 20** (open) — each `Surface`
  labelled distinctly, matching the **D-8** definition of "curated". A surface added later
  (e.g. search, direct-link) appears in the same breakdown **without a dashboard rewrite**
  (the breakdown enumerates the `Surface` vocabulary, not a hardcoded two-way split).
- **AC4 (S2) — honest zero, not a blank.** *Given* an accepted app with **no** impressions on
  a given source (the MVP reality for `DIGEST` until a digest emitter ships), *When* the
  developer views its reach, *Then* that source reads **0** explicitly (an honest zero with a
  "no curated shows yet" affordance for `DIGEST`), never a hidden/blank or a fabricated number.
- **AC10 (S2) — reach trend with a distinguished curated line.** *Given* an app with
  impressions spread across the selected window, *When* the developer views the reach trend,
  *Then* impressions are plotted over time bucketed to the window, with the **curated
  (`DIGEST`) series drawn as its own distinguished line** separate from open impressions.
  *(User-selectable series/subsets in the graph are explicitly deferred — DN-19.a "maybe
  later"; MVP draws the total + the curated line.)*
- **AC5 (S3) — funnel matches the corpus.** *Given* an app with known D-7 events in the
  window, *When* the developer views its funnel, *Then* every displayed count
  (impressions, click-throughs, returns short/long, subscribes, page-reengagements, shares)
  equals the corresponding `signals.selectors.app_funnel` field for that app and window, and
  the off-platform proxy is shown **separately**, never folded into click-throughs (D-7 §AC7).
- **AC6 (S4) — reviews are shown faithfully, with no average.** *Given* an app with several
  ratings, *When* the developer views incoming reviews, *Then* they see the total count, the
  raw per-score distribution, and the recent review list (via `reviews_for_app`), and **no
  computed average / star score / rank** is presented anywhere (D-8 §AC6).
- **AC7 (S5) — window bounds the figures.** *Given* an app with events both inside and
  outside the selected window, *When* the developer picks a window from the fixed set —
  **last week / 2 weeks / month / 3 months / 6 months / year / 3 years / all-time** (DN-19.b,
  config-driven) — *Then* the reach, breakdown, trend and funnel figures recompute to count
  only events whose `occurred_at` falls in that window (window-derived returns honoured), and
  the "all-time" option counts every event.
- **AC8 (cross-cutting) — read-only, never an allocation lever.** *Given* any reception view,
  *When* the developer interacts with it, *Then* nothing the dashboard exposes lets them
  change their app's allocation, ranking, or position, and no action on the dashboard mutates
  the D-7 / D-8 corpus (it is a pure read — vision §5.6: a tool, never position).
- **AC9 (cross-cutting) — bounded reads at scale.** *Given* a developer who owns *K* accepted
  apps, *When* the my-apps list renders, *Then* the reception summaries are fetched in a
  **bounded** number of queries independent of *K* (e.g. via `funnel_for_apps`), not one
  funnel query per app (no N+1).

### Success metrics

| # | Metric | What it tells us | Source |
|---|--------|------------------|--------|
| M1 | **Dashboard adoption** — % of developers with ≥1 accepted app who open their dashboard at least once | Is the H2 payoff reaching the person who cares most? | dashboard page-view (own instrumentation; *not* a D-7 app-impression) |
| M2 | **Reception-view return rate** — % of dashboard-viewing developers who come back to it within 7 / 30 days | Is the dashboard *actionable* enough to be habitual? | dashboard page-view |
| M3 | **Non-empty reception rate** — % of viewed apps whose dashboard shows a non-zero funnel (any click-through or return) | The literal H2 demo: does a $0-marketing app show *real* reception? | derived from `app_funnel` |
| M4 | **Curated-reach coverage** — % of viewed apps with ≥1 curated (`DIGEST`) impression | How thin is the "matched audience" story until a digest emitter ships (expected ~0 at MVP — honest, not a bug) | `app_funnel` / surface split |
| M5 | **Owner-scope leak count** — number of incidents where a developer is served another developer's reception | The integrity invariant; target **0** | access logs / tests |
| M6 | **Dashboard read latency (p95)** | Is the read fast enough to be a usable tool at 100× corpus? | request timing |

> M3/M4 are expected **thin at MVP**: the only live impression emitter is `app-pages`
> (`APP_PAGE`), and there is **no `DIGEST` emitter yet** (it arrives with
> `weekly-digest` / `editorial-curation-tools`). The dashboard must report this honestly
> (AC4) — a true zero is the correct reading, made visible, not a defect.

### In scope

- A **read-only** developer-facing surface listing the developer's **accepted** apps (D-6),
  each with a reception summary, and a per-app reception view.
- **Reach** for an app as a **combined total + per-source breakdown** over the `Surface`
  vocabulary (curated `DIGEST` first/highlighted, then open `APP_PAGE` and any later-added
  surfaces) per the D-8 gate, **plus an impressions-over-time trend** with the curated
  (`DIGEST`) series as a distinguished line (DN-19.a).
- The **engagement funnel** for an app, read from `signals.selectors.app_funnel` /
  `funnel_for_apps` (impressions, click-throughs, returns short/long, subscribes,
  page-reengagements, shares, off-platform proxy shown separately).
- **Incoming reviews** for an app via `ratings.selectors.reviews_for_app` (count +
  distribution + recent list, no average).
- A **fixed config-driven reporting window** selector — **last week / 2 weeks / month /
  3 months / 6 months / year / 3 years / all-time** (DN-19.b).
- **Owner-scoping** and developer-role gating on every read.

### Out of scope (and why it's safe to defer)

- **Quality Score, ring position, score components, impression *allocation*** (vision §6
  Dev-facing) — the score/allocator do not exist at MVP (breakdown §3, deferred); the
  dashboard shows **raw reception only**. Surfacing a score now would be fabricating one.
- **Retention *curves* / funnel time-series, and user-selectable graph series** — MVP draws
  **one** trend (impressions over time with the curated line, AC10) and otherwise windowed
  **counts**; plotting the *funnel* over time, retention-curve shape, and a UI to pick which
  series/subsets to chart are deferred (DN-19.a "maybe later"). (The impressions trend itself
  **is** in scope — see In scope / AC10.)
- **Any write / action** — no re-boost, no "talk to subscribers", no update posting
  (that is `developer-updates`); no editing reviews. Read-only (AC8).
- **Per-review weight-eligibility shown to the developer** — the gate flag is internal
  substrate (D-8 §AC7 keeps it off `ReviewRow`); exposing "which reviews count" risks the
  gaming-manual line (vision Open Q5) and adds nothing until a score consumes it. Deferred;
  logged as OQ.
- **A public HTTP/DRF analytics API** — the MVP is a server-rendered owner-scoped view over
  in-process selectors (D-4 templates default); a public API is not required to prove H2.
- **Cross-app / portfolio aggregate analytics, exports, alerts/notifications, comparison to
  category baselines** — `category_impressions` exists (D-7) but per-category benchmarking is
  a richer analytics step, deferred.
- **Non-accepted apps' "reception"** — pending/rejected/withdrawn apps have no catalogued
  presence and no reception; their status is already visible via `submission-intake`.

### Constraints & assumptions

| # | Constraint / assumption | Status |
|---|--------------------------|--------|
| C1 | Reach/engagement is read **only** through `signals.selectors.*` (`app_funnel`, `funnel_for_apps`, `has_impression`, `category_impressions`); nothing reads `signals_*` directly (D-7). | **verified** — [apps/signals/selectors.py](../../apps/signals/selectors.py) |
| C2 | "Curated reach" = impressions on `Surface.DIGEST`; "open" = `Surface.APP_PAGE` — the **D-8** gate's single definition; the dashboard must not invent a different one. | **verified** — [DECISIONS.md D-8](../../DECISIONS.md), `apps/ratings/gate.CURATED_SURFACES` |
| C3 | Reviews are read **only** through `ratings.selectors.reviews_for_app` (count + distribution + capped recent list); no average/score is available or computed (D-8). | **verified** — [apps/ratings/selectors.py](../../apps/ratings/selectors.py) |
| C4 | A developer's owned apps come from `catalog.selectors.list_owned_apps(owner)` / `get_owned_app(owner, id)` — **owner-scoped** by construction (D-6). The dashboard filters to **accepted** apps for reception. | **verified** — [apps/catalog/selectors.py](../../apps/catalog/selectors.py) |
| C5 | Authentication + the `developer` role gate come from `apps/accounts` (D-3); the dashboard adds no identity surface. | **verified** — D-3 |
| C6 | Per the selector docstring, the signals read surface is **internal/admin, in-process only**; a developer-facing read is "a thin role-gated view over these selectors — a one-feature-later addition, not built [in signals]." This feature *is* that addition. | **verified** — [apps/signals/selectors.py](../../apps/signals/selectors.py) lines 23–26 |
| C7 | `app_funnel.impressions` counts **all** surfaces collapsed and is **not time-bucketed**; the per-source breakdown (AC3) *and* the over-time trend (AC10) both need a new **surface-aware + time-bucketed** read that distinguishes `Surface` and groups by time. This is a **Stage-2 design** call (OQ-DD-4) — it must live in `signals.selectors` (preserving D-7: nothing reads `signals_*` directly), never a dashboard-side raw-table read. The breakdown enumerates the `Surface` vocabulary so new surfaces appear automatically (§5.2 design-for-change). | **verified gap — design concern** ([apps/signals/selectors.py](../../apps/signals/selectors.py), [apps/signals/kinds.py](../../apps/signals/kinds.py)) |
| C8 | Returns @ short/long windows are config tunables (no magic 3/14), derived at read; the dashboard reuses them, it does not redefine windows. | **verified** — D-7 §SC-9 |
| C9 | Performance: my-apps list must be bounded-query (AC9) via `funnel_for_apps`; per-app views are 2-query reads (D-7). Targets follow D-2 ("scale as we go") — no hard global budget, but designs must hold at 100×. | **verified posture** — D-2 |
| C10 | Privacy: reviews already anonymize deleted-account authors ("a former user"); reach/funnel figures are **aggregate counts**, never per-identified-user lists — the dashboard exposes no PII the dependencies don't already publish. | **verified** — D-7/D-8 |

### Risks

| # | Risk | Likelihood × Impact | Mitigation |
|---|------|---------------------|------------|
| R1 | **The "empty dashboard" undercuts the H2 demo** — with no `DIGEST` emitter and thin traffic, most apps show near-zero curated reach, reading as "the platform isn't working." | High × Med | Report honestly with explanatory affordances (AC4); make *open* reach + the live funnel visible so there is a real story; treat M3/M4 thinness as expected (documented), not a bug. |
| R2 | **Transparency-vs-gaming line** (vision Open Q5 / §6 "abstracted enough to resist reverse-engineering for manipulation") — showing too much raw signal becomes a manipulation manual. | Med × Med | At MVP there is no score to game, so raw reception counts are low-risk; keep per-review eligibility and any allocation logic **out** (out-of-scope); flag the line for the Architect and revisit when a score consumes the corpus. |
| R3 | **Owner-scope leak** — a bug serves developer A the reception of developer B's app. | Low × High | Route every read through the owner-scoped `get_owned_app`/`list_owned_apps`; make AC1/AC2/M5 explicit test targets; never accept an app id without an owner check. |
| R4 | **Curated/open split has no single existing selector** (C7) — tempting to read `signals_*` directly and break D-7. | Med × Med | Hold the line: the split is a **design** task (add a surface-aware read to `signals.selectors` if needed), never a direct table read; logged as OQ for Stage 2. |
| R5 | **Scope creep into charts/score/allocation** — "actionable" invites curves, comparisons, a score. | Med × Med | Out-of-scope list is explicit; MVP = windowed counts + reviews; richer analytics and any score are separately-designable later features. |

### Vision alignment

Serves **H2** (breakdown §1) and vision **§6 Dev-facing** ("Dashboard … transparent enough
to be actionable, abstracted enough to resist reverse-engineering for manipulation") and
**§5.6** (analytics dashboards are an explicitly **position-neutral tool** — *money buys
tools, never position*). The **money-buys-position test → PASS**: the dashboard is a pure
read of reception; it exposes no lever to change allocation, and reception itself is earned
through the audience (vision §2–§4), never bought (AC8).

---

## Decisions resolved (DN-19 — answered 2026-06-24)

The brief is **APPROVED** with the three bundled scoping calls answered (full record in
[DECISIONS.md](DECISIONS.md) DD-1…DD-3, now RESOLVED; questions closed in
[OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)):

- **DN-19.a — reach presentation → EXPANDED.** Not a binary split but a **combined
  impressions total + per-source breakdown** over the `Surface` vocabulary (Steam-style),
  with **curated `DIGEST` first/highlighted** as the most important source and an
  **impressions-over-time trend carrying a distinguished curated line** (AC3/AC4/AC10).
  User-selectable graph series are deferred. Cost: a surface-aware **and time-bucketed** read
  in `signals.selectors` (C7 / OQ-DD-4 — Stage-2 design).
- **DN-19.b — window set → EXPANDED.** Fixed config-driven set: **last week / 2 weeks /
  month / 3 months / 6 months / year / 3 years / all-time** (no arbitrary custom ranges).
- **DN-19.c — per-review weight-eligibility → HIDDEN** (as recommended): the developer sees
  review *content* + distribution, not "which reviews count". Revisit when a Quality Score
  consumes the gate.

No new **global** ADR is proposed — the feature reuses **D-3/D-5/D-6/D-7/D-8 as-is**. The
surface-aware/time-bucketed read (OQ-DD-4) is an **additive read-surface extension** to the
closed `signals` app, carried to Stage 2.
