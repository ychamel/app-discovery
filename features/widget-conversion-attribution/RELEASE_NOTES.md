# RELEASE_NOTES — widget-conversion-attribution

*Stage 5 artifact (Release Engineer). Status: **RELEASED to local/dev** 2026-06-27.
Production promotion + the live-metrics window defer until a prod target/traffic exists (as
the prior twelve features).*

Traces to [DESIGN §10 Operations / §14 Rollout](DESIGN.md) · [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
success metrics M1–M6 · [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC6).

---

## 1. What changed

The developer-wedge funnel is now **closed end to end**: impression → click → **conversion**.
A widget **click-through** that later turns into a real outcome — a new **follow** of the
clicked-through app, or a new platform **account** — is now **credited back to the widget
source** that drove it, and the developer sees that conversion count on their dashboard beside
the reach the [embeddable-update-widget](../embeddable-update-widget/) already showed.

The mechanism is a **first-party, signed, source-only cookie** `widget_src`. The widget's "view
on platform" control is a `target="_top"` top-level navigation onto the **platform** origin, so
the click-through is **first-party from birth** — there is no third-party iframe boundary to
cross, no tracking cookie, no fingerprint, no cross-site identifier. On that 302 we set a signed
cookie carrying only `{version, source app-id, credited-kinds}` — **a public app identifier and
two bookkeeping fields, never a person**. When the anonymous visitor later follows the app or
registers, a thin **fail-soft hook** reads the live marker, enforces the bounded window + dedup,
and bumps an **aggregate, source-keyed** counter. No per-person profile is ever built.

Two integrity properties carried in from the widget feature are **preserved structurally**:

- **The AC6 firewall (R1, vision §5.4/§5.6 — M5 = 0).** A widget interaction is a **non-curated
  surface** and can never confer [D-8](../../DECISIONS.md) curated-rating eligibility or move the
  Quality Score. `apps/widget` **imports nothing from `apps/signals`** (AST-enforced; the test
  now covers the new `source` and `rollup` modules too), so no attribution path can write a
  corpus row. A *credited* follow writes **the same single** `record_subscribe` event as an
  un-attributed follow — attribution **adds nothing** to the corpus (AC5). M5 = 0 **by
  construction**, not by measurement.
- **No PII (AC4).** The marker payload has nowhere to put a person (`{v, src, credited}` only),
  and the new `widget_conversion_count` table has **no `user`/IP/UA/referrer/device/score
  column** — the no-PII posture is structural in both the cookie format and the schema.

**Shipped components** (all in `apps/widget`, plus two one-line hooks + an additive dashboard
slot):

- **NEW table `widget_conversion_count`** ([`models.py`](../../apps/widget/models.py),
  migration `widget/0002_widgetconversioncount`; UUID pk; soft [D-6](../../DECISIONS.md) `app_id`
  = the credited **source** app, no DB FK so a later withdrawal doesn't cascade-erase history;
  `kind ∈ {follow, account}`; `count_date`; `count`; unique `(app_id, kind, count_date)` +
  matching index; **no person/score column**). Same shape as `widget_reach_count`, **separate
  table** — distinct facts, distinct counts (brief §3); makes the feature **deletable** by
  dropping one table.
- **NEW `kinds.WidgetConversionKind`** ([`kinds.py`](../../apps/widget/kinds.py)) — the closed
  conversion vocabulary `{follow, account}`, distinct from the reach `WidgetEventKind`.
- **NEW `rollup._increment_daily(model, app_id, kind)`** ([`rollup.py`](../../apps/widget/rollup.py))
  — the one concurrency-correct daily increment (atomic `F()+1` + create-race retry in a nested
  `transaction.atomic()` savepoint, the **EUW-IMPL-1** pattern) **extracted** from the reach
  writer and now shared by both the reach and the conversion writers. The hard part is reused,
  not duplicated (the reach writer's public surface is unchanged).
- **NEW `attribution.record_widget_conversion(app_id, kind)`** — the single conversion writer
  (calls `_increment_daily`; trusts the marker's self-signed `app_id`; raises on DB error).
- **NEW `source.py`** ([`source.py`](../../apps/widget/source.py)) — the **marker codec + credit
  logic**, the only module that knows the cookie format:
  - `set_marker(response, source_app_id)` — signs `{v:1, src, credited:[]}` via
    `django.core.signing` and sets `widget_src` (`Max-Age` = window, `SameSite=Lax`,
    `Secure`=`SESSION_COOKIE_SECURE` (**WCA-IMPL-1**), `HttpOnly`, `Path=/`); overwrites any
    prior marker (**last-touch**, no comparison logic).
  - `attribute_follow(request, response, *, followed_app_id)` / `attribute_account(request,
    response)` — decode the live marker, enforce **window** (the signature's own `max_age` — one
    source of truth, no hand-rolled timestamp) + **dedup** (the per-marker `credited` set, then
    re-issue the cookie with the **remaining** window — **WCA-IMPL-2**), and credit once. A
    missing / malformed / expired / tampered / mismatched marker is a **normal "no source"
    no-op** with a counter, never an error to the visitor (AC2 — no fabricated links).
- **NEW `selectors.widget_conversions[_for_apps]`** ([`selectors.py`](../../apps/widget/selectors.py))
  — windowed grouped `SUM(count) … GROUP BY kind`, zero-filled, **no N+1** (one bulk query
  regardless of app count), frozen `WidgetConversion{follows, accounts}` DTO — the sibling of the
  reach reads.
- **Four `WIDGET_CONVERSION_*` counters** ([`observability.py`](../../apps/core/observability.py))
  + **one config tunable** `widget_attribution_window_days()` (default **30**, in `validate_all`,
  loud at startup) — one source of truth for the cookie max-age, the signing max_age, and the
  remaining-window re-issue.

- **TWO one-line, fail-soft conversion hooks** (the only new `→ widget` import edges, each
  wrapped so a fault never breaks the outcome — AC6):
  - [`subscriptions.views.follow`](../../apps/subscriptions/views.py) — on a **genuinely new**
    follow (`created == True`), `source.attribute_follow(..., followed_app_id=app_id)`. The
    follow's own state + its `record_subscribe` corpus event are already committed and untouched.
  - [`accounts.views.register`](../../apps/accounts/views.py) — on the **202 new-account** path
    only (not 400/409/503), `source.attribute_account(...)` (**WCA-DESIGN-7**: credited at the
    register act where the marker is co-located; the confirmed-account / cross-device nuances are
    documented limitations, not correctness bugs).

- **ONE additive, fail-soft dashboard change** ([`dashboard/reception.py`](../../apps/dashboard/reception.py)
  + `app_reception.html`): the existing off-platform widget slot (Screen B) gains a **conversions
  funnel stage** — `Follows from widget`, `New accounts from widget`, and a **derived M2 rate**
  (`(follows+accounts) ÷ click-throughs`, computed at display, never stored). Reach numbers are
  **byte-identical** to before (separate tables — one source of truth per fact). The whole widget
  slot (reach + conversions) degrades **together**, fail-soft, via the existing
  `DASHBOARD_WIDGET_DEGRADED`; the core on-platform reception keeps its loud-500 posture.

**Verified before ship (this session, independently re-run):** **962 tests** green (+69 over the
893 baseline), `ruff check .` clean, `python manage.py check` no issues, `makemigrations
--check` → no drift; `widget/0002` reversible (down→up rehearsed on the live PostgreSQL DB — see
§5).

## 2. Who is affected

- **Developers** (the `developer` role) with an **accepted** app — they now see, beside the
  off-platform reach already shipped, **how many of those click-throughs converted** into follows
  of their app and new platform accounts, plus the conversion rate. The payoff of the wedge made
  visible.
- **End users** — **no change they can perceive.** Attribution is a silent first-party side
  effect: a signed cookie set on the platform's own redirect, read once at a conversion. Nothing
  is shown to or asked of the converting visitor (no banner — §7), the follow and registration
  flows are unchanged, and no per-person profile is built.
- **No one else, and no regression.** All attribution lives in `apps/widget`; the two hooks are
  fail-soft and additive (a fault logs + counts `WIDGET_CONVERSION_DEGRADED` and the
  follow/registration completes normally); the dashboard change is additive + fail-soft. A
  conversion with no live marker simply isn't credited (`WIDGET_CONVERSION_NO_SOURCE`).

## 3. How to use it

Nothing new to install or embed — the same one-line `<iframe>` from
[`apps/widget/README.md`](../../apps/widget/README.md) that already shipped now also drives
conversion attribution automatically. A developer just keeps the widget in their app; when a
visitor clicks "view on platform" and later follows the app or signs up (within the
30-day window, `widget_attribution_window_days()`), it shows up under **Conversions** in the
off-platform widget slot of their dashboard. An app with reach but no conversions yet shows a
truthful `0 / 0`, not a hidden state.

## 4. Operator rollout

- **Stack:** reuse **D-4** (Python/Django + PostgreSQL, server-rendered templates) — no new
  global ADR. All attribution code lives in `apps/widget`.
- **Activation = one migration + additive code, all in place** (DESIGN §14): the surface is
  **inert until the build lands** and behaviorally invisible to end users.
  1. Migration `widget/0002_widgetconversioncount` (the new table). **Deploy the migration before
     the code goes live** (the writer needs the table).
  2. The `set_marker` call on the click-through 302 + the two fail-soft conversion hooks + the
     dashboard slot extension + the `core` additions (one `widget_attribution_window_days`
     tunable, four `WIDGET_CONVERSION_*` counters).
- **No feature flag, no data backfill.** All changes are additive; no existing contract altered;
  attribution is best-effort and fail-soft, so there is nothing to gate behind a flag (DESIGN §14).
- **Promotion table:**

  | Stage | Target | Promotion criterion |
  |-------|--------|---------------------|
  | local/dev | **done (2026-06-27)** | 962 tests green; `widget/0002` reversible; rollback rehearsed (§5) |
  | internal | _deferred_ | `WIDGET_CONVERSION_DEGRADED` ≈ 0 and `DASHBOARD_WIDGET_DEGRADED` flat for the soak window; M3 coverage (`ATTRIBUTED ÷ (ATTRIBUTED+NO_SOURCE+EXPIRED)`) sane |
  | prod (% → full) | _deferred_ | **M5 = 0** (structural, asserted); `WIDGET_CONVERSION_DEGRADED` below threshold for the soak window; M1 (credits by kind) + M2 (rate) visible — **deferred: no prod target/traffic** |

## 5. Rollback (rehearsed)

Like `developer-updates` and `embeddable-update-widget`, this feature **touches closed apps** —
`subscriptions`, `accounts`, and `dashboard` now each import `apps/widget`. So rollback is **not**
a single line-removal: pulling a hook by hand would leave a dangling import. **The clean, atomic
operational rollback is `git revert` of the build commit** (`5df8daa` *widget-conversion-attribution/
development*) — the **DU-REL-1** precedent — which drops the two hooks **and** the dashboard slot
**and** the new `apps/widget` modules **and** the migration together in one reversible step. The
manual equivalent, if reverting by hand:

1. **subscriptions / accounts** — remove the `_attribute_*_fail_soft` call + its
   `from apps.widget import source` import from [`subscriptions/views.py`](../../apps/subscriptions/views.py)
   and [`accounts/views.py`](../../apps/accounts/views.py).
2. **dashboard** — revert the conversion funnel stage in
   [`dashboard/reception.py`](../../apps/dashboard/reception.py) + `app_reception.html` (the reach
   slot stays; only the conversion lines are removed).
3. **widget** — remove the `set_marker` call from `views.py`, and the new `source` / `rollup` /
   `kinds` modules + the conversion writer/selectors, plus the additive `core`
   `widget_attribution_window_days` tunable / `WIDGET_CONVERSION_*` counters.
4. **Data (optional)** — `widget_conversion_count` may stay inert (PII-free aggregate counts) or
   be dropped: `python manage.py migrate widget 0001`.

→ Conversion attribution is instantly gone; the follow, registration, reach counts, and the
widget reach slot all return to their pre-feature behavior; the corpus and catalogue are
untouched.

**Who can trigger it:** any operator with repo/deploy access (`git revert 5df8daa` + redeploy;
the optional DB step needs no data coordination — the table holds only aggregate conversion
counts).

**Rehearsal (2026-06-27, performed this session — on the live local PostgreSQL cluster):**
- **Up:** full suite **962 green**; `ruff` clean; `manage.py check` clean; `makemigrations
  --check` no drift.
- **Migration down→up:** `migrate widget 0001` unapplies `0002_widgetconversioncount` cleanly;
  `migrate widget 0002` re-applies it cleanly (the down-migration is sound).
- **Operational rollback:** `git revert --no-commit 5df8daa` removed the `source`/`rollup`/`kinds`
  modules, the migration, the two hooks, **and** the dashboard slot in one step; **`manage.py
  check` then passed with no dangling `subscriptions`/`accounts`/`dashboard → widget` import**
  (the load-bearing DU-REL-1 property — proven, not assumed). Restored to `5df8daa`
  (`git status` clean).

## 6. Monitoring — metrics → signals → alert

Four counters in [`apps/core/observability.py`](../../apps/core/observability.py):

| Counter | Feeds | Notes |
|---------|-------|-------|
| `WIDGET_CONVERSION_ATTRIBUTED{kind}` | **M1** (headline payoff) / the dashboard number | a conversion was credited to a widget source |
| `WIDGET_CONVERSION_NO_SOURCE` | **M3** denominator | a conversion ran with no live marker (expected; the honest coverage floor) |
| `WIDGET_CONVERSION_EXPIRED` | **M3** + AC2 evidence | a marker existed but was outside the window (proves the window holds, no fabrication) |
| `WIDGET_CONVERSION_DEGRADED` | **actionable — the one alert** | an attribution read/write failed → still fail-soft (the outcome completed) but a credit was lost; a rising rate is the Sev signal (**M6**) |

- **The one actionable signal is `WIDGET_CONVERSION_DEGRADED`.** Everything else is an
  expected-trend or coverage counter. `DASHBOARD_WIDGET_DEGRADED` (reused, not re-added) covers
  the dashboard slot.
- **M1** = `WIDGET_CONVERSION_ATTRIBUTED` by kind. **M2** (rate) = dashboard-derived
  `(follows+accounts) ÷ click_throughs`. **M3** (coverage) =
  `ATTRIBUTED ÷ (ATTRIBUTED + NO_SOURCE + EXPIRED)` — a mechanism-health signal, honestly lossy
  rather than a misleading per-app ratio.
- **M4** (firewall conferred eligibilities) and **M5** (PII fields) target = **0**, enforced
  **structurally** — `apps/widget` imports no `signals` (AST-asserted), the schema has no person
  column. Asserted test invariants ([TEST_PLAN.md](TEST_PLAN.md) AC4/AC5), not runtime gauges —
  no "must-stay-0" alert is needed because no path can break them.
- **M6** = `WIDGET_CONVERSION_DEGRADED` rate; sustained nonzero ⇒ attribution silently lossy ⇒ alert.

## 7. Known limitations

- **No live metrics yet** — local/dev only, no prod traffic; M1–M6 are instrumented but the
  measurement window opens when a prod target/traffic exists (the prior-feature pattern).
- **Cross-device under-attribution** — if a visitor clicks the widget on one device and
  converts on another, the marker isn't present → that conversion isn't credited. It never
  produces a *wrong* attribution (AC2), and the loss is reported via M3 coverage. The cross-device
  fix is a per-person store (DESIGN §11 A2), rejected on no-PII grounds.
- **Register-act vs confirmed account** — an account is credited at the register POST, which may
  not confirm → slight over-count of accounts. Bounded (rate-limited register; one per marker)
  and reported (M3). **Flagged to revisit on real data** (WCA-DESIGN-7, DESIGN §14): switching to
  verify-time is a localized change.
- **No cross-browser dedup** — aggregate-only holds no person key, so repeats by one human across
  browsers aren't dedup'd. The metric is **firewalled** (M5 = 0), so the worst case is vanity
  inflation, never ranking manipulation.
- **30-day window is a default, not a tuning** — `widget_attribution_window_days()` = 30 is a
  config value; M3 coverage on real data will tell us whether it's too short/long (DESIGN §14).
- **ePrivacy consent is a deferred legal judgment, not an architecture gap** — the marker
  processes **no PII**, so under the no-PII WCA-3 posture **no consent banner** ships. A maximalist
  ePrivacy reading can attract a consent requirement for a non-essential cookie regardless of PII;
  that is a legal call, surfaced not buried. The design is built so that **if counsel later
  requires consent for the EU**, gating `source.set_marker` behind a consent check is a
  **one-call change at a single site** with no schema impact. **Revisit with counsel before any
  EU production launch.**

---

*Reuses **D-3** (roles), **D-4** (stack), **D-6** (accepted-only / soft `app_id`), **D-7**
(corpus — *not* extended; the firewall is by absence), **D-8** (the curated-rating gate it stays
outside), **D-9** (free tool, non-curated surface), **D-10** (developer wedge) — no new global
ADR. Feature-local decisions WCA-DESIGN-1…8 + impl notes WCA-IMPL-1/2/3 (**BUILT**) in
[DECISIONS.md](DECISIONS.md).*
