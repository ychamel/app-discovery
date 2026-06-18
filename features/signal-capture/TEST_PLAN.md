# TEST_PLAN — signal-capture

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (AC1–AC11) from
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) and [DESIGN.md](DESIGN.md) §14 to the automated
test(s) that exercise it. All tests live under `apps/signals/tests/`.*

Run: `python manage.py test apps.signals` (or the whole suite, `python manage.py test`).

---

## Acceptance-criterion coverage

| AC | What it requires | Automated test(s) |
|----|------------------|-------------------|
| **AC1** | An impression is recorded with user, `App.id`, a unique id, a timestamp, and the app's capture-time category tags | `test_capture_impression.RecordImpressionTests.test_records_impression_with_frozen_tag_snapshot`; `test_models.IdentityTests.test_all_four_models_have_uuid_primary_keys`; `test_kinds.SurfaceTests` |
| **AC2** | Stable `user × App.id × impression` keys; tags captured **at show time**, not resolved live | `test_capture_impression.test_snapshot_is_frozen_against_later_tag_rename`; `test_models.ConstraintTests.test_impression_tag_unique_per_impression`; `test_selectors.CategoryImpressionsTests.test_counts_impressions_whose_snapshot_includes_tag` |
| **AC3** | A click-through links to the originating **impression** (the instance, not just the app); cross-app/user forgery refused | `test_capture_engagement` (`test_click_through_links_impression`, `test_click_through_requires_an_impression`, `test_click_through_rejects_mismatched_app`, `test_click_through_rejects_another_users_impression`) |
| **AC4** | Return-to-platform @3d & @14d, distinguishable by window, per user×app, **directly observed** | `test_selectors.ReturnsDerivationTests` (`test_visit_on_day_plus_3_counts_in_both_windows`, `test_visit_on_day_plus_10_counts_only_in_long_window`, `test_no_in_window_visit_counts_in_neither`, `test_same_day_visit_is_not_a_return`, `test_window_length_comes_from_config`); `test_capture_impression.RecordPlatformVisitTests`; `test_middleware` |
| **AC5** | Subscribe + on-page re-engagement tied to user×App.id (+ impression where known) | `test_capture_engagement` (`test_subscribe_without_impression`, `test_page_reengagement_with_impression`, `test_optional_kind_still_validates_a_supplied_impression`) |
| **AC6** | Share tied to App.id + the sharing user | `test_capture_engagement.test_share_without_impression`; `test_kinds.EventKindTests.test_exactly_the_five_kinds` |
| **AC7** | Off-platform proxy = flagged **secondary**; funnel complete without it; `is_proxy` service-set | `test_capture_engagement` (`test_off_platform_proxy_is_flagged_secondary`, `test_on_platform_recorders_never_set_is_proxy`, `test_off_platform_proxy_requires_an_impression`); `test_selectors.AppFunnelCountTests.test_proxy_is_never_folded_into_click_throughs`; `test_models.ConstraintTests.test_is_proxy_defaults_false` |
| **AC8** | The full on-platform funnel is reconstructable from stored data, no backfill | `test_selectors.AppFunnelCountTests` (`test_counts_each_funnel_field_from_stored_rows`, `test_out_of_window_events_excluded`); `test_selectors.ReturnsDerivationTests` (returns derived, not stored) |
| **AC9** | Developer-readable **raw** funnel via a defined read path; never scored; bulk no-N+1 | `test_selectors.FunnelForAppsTests` (`test_bulk_funnel_does_not_n_plus_one`, `test_app_with_no_signal_returns_zero_filled_funnel`, `test_funnel_dto_has_no_score_field`); `test_models.StructuralGuaranteeTests.test_no_scoring_column_on_any_table` |
| **AC10** | Privacy posture: only permitted fields (no IP/UA/PII); what/why/retention human-readable | `test_models.StructuralGuaranteeTests.test_no_pii_column_on_any_table`; `apps/signals/PRIVACY.md` (manual: what/why/retention/deletion documented) |
| **AC11** | A failed capture surfaces (logged/alertable via `capture_error`) — never silent; partial writes never persist | `test_capture_impression.test_partial_write_failure_is_atomic_and_counted` / `CaptureErrorIsZeroOnHappyPathTests`; `test_capture_engagement.test_failure_counts_capture_error_tagged_with_kind` / `test_happy_path_emits_no_capture_error`; `test_middleware.test_capture_failure_is_fail_soft_but_counted` |

Every AC is exercised by ≥1 automated test.

## Edge cases covered

- **Empty / boundary:** an app with no signal returns a zero-filled funnel
  (`test_selectors.test_app_with_no_signal_returns_zero_filled_funnel`); out-of-window
  events excluded (`test_out_of_window_events_excluded`); return-window boundaries at +3 /
  +10 / same-day / none (`ReturnsDerivationTests`).
- **Malformed / closed vocabulary:** an unknown surface and an unknown/non-accepted app id
  are refused with nothing written (`test_capture_impression.test_invalid_surface_is_rejected`,
  `test_unknown_app_raises_and_writes_nothing`, `test_non_accepted_app_is_rejected`); the
  event-kind / surface enums are pinned to their exact member set (`test_kinds`).
- **Concurrency / idempotency:** repeated same-day visits yield exactly one row
  (`test_capture_impression.RecordPlatformVisitTests`,
  `test_middleware.test_repeated_requests_same_day_are_idempotent`); the
  `(user, visit_date)` unique constraint is enforced
  (`test_models.test_platform_visit_unique_per_user_per_day`).
- **Failure injection:** a forced mid-write failure leaves neither impression nor tag rows
  and is counted + re-raised (`test_partial_write_failure_is_atomic_and_counted`); a deep
  capture failure under the middleware is counted yet navigation is unbroken
  (`test_capture_failure_is_fail_soft_but_counted`).
- **Deletion semantics (SC-10):** account deletion `SET_NULL`s the event corpus (rows
  survive, anonymized) and `CASCADE`s the visit ticks
  (`test_models.DeletionSemanticsTests`).
- **Structural guarantees:** no score/weight/rank column (AC9) and no IP/UA/device/geo/
  referrer/free-text column (AC10) on any model; `app_id`/`tag_id` are soft (non-FK) refs
  (`test_models.StructuralGuaranteeTests`, `SoftReferenceTests`).

## `capture_error` discipline (CLAUDE.md §6.6)

`capture_error` is the never-silent loss signal and must read **0** on every happy path
(`test_capture_impression.CaptureErrorIsZeroOnHappyPathTests`,
`test_capture_engagement.test_happy_path_emits_no_capture_error`). The fail-loud tests
deliberately trigger it and assert **both** the increment (tagged with the event kind)
**and** the re-raise — the loss is loud, counted, and never swallowed.

## Regression checklist (areas touched)

- `apps/core/config.py` — two new tunables; existing tunables + `validate_all` unchanged
  (`test_config`); full suite green.
- `apps/core/observability.py` — additive metric constants only; `increment` unchanged.
- `config/settings.py` — `apps.signals` added to `INSTALLED_APPS`,
  `PlatformVisitMiddleware` appended to `MIDDLEWARE` after auth + request-context; no
  existing app touched.
- `apps/accounts`, `apps/taxonomy`, `apps/catalog` — reused as-is, not modified (boundary
  check, DESIGN §1).
- Migration `signals/0001_initial` is reversible (`migrate signals zero` drops all four
  tables; rehearsed).
