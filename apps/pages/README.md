# apps/pages — public app pages

One **openly-accessible, structurally-uniform public page per accepted app**: it renders the
app's media, description, resolved category tags, and a try-it action, and captures try-it +
share as behavioral signal. The page doubles as each app's web home / press kit.

This app is a **pure consumer** — it owns **no model and no migration**. Its only persistence
is the D-7 rows written *through* `apps.signals.capture`. Content comes from the catalog
(read-only via D-6). See [DESIGN.md](../../features/app-pages/DESIGN.md).

## Routes (mounted under `apps/`)

| Name | Method | Auth | Behavior |
|------|--------|------|----------|
| `pages:app-page` (`apps/<uuid:app_id>/`) | GET | AllowAny | Render the uniform page for the accepted app; emit a page-view impression (authenticated, fail-soft). Non-accepted/unknown id → 404 `not_available.html`; a catalog read failure → loud 500. |
| `pages:try` (`apps/<uuid:app_id>/try`) | GET | AllowAny | Record a `click_through` (authenticated + valid `imp`, fail-soft), then **302 to the app's server-side stored URL** (never a request param — no open redirect). |
| `pages:share` (`apps/<uuid:app_id>/share`) | POST + CSRF | AllowAny | Record a `share` (authenticated, fail-soft); return **204**. |

URLs are keyed on the immutable `App.id` UUID (AP-5) so a shared link survives metadata edits.

## The emission policy ([emission.py](emission.py))

The one place the **surface-side non-blocking** rule lives — the complement of the signals
fail-loud contract (D-7 §5d). Two invariants, nothing else:

1. **Authenticated-only (AP-4)** — `request.user.is_authenticated` gates all capture. Anonymous
   visitors get the full page (AC5) but generate no events (the D-7 corpus is keyed `user × App.id`).
2. **Fail-soft-but-counted (AC7)** — every `signals.capture.*` call is wrapped; any failure
   (infra down, or a forged/foreign `imp`) is caught, counted on `app_page_capture_degraded`,
   logged, and swallowed — render/redirect/share always proceed.

Ownership validation, the tag snapshot, and app validity stay inside `signals.capture` (one
source of truth) — emission holds no business logic beyond fetching the impression to link.

## Observability

`app_page_rendered{app_id}`, `app_page_not_available`, `app_page_capture_degraded{action}`
(in `apps/core/observability.py`), plus the reused D-7 funnel counters
(`impression_captured{surface=app_page}`, `click_through_captured`, `share_captured`,
`capture_error`). Render duration is logged per request.

## Rollback / operations

Additive, **no feature flag**. To disable: remove the `path("apps/", include("apps.pages.urls"))`
include from [config/urls.py](../../config/urls.py) — the pages vanish with **zero data
migration** (the app owns no schema). The one semi-permanent footprint is the additive
`Surface.APP_PAGE` enum value, which stays once any `app_page` impression exists (removing an
in-use choice would orphan rows). No `.env` keys are introduced — the feature has no tunables.
