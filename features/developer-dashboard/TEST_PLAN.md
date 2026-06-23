# TEST_PLAN — developer-dashboard

*Stage 4 artifact (Senior Engineer). Status: **COMPLETE** — every acceptance criterion (AC1–AC10)
maps to ≥1 automated test; the build is green. Upstream: the approved
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1–AC10) and the ratified [DESIGN.md](DESIGN.md) (§9).
See [phase-4-engineer.md](../../process/personas/phase-4-engineer.md).*

## How to run

```
python manage.py test apps.signals apps.dashboard   # the feature's suites
python manage.py test                               # the full regression suite
ruff check .                                         # lint
python manage.py makemigrations --check --dry-run    # no schema drift (app owns no model)
```

## Test modules

| Module | Covers |
|---|---|
| `apps/signals/tests/test_dashboard_reads.py` | T-01 — the additive signals reads + the §4.2 invariant (ORM level) |
| `apps/dashboard/tests/test_windows.py` | T-02 — the 8 windows + `resolve_window` (pure) |
| `apps/dashboard/tests/test_charts.py` | T-03 — the inline-SVG sparkline geometry (pure) |
| `apps/dashboard/tests/test_reception.py` | T-04 — the composition layer (real selectors + fixtures) |
| `apps/dashboard/tests/test_views.py` | T-05 — the two HTTP views (test client, project URLconf) |
| `apps/dashboard/tests/test_imports.py` | AC8 structural — no `signals.capture` import (AST) |

## Acceptance-criterion coverage

| AC (Given / When / Then) | Test(s) |
|---|---|
| **AC1** — a developer's my-apps list shows exactly their owned, accepted apps | `test_reception.OwnerScopeTests.test_my_apps_lists_only_owned_accepted_apps`; `test_views.MyAppsListTests.test_lists_only_the_callers_accepted_apps` |
| **AC2** — non-developer → 403; own-nothing → 200 empty; another dev's id → 404 | `test_views.AccessControlTests.test_non_developer_gets_403_on_both_routes` / `test_another_devs_app_is_404_indistinguishable`; `test_views.MyAppsListTests.test_own_nothing_state_is_200`; `test_reception.OwnerScopeTests.test_my_apps_empty_for_owner_with_no_accepted_apps` / `test_app_reception_none_for_another_devs_app` / `test_app_reception_none_for_non_accepted_owned_app` |
| **AC3** — total + per-source breakdown, curated `DIGEST` first; new `Surface` auto-appears | `test_dashboard_reads.ImpressionBreakdownTests.test_counts_per_surface_with_total` / `test_every_surface_is_present_zero_filled`; `test_reception.ReachBreakdownTests.test_total_and_curated_first_breakdown`; `test_views.ReachRenderTests.test_total_and_curated_first_breakdown_render` |
| **AC4** — honest zero: an empty `DIGEST` reads `0` with the "no curated shows yet" affordance | `test_dashboard_reads.ImpressionBreakdownTests.test_every_surface_is_present_zero_filled`; `test_reception.ReachBreakdownTests.test_zero_digest_is_present_as_an_honest_zero`; `test_views.ReachRenderTests.test_empty_digest_shows_honest_zero_affordance` |
| **AC5** — funnel = corpus; off-platform proxy shown separately, never folded in | `test_reception.FunnelProjectionTests.test_funnel_view_matches_app_funnel_and_keeps_proxy_separate`; `test_views.FunnelRenderTests.test_funnel_counts_and_separate_proxy_line` |
| **AC6** — reviews: count + raw distribution + recent list, **no average/eligibility** | `test_reception.ReviewsSlotTests.test_reviews_carry_count_distribution_list_and_no_average`; `test_views.ReviewsRenderTests.test_reviews_render_without_an_average` |
| **AC7** — figures recompute per window; all-time counts every event; bad `?window=` → default (no 500) | `test_dashboard_reads.ImpressionBreakdownTests.test_window_excludes_out_of_range_events`; `test_windows.ResolveWindowTests` (all four); `test_views.WindowCoercionTests.test_in_and_out_of_window_figures_and_all` / `test_bad_window_falls_back_to_default_without_500` |
| **AC8** — read-only: GET-only (POST → 405); no `signals.capture` import; a GET writes no signal row | `test_views.AccessControlTests.test_post_is_405_read_only` / `test_viewing_writes_no_signal_rows`; `test_imports.DashboardImportsTests.test_no_module_in_the_app_imports_signals_capture` |
| **AC9** — bounded reads: constant query count for the my-apps list at K=2 vs K=20; per-app fixed | `test_dashboard_reads.ImpressionBreakdownForAppsTests.test_query_count_is_constant_in_app_count`; `test_dashboard_reads.*.test_is_one_query`; `test_reception.BoundedReadTests`; `test_views.BoundedQueryTests.test_my_apps_query_count_independent_of_app_count` |
| **AC10** — trend over time + distinguished curated line; empty window → no chart; exact numbers | `test_dashboard_reads.ImpressionTrendTests` (all five); `test_charts.BuildSparklineTests`; `test_reception.TrendTests`; `test_views.TrendRenderTests.test_svg_and_table_render_with_exact_numbers` / `test_empty_window_shows_no_chart` |

