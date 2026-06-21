# TEST_PLAN — app-subscriptions

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (FEATURE_BRIEF §4, AC1–
AC9) to the automated test(s) that verify it, plus edge cases and a regression checklist.
See [phase-4-engineer.md](../../process/personas/phase-4-engineer.md).*

**Suite status:** full project suite **552 tests green** (+66 for this feature), `ruff` clean,
`makemigrations --check` clean, `manage.py check` clean. The new migration
`subscriptions/0001` rehearsed up→down→up.

Run this feature's tests: `python manage.py test apps.subscriptions` (plus the additive
catalog read: `apps.catalog.tests.test_selectors.GetCataloguedAppsTests`, and the config
tunable: `apps.core.tests.test_config.FollowedFeedPageSizeTests`).

---

## Acceptance criteria → tests

| AC | What it requires | Verifying test(s) |
|----|------------------|-------------------|
| **AC1** follow + idempotent + reflected | signed-in follow of an accepted app stores one row keyed user×app_id + exactly one `subscribe` event; re-follow is a no-op; the page reflects the state | `test_services.FollowAppTests.test_follow_creates_one_row_and_exactly_one_subscribe_event`, `::test_re_follow_of_a_current_follow_is_a_noop`, `::test_re_follow_after_unfollow_is_a_genuine_new_event`, `test_views.FollowViewTests.test_signed_in_follow_stores_and_redirects_to_the_page`, `test_templatetags.FollowSlotRenderTests.test_signed_in_not_following_sees_a_follow_form`, `::test_signed_in_following_sees_an_unfollow_form`, `test_models.SubscriptionShapeTests.test_unique_constraint_on_user_and_app` |
| **AC2** anonymous boundary, page renders | anonymous follow → sign-in redirect, no write; the app page still renders with "Sign in to follow" | `test_views.FollowViewTests.test_anonymous_follow_redirects_to_signin_and_writes_nothing`, `test_templatetags.FollowSlotRenderTests.test_anonymous_sees_a_signin_link_and_no_form` |
| **AC3** unfollow + idempotent | signed-in unfollow removes the row + PRG; unfollow-when-absent is a no-op | `test_services.UnfollowAppTests.test_unfollow_deletes_the_row_emits_no_event_and_reports_existed`, `::test_unfollow_when_absent_is_a_noop`, `test_views.UnfollowViewTests.test_unfollow_removes_the_row_and_redirects`, `::test_unfollow_when_not_following_still_redirects` |
| **AC4** feed + empty state, never errors | feed lists exactly current follows (most-recent first, D-6 data); no follows → clear empty state, no error | `test_selectors.FollowedAppsTests.test_returns_current_follows_most_recent_first`, `::test_empty_when_no_follows`, `::test_withdrawn_followed_app_is_silently_absent`, `::test_honours_the_limit`, `test_views.FeedViewTests.test_feed_lists_current_follows`, `::test_feed_empty_state_when_no_follows` |
| **AC5** one subscribe via capture, keyed user×App.id, no score | exactly one `subscribe` `EngagementEvent` per new follow through `signals.capture.*`; store has no score/weight/rank column | `test_services.FollowAppTests.test_follow_creates_one_row_and_exactly_one_subscribe_event`, `test_models.SubscriptionShapeTests.test_has_only_the_relationship_columns`, `::test_has_no_forbidden_columns` |
| **AC6** return via existing seams, no double-build | the feed's app links target `pages:app-page` so re-engagement flows through the existing `signal-capture` seams; this feature emits only `subscribe` | `test_views.FeedViewTests.test_feed_app_links_target_the_app_page` (+ the feature imports no return/re-engagement recorder — only `record_subscribe` in `services.py`) |
| **AC7** fail loud, state honest | capture failure rolls the follow back (no orphan row) + counts `CAPTURE_ERROR{kind=subscribe}`; the view surfaces it and the user is not-following | `test_services.FollowAppTests.test_capture_failure_rolls_back_the_follow`, `::test_capture_failure_increments_capture_error`, `test_views.FollowViewTests.test_capture_failure_shows_a_message_and_leaves_user_not_following` |
| **AC8** notice surface forward-compatible | the feed renders the notices region with a "No news yet" empty state and never errors on "no producer"; `Notice` DTO pins the contract | `test_views.FeedViewTests.test_feed_renders_the_notices_empty_state`, `test_notices.NoticesForAppsTests.test_returns_empty_for_any_input`, `test_notices.NoticeShapeTests.test_notice_exposes_exactly_the_five_contract_fields`, `::test_notice_is_frozen` |
| **AC9** deletion removes follows; events anonymized | account deletion CASCADEs the follow rows away while emitted `subscribe` events anonymize-not-purge (SC-10) | `test_models.AccountDeletionTests.test_deleting_the_account_removes_its_follow_rows`, `::test_deleting_one_account_leaves_another_users_follows_intact`, `test_services.AccountDeletionCorpusTests.test_deletion_removes_follows_but_anonymizes_the_subscribe_events`, `test_models.SubscriptionShapeTests.test_user_fk_is_cascade_on_deletion` |

---

## The atomic follow + emit (DESIGN §6.1/§14) — dedicated coverage

