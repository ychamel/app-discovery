# TASKS — widget-conversion-attribution

*Stage 3 (Planner / Tech Lead). Ordered, independently verifiable work items. **Status:
READY** — decomposed from the **APPROVED** [DESIGN.md](DESIGN.md) (WCA-DESIGN-1…8 RATIFIED)
against the **APPROVED** [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1–AC6, M1–M6).*

**8 tasks, all S/M (no L).** Every design element maps to ≥1 task; every AC1–AC6 is
covered (map at the end). Sequencing: constants/config → schema → core logic →
interface/API → UI/telemetry → docs. **Risk is front-loaded:** the AC5 firewall proof +
the concurrency-correct conversion writer land at **T-03**, and the novel signed-cookie
`widget_src` sign/verify/`credited`-dedup codec at **T-04** — both **before any HTTP
wiring** (the `embeddable-update-widget` T-02 precedent the [CONTROL.md](../../CONTROL.md)
hand-off named).

Each task leaves the system green and releasable. Tests live with each task's DoD; the
Senior Engineer assembles them into `TEST_PLAN.md` (the Stage-4 artifact). No task
re-designs — any gap escalates via [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md), not a quiet fix.

---

## T-01 — Feature constants: conversion kinds, the window tunable, the metrics

**Description.** The additive constant/config substrate every later task references
(DESIGN §2 modules, §5.6, §10). Three small, independent additions:
- `apps/widget/kinds.py`: add a **new** closed enum `WidgetConversionKind(TextChoices)` =
  `{follow, account}`, **distinct** from `WidgetEventKind` (DESIGN §2). One source of truth
  for the conversion `kind` column + the writer + the selectors.
- `apps/core/config.py`: add `widget_attribution_window_days()` (default **30**,
  `_positive_int`, WCA-2) and register it in `validate_all()` so it is **loud at startup**
  (DESIGN §5.6). The one source of truth for cookie `Max-Age`, `signing` `max_age`, and the
  remaining-window re-issue.
- `apps/core/observability.py`: add the four `WIDGET_CONVERSION_*` constants —
  `ATTRIBUTED` (tags `kind`, M1), `NO_SOURCE` (M3 denom), `EXPIRED` (M3 + AC2),
  `DEGRADED` (the one alert, M6) — per the DESIGN §10 table. **No** new dashboard counter
  (reuse `DASHBOARD_WIDGET_DEGRADED`).

**Dependencies.** None.

**Definition of done.**
- `WidgetConversionKind.values == ["follow", "account"]`; it is a separate class from
  `WidgetEventKind` (no shared members).
- `config.widget_attribution_window_days()` returns 30 by default; an invalid override
  fails `validate_all()` at startup (mirror an existing `_positive_int` tunable test).
- The four metric constants exist with the DESIGN §10 string values.
- `ruff` + `manage.py check` clean; no migration drift.

**Size.** S.

**Files/areas.** `apps/widget/kinds.py`, `apps/core/config.py`,
`apps/core/observability.py`, their existing test modules.

---

## T-02 — The `widget_conversion_count` table (schema only)

**Description.** Add the conversion rollup table — DESIGN §6.1, the `WidgetReachCount`
shape, **separate table** (WCA-DESIGN-4). New `WidgetConversionCount` in
`apps/widget/models.py`: `id` (UUID pk), `app_id` (UUID, **soft D-6 ref, no FK** — the
**source** app credited), `kind` (`WidgetConversionKind`), `count_date` (date),
`count` (PositiveInt), `created_at`/`updated_at`. `UniqueConstraint(app_id, kind,
count_date)` (turns a concurrent create into the caught `IntegrityError` the writer
retries) + an index on the same triple. **Structurally no** `user`/IP/UA/referrer/device
column (AC4) and **no** score/weight/rank column (AC5/AC6) — illegal states unrepresentable
by absence, the `WidgetReachCount` precedent. Migration `widget/0002_widgetconversioncount`
(additive).

**Dependencies.** T-01 (the `WidgetConversionKind` enum).

**Definition of done.**
- Migration `widget/0002` applies; **up → down → up is clean** (drops cleanly — PII-free
  aggregates, no data coordination); `makemigrations --check` reports no drift.
- A schema/inspection test asserts the table has **no** person column (no user FK / IP / UA
  / referrer / device) and **no** score/rank column (AC4 / AC6 column-absence proof, M5 = 0
  by construction).
- The unique constraint + index exist with the DESIGN §6.1 names.
- `ruff` + `manage.py check` clean.

**Size.** S.

**Files/areas.** `apps/widget/models.py`, `apps/widget/migrations/`,
`apps/widget/tests/test_models.py`.

---

## T-03 — Shared daily-increment + the conversion writer + firewall proof