## Integrity invariant & failure split

| Item | Test(s) |
|---|---|
| §4.2 invariant `impression_breakdown.total == app_funnel.impressions` (random fixtures, several windows) | `test_dashboard_reads.BreakdownFunnelInvariantTests.test_total_matches_funnel_impressions_over_random_fixtures` |
| §7 core read **fails loud** (raise propagates → 500 + `DASHBOARD_RECEPTION_DEGRADED`) | `test_reception.FailLoudTests` (breakdown/funnel/my-apps); `test_views.FailureSplitTests.test_core_read_error_is_a_loud_500_with_alert_counter` |
| §7 reviews slot **fails soft** (`available=False`, rest intact, 200 + `DASHBOARD_REVIEWS_DEGRADED`) | `test_reception.ReviewsSlotTests.test_reviews_read_failure_degrades_soft`; `test_views.FailureSplitTests.test_reviews_error_is_soft_200_with_degraded_counter` |

## Metric coverage (M1–M6, DESIGN §8)

- **M1/M2** (view volume): `DASHBOARD_MY_APPS_VIEWED` / `DASHBOARD_RECEPTION_VIEWED` fire on the
  view paths — exercised implicitly across `test_views`; the counters exist in
  `apps/core/observability.py`.
- **M3** (`DASHBOARD_NONEMPTY_RECEPTION`, only on a non-zero funnel):
  `test_views.FailureSplitTests.test_nonempty_reception_counter_only_on_nonzero_funnel`.
- **M4** (curated-reach coverage): the curated split is computed and tested
  (`test_reception.ReachBreakdownTests`); expected **thin** until a `DIGEST` emitter ships —
  reported honestly, not a bug (brief R1/AC4).
- **M5** (owner-scope leak = 0): the AC1/AC2 owner-scope tests are the guard (a leak is a test
  failure, not a counter) — `test_reception.OwnerScopeTests`, `test_views.AccessControlTests`.
- **M6** (bounded at 100×): the bounded-read tests above (AC9) + the per-window granularity bound
  (`test_windows`).

## Regression checklist (areas touched)

- `apps.signals` — the additive `TrendGranularity` / `impression_breakdown[_for_apps]` /
  `impression_trend` change **no existing read**; the full `apps.signals` suite stays green
  (`app_funnel` / `funnel_for_apps` / `has_impression` / `category_impressions` unchanged).
- `apps.core.observability` — six additive `DASHBOARD_*` constants; no existing metric touched.
- `config/settings.py` + `config/urls.py` — the activation switch (one `INSTALLED_APPS` line +
  one `dashboard/` include); no other route/app affected.
- `makemigrations --check` clean (the dashboard owns no model; signals is unchanged schema-wise).

## Result

Full suite **green**; `ruff` clean; no migration drift. The surface goes live only via the
`config/urls` `dashboard/` include + the `INSTALLED_APPS` line; removing both is the entire
rollback (zero data migration).
