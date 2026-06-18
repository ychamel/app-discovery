# TEST_PLAN — submission-intake

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (AC1–AC9) from
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) and [DESIGN.md](DESIGN.md) §14 to the automated
test(s) that exercise it. All tests live under `apps/catalog/tests/`. Full suite: **315
tests green** (184 prior + 131 new), `ruff` clean, no migration drift.*

Run: `python manage.py test apps.catalog` (or the whole suite, `python manage.py test`).

---

## Acceptance-criterion coverage

| AC | What it requires | Automated test(s) |
|----|------------------|-------------------|
| **AC1** | Submit with required fields; fail loud + no partial write on missing/malformed | `test_services_write.SubmitAppTests` (`test_valid_submission_creates_pending_app`, `test_missing_name_writes_nothing`, `test_missing_description_rejected`, `test_malformed_url_rejected`, `test_non_http_scheme_rejected`, `test_zero_tags_rejected`, `test_zero_media_rejected`); `test_api_developer.test_create_app_returns_201_pending` / `test_create_missing_field_returns_400_no_write`; `test_pages_developer.test_submit_valid_creates_pending_and_redirects` / `test_submit_invalid_rerenders_and_creates_nothing` |
| **AC2** | Submission is developer-gated | `test_api_developer.test_create_requires_developer_role` / `test_unauthenticated_create_is_403`; `test_pages_developer.test_submit_requires_developer_role` |
| **AC3** | Identical free intake — no pay/tier/priority anywhere | `test_models.test_no_monetary_or_priority_field_exists`; `test_selectors.test_queue_row_has_no_priority_field`; `test_api_review.test_queue_is_fifo_with_hint_and_no_priority` |
| **AC4** | Closed vocabulary; store by `Tag.id`; off-vocab refused + counted | `test_services_write.test_off_vocabulary_tag_refused_and_counted` / `test_duplicate_tag_ids_collapse`; `test_models.AppTagModelTests`; `test_api_developer.test_create_off_vocabulary_tag_returns_400` |
| **AC5** | Accept only if all floors pass; record failing criterion (append-only) | `test_services_lifecycle.AcceptRejectTests` (`test_accept_flips_status_and_writes_decision`, `test_reject_flips_status_and_records_criteria`, `test_decision_atomic_failure_leaves_neither`, `test_review_decisions_are_append_only`); `test_api_review.test_accept_decision` / `test_reject_decision_records_criteria`; `test_pages_review.test_accept_moves_app_to_accepted` / `test_reject_with_floor_moves_app_to_rejected` |
| **AC6** | No taste gate — a taste rejection is unrepresentable | `test_gate` (`test_exactly_the_five_objective_floors`, `test_no_catch_all_value`); `test_services_lifecycle.test_reject_with_zero_criteria_refused` / `test_reject_with_unknown_criterion_refused`; `test_api_review.test_reject_with_zero_criteria_is_400` / `test_reject_with_unknown_criterion_is_400`; `test_pages_review.test_reject_with_no_floor_refused` |
| **AC7** | Actionable decision + non-terminal rejection | `test_notifications.test_rejected_body_lists_each_failing_criterion_and_note` / `test_accepted_decision_sends_accepted_template` / `test_send_failure_is_counted_and_decision_stands`; `test_services_lifecycle.WithdrawResubmitTests.test_resubmit_from_rejected`; `test_pages_developer.test_my_apps_shows_status_and_rejection_reasons` / `test_withdraw_and_resubmit` |
| **AC8** | Ownership + correction + withdrawal + re-validation | `test_services_write.EditAppTests` (`test_gate_relevant_edit_of_accepted_returns_to_pending`, `test_unchanged_edit_of_accepted_stays_accepted`) + `MediaServiceTests`; `test_selectors.OwnerScopeTests`; `test_api_developer.test_detail_of_another_owners_app_is_404` / `test_add_and_remove_media` / `test_withdraw_then_resubmit`; `test_pages_developer.test_accepted_app_detail_shows_return_to_review_warning` / `test_detail_of_another_owners_app_is_404` |
| **AC9** | Downstream contract — accepted-only, stable id, resolved tags + ordered media | `test_selectors.CataloguedAppTests` (one test per non-accepted state: `test_pending_/test_rejected_/test_withdrawn_app_is_not_catalogued`; `test_tags_are_resolved_to_current_label`; `test_retired_tag_resolves_to_successor`; `test_media_returned_in_position_order`; `test_list_does_not_n_plus_one`) |

Every AC is exercised by ≥1 automated test.

## Edge cases covered

- **Empty / boundary:** zero tags, zero media, blank name/description (`test_services_write`);
  empty my-apps and empty review queue (`test_pages_developer`, `test_pages_review`).
- **Malformed / huge:** non-image upload, disallowed format (GIF), oversize file, over the
  count cap, client-filename suppression (`test_services_write` media tests).
- **Concurrency:** double decision refused — exactly one `ReviewDecision` survives
  (`test_services_lifecycle.DoubleDecisionTests`); atomic decision rollback on a mid-call
  failure (`test_decision_atomic_failure_leaves_neither`).
- **Failure injection:** email-send failure is counted and the decision stands
  (`test_notifications.test_send_failure_is_counted_and_decision_stands`).
- **Lifecycle illegal transitions:** accept/decision on a non-pending app → 409; double
  withdraw → 409; resubmit of a pending app refused (`test_services_lifecycle`,
  `test_api_*`).
- **URL normalization** equivalence / distinctness / idempotence (`test_urlnorm`).
- **Read at scale:** no N+1 on the catalogue list (`test_selectors.test_list_does_not_n_plus_one`).

## Regression checklist (areas touched)

- `apps/core/config.py` — two new tunables, defaults + fail-loud
  (`apps.core.tests.test_config.CatalogMediaLimitTests`); `validate_all` still green.
- `apps/core/observability.py` — added catalog metric constants only (no behavior change);
  full prior suite (184 tests) still green.
- `config/settings.py` / `config/urls.py` — app registered, media served in DEBUG;
  `manage.py check` clean, no migration drift (`makemigrations --check`).
- Migration `catalog.0001` reversible on a scratch DB (`migrate catalog zero` drops the
  four tables, keeps shared `citext`) — rehearsed manually in Stage 4; re-verify at release.
