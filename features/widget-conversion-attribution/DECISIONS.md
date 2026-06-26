# DECISIONS — widget-conversion-attribution

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Stage 0 — Coordinator (feature created, 2026-06-26)

**Choice:** Scaffold `widget-conversion-attribution` as a follow-up feature to pick up
the deferred **M3 / OQ-EUW-5** per-account conversion attribution from
[embeddable-update-widget](../embeddable-update-widget/) (DESIGN §11, EUW-10). The widget
shipped **reach** (impressions + click-throughs); *which signup came from which click* was
deferred because it is a materially harder problem (anonymous token-carry across
sessions/domains, cookie consent, cross-domain identity, no-PII posture).

**Why:** User-directed (Coordinator decision, 2026-06-26) — with the developer wedge
([D-10](../../DECISIONS.md)) complete, deepening the just-shipped widget's measurement is
the chosen next step over activating the density-gated network features or starting the
D-9 monetization surface. The deferral was logged traceably (OQ-EUW-5), so this is the
named follow-up, not new scope invented out of nowhere.

**Rejected (this turn):** activating `weekly-digest` / `editorial-curation-tools` (held
until per-niche density, D-10); starting `D-9` promotion-placements monetization (the
other live option — deferred, not dropped).

**Constraints carried in (not yet decisions — for the Product Analyst / Architect):**
- Must preserve the **AC6 firewall** — no widget interaction may confer D-8 curated-rating
  eligibility (M5=0); `apps/widget` imports nothing from `signals`, structural by absence.
- Must preserve the **no-PII posture** of the widget surface.

No new global ADR at scaffold time. Stage advanced to `1-define`; handed to the Product
Analyst to author [FEATURE_BRIEF.md](FEATURE_BRIEF.md).

## Stage 1 — Product Analyst (brief authored, 2026-06-26)

