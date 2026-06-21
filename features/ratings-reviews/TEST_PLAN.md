# TEST_PLAN — ratings-reviews

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (FEATURE_BRIEF §4, AC1–
AC9) to the automated test(s) that verify it, plus edge cases and a regression checklist.
See [phase-4-engineer.md](../../process/personas/phase-4-engineer.md).*

**Suite status:** full project suite **486 tests green** (+69 for this feature), `ruff` clean,
`makemigrations --check` clean, `manage.py check` clean. Both new migrations rehearsed
up→down→up.

Run this feature's tests: `python manage.py test apps.ratings apps.signals.tests.test_has_impression`

---

## Acceptance criteria → tests

| AC | What it requires | Verifying test(s) |
|----|------------------|-------------------|
| **AC1** submit & reflected | signed-in submit on an accepted app stores one row keyed user×app_id; appears on the page | `test_services.SubmitRatingTests.test_creates_one_row_keyed_on_user_and_app`, `test_services::test_review_text_is_optional`, `test_views.SubmitViewTests.test_signed_in_valid_submit_stores_and_redirects_to_the_page`, `test_templatetags.ReviewsSlotRenderTests.test_app_with_reviews_renders_summary_and_list` |
| **AC2** validation fail-loud, nothing stored | out-of-range score / over-length text → rejected, DB unchanged, `RATING_REJECTED` | `test_services::test_score_below_range_is_rejected_and_nothing_stored`, `::test_score_above_range_…`, `::test_over_length_review_…`, `test_views::test_invalid_score_redirects_back_with_a_message_and_stores_nothing` |
| **AC3** auth required, page renders anon | anonymous write → sign-in redirect, no write; anonymous page render is full + read-only + "Sign in to rate" | `test_views::test_anonymous_submit_redirects_to_signin_and_writes_nothing`, `RemoveViewTests.test_anonymous_remove_redirects_to_signin`, `test_templatetags::test_anonymous_sees_read_only_reviews_and_a_signin_link_no_form`, `::test_signed_in_sees_the_form` |
| **AC4** display + empty state | app with ≥1 rating → count + distribution + list; 0 ratings → defined empty state, no broken layout | `test_selectors.ReviewsForAppTests.test_count_and_distribution_match_fixtures`, `::test_list_is_most_recent_first`, `::test_empty_state_when_no_ratings`, `test_templatetags::test_app_with_reviews_renders_summary_and_list`, `::test_empty_state_when_no_reviews` |
| **AC5** gate recorded for 100% | every stored rating has non-null `weight_eligible` + `basis` + `determined_at`; `CURATION_UNVERIFIED` still stores | `test_services::test_every_write_stamps_a_determination`, `::test_gate_unverified_still_stores`, `test_gate.DetermineEligibilityTests.test_fails_closed_and_loud_when_the_evidence_read_raises`, `test_models.RatingShapeTests.test_records_the_gate_determination` |
| **AC6** no scoring in this layer | no score/weight/rank/average column; summary = count + raw distribution; no average computed | `test_models::test_has_no_score_or_quality_column`, `test_selectors::test_summary_shape_is_count_plus_distribution_only`, `::test_no_averaging_machinery_is_used` |
| **AC7** outside ratings displayed but marked | non-curated rater → stored `weight_eligible=False`, basis `NO_CURATED_IMPRESSION`, **still shown** with no badge | `test_services::test_non_curated_rater_stores_not_eligible`, `test_gate::test_not_curated_when_no_qualifying_impression`, `test_selectors::test_not_weight_eligible_rating_is_included`, `test_templatetags::test_not_eligible_rating_shows_without_a_badge` |
| **AC8** one active, editable, removable | re-submit updates the same row (no dup) + re-determines; remove deletes | `test_services::test_resubmit_updates_the_same_row`, `::test_resubmit_redetermines_eligibility_as_of_the_edit`, `RemoveRatingTests::*`, `test_views::test_resubmit_updates_the_same_row`, `RemoveViewTests::test_remove_deletes_the_row_and_redirects`, `test_models::test_unique_constraint_on_user_and_app` |
| **AC9** accepted apps only | pending/rejected/withdrawn/unknown/non-UUID → rejected, nothing stored | `test_services::test_unknown_app_is_rejected_and_nothing_stored`, `test_views::test_unknown_app_is_404`, `::test_non_accepted_app_is_404`, `::test_non_uuid_path_is_404_at_routing` |

