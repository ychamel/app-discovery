# DECISIONS — embeddable-update-widget

_Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide decisions
go in the top-level [DECISIONS.md](../../DECISIONS.md). This feature is activated by global
**[D-10](../../DECISIONS.md)** (developer-wedge pivot)._

## Stage 1 — Product Analyst (2026-06-26) — RESOLVED (DN-EUW-BRIEF approved — all 5 as recommended, with a source-attribution refinement on EUW-5 → EUW-6)

- **EUW-1 (RESOLVED) — The widget is display-only; it never authors notices.** It renders the
  app's existing published notices (the AS-3 `PublishedNotice` source of truth) + a link back to
  the app page. *Rejected:* a second authoring path inside the widget — would split the
  single-source-of-truth `developer-updates` owns and duplicate state.
- **EUW-2 (RESOLVED) — Capture happens by click-through, not in-widget auth.** The widget links to
  the existing app page; account creation / follow / sign-up use the platform's existing paths. The
  widget itself does no auth UI. *Rejected:* embedding follow/login in a third-party host app —
  large cross-origin auth surface for no MVP gain; the app page already does this.
- **EUW-3 (RESOLVED) — The widget is a FREE single-player tool, not a paid promotion placement.**
  It surfaces a developer's **own** notices; paid promotion placements ([D-9](../../DECISIONS.md))
  are a separate future monetization surface, out of scope here. *Rejected:* folding promo
  placements into this feature — conflates a free tool with the paid surface and bloats scope.
- **EUW-4 (RESOLVED) — Widget interactions are a non-curated surface (the hard firewall).** No
  widget impression or click-through may enter `ratings.gate.CURATED_SURFACES` or confer D-8
  eligibility (brief AC6 / M5 = 0). Binding on Stage 2 regardless of OQ-EUW-2's resolution.
- **EUW-5 (RESOLVED) — Published notices become a public read via the widget.** Today notices show
  only in the follower feed; the widget exposes a developer's **own** app's notices to anonymous
  end users. The developer authors them (implicit consent), and a changelog is public by nature.
  Approved as a deliberate product expansion. **User refinement:** end users are **anonymous when
  not logged in**, but in **all** cases the **source of the view is tracked** — see EUW-6.
- **EUW-6 (RESOLVED) — Widget interactions are tracked by source for developer-dashboard
  attribution.** Per the user's DN-EUW-BRIEF refinement: every widget impression / click-through —
  anonymous or signed-in — is **attributed to the widget as its source**, so the developer can see
  on their dashboard **how many people reached the platform from the widget** (brief **AC9**;
  firms M2/M3/M4). This is a required MVP capability and is **orthogonal to EUW-4/AC6**: tracking a
  source neither confers D-8 eligibility nor moves the Quality Score (the firewall is
  per-impression, not per-user). *Rejected:* leaving attribution unspecified / dashboard-only-later
  — the user explicitly wants widget-sourced reach visible to the developer at MVP. **Mechanism
  (the `Surface` value, the D-7 emit shape, and the `developer-dashboard` read) is Stage-2 design —
  OQ-EUW-2.**

> **Stage-2 design questions (NOT decided here):** the embedding mechanism (OQ-EUW-1); *how* the
> non-curated widget-source signal is emitted / whether a new `Surface` (e.g. `WIDGET`) is added
> and how `developer-dashboard` reads it for AC9/M2-M4 attribution (OQ-EUW-2); and the rate/abuse
> limits on the public read (OQ-EUW-3). See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## Stage 2 — Software Architect (2026-06-26) — RATIFIED (DN-EUW-DESIGN approved 2026-06-26 — binding for Stage 3)

> **Stage 4 status (Senior Engineer, 2026-06-26): EUW-7 … EUW-11 are BUILT** exactly as ratified
> (T-01…T-07, full suite green; per-AC coverage in [TEST_PLAN.md](TEST_PLAN.md)). The only
> implementation addition is **EUW-IMPL-1** (the nested-savepoint on the EUW-9 create-race retry,
> recorded under Stage 4 below) — same algorithm, no contract change.

These resolve OQ-EUW-1/2/3 and back [DESIGN.md](DESIGN.md). Binding inputs AC6 (firewall) and
AC9 (attribution) are honored, not re-decided. Reuses D-4/D-6/D-7/D-8/D-9/D-10 — **no new global
ADR**.

- **EUW-7 (RATIFIED) — Embedding = a server-rendered `<iframe>` (resolves OQ-EUW-1).** The
  developer pastes one `<iframe src=".../widget/<app_id>/">`; the platform serves a complete,
  self-contained HTML page (inline CSS, **no JS, no build** — AC7). The "view on platform" control
  is a `target="_top"` link routed through `/widget/<app_id>/view`. *Rejected:* a `<script>` DOM
  injector (needs client JS + a build, XSS/style-collision surface in the host page, fragile
  cross-origin) and a JSON-render-yourself endpoint (violates AC7, moves firewall-relevant render
  into untrusted host code). The iframe is zero-build, cross-origin-safe by construction, and
  keeps the rendered content entirely platform-controlled. *Cost:* fixed-box sizing + minimal
  theming (accepted for MVP, brief §7).