**Description.** Core logic, risk-front-loaded (DESIGN §6.2, §5.4, §3.1; WCA-DESIGN-4).
- **Extract** the existing `attribution._increment_today` body (atomic `F("count")+1` +
  nested-savepoint create-race retry, EUW-IMPL-1) into a **new** module
  `apps/widget/rollup.py` as `_increment_daily(model, app_id, kind)`, parameterized by the
  model class. Two concrete callers justify the extraction (not speculative). Repoint
  `record_widget_impression`/`record_widget_click_through` to it — the **reach writer's
  public surface is unchanged**.
- Add `attribution.record_widget_conversion(app_id, kind)` — the **single writer** of
  `widget_conversion_count`, delegating to `_increment_daily(WidgetConversionCount, …)`.
  Trusts a caller-validated `app_id` (the marker's `src`, a value we ourselves signed);
  **raises** on a DB error (the caller wraps fail-soft).
- **Firewall (AC5 / M5 = 0).** The new `rollup` and `attribution` code imports **nothing**
  from `apps.signals`. The existing AST test (`tests/test_imports.py`) auto-walks the
  package, so it must stay green with the new modules present — assert that explicitly.

**Dependencies.** T-01, T-02.

**Definition of done.**
- All existing reach tests (`test_attribution.py`) stay **green** — the reach writer
  behaves identically (extraction is behavior-preserving).
- Two concurrent first-of-day conversions for the same `(app_id, kind)` end at `count == 2`
  (create-race retry, reused pattern).
- `record_widget_conversion` raises on a forced DB error (not swallowed).
- `tests/test_imports.py` passes with `rollup` + `attribution` walked (no `signals` import).
- A credited conversion writes **zero** D-7 corpus rows and **no** per-person row (M5 = 0).
- `ruff` + `manage.py check` clean.

**Size.** M.

**Files/areas.** `apps/widget/rollup.py` (new), `apps/widget/attribution.py`,
`apps/widget/tests/test_attribution.py`, `apps/widget/tests/test_imports.py`,
new `apps/widget/tests/test_rollup.py`.

---

## T-04 — `widget.source`: the signed-cookie codec + credit logic

**Description.** The new core surface and the highest-novelty module — DESIGN §5.1, §3
(WCA-DESIGN-1/2/3/5). New `apps/widget/source.py`, the **only** module that knows the
cookie format:
- `set_marker(response, source_app_id)` — sign `{"v":1,"src":<app_id>,"credited":[]}` with
  `django.core.signing.dumps` and set `widget_src` with `Max-Age = window×86400`,
  `SameSite=Lax`, `Secure`, `HttpOnly`, `Path=/`. **Overwrites** any prior marker
  (last-touch by construction). Pure cookie write, no DB.
- `attribute_follow(request, response, *, followed_app_id)` — load the marker
  (`signing.loads(value, max_age=window_seconds)`); credit a FOLLOW **iff** `src ==
  followed_app_id` **and** FOLLOW not in `credited`; on credit call
  `record_widget_conversion(src, FOLLOW)`, add `"follow"` to `credited`, and **re-issue**
  the cookie with `Max-Age = remaining = window − signature_age` (DESIGN §3.4 — keeps the
  window anchored to the click; if `remaining ≤ 0`, expired, don't re-issue). No marker /
  expired / mismatch / already-credited → **no-op** + the matching ops counter
  (`NO_SOURCE`/`EXPIRED`). Emits `WIDGET_CONVERSION_ATTRIBUTED` (tag `kind`) on credit.
- `attribute_account(request, response)` — same shape, **not** app-scoped (an account is
  platform-wide; credit the live marker's `src`), dedup via `"account"` in `credited`.
- A missing/malformed/expired/tampered/version-skew marker is a **normal "no source"**
  outcome (no-op + counter), never an error. A DB write error **raises** to the caller.
- Imports **nothing** from `apps.signals` (firewall, auto-covered by the AST test).

**Dependencies.** T-01 (window tunable + metrics), T-03 (`record_widget_conversion`).

**Definition of done.** Unit tests (DESIGN §12, "each module in isolation"):
- **Round-trip**: a marker set by `set_marker` decodes to the right `src`/`credited`.
- **Tamper**: an edited cookie → `BadSignature` → "no source" no-op + `NO_SOURCE`.
- **Expiry**: a signature older than `window` (`signing` `max_age` elapsed) → `EXPIRED`
  no-op (not credited — AC2).
- **Version skew**: `v:2` (unknown) → "no source" no-op.
- **Mismatch**: marker `src == Y`, `attribute_follow(followed_app_id=X)` → not credited.
- **Credit + dedup**: first follow credits once (`record_widget_conversion` called,
  `ATTRIBUTED` counted, `credited` now `["follow"]`); a second follow in the same browser
  within the window → **no-op** (per-marker dedup, R4); `account` is independently
  creditable once.
- **Remaining-window re-issue**: after a credit the re-issued cookie's `Max-Age` ≈
  `window − age`, not a full reset (the window stays anchored to the click).
- A forced `record_widget_conversion` DB error **propagates** (not swallowed).
- `set_marker` cookie attributes match (`SameSite=Lax`, `Secure`, `HttpOnly`, `Path=/`).
- `test_imports.py` green with `source` walked; `ruff` + `check` clean.

**Size.** M.

**Files/areas.** `apps/widget/source.py` (new), new `apps/widget/tests/test_source.py`.

---

## T-05 — Arm the marker on the click-through 302

**Description.** Wire `set_marker` into the one first-party touchpoint — DESIGN §5,
§2 diagram, §9 (WCA-DESIGN-1/6). Modify `widget.views.widget_view_redirect`: after building
the server-derived 302 to `pages:app-page`, call `source.set_marker(response, app_id)`
wrapped **fail-soft** (the existing `_count_fail_soft` discipline — on error: log +
`WIDGET_CONVERSION_DEGRADED`, return the 302 unaffected). The redirect target stays
server-derived (no open redirect; the marker never influences it).

**Dependencies.** T-04.

**Definition of done.**
- A `GET /widget/<id>/view` response carries a signed `widget_src` cookie with the DESIGN
  §3.1 attributes; its `src` decodes to `app_id`.
- A successive click for a different app **overwrites** the cookie (last-touch).
- Forcing `set_marker` to raise → the **302 still fires**, the click-through **reach count
  is unaffected**, and `WIDGET_CONVERSION_DEGRADED` is counted (AC6).
- An unknown/non-accepted id still 404s before any marker is set (unchanged).
- `ruff` + `check` clean; existing widget view tests stay green.

**Size.** S.

**Files/areas.** `apps/widget/views.py`, `apps/widget/tests/test_views.py`.

---

## T-06 — The two fail-soft conversion hooks (follow + register)

**Description.** Credit conversions at the two view boundaries — DESIGN §5.2, §5.3, §9
(WCA-DESIGN-6/7). Explicit, readable, request-aware view hooks (not middleware/signals — A4):
- `subscriptions.views.follow`: **bind** `created = services.follow_app(...)` (it already
  returns `created`); on a genuinely **new** follow only, call a new
  `_attribute_follow_fail_soft(request, response, app_id)` wrapping
  `source.attribute_follow(request, response, followed_app_id=app_id)`. New import edge
  `subscriptions → widget`.
- `accounts.views.register`: on the **202 new-account path only** (not 400/409/503), after
  building the `check_email.html` response, call a new `_attribute_account_fail_soft(request,
  response)` wrapping `source.attribute_account`. New import edge `accounts → widget`.
- Both wrappers: on error → log + `WIDGET_CONVERSION_DEGRADED`, return the response
  unaffected. The follow's own state + its `record_subscribe` corpus event, and the created
  account, are **already committed and untouched** (AC5 — attribution adds nothing).

**Dependencies.** T-04, T-05 (an end-to-end credit needs an armed marker).

**Definition of done.**
- **E2E (AC1)**: arm a marker for app X (via T-05) → `POST …/X/follow` → `widget_conversions(X)`
  shows one follow; `POST /auth/register` (202) → the account conversion is credited to X.
- **AC5**: a credited follow writes the **same** `record_subscribe` row as an un-attributed
  follow (byte-identical corpus); `has_impression(CURATED_SURFACES)` stays False.
- **AC6 fail-soft**: forcing `source.attribute_*` to raise → the follow redirect, the
  registration **202**, and the reach counts all still succeed; `WIDGET_CONVERSION_DEGRADED`
  counted.
- **No false credit**: register **400/409/503** paths credit nothing; a follow that returns
  `created == False` (re-follow) credits nothing at the view.
- `apps/widget` still imports neither `subscriptions` nor `accounts` (DAG preserved);
  `ruff` + `check` clean; existing follow/register tests green.

**Size.** M.

**Files/areas.** `apps/subscriptions/views.py`, `apps/accounts/views.py`, their test
modules.

---

## T-07 — Conversion selectors + the dashboard funnel slot + M2

**Description.** Surface the funnel — DESIGN §5.5, §4, §9 (WCA-DESIGN-8). Two parts:
- `apps/widget/selectors.py`: add a frozen `WidgetConversion{follows, accounts}` DTO and
  `widget_conversions(app_id, *, start, end)` + `widget_conversions_for_apps(app_ids, *,
  start, end)` — one grouped `SUM(count) … GROUP BY kind` over the window's UTC-day range,
  zero-filled, **no N+1**, the exact discipline of `widget_reach[_for_apps]`.
- `apps/dashboard/reception.py` + template: extend the Screen-B widget slot with a
  **Conversions** funnel stage (`Follows from widget: N`, `New accounts from widget: M`) +
  **Conversion rate = (N+M) ÷ click_throughs** **derived at display, never stored** (M2).
  Reach numbers **untouched** (separate tables → one source of truth per fact). The **whole**
  widget slot (reach + conversions) degrades **together** fail-soft on a read error (reuse
  `DASHBOARD_WIDGET_DEGRADED`); the loud core signals reads are unaffected.

**Dependencies.** T-01 (kind), T-02 (table). (Reads tolerate empty data, so it does not
require the writers — but a meaningful integration test seeds via T-03's writer.)

**Definition of done.**
- **AC3**: the slot renders reach **and** conversions as distinct labeled lines + the
  derived rate; the reach integers are **byte-identical** to the pre-conversion slot.
- Selector: zero-filled when no rows; `widget_conversions_for_apps([])` → `{}`; the bulk
  read is **one** grouped query regardless of app count (no N+1, asserted).
- Truthful zero state (reach present, conversions `0`/`0`) renders, not hidden.
- A forced selector read error degrades the **whole** widget slot together
  (`available=False`) while the rest of the reception renders; `DASHBOARD_WIDGET_DEGRADED`
  counted.
- `ruff` + `check` clean; existing dashboard tests green.

**Size.** M.

**Files/areas.** `apps/widget/selectors.py`, `apps/widget/tests/test_selectors.py`,
`apps/dashboard/reception.py`, the dashboard widget-slot template, dashboard tests.

---

## T-08 — Docs: CODEMAP + module docstrings

**Description.** Keep the shared-code index honest (CLAUDE.md §5.3) — DESIGN §14 increment 6.
Record the new shared/reusable surfaces in [CODEMAP.md](../../CODEMAP.md):
`widget.rollup._increment_daily` (now shared by both writers), `widget.source` (the marker
codec), `widget.attribution.record_widget_conversion`, and `widget.selectors.widget_conversions[_for_apps]`.
Update the `apps/widget` README to name the new conversion table + module. No behavior change.

**Dependencies.** T-03, T-04, T-07.

**Definition of done.**
- CODEMAP rows exist for each new shared surface, pointing at the right module.
- The widget README mentions `widget_conversion_count` + the `source`/`rollup` modules.
- No code/test change; `ruff` + `check` still clean.

**Size.** S.

**Files/areas.** [CODEMAP.md](../../CODEMAP.md), `apps/widget/README.md`.

---

## Coverage map (AC → task; design element → task)

| AC | Tasks |
|----|-------|
| **AC1** (conversion shows on dashboard) | T-02, T-03, T-06 (credit), T-07 (display) |
| **AC2** (window + no fabrication) | T-04 (expiry/no-source/mismatch), T-06 |
| **AC3** (distinct funnel stage, reach unchanged) | T-07 |
| **AC4** (no-PII) | T-02 (column absence), T-04 (payload = `{v,src,credited}` only) |
| **AC5** (firewall, `record_subscribe` untouched) | T-03 (AST + M5=0), T-06 (corpus byte-identical) |
| **AC6** (fail-soft) | T-05, T-06, T-07 |

| Design element | Task |
|----------------|------|
| `WidgetConversionKind` (§2) · `widget_attribution_window_days()` (§5.6) · `WIDGET_CONVERSION_*` ×4 (§10) | T-01 |
| `WidgetConversionCount` table + migration (§6.1) | T-02 |
| `rollup._increment_daily` extraction (§6.2) · `record_widget_conversion` (§5.4) · AST firewall test (§12) | T-03 |
| `widget.source` codec + window/dedup/re-issue (§5.1, §3) · security/tamper (§8) | T-04 |
| `set_marker` on the 302 (§5, views) · no-open-redirect (§8) | T-05 |
| `subscriptions.views.follow` hook (§5.2) · `accounts.views.register` hook (§5.3) | T-06 |
| `widget.selectors.widget_conversions[_for_apps]` + `WidgetConversion` (§5.5) · dashboard funnel slot + M2 (§4, WCA-DESIGN-8) · slot fail-soft (§9) | T-07 |
| CODEMAP + docs (§14) | T-08 |

**Exit-gate check:** full coverage (every design element in ≥1 task); every task has a
concrete DoD; no `L` remains. Build order **T-01 → T-08**; the firewall proof + writer
(T-03) and the codec (T-04) precede all HTTP wiring (T-05+).
