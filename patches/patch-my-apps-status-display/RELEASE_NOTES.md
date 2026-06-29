# RELEASE_NOTES.md — patch-my-apps-status-display

## Summary

Resolves **UX-004** and **UX-006**: the developer's "My Apps" page now has a meaningful
heading, groups apps by lifecycle status, and provides a direct link to the public app page
for accepted apps.

## Who Is Affected

Developers who have submitted apps. No change to the API, admin, or public-facing surfaces.

## Changes

### `apps/catalog/templates/catalog/my_apps.html`
- H1 renamed: `"My submissions"` → `"My Apps"`.
- Subtitle updated to `"Submit and manage your apps and track their review status."`.
- Flat `{% for app in apps %}` loop replaced with a `{% regroup %}`-based structure that
  emits a section `<h2>` per status group: **Active**, **Awaiting Review**, **Needs Changes**,
  **Withdrawn**. Only groups with at least one app are rendered.
- Card heading demoted from `<h2>` to `<h3>` to maintain correct document outline under
  the new group headers.
- CTA section for non-rejected apps now shows a `"View live page"` button (primary, opens
  in new tab) when `app.status == 'accepted'`, followed by the existing `"Manage Submission"`
  button.

### `apps/catalog/views.py`
- Added module-level constant `_MY_APPS_STATUS_ORDER` after `_decorate_apps`.
- `my_apps_page` sorts the decorated list by this priority before rendering so that
  `{% regroup %}` produces groups in the correct order: Active → Awaiting Review →
  Needs Changes → Withdrawn.
- `MyAppsView` (JSON API) is untouched — its ordering is unchanged.

### `apps/core/templates/core/base.html`
- Nav link label updated: `"My submissions"` → `"My Apps"` to match the page heading.

## Tests

4 new regression tests in `DeveloperPagesTests`:
- `test_my_apps_heading_says_my_apps`
- `test_my_apps_status_grouping_shows_group_headers`
- `test_my_apps_accepted_app_has_live_page_link`
- `test_my_apps_pending_app_has_no_live_page_link`

Full suite: **1004 tests green** (+4). `ruff`, `manage.py check`, `makemigrations --check`
all clean.

## Rollback

No schema migration — rollback is `git revert <commit>`. Rehearsed: stashed patch →
clean check/no-drift/170 catalog tests green on reverted tree → restored intact.
