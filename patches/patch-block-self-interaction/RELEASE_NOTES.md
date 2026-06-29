# RELEASE_NOTES.md — patch-block-self-interaction

**Status:** Built + verified local/dev. Released 2026-06-29.
**Resolves:** Q-002 (self-review blocked) · Q-003 (self-follow blocked).
**Tests:** 1013 green (+9 new) · ruff clean · check clean · no schema drift.

## What changed

**Service-layer guards (trust boundary)**

- `catalog.selectors.is_app_owner(user, app_id) -> bool` — new single source of truth for ownership; one EXISTS query, anonymous-safe.
- `ratings.errors.SelfRatingError` — new error class raised before any write when owner submits a rating.
- `ratings.services.submit_rating` — `_require_non_owner` guard added after `_require_catalogued_app`; raises `SelfRatingError`.
- `ratings.views.submit` — `except SelfRatingError` clause added (before `RatingValidationError`); surfaces as `messages.error` + PRG.
- `subscriptions.errors.SelfFollowError` — new error class raised before any write when owner follows their own app.
- `subscriptions.services.follow_app` — `_require_non_owner` guard added after `_require_catalogued_app`; raises `SelfFollowError`.
- `subscriptions.views.follow` — `except SelfFollowError` clause added (before broad `except Exception`); surfaces as `messages.error` + PRG.

**Template-layer UX (cooperating hide)**

- `ratings.templatetags.ratings_tags.app_reviews` — computes `is_owner` via `catalog.is_app_owner`; included in both normal and degraded context dicts.
- `ratings/templates/ratings/_reviews_slot.html` — authenticated owner sees "You can't review your own app." notice instead of the submit form; Remove form still shown if a pre-existing rating exists (cleanup path).
- `subscriptions.templatetags.subscriptions_tags.app_follow` — computes `is_owner` via `catalog.is_app_owner`; included in both context dicts.
- `subscriptions/templates/subscriptions/_follow_slot.html` — authenticated owner: if no pre-existing follow → slot is empty (no Follow button); if pre-existing follow → Unfollow button only (cleanup path).

## No-Schema Assertion

No migrations. No new or changed public API endpoints. No global ADR update. All changes are additive behaviour on existing endpoints and template slots.

## Rollback

No migration → rollback is `git revert <build-commit>` with zero DB operations. Rehearsed: stash → 157 targeted tests green on reverted tree → restored intact.

## Edge-case decision (BSI-D-1)

Pre-existing owner ratings/follows (created before this patch) are not retroactively deleted. Owners may remove/unfollow via the existing controls — see [DECISIONS.md](DECISIONS.md).