---

## The gate (D-8) — dedicated coverage

| Property | Test |
|----------|------|
| `CURATED_SURFACES == {DIGEST}`; `APP_PAGE` excluded (D-8 definition pinned) | `test_gate.CuratedSurfacesTests.test_pins_the_d8_definition_to_digest_only` |
| curated (DIGEST impression at/before as_of) → weight-eligible | `test_gate::test_curated_when_a_qualifying_impression_exists`, `test_services::test_curated_rater_stores_weight_eligible` |
| evidence read raises → fail-closed (`CURATION_UNVERIFIED`), metric, **no propagation** | `test_gate::test_fails_closed_and_loud_when_the_evidence_read_raises` |
| `has_impression` surface filter (DIGEST ≠ APP_PAGE) + inclusive `as_of` boundary | `test_has_impression.HasImpressionTests::*` (7 tests) |

---

## Security (DESIGN §7)

| Concern | Test |
|---------|------|
| no IDOR (own-data-only; remove touches only the caller's row) | `test_services.RemoveRatingTests.test_remove_only_touches_the_callers_row` (the URL carries no rating id — structural) |
| CSRF required on writes | `test_views::test_post_without_csrf_is_403` |
| wrong method rejected | `test_views::test_get_is_405_for_authenticated_user` |
| XSS — review_text auto-escaped | rendered via `{{ review.review_text }}` (no `\|safe`); `test_templatetags` renders user text through the page |
| catalog read failure propagates loud (not swallowed) | `test_services::test_catalog_read_that_raises_propagates_loud` |

---

## Failure modes (DESIGN §8)

| Mode | Expected | Test |
|------|----------|------|
| gate (signals) read fails | fail-closed + `RATING_GATE_UNVERIFIED`, rating still stores | `test_gate::test_fails_closed_…`, `test_services::test_gate_unverified_still_stores` |
| DB write fails mid-transaction | atomic rollback, no partial row | `test_services::test_write_is_atomic_no_partial_row_on_failure` |
| display selector fails | fail-soft degraded slot + `RATING_DISPLAY_DEGRADED`, page still 200s | `test_templatetags::test_selector_error_degrades_the_slot_without_500ing_the_page` |
| author account deleted | row anonymized, renders "a former user" | `test_selectors::test_anonymized_author_renders_a_placeholder`, `test_models::test_user_fk_is_set_null_on_deletion` |

---

## Edge cases covered

- Empty: app with 0 ratings (empty distribution, empty list, empty state).
- Boundary: score range ends rejected (0 and `scale_max`+1); `as_of` exactly at the impression instant counts, one second before does not.
- Limit: more ratings than `reviews_display_limit` → exactly `limit` rows returned; count
  still reflects all (`test_selectors::test_honours_the_limit`).
- Concurrency-shape: unique `(user, app_id)` constraint + `update_or_create` prevent duplicates
  (AC8); bounded query count asserted (`test_selectors::test_runs_in_a_bounded_query_count`).
- Multi-user: different users keep separate rows; remove is caller-scoped.

---

## Regression checklist (areas touched outside `apps/ratings/`)

- [x] `apps/signals/selectors.py` — additive `has_impression` only; existing funnel selectors
      untouched (full `apps.signals` suite green, 67 tests).
- [x] `apps/signals/models.py` + migration `0003` — additive index only (AddIndex);
      up→down→up rehearsed; no column/data change.
- [x] `apps/pages/templates/pages/app_page.html` — slot-6 content-only edit; all six slots +
      the `Reviews` `aria-label`/heading intact (`test_templatetags::test_app_page_keeps_its_six_slots_…`);
      `apps.pages` suite green.
- [x] `apps/core/config.py` + `observability.py` — additive tunables/constants only;
      `apps.core` + `apps.signals` config tests green.
- [x] `config/urls.py` — additive `ratings/` include (the activation switch).
