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

The following are **RATIFIED** (DN-WCA-DESIGN approved as designed, 2026-06-27 — they now
bind Stage 3):

- **WCA-DESIGN-1 (RATIFIED) — token-carry mechanism (resolves OQ-WCA-2).** A **first-party,
  signed, source-only HTTP cookie** `widget_src` set on the click-through 302. Payload =
  `{v, src=<source app_id>, credited=[]}` signed via `django.core.signing` (tamper-evident; the
  signer timestamp + `loads(max_age=window)` *is* the window). `SameSite=Lax` (every post-click
  step is same-site first-party), `Secure`, `HttpOnly`, `Path=/`. *Rejected:* a query param
  (can't survive the 30-day gap; forgeable/leaky — A6).
- **WCA-DESIGN-2 (RATIFIED) — cross-domain identity dissolved (resolves OQ-WCA-3).** The marker
  is created and read **entirely first-party** on the platform origin; the third-party iframe
  never participates in attribution. *Rejected:* third-party cookie / device fingerprint /
  cross-site id (unnecessary **and** the covert per-person tracking R1/AC4 forbid — A1).
- **WCA-DESIGN-3 (RATIFIED) — no PII processed → aggregate-only feasible (resolves OQ-WCA-4).**
  The marker's entire content is a public app-id + bookkeeping flags; it is never joined to a
  person and builds **no** per-person profile (AC4 / M5=0 by construction). Aggregate-only is
  **feasible** — it does **not** return to the user as a forced relaxation. **Honest residual:**
  "no consent banner" rests on the chosen no-PII/purpose-limited posture (WCA-3); the strict
  ePrivacy "non-essential cookie needs consent regardless of PII" reading is a **legal/policy
  judgment**, surfaced to the approver (DN-WCA-DESIGN), with a **one-call consent gate** designed
  in as the contingency. **Not silently relaxed.**
- **WCA-DESIGN-4 (RATIFIED) — storage.** A **separate** `widget_conversion_count` daily-rollup
  table keyed `(app_id, kind∈{follow,account}, count_date)` — same no-`user`/no-IP/no-score
  structural shape as `widget_reach_count` — plus a **shared `_increment_daily(model, app_id,
  kind)`** helper extracted from the existing reach writer (reuse the concurrency-hard part, not
  the table). *Rejected:* extending `WidgetEventKind` on the reach table (conflates "distinct
  facts, distinct counts", breaks design-for-deletion — A3).
- **WCA-DESIGN-5 (RATIFIED) — touch model + window + dedup (refines WCA-2).** **Last-touch** by
  cookie overwrite-on-click; **bounded window** enforced twice (cookie max-age + signing
  max_age); **dedup via the `credited` set** in the marker (per-browser, at-most-once per kind) —
  no per-person key exists, so cross-browser repeats are an accepted bounded over-count on a
  firewalled metric, reported via M3. *Rejected:* a server-side per-person row (the PII surface
  WCA-3 forbids — A2).
- **WCA-DESIGN-6 (RATIFIED) — conversion hooks.** **Explicit, fail-soft view hooks** at
  `subscriptions.views.follow` (only when `follow_app` returns `created=True`) and
  `accounts.views.register` (only the 202 new-account path), each calling a single `apps/widget`
  entry point and wrapped so attribution **never** breaks a follow / a registration / the reach
  counts (AC6). The conversion's own corpus event (`record_subscribe`) is **untouched** (AC5).
  *Rejected:* middleware / Django `post_save` signal (magic + no `request`/`response` for the
  cookie — A4).
- **WCA-DESIGN-7 (RATIFIED) — account credited at the register act.** Credit the `account`
  conversion at the **register POST** the brief names (marker reliably co-located in the
  submitting browser), accepting that it counts the registration act (not necessarily a confirmed
  account) and loses cross-device cases. *Rejected for now:* crediting at `verify` (confirmed but
  email-link often opens in a different browser → worse coverage — A5). **Flagged to revisit on
  real data.**
- **WCA-DESIGN-8 (RATIFIED) — dashboard surface (AC3).** Extend the existing Screen-B widget
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

### DN-WCA-DESIGN approved → Stage 2→3 hand-off (Software Architect, 2026-06-27)

User answered **"accept and proceed"** = approve [DESIGN.md](DESIGN.md) **as designed**. Actions
taken (hand-off only — one persona/session, no Stage-3 work started):

- **Ratified** [DESIGN.md](DESIGN.md) (status → APPROVED) and promoted **WCA-DESIGN-1…8 →
  RATIFIED** (binding for Stage 3).
- **ePrivacy residual resolved as recommended:** **no consent banner** under the no-PII WCA-3
  posture (WCA-DESIGN-3's confirmed "no personal data processed" premise). The strict-ePrivacy
  one-call **consent gate** stays a **documented contingency** in the design, to revisit **with
  counsel before any EU production launch** — not built now, not silently relaxed.
- Marked **OQ-WCA-2 / OQ-WCA-3 / OQ-WCA-4 → RESOLVED** in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
- Reuses **D-3/D-4/D-6/D-7/D-8/D-9/D-10 — no new global ADR.**

Set `Stage: 3-plan` + Persona **Planner / Tech Lead** in [CONTROL.md](../../CONTROL.md); cleared
DN-WCA-DESIGN; updated [INDEX.md](../INDEX.md) (→ `3-plan`). Handed to the **Planner / Tech Lead**
to decompose [DESIGN.md](DESIGN.md) into [TASKS.md](TASKS.md) — **risk-front-load the firewall
proof + the signed source-marker codec** (the EUW T-02 precedent: prove the AC6 structural
firewall — `apps/widget` imports no `signals`, AST test extends to the new `source` module — and
the `widget_src` sign/verify/`credited`-dedup codec before any HTTP wiring).

## Stage 4 — Senior Engineer (build, 2026-06-27)

Built **T-01…T-08** from the APPROVED [DESIGN.md](DESIGN.md) + [TASKS.md](TASKS.md); risk
front-loaded as planned (the firewall proof + the concurrency writer at T-03, the codec at T-04,
before any HTTP wiring). Full suite green; [TEST_PLAN.md](TEST_PLAN.md) maps every AC1–AC6.
Implementation notes (no scope/interface change — the ratified WCA-DESIGN-1…8 all stand):

- **WCA-IMPL-1 — `Secure` follows the platform cookie policy, not a flat literal.** DESIGN §3.1
  lists `Secure` for `widget_src`. Implemented as `secure=settings.SESSION_COOKIE_SECURE` (the
  platform's existing `not DEBUG` policy that already governs the session/CSRF cookies), so the
  marker is stored over plain HTTP in **local dev** (the only current release target) and
  required-HTTPS in production. A flat `Secure=True` would make the cookie undeliverable in dev.
  Matches existing conventions (CLAUDE.md §5.5); one source of truth for "are cookies secure here".

- **WCA-IMPL-2 — signature age read via the signer's own timestamp for the remaining-window
  re-issue.** DESIGN §3.4 anchors the re-issued cookie to the original click via
  `Max-Age = window − signature_age`. `django.core.signing.loads` validates `max_age` but discards
  the timestamp, so `source._signature_age_seconds` strips the HMAC and parses the signer's base62
  timestamp (called only on the credit/re-issue path, on an already-integrity-checked value). The
  literal signer-timestamp mechanism is **correct** for exactly two one-time-creditable kinds: the
  first credit's re-issue anchors the cookie to `click+window`, and the second credit lands inside
  that browser-enforced window; the marker is fully credited by then, so a later over-extension is
  unobservable. (Analyzed and confirmed during the build — no stored click-time needed; AC4 payload
  stays `{v, src, credited}`.)

- **WCA-IMPL-3 — counter mapping for the "no credit" branches.** A live marker for a *different*
  app (a follow of X with a marker for Y) counts `WIDGET_CONVERSION_NO_SOURCE` (from that
  conversion's standpoint there was no applicable widget source — the M3 denominator). An
  *already-credited* kind (per-marker dedup, R4) is a **silent** no-op (no counter) — it is not a
  coverage miss, so counting it would distort M3.

No new global ADR (reuses D-3/D-4/D-6/D-7/D-8/D-9/D-10 + the carried-in AC6 firewall). New shared
code recorded in [CODEMAP.md](../../CODEMAP.md); the `apps/widget` README names both tables + the
new `rollup`/`source` modules.
