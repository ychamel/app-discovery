# TEST_PLAN — embeddable-update-widget

_Status: **COMPLETE** — Stage 4 (Senior Engineer). All of T-01…T-07 built; **AC1–AC9 covered**;
full suite green (893 tests), `ruff` clean, `makemigrations --check` clean. Built alongside the
code, task by task._
Upstream: the APPROVED [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1–AC9 / M1–M6), the ratified
[DESIGN.md](DESIGN.md), and [TASKS.md](TASKS.md) (T-01…T-07). Each acceptance criterion maps to
the automated test(s) that verify it; edge cases and a per-task regression checklist follow._

The full suite is run with `python manage.py test` (needs PostgreSQL) and `ruff check`.

---

## Acceptance-criterion coverage (target: 100% by exit)

| AC | Criterion (brief) | Verifying test(s) | Status |
|----|-------------------|-------------------|--------|
| AC1 | Notices rendered newest-first, capped | `test_content` (T-04) + `test_views` (T-05) | **✓** (T-04 assembler + T-05 render) |
| AC2 | Neutral empty state, link still offered | `test_content` (T-04) + `test_views` (T-05) | **✓** (T-04 + T-05) |
| AC3 | Reflects publish/withdraw live (no widget store of notices) | `test_content` (T-04) + `test_views` (T-05) | **✓** (T-04 + T-05) |
| AC4 | Labeled "view on platform" → app page | `test_views` (T-05) | **✓** (T-05) |
| AC5 | Renders to anonymous users; only public content | `test_views` (T-05) | **✓** (T-05) |
| AC6 | Firewall: no widget interaction confers D-8 eligibility (M5 = 0) | `test_imports` + `test_attribution` (T-02), re-asserted in `test_views` (T-05) | **✓** (T-02 AST + 0-corpus; T-05 end-to-end) |
| AC7 | Drop-in embed, no build toolchain | `test_views` (T-05) + README `<iframe>` (T-07) | **✓** render (T-05); README snippet pending T-07 |
| AC8 | Per-IP rate limit on the public read | `core` limiter tests (T-03) + `test_views` (T-05) | **✓** (T-03 limiter + T-05 end-to-end + Cache-Control) |
| AC9 | Attribute reach (incl. anonymous); show on dashboard | `test_attribution`/`test_selectors` (T-02) + `test_views` (T-05) + dashboard tests (T-06) | **✓** (T-02/T-05 store+count; T-06 dashboard display) |

**Metrics:** M1/M2/M4 → `WIDGET_RENDERED`/`WIDGET_CLICK_THROUGH` counters + `widget_reach`
windows (T-03/T-05/T-06). M3 (per-account conversion) → **deferred** (OQ-EUW-5, DESIGN §11).
M5 (reach beyond the firewall = 0) → **structural**, asserted in T-02 + T-05. M6 (latency +
`*_DEGRADED` fail-soft) → T-05/T-06.

---

## Per-task detail

### T-01 — `apps/widget/` scaffold + `widget_reach_count` table (DONE)

The table is inert/unrouted at this stage; these tests lock the durable schema contract the
later tasks build on. No acceptance criterion is fully satisfied yet, but the **AC10 PII-free /
AC6 no-score posture is made structural here** (the model cannot represent an actor or a score).

Automated — `apps/widget/tests/test_models.py`:

| Check | Test |
|-------|------|
| All fields persist (`app_id`, `kind`, `count_date`, `count`, timestamps, UUID pk) | `test_persists_all_fields` |
| Both `WidgetEventKind` values accepted | `test_both_kinds_are_accepted` |
| `kind` choices are exactly `impression` \| `click_through` | `test_kind_choices_are_exactly_the_two_pinned_values` |
| `db_table == "widget_reach_count"` | `test_db_table_name` |
| Unique constraint rejects a 2nd `(app_id, kind, count_date)` row (`IntegrityError`) | `test_unique_constraint_rejects_a_second_row_for_the_same_app_kind_day` |
| A different kind/day/app is a separate row (constraint scope is correct) | `test_different_kind_or_day_or_app_is_a_separate_row` |
| `widget_reach_app_kind_date_idx` present (Meta + DB introspection) | `test_reach_index_is_present` |
| **No `user`/IP/UA/referrer/geo/device/score/weight/rank field** (AC6/AC10 structural) | `test_no_actor_or_pii_or_score_field_exists` |
| Field set is exactly the designed seven | `test_fields_are_exactly_the_designed_set` |