| Property | Test |
|----------|------|
| committed follow ⟺ committed `subscribe` event (M5 1:1 by construction) | `test_services::test_follow_creates_one_row_and_exactly_one_subscribe_event` |
| capture failure → the follow row does **not** persist (savepoint rollback), durable state not-followed | `test_services::test_capture_failure_rolls_back_the_follow` |
| capture failure counted by signals `_guard` as `CAPTURE_ERROR{kind=subscribe}` | `test_services::test_capture_failure_increments_capture_error` |
| re-follow after unfollow = a genuine new corpus fact (append-only D-7) | `test_services::test_re_follow_after_unfollow_is_a_genuine_new_event` |
| idempotent re-follow emits no second event | `test_services::test_re_follow_of_a_current_follow_is_a_noop` |
| unfollow emits **no** corpus event (OQ-3 = no D-7 `unfollow` kind) | `test_services::test_unfollow_deletes_the_row_emits_no_event_and_reports_existed` |

---

## Security (DESIGN §8)

| Concern | Test |
|---------|------|
| no IDOR (own-data-only; unfollow touches only the caller's row) | `test_services.UnfollowAppTests.test_unfollow_only_touches_the_callers_row` (URLs carry no subscription id — structural) |
| CSRF required on writes | `test_views.FollowViewTests.test_post_without_csrf_is_403` |
| wrong method rejected | `test_views.FollowViewTests.test_get_is_405` |
| typed uuid boundary | `test_views.FollowViewTests.test_non_uuid_path_is_404_at_routing` |
| app validated before any write; unknown/non-accepted → no write | `test_services.FollowAppTests.test_unknown_app_raises_and_stores_nothing`, `::test_non_accepted_app_raises`, `test_views.FollowViewTests.test_unknown_app_is_404`, `::test_non_accepted_app_is_404` |
| catalog read failure propagates loud (not swallowed) | `test_services.FollowAppTests.test_catalog_read_that_raises_propagates_loud` |
| XSS — app/notice text auto-escaped | `feed.html` / `_follow_slot.html` render via `{{ }}` (no `\|safe`) |

---

## Failure modes (DESIGN §9)

| Mode | Expected | Test |
|------|----------|------|
| capture/DB write fails mid-transaction | atomic rollback, no partial follow | `test_services::test_capture_failure_rolls_back_the_follow` |
| feed `followed_apps` read fails | fail-soft empty/degraded feed + `SUBSCRIPTION_FEED_DEGRADED`, page 200s | `test_views.FeedViewTests.test_feed_degrades_when_followed_apps_raises` |
| feed `notices_for_apps` fails | fail-soft "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`, page 200s | `test_views.FeedViewTests.test_feed_degrades_when_notices_raises` |
| follow-slot `is_following` fails | fail-soft degraded slot + `SUBSCRIPTION_CONTROL_DEGRADED`, app page still 200s; ratings slot unaffected | `test_templatetags.FollowSlotRenderTests.test_selector_error_degrades_the_slot_without_500ing_the_page`, `::test_follow_slot_failure_does_not_affect_the_reviews_slot` |
| account deleted | follow rows CASCADE away; `subscribe` events anonymize (SET_NULL/SC-10) | `test_services.AccountDeletionCorpusTests::*`, `test_models.AccountDeletionTests::*` |

---

## Edge cases covered

- Empty: user with 0 follows (empty feed state), `notices_for_apps([])` → `[]`.
- Withdrawn followed app: silently absent from the feed, never an error
  (`test_selectors::test_withdrawn_followed_app_is_silently_absent`).
- Limit: more follows than `followed_feed_page_size` → exactly `limit` rows
  (`test_selectors::test_honours_the_limit`).
- No N+1: feed query count is bounded and independent of follow count
  (`test_selectors::test_runs_in_a_bounded_query_count`); same for the bulk catalog read
  (`test_selectors.GetCataloguedAppsTests.test_does_not_n_plus_one`).
- Anonymous/`None`: `is_following` and `followed_apps` return False/`[]` without a query.
- Multi-user: unfollow and deletion are caller-scoped (a second user's follows survive).
- Config: `followed_feed_page_size` default / override / fail-loud-on-zero
  (`test_config.FollowedFeedPageSizeTests::*`).

---

## Regression checklist (areas touched outside `apps/subscriptions/`)

- [x] `apps/catalog/selectors.py` — additive `get_catalogued_apps(ids)` only; existing reads
      untouched; accepted-only + shape parity asserted; `apps.catalog` suite green.
- [x] `apps/pages/templates/pages/app_page.html` — one content-only insertion (a new
      `<section aria-label="Follow">` after the header + the `{% load subscriptions_tags %}`
      line); the existing six slots + the Reviews `aria-label`/heading intact
      (`test_templatetags::test_app_page_renders_follow_after_header_with_all_slots_intact`);
      `apps.pages`/`apps.ratings` suites green. The pages `test_template.py` slot-count
      assertions updated 6→7 (the sanctioned new slot — uniformity preserved).
- [x] `apps/core/config.py` + `observability.py` — additive tunable/constants only;
      `apps.core` config tests green.
- [x] `config/settings.py` `INSTALLED_APPS` — additive `apps.subscriptions` registration.
- [x] `config/urls.py` — additive `subscriptions/` include (one half of the activation switch).
- [x] `signals` / `accounts` — **unchanged**: this feature only *calls* `record_subscribe`
      and relies on the existing CASCADE-on-`account.delete()` + SC-10 posture.
