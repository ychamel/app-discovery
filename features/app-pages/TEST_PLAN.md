# TEST_PLAN — app-pages

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion (AC1–AC9) from
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) §4 and [DESIGN.md](DESIGN.md) §14 to the automated
test(s) that exercise it. Tests live under `apps/pages/tests/` (plus the `Surface.APP_PAGE`
additive extension verified in `apps/signals/tests/`).*

Run: `python manage.py test apps.pages apps.signals` (or the whole suite,
`python manage.py test`).

---

## Acceptance-criterion coverage

| AC | What it requires | Automated test(s) |
|----|------------------|-------------------|
| **AC1** | Page shows name, description, ordered media, `resolve_tag`'d categories, and a try-it action linking to the app's URL | `test_template.FullyPopulatedTests.test_all_core_content_present`; `test_views.AppPageRenderTests.test_anonymous_gets_full_page_no_auth_wall` |
| **AC2** | Every slot still renders in the uniform layout with a defined empty/absent state (one image, no tags) — no broken/collapsed slot | `test_template.EmptyAndPartialStateTests` (`test_no_tags_shows_uncategorized`, `test_no_media_shows_placeholder_and_all_slots`, `test_single_image_renders_and_keeps_all_slots`) |
| **AC3** | Any two apps use the same template/slots/order; no slot or styling varies by identity/team/paid status (structural — no such input) | `test_template.StructuralUniformityTests` (`test_two_different_apps_render_identical_slot_order`, `test_dto_has_no_owner_team_or_paid_field`) |
| **AC4** | Stable, shareable URL that survives metadata edits; self-contained public home (no login wall) | `test_template.PressKitAndAccessibilityTests.test_canonical_url_is_present_and_copyable`; routes keyed on `App.id` (all `reverse("pages:…", args=[app.id])` in `test_views`); AP-5 (URL = immutable `App.id`) |
| **AC5** | An anonymous visitor opening a page by direct link gets the full page, no auth required | `test_views.AppPageRenderTests.test_anonymous_gets_full_page_no_auth_wall`; `test_emission.RecordPageViewTests.test_anonymous_captures_nothing_and_returns_none` |
| **AC6** | Try-it / share recorded **through `signals.capture.*`** keyed to `App.id`; the page never writes `signals_*` directly | `test_views.TryRedirectTests.test_authenticated_try_records_click_through_linked_and_302s`; `test_views.ShareTests.test_authenticated_share_records_event_and_returns_204`; `test_views.AppPageRenderTests.test_authenticated_view_emits_app_page_impression`; `test_emission.*` (capture is the only write seam) |
| **AC7** | If capture is unavailable/errors, the page still renders and try-it/share still work; the loss is counted, not hidden, not blocking | `test_views.CaptureFailureIsNonBlockingTests.test_render_redirect_share_survive_capture_failure`; `test_emission` (`test_capture_failure_is_caught_counted_and_returns_none`, `RecordTryClickTests.test_mismatched_impression_is_caught_no_raise`, `RecordShareTests.test_capture_failure_is_caught_no_raise`) |
| **AC8** | A `pending`/`rejected`/`withdrawn`/unknown id is **not** rendered as a live entry → not-available/not-found | `test_views.NotAvailableTests` (`test_unknown_id_is_404_and_counted`, `test_pending_app_is_404`, `test_non_uuid_path_is_404_at_routing`); `test_views.TryRedirectTests.test_try_on_unknown_app_is_404`; `test_views.ShareTests.test_share_on_unknown_app_is_404` |
| **AC9** | The reviews slot shows a defined empty state; the page captures/stores/displays no rating data | `test_template.ReviewsSlotTests.test_reviews_empty_state_present_no_rating_data` |

Every AC is exercised by ≥1 automated test.

## Design-specific guarantees (DESIGN §6/§7/§10/§11)

| Guarantee | Test(s) |
|-----------|---------|
| **AP-3** page view = `app_page`-surface impression; try-it/share link to it | `test_views.AppPageRenderTests.test_authenticated_view_emits_app_page_impression`; `test_views.TryRedirectTests.test_authenticated_try_records_click_through_linked_and_302s`; `apps/signals/tests/test_capture_impression.RecordImpressionTests.test_app_page_surface_is_accepted` |
| **AP-4** capture authenticated-only; render anonymous | `test_emission` anonymous cases; `test_views` anonymous render/try/share (no event) |
| **§7** catalog read = loud 500 (not hidden) | `test_views.NotAvailableTests.test_catalog_read_failure_is_a_loud_500` |
| **§10** no open redirect (target is server-side `CatalogApp.url`) | `test_views.TryRedirectTests.test_redirect_target_is_server_side_not_a_request_param` |
| **§10** no attribution forgery (forged/foreign `imp` → no event, still redirects) | `test_views.TryRedirectTests.test_foreign_impression_writes_no_event_but_still_redirects` |
| **§10** CSRF on share; GET on share is 405 | `test_views.ShareTests` (`test_share_without_csrf_is_403`, `test_share_get_is_405`) |
| **§11** `Surface.APP_PAGE` additive + reversible migration | `apps/signals/tests/test_kinds.SurfaceTests.test_exactly_the_known_surfaces`; migration `0002` reversibility rehearsed (`migrate signals 0002 → 0001 → 0002`) |
| **§2/§4** owns no model (never adds a migration) | `test_scaffold.ScaffoldTests.test_app_owns_no_model`; `makemigrations --check` clean |

## Edge cases covered

- **Empty / partial:** no tags → "Uncategorized"; no media → placeholder; single image —
  all six slots still present (`test_template.EmptyAndPartialStateTests`).
- **Malformed input:** a malformed/absent `imp` query/POST param is treated as absent (no
  link, no error) — `views._parse_imp`, exercised by the anonymous and empty-`imp` view tests.
- **Forged / cross-user:** a foreign impression id yields no event but still redirects
  (`test_views.TryRedirectTests.test_foreign_impression_writes_no_event_but_still_redirects`).
- **Failure injection:** `signals.capture` patched to raise on impression/click/share — page
  still 200, try still 302, share still 204; loss counted
  (`test_views.CaptureFailureIsNonBlockingTests`, `test_emission` failure cases).
- **Wrong method / non-UUID routing:** share GET → 405; `/apps/not-a-uuid/` → 404 at routing.

## Regression checklist (areas touched)

- `apps/signals/kinds.Surface` + migration `0002_alter_impression_surface` — full
  `apps.signals` suite green; reversibility rehearsed; `makemigrations --check` clean.
- `apps/core/observability.py` — three constants added; existing metric tests unaffected.
- `config/settings.INSTALLED_APPS` + `config/urls.py` — `manage.py check` clean; whole suite
  green.

**Status:** full suite green (`python manage.py test`), `ruff` clean, no migration drift.