Migration checks (manual, per DoD):
- `makemigrations widget` produced exactly `widget/0001_initial`; `makemigrations --check
  --dry-run` then reports **no** further changes (model matches migration). ✓
- `migrate widget` → `migrate widget zero` → `migrate widget` applies/reverses/re-applies
  cleanly (up→down→up). ✓
- App is in `INSTALLED_APPS`; package imports cleanly; the runner discovers `apps/widget/tests/`. ✓

**Regression:** full suite `python manage.py test` green (837 tests, +9 from the 828 baseline);
`ruff check` clean; `manage.py check` clean. T-01 adds an inert, unrouted table only — no
existing behaviour touched.

### T-02 — `attribution` writer + `selectors` reader + the AC6 firewall proof (DONE)

The risk centerpiece. The store is reachable only by tests at this stage (no route yet).

**AC6 firewall (structural — the headline risk):**

| Check | Test |
|-------|------|
| No `apps.widget` module (excl. tests) imports anything matching `signals` (AST walk) | `test_imports.py::test_no_module_in_the_app_imports_signals` |
| A widget impression + click-through writes **0** `Impression`/`EngagementEvent` rows | `test_attribution.py::FirewallTests::test_recording_widget_reach_writes_no_signals_rows` |
| `has_impression(..., surfaces=CURATED_SURFACES)` stays **False** after widget reach (M5 = 0) | `test_attribution.py::FirewallTests::test_widget_reach_is_not_curated_surface_evidence` |

**Write correctness + concurrency** (`test_attribution.py::RecordImpressionTests`):

| Check | Test |
|-------|------|
| First impression creates today's row with `count == 1` | `test_first_impression_creates_todays_row_with_count_one` |
| Subsequent impressions increment the **same** row (not new rows) | `test_subsequent_impressions_increment_the_same_row` |
| Impression and click-through are **separate** rows | `test_impression_and_click_through_are_separate_rows` |
| A different app is a separate row | `test_a_different_app_is_a_separate_row` |
| The `IntegrityError` create-race falls back to an atomic increment (no lost update, no dup) — EUW-IMPL-1 savepoint | `test_create_race_falls_back_to_an_atomic_increment` |

**Read correctness** (`test_selectors.py`):

| Check | Test |
|-------|------|
| Sums across days per kind | `test_sums_across_days_per_kind` |
| Zero-filled when no rows / when a kind is absent | `test_zero_filled_when_no_rows`, `test_zero_filled_when_a_kind_is_absent` |
| Rows outside the window excluded; window day-bounds inclusive | `test_rows_outside_the_window_are_excluded`, `test_window_bounds_are_inclusive_of_their_days` |
| `widget_reach` is one query | `test_is_one_query` |
| `widget_reach_for_apps`: `[]` ⇒ `{}`; one entry per app, zero-filled; **one query** vs 50 apps (no N+1) | `test_empty_input_returns_empty_dict`, `test_one_entry_per_requested_app_zero_filled`, `test_is_one_query_regardless_of_app_count` |

