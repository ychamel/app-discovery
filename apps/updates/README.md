# apps/updates — the developer-updates channel

The single **producer** of developer→follower **update / early-access** notices (Phase-3
developer value; H2). A developer posts a notice about an app they own; it appears —
newest-first, to **only that app's current followers** — in the existing followed-apps feed,
filling the **AS-3** empty-until-producer seam that [`apps/subscriptions/`](../subscriptions/)
shipped against. Unlike the model-less consumers ([`apps/pages/`](../pages/),
[`apps/discovery/`](../discovery/), [`apps/dashboard/`](../dashboard/)), this app **owns one
table** (`updates_notice`) because a notice is durable authored content with no existing home.

## What it does

- **My channels** (`GET /updates/`, name `updates:my-channels`): the developer's *accepted*
  apps (the only apps that can have followers), each linking to its channel. Own-nothing → 200.
- **Channel** (`GET /updates/apps/<uuid>/`, name `updates:channel`): the post form, an
  **audience hint** ("Reaches N current followers"), and the owner's notices each with a
  Withdraw control. A non-owner/unknown id → 404 (indistinguishable).
- **Post** (`POST /updates/apps/<uuid>/post`, name `updates:post`): create an `update` or
  `early_access` notice, then PRG to the channel.
- **Withdraw** (`POST /updates/apps/<uuid>/notices/<uuid>/withdraw`, name `updates:withdraw`):
  hard-delete the caller's own notice, then PRG. It disappears from the channel **and** from
  every follower's feed on its next read.

## Design guarantees

- **The transparency line (AC6).** Posting confers **no reach and no signal**. This app
  **imports nothing from `signals`** — enforced structurally by
  [`tests/test_imports.py`](tests/test_imports.py) — so a notice is *content*, never a
  score-bearing D-7 signal the Quality Score could trust. The only corpus entries are a
  follower's **own** genuine returns via the existing `apps/pages` `APP_PAGE`/`page_reengagement`
  kinds — the user's action, which the developer cannot trigger at will.
- **Pull delivery, M5 = 0 structural (AC5).** Notices are keyed by `app_id`; the feed *pulls*
  notices for the apps a user already follows ([`subscriptions.notices.notices_for_apps`](../subscriptions/notices.py)
  → [`updates.selectors.published_notices_for_apps`](selectors.py)). The producer never
  enumerates followers, so a non-follower is **structurally** unreachable — there is no
  post-time fan-out and no per-user feed-item table.
- **Owner + role gated (AC1).** All four routes are `login_required` + `require_role(developer)`
  (D-3, fail-closed); every write gates ownership via `catalog.get_owned_app` (D-6). A
  non-owner id is a 404 identical to a genuine not-found (no ownership oracle, no IDOR — writes
  are addressed by `request.user` + `app_id` + a scoped `notice_id`).
- **Durable rate limit (AC8).** `post_notice` counts the author's own recent notices for the
  app within `updates_post_window_hours()` against `updates_max_posts_per_window()` — exact and
  multi-worker-correct from the durable rows, no cache infra. The count→create TOCTOU is an
  accepted spam-guardrail trade-off (no row lock).
- **No-import-cycle DAG.** The two packages reference each other only at two named seams —
  `subscriptions.notices → updates.selectors` (the feed pulls) and `updates.views →
  subscriptions.selectors.subscriber_count` (the audience hint) — and never form a module-load
  cycle (the producer core `selectors`/`models`/`services` imports nothing from `subscriptions`;
  `subscriptions.selectors`/`models` import nothing from `updates`). Proven in
  [`tests/test_seam.py`](tests/test_seam.py).
- **Failure split (§7).** The feed's producer read is caught by the *existing*
  `subscriptions.views._notices_fail_soft` → "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`
  (the feed never errors). On the channel, the audience hint and the notices list each fail
  **soft** (`UPDATES_AUDIENCE_DEGRADED` / `UPDATES_CHANNEL_DEGRADED`) so a degraded read never
  blocks posting; an unexpected post write fails **soft to the user** (message + PRG +
  `UPDATES_POST_FAILED`), never a 500.

## Modules

| File | Responsibility |
|---|---|
| [`models.py`](models.py) | `Notice` / `updates_notice` — the durable shape only (no logic). No score/`updated_at`/`withdrawn_at` column; `author` FK CASCADE; soft D-6 `app_id` ref. |
| [`selectors.py`](selectors.py) | The read API → frozen `PublishedNotice` DTOs: `published_notices_for_apps` (the AS-3 producer feed read, `limit`-bounded) + `notices_for_channel` (the owner manage list). |
| [`services.py`](services.py) | The **only** writer: `post_notice` (owner-gate + validation + rate-limit) / `withdraw_notice` (scoped hard delete, idempotent). Imports no `signals`. |
| [`errors.py`](errors.py) | `AppNotOwnedError` → 404, `InvalidNoticeError` / `RateLimitedError` → message + PRG. |
| [`views.py`](views.py) / [`urls.py`](urls.py) | Thin HTTP: gate, call service/selector, render/redirect. No ORM, no business logic. |
| `templates/updates/` | Server-rendered, no JS, all text auto-escaped (title/summary are untrusted dev input shown to followers — never `|safe`). |

## Configuration ([`apps/core/config.py`](../core/config.py))

`updates_feed_notice_limit` (50), `updates_max_posts_per_window` (5), `updates_post_window_hours`
(24), `updates_title_max_length` (120), `updates_summary_max_length` (4000) — all validated at
startup by `validate_all`.

## Observability ([`apps/core/observability.py`](../core/observability.py))

`UPDATES_NOTICE_POSTED{kind}` (M1), `UPDATES_NOTICE_WITHDRAWN`, `UPDATES_POST_REJECTED{reason}`
(M6 trend when `rate_limited`), `UPDATES_POST_FAILED` (the one alert), `UPDATES_CHANNEL_DEGRADED`,
`UPDATES_AUDIENCE_DEGRADED`. The **feed** producer-health signal reuses the existing
`SUBSCRIPTION_NOTICE_DEGRADED`. M5 (reach beyond followers = 0) is structural — asserted in
tests, no counter.

## Rollback (DESIGN §12 — honest)

This is the **first feature to repoint a *closed* app's seam**, so rollback is **not** a single
include-removal. The three-part revert:

1. Revert [`subscriptions/notices.py::notices_for_apps`](../subscriptions/notices.py) to the
   empty-seam body (`return []`) — the feed instantly returns to its empty-until-producer state.
2. Remove the `path("updates/", include("apps.updates.urls"))` line from
   [`config/urls.py`](../../config/urls.py).
3. Remove the `"apps.updates"` line from `INSTALLED_APPS`.

The `updates_notice` table and the `subscriptions_app_idx` index may remain inert or be migrated
down (`migrate updates zero`, `migrate subscriptions 0001`). The render `Notice` DTO and its
call site are unchanged across the repoint, so the feed is forward/backward compatible.
