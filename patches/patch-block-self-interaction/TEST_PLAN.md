# TEST_PLAN.md — patch-block-self-interaction

## Suite result

**1013 tests — all green.** (+9 new tests from this patch; 1004 pre-existing tests unchanged.)

`ruff check` clean · `manage.py check` clean · `makemigrations --check` no drift (No-Schema Assertion confirmed).

## New tests added by this patch

| File | Test | What it guards |
|------|------|----------------|
| `apps/catalog/tests/test_selectors.py` | `IsAppOwnerTests.test_is_app_owner_returns_true_for_owner` | `is_app_owner` returns `True` for the owner |
| `apps/catalog/tests/test_selectors.py` | `IsAppOwnerTests.test_is_app_owner_returns_false_for_non_owner` | `is_app_owner` returns `False` for a non-owner |
| `apps/catalog/tests/test_selectors.py` | `IsAppOwnerTests.test_is_app_owner_returns_false_for_anonymous` | `is_app_owner` returns `False` for `AnonymousUser` |
| `apps/ratings/tests/test_services.py` | `SelfRatingTests.test_submit_rating_raises_self_rating_error_for_owner` | `submit_rating` raises `SelfRatingError` for owner; no row created |
| `apps/ratings/tests/test_views.py` | `OwnerSubmitBlockTests.test_submit_view_blocks_owner_with_message` | Submit view redirects owner with an error message; no `Rating` row |
| `apps/ratings/tests/test_templatetags.py` | `ReviewsSlotRenderTests.test_reviews_slot_shows_notice_for_owner` | Slot shows "can't review your own app" notice; no submit form |
| `apps/subscriptions/tests/test_services.py` | `SelfFollowTests.test_follow_app_raises_self_follow_error_for_owner` | `follow_app` raises `SelfFollowError` for owner; no row created |
| `apps/subscriptions/tests/test_views.py` | `OwnerFollowBlockTests.test_follow_view_blocks_owner_with_message` | Follow view redirects owner with an error message; no `Subscription` row |
| `apps/subscriptions/tests/test_templatetags.py` | `FollowSlotRenderTests.test_follow_slot_hides_button_for_owner` | Slot hides Follow button for owner (follow URL absent from HTML) |

## Regression coverage (pre-existing, confirmed green)

- All existing `apps.ratings.tests.*` — service write path, view PRG, gate, selectors, template tag, admin.
- All existing `apps.subscriptions.tests.*` — follow/unfollow write path, view PRG, feed, notices, selectors, template tag.
- All existing `apps.catalog.tests.*` — owner isolation (AC8), accepted-only catalogue (AC9), tag resolution (D-5).

## Rollback rehearsal (DU-REL-1)

Stashed the patch → `makemigrations --check` no drift + 157 targeted tests green on the reverted tree → restored intact. No migration means rollback is `git revert` of the build commit with zero DB operations.