**Regression:** full suite green (854 tests, +17 from T-01's 837); `ruff` clean. No route/UI yet —
the store stays unreachable outside tests.

### T-03 — `core` additions: per-IP GET limiter + 3 `widget_*` tunables + 10 metric constants (DONE)

Inert until T-05/T-06 (no widget caller yet). The limiter generalizes the existing
`core.ratelimit` internals by one `window_seconds` parameter — no new framework (DESIGN §14).

**Rate limiter** (`apps/core/tests/test_ratelimit.py::IpRateLimitedGetTests`):

| Check | Test |
|-------|------|
| Under the limit a GET passes through (body runs) | `test_under_limit_passes_through` |
| `(limit)+1`-th GET ⇒ 429, the view body is **not** called, `limited_metric` counted | `test_over_limit_returns_429_and_does_not_call_the_view` |
| Limit is per-IP (a different IP has its own allowance) | `test_limit_is_per_ip` |
| Window reset restores allowance | `test_window_reset_restores_allowance` |
| Limit is config-driven (`override_settings`, no code change) | `test_limit_is_config_driven` |
| Cache backend error ⇒ **fail-open** (body runs), `degraded_metric` counted — not a 500 | `test_cache_error_fails_open_and_counts_degraded` |
| Non-GET passes through unlimited (the view's own method gate applies) | `test_non_get_passes_through_unlimited` |
| **Regression:** the auth `rate_limited` suite stays green (the `_exceeds_limit` window default is unchanged) | existing `PerEmailLimitTests`/`PerIpLimitTests` |

**Config** (`apps/core/tests/test_config.py::WidgetTunableTests` + `ValidateAllTests`):

| Check | Test |
|-------|------|
| The three `widget_*` tunables resolve to defaults (5 / 60 / 60) | `WidgetTunableTests::test_defaults` |
| Honor `override_settings` | `WidgetTunableTests::test_overrides` |
| Non-positive ⇒ `ImproperlyConfigured` (fail-loud) | `WidgetTunableTests::test_non_positive_fails_loudly` |
| `validate_all()` evaluates the widget tunables (bad value surfaces at startup) | `ValidateAllTests::test_evaluates_widget_tunables` |

**Observability:** the ten `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` constants exist as unique
strings (declared in `core/observability.py`; referenced by name in T-05/T-06). M5 needs none —
0 by construction.

**Regression:** full suite green (865 tests, +11 from T-02's 854); `ruff` clean.

### T-04 — `content.build_widget_view` — the pure view-model assembler (DONE)

`apps/widget/tests/test_content.py` (real ORM-seeded catalog + `updates_notice`; no HTTP):

| Check | Test |
|-------|------|
| **AC1:** N seeded notices ⇒ newest-first, capped at the limit; correct `app_name` + `app_page_path == reverse("pages:app-page", [id])` | `test_returns_notices_newest_first_capped_with_name_and_link` |
| Cap honors the config limit (`override_settings`) | `test_cap_honors_the_config_limit` |
| **AC2:** accepted app, no notices ⇒ `notices == []`, `notices_degraded == False` (truthful empty) | `test_empty_is_truthful_not_degraded` |
| **AC3:** a notice seeded then deleted via `updates` changes the next build (live read, no widget store) | `test_reads_notices_live` |
| Notice-read failure ⇒ `notices == []`, `notices_degraded == True`, `WIDGET_NOTICES_DEGRADED` counted, **name + link still present** | `test_notice_read_failure_degrades_link_only_and_counts` |
| Unknown/non-accepted id ⇒ `None` (D-6 gate; catalog exception is left to the view wrapper) | `test_unknown_or_unaccepted_app_returns_none` |

**Regression:** full suite green; `ruff` clean. Pure assembler — no route yet.

### T-05 — the HTTP layer + framable templates + the activation include (DONE)

The `widget/` include in `config/urls.py` makes the surface live. `apps/widget/tests/test_views.py`
(Django test client, project URLconf):

| Check | Test |
|-------|------|
| **AC5:** anonymous render ⇒ 200 with notices + the link (no auth) | `RenderTests::test_anonymous_render_returns_200_with_notices_and_link` |
| **AC7:** self-contained HTML, no `<script>`, no external asset | `RenderTests::test_render_is_self_contained_no_build` |
| **AC1:** notices newest-first, capped | `RenderTests::test_notices_newest_first_capped` |
| **AC2:** empty state message + link | `RenderTests::test_empty_state_shows_message_and_link` |
| **AC3:** withdrawn notice gone next render (live read) | `RenderTests::test_withdrawn_notice_is_gone_on_next_render` |
| **AC8:** `Cache-Control: public, max-age=<config>` present | `RenderTests::test_cache_control_present_on_render` |
| **AC9/§5.1:** `@xframe_options_exempt` (no `X-Frame-Options: DENY`) | `RenderTests::test_xframe_exempt_no_deny_header` |
| Unknown id ⇒ `unavailable.html` 404 | `RenderTests::test_unknown_id_is_404_unavailable` |
| **AC4:** `/view` 302 to `reverse("pages:app-page", [id])` (`Location` asserted, server-derived) | `ClickThroughTests::test_view_302s_to_the_app_page` |
| `/view` unknown id ⇒ 404 | `ClickThroughTests::test_view_unknown_id_is_404` |
| **AC9:** a render counts an impression, a `/view` a click-through (read via `widget_reach`) | `AttributionTests::test_render_counts_an_impression_and_view_counts_a_click_through` |
| **AC6 (HTTP):** render + `/view` write 0 `Impression`/`EngagementEvent`; `has_impression(CURATED_SURFACES)` False | `FirewallHttpTests::test_render_and_view_write_no_signals_rows` |
| **AC8:** over the limit ⇒ 429, no render, **no impression counted**, `WIDGET_RATE_LIMITED` | `RateLimitTests::test_over_limit_returns_429_with_no_render_and_no_count` |
| **§8 fail-soft:** impression-count failure ⇒ still 200 + `WIDGET_COUNT_DEGRADED` | `FailSoftTests::test_impression_count_failure_still_renders_200` |
| **§8 fail-soft:** build/catalog failure ⇒ `unavailable.html` 200 + `WIDGET_RENDER_DEGRADED` | `FailSoftTests::test_build_failure_renders_neutral_unavailable_200` |
| **§8 fail-soft:** limiter cache error ⇒ fail-open 200 + `WIDGET_LIMITER_DEGRADED` | `FailSoftTests::test_limiter_cache_error_fails_open` |
| **method gate:** `POST` to either route ⇒ 405 | `RenderTests::test_post_is_405`, `ClickThroughTests::test_view_post_is_405` |

**Regression:** full suite green (889 tests, +24 from T-03's 865); `ruff` clean; `manage.py check`
clean; `makemigrations --check` clean. The widget surface is now user-reachable (the `widget/`
include is the activation switch).

### T-06 — additive fail-soft "Widget reach" slot on the closed `apps/dashboard/` (DONE)

The only edit to the closed dashboard — additive + fail-soft (the reviews-slot precedent); the
core signals read keeps its loud-500 posture. `apps/dashboard/tests/test_reception.py::WidgetReachSlotTests`:

| Check | Test |
|-------|------|
| **AC9 (Screen B):** seeded `widget_reach_count` rows ⇒ "Widget reach" with correct impressions/click-throughs over the window | `test_screen_b_shows_widget_reach_over_the_window` |
| **AC9 (Screen A):** `build_my_apps_summaries` includes `widget_impressions` via **one** `widget_reach_for_apps` call (zero-filled, no N+1) | `test_screen_a_includes_widget_impressions_via_one_bulk_read` |
| **§8 fail-soft (B):** `widget_reach` raises ⇒ slot `available == False`, impressions 0; reach/funnel/reviews still render | `test_screen_b_widget_read_failure_degrades_only_that_slot` |
| **§8 fail-soft (A):** `widget_reach_for_apps` raises ⇒ widget column → 0, list still 200 | `test_screen_a_widget_read_failure_degrades_column_to_zero` |
| **Regression:** the core signals reads stay loud-500 (existing `FailLoudTests`); Screen-A query count independent of K — now including the widget bulk read (existing `BoundedReadTests`) | existing dashboard suite |

The derived click-through **rate** is computed at display in `app_reception.html` (not stored);
the slot is **labeled off-platform** and rendered distinct from the per-`Surface` breakdown.

**Regression:** full suite green (893 tests, +4 from T-05's 889); `ruff` clean;
`makemigrations --check` clean (no schema change in `dashboard`).

### T-07 — README, CODEMAP, DECISIONS finalize (DONE)

Docs-only close-out; covered by the close-out sweep (full suite green, `ruff` clean,
`makemigrations --check` clean). README documents the one-line `<iframe>` (completing AC7) +
the rollback note; `CODEMAP.md` records every new shared surface; `DECISIONS.md` marks EUW-7…11
built. No behavioural change.