Authored [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (5 stories / AC1–AC6 / M1–M6); grounded
every dependency in code (widget click-through 302, `follow_app`/register conversions,
the `record_subscribe` corpus event, the shipped reach slot, the `signals`-import
firewall). Money-buys-position test → **PASS**. Left the token-carry **mechanism** OPEN
for Stage 2 (OQ-WCA-2…4) — did not guess architecture. Raised **DN-WCA-BRIEF** (approve
brief + the three scoping calls below) in [CONTROL.md](../../CONTROL.md); **stopped at the
gate** (no Stage advance until approved).

The following are **RESOLVED** (DN-WCA-BRIEF approved as recommended, 2026-06-26 — they
now bind Stage 2):

- **WCA-1 (RESOLVED) — conversion set.** Count **both** a new **follow** of the
  clicked-through app (primary) and a new **account registration** (secondary), as
  distinct counts. *Rejected for now:* follow-only / account-only (narrower; loses half
  the funnel). Rationale: the wedge's payoff is turning a developer's audience into
  followers, but a brand-new account is the broader platform conversion worth seeing too.
- **WCA-2 (RESOLVED) — attribution model + window.** **Last-touch** within a bounded,
  configurable **~30-day** window. *Rejected for now:* first-touch (credits the wrong
  click when a visitor returns via a later widget click); unbounded window (stale,
  noisy). Rationale: last-touch + a bounded window is the boring, defensible default;
  the value is config (§5.2 design-for-change).
- **WCA-3 (RESOLVED) — privacy/tracking posture.** **Aggregate-only, source-keyed** — no
  per-person cross-site profile, so no PII is processed and no consent banner is required;
  the source marker is transient and identifies the widget, not the person. *Rejected for
  now:* consented per-person attribution (richer, but creates a PII-handling + consent
  surface that contradicts the carried-in no-PII posture). Rationale: holds AC4 / M5 = 0
  by construction. If Stage 2 finds aggregate-only infeasible, it returns as a decision,
  not a silent relaxation.

Reuses D-3/D-4/D-6/D-7/D-8 + the carried-in AC6 firewall — **no new global ADR**.

## Stage 2 — Software Architect (DESIGN drafted, 2026-06-27)

Drafted [DESIGN.md](DESIGN.md) via the 14-step protocol against the APPROVED brief, surveying
the upstream code (`apps/widget` views/attribution/selectors/models, `subscriptions.services.
follow_app`, `accounts.views.register`, `dashboard.reception`, `core.config`/`ratelimit`/
`observability`, the firewall AST test). **Resolved all three Stage-2 OQs.** The pivotal finding:
the widget click-through (`GET /widget/<id>/view`) is a **`target="_top"` top-level navigation
onto the platform's own origin**, so any source marker set on its 302 is **first-party from
birth** — which dissolves the cross-domain-identity problem (OQ-WCA-3) and makes the no-PII,
cookieless-cross-domain posture *achievable* rather than the hard problem the brief flagged
(§8 [unverified] → now verified in design).

The following are logged **PROPOSED** (ratify on DN-WCA-DESIGN approval; binding for Stage 3):

- **WCA-DESIGN-1 (PROPOSED) — token-carry mechanism (resolves OQ-WCA-2).** A **first-party,
  signed, source-only HTTP cookie** `widget_src` set on the click-through 302. Payload =
  `{v, src=<source app_id>, credited=[]}` signed via `django.core.signing` (tamper-evident; the
  signer timestamp + `loads(max_age=window)` *is* the window). `SameSite=Lax` (every post-click
  step is same-site first-party), `Secure`, `HttpOnly`, `Path=/`. *Rejected:* a query param
  (can't survive the 30-day gap; forgeable/leaky — A6).
- **WCA-DESIGN-2 (PROPOSED) — cross-domain identity dissolved (resolves OQ-WCA-3).** The marker
  is created and read **entirely first-party** on the platform origin; the third-party iframe
  never participates in attribution. *Rejected:* third-party cookie / device fingerprint /
  cross-site id (unnecessary **and** the covert per-person tracking R1/AC4 forbid — A1).
- **WCA-DESIGN-3 (PROPOSED) — no PII processed → aggregate-only feasible (resolves OQ-WCA-4).**
  The marker's entire content is a public app-id + bookkeeping flags; it is never joined to a
  person and builds **no** per-person profile (AC4 / M5=0 by construction). Aggregate-only is
  **feasible** — it does **not** return to the user as a forced relaxation. **Honest residual:**
  "no consent banner" rests on the chosen no-PII/purpose-limited posture (WCA-3); the strict
  ePrivacy "non-essential cookie needs consent regardless of PII" reading is a **legal/policy
  judgment**, surfaced to the approver (DN-WCA-DESIGN), with a **one-call consent gate** designed
  in as the contingency. **Not silently relaxed.**
- **WCA-DESIGN-4 (PROPOSED) — storage.** A **separate** `widget_conversion_count` daily-rollup
  table keyed `(app_id, kind∈{follow,account}, count_date)` — same no-`user`/no-IP/no-score
  structural shape as `widget_reach_count` — plus a **shared `_increment_daily(model, app_id,
  kind)`** helper extracted from the existing reach writer (reuse the concurrency-hard part, not
  the table). *Rejected:* extending `WidgetEventKind` on the reach table (conflates "distinct
  facts, distinct counts", breaks design-for-deletion — A3).
- **WCA-DESIGN-5 (PROPOSED) — touch model + window + dedup (refines WCA-2).** **Last-touch** by
  cookie overwrite-on-click; **bounded window** enforced twice (cookie max-age + signing
  max_age); **dedup via the `credited` set** in the marker (per-browser, at-most-once per kind) —
  no per-person key exists, so cross-browser repeats are an accepted bounded over-count on a
  firewalled metric, reported via M3. *Rejected:* a server-side per-person row (the PII surface
  WCA-3 forbids — A2).
- **WCA-DESIGN-6 (PROPOSED) — conversion hooks.** **Explicit, fail-soft view hooks** at
  `subscriptions.views.follow` (only when `follow_app` returns `created=True`) and
  `accounts.views.register` (only the 202 new-account path), each calling a single `apps/widget`
  entry point and wrapped so attribution **never** breaks a follow / a registration / the reach
  counts (AC6). The conversion's own corpus event (`record_subscribe`) is **untouched** (AC5).
  *Rejected:* middleware / Django `post_save` signal (magic + no `request`/`response` for the
  cookie — A4).
- **WCA-DESIGN-7 (PROPOSED) — account credited at the register act.** Credit the `account`
  conversion at the **register POST** the brief names (marker reliably co-located in the
  submitting browser), accepting that it counts the registration act (not necessarily a confirmed
  account) and loses cross-device cases. *Rejected for now:* crediting at `verify` (confirmed but
  email-link often opens in a different browser → worse coverage — A5). **Flagged to revisit on
  real data.**
- **WCA-DESIGN-8 (PROPOSED) — dashboard surface (AC3).** Extend the existing Screen-B widget
  slot with a **conversions funnel stage** (follows / accounts) + the **M2 rate derived at
  display**; the reach integers are **untouched** (separate tables = one source of truth);
  fail-soft together via the existing `DASHBOARD_WIDGET_DEGRADED`. Screen-A my-apps list stays
  reach-only (noted, not built — avoids an N+1).

The dependency graph stays a **DAG** (`subscriptions → widget`, `accounts → widget`; `apps/widget`
imports neither, nor `signals`), so the **AC6 firewall stays structural** (the AST test extends
to the new `source` module). Reuses D-3/D-4/D-6/D-7/D-8/D-9/D-10 — **no new global ADR**. Honest
rollback note (DU-REL-1): `subscriptions`/`accounts`/`dashboard` now import `widget`, so rollback
= a single `git revert` of the build commit (+ optional table drop). **Raised DN-WCA-DESIGN;
stopped at the gate** (one persona/session — no Stage advance until approved).