- **EUW-8 (RATIFIED) — Widget attribution lives in a dedicated `apps/widget`-owned store, NOT the
  D-7 `signals` corpus (resolves OQ-EUW-2).** Widget impressions/click-throughs are counted in
  `widget_reach_count`; `apps/widget` **imports nothing from `signals`** (AST-enforced). The
  firewall (AC6/M5=0) is therefore **structural by total absence from the corpus** — a widget
  interaction cannot be `has_impression(surfaces=CURATED_SURFACES)` evidence because it creates no
  corpus row. The developer-dashboard reads widget reach as a distinct, clearly-labeled
  off-platform slot. *Rejected:* the brief's illustrative `Surface.WIDGET` — would force anonymous,
  high-volume, scrape-prone third-party traffic into the authenticated, PII-free integrity corpus,
  break `signals.capture`'s authenticated-actor invariant, overload `user IS NULL`, and make the
  firewall runtime rather than structural. AC9 is fully met (source tracked, reach on the
  dashboard); only the *mechanism* (which the brief delegated to design) differs from the §8 sketch.
- **EUW-9 (RATIFIED) — Attribution storage = a daily rollup counter, atomic `F()`-increment, not
  append-per-event.** `widget_reach_count(app_id, kind, count_date, count)` bounds growth to
  `apps × 2 × days` on a surface designed to sit in high-traffic third-party apps, and stores
  exactly the daily shape the dashboard reads (M4). No cache/queue infra (the `developer-updates`
  durable-table precedent). *Rejected:* append-per-event (unbounded growth on an anonymous open
  surface for per-event granularity no AC needs). **Bounded trade-off:** a popular app's daily row
  is write-hot; throttled by the per-IP rate limit + `Cache-Control` TTL, named growth path =
  per-day counter sharding / async write-behind (not built — no speculative abstraction).
- **EUW-10 (RATIFIED) — MVP attribution = reach (impressions + click-throughs); per-account
  conversion (M3) is deferred.** AC9's binding requirement (reach visible to the developer) is
  delivered. Linking a *new account/follow* to a specific widget click requires carrying a
  widget-source token through an anonymous click → app page → sign-up across sessions/domains
  (cookie consent + cross-domain identity + the no-PII posture) — a materially harder problem the
  brief flags as aspirational. Deferred and re-opened as **OQ-EUW-5**, not silently dropped.
- **EUW-11 (RATIFIED) — The view is the app-validation boundary; `attribution` trusts a validated
  `app_id`.** The render/redirect views validate ACCEPTED (D-6) via `catalog.get_catalogued_app`
  before counting; the single-caller `attribution` writer does not re-read the catalog on every
  increment. *Rejected:* re-validating inside `attribution` — doubles the hot-path catalog read for
  no gain since the view is the only caller. *Cost:* if a future second caller is added it must
  validate first (documented at the write surface).

> **AC6 / AC9 are binding brief inputs honored above, not decisions made here.** **No new global
> ADR** — the stack (D-4) and shared-code root (`apps/`) already exist. Touches two closed apps
> additively (`apps/dashboard` gains a fail-soft widget-reach slot; `apps/core` gains a reusable
> GET rate limiter + config + metrics). Rollback = `git revert` of the build commit (DU-REL-1
> precedent), since the dashboard imports `widget.selectors`.

## Stage 4 — Senior Engineer (2026-06-26) — implementation notes (no scope/interface/schema change)

These record where the build adds a faithful implementation detail the design's illustrative
pseudocode omitted. None changes a contract, schema, or decision above.

- **EUW-IMPL-1 (T-02) — the atomic-increment create-race retry uses a nested `transaction.atomic()`
  savepoint.** DESIGN §6's pseudocode wraps the `create()` in a bare `try/except IntegrityError`
  inside the outer `atomic()`. On PostgreSQL (D-4) that does not work: an `IntegrityError` marks the
  whole transaction for rollback, so the `except` branch's follow-up `update()` raises
  `TransactionManagementError` ("current transaction is aborted"). The fix is the canonical Django
  pattern — wrap the `create()` in its own `transaction.atomic()` **savepoint** so a failed create
  rolls back only the savepoint and the outer transaction stays usable. Same algorithm, same
  atomic-`F()`-increment + unique-constraint-as-retry-hinge design (EUW-9); only the savepoint
  boundary is added. Proven by `test_create_race_falls_back_to_an_atomic_increment`.
