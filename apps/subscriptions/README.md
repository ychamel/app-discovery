# apps/subscriptions — app subscriptions (follow)

One **durable follow per user per app**, plus a personal **followed-apps feed**. Following an
accepted app records the relationship *and* emits exactly **one D-7 `subscribe` event** — the
on-platform signal the corpus measures (the Phase-2 user-side engagement loop). The feed gives
followers a reason to return; that return / re-engagement is captured by the **existing**
signal-capture seams, never re-implemented here (AC6).

This app **computes no score** — it records the relationship only; turning follows/returns into
a quality number is a downstream consumer's job. See
[DESIGN.md](../../features/app-subscriptions/DESIGN.md).

It owns **one mutable table**, `subscriptions_subscription` — the *current* follow, created and
removed but never versioned. The deliberate contrast with the append-only D-7 corpus (and with
ratings' SET_NULL): the `user` FK **CASCADE**s — a follow is live relationship state, removed
with the account, while the already-emitted `subscribe` events are owned by signals and
anonymize-not-purge under SC-10 (the two-owner split, AC9).

## Routes (mounted under `subscriptions/`)

| Name | Method | Auth | Behavior |
|------|--------|------|----------|
| `subscriptions:follow` (`subscriptions/apps/<uuid:app_id>/follow`) | POST + CSRF | `login_required` | Follow the app, then PRG-redirect to `pages:app-page`. Unknown/non-accepted app → 404 (AC1); capture/DB failure → message + redirect, state honestly **not-followed** (AC7). |
| `subscriptions:unfollow` (`subscriptions/apps/<uuid:app_id>/unfollow`) | POST + CSRF | `login_required` | Hard-delete the caller's follow, then redirect to the page (AC3). |
| `subscriptions:feed` (`subscriptions/feed`) | GET | `login_required` | The personal followed-apps feed: a notices region (empty until a producer) + the current follows, each linking to its app page (AC4/AC6/AC8). |

No subscription id ever appears in a URL: a follow is addressed by `request.user` + `app_id`,
so a user can only ever touch their own (no IDOR).

## The atomic follow + emit ([services.py](services.py))

`follow_app` / `unfollow_app` is the **only** place `Subscription` rows change, and `services`
is the only module that imports `signals.capture`. In `follow_app`, the follow row and its one
`subscribe` emit are written in **one `transaction.atomic()`**: a committed follow ⟺ a
committed `subscribe` event (M5's 1:1 is *structural*, not just measured). If the corpus emit
raises, the follow row rolls back with it — no orphan state, the durable result is correctly
not-followed (AC5/AC7), and signals' own `_guard` has counted `CAPTURE_ERROR{kind=subscribe}`.

Re-following a current follow is an idempotent no-op (no second row, no second event).
Re-following *after* an unfollow is a genuine new follow → a new event (each act of following
is its own append-only corpus fact). Unfollow emits **no** corpus event — there is no D-7
`unfollow` kind (OQ-3; additive later if a churn consumer ever needs it).

## Single read + the notice seam

- **Read:** [selectors.py](selectors.py) (`is_following` / `followed_apps`) is the only display
  surface. `followed_apps` resolves the most-recent `limit` follows to their D-6 shape via the
  additive bulk `catalog.get_catalogued_apps(ids)` — a bounded query count independent of the
  follow count (no N+1 at 100× follows). A withdrawn followed app is silently dropped.
- **Notices:** [notices.py](notices.py) (`Notice` DTO + `notices_for_apps`) is the
  **empty-until-producer** seam (AS-3 = option A). It returns `[]` today; when `developer-updates`
  (Phase 3) ships, it is **the one place to repoint** — the feed template renders `Notice`s
  unchanged. No producer/registry machinery is built (the producer is one named future feature).

## The Follow slot ([templatetags/subscriptions_tags.py](templatetags/subscriptions_tags.py))

`{% app_follow app %}` is the only coupling to the closed-out app-page template: a new
`<section aria-label="Follow">` after the header, viewer-state-driven (anonymous → "Sign in to
follow"; signed-in → Follow/Unfollow), so page uniformity holds. **Fail-soft:** any selector
error renders a degraded slot + `subscription_control_degraded` and never 500s the page.

## Observability ([apps/core/observability.py](../../apps/core/observability.py))

`subscription_followed` (M1/M2), `subscription_unfollowed` (M6), `subscription_follow_noop`
(idempotency health), and the three display fail-soft counters `subscription_feed_degraded` /
`subscription_notice_degraded` / `subscription_control_degraded`. The **one actionable alert**
is the **reused** signals `capture_error{kind=subscribe}` (M5 integrity) — not re-added here.

## Config tunables ([apps/core/config.py](../../apps/core/config.py))

`followed_feed_page_size()` (100) — the feed cap; cursor pagination is the named growth lever,
not built.

## Rollback / operations

Additive, **no feature flag**. Two-part rollback (the activation switch):

1. Remove the `<section aria-label="Follow">` + the `{% load subscriptions_tags %}` line from
   `apps/pages/templates/pages/app_page.html` (one-section revert).
2. Remove the `path("subscriptions/", include("apps.subscriptions.urls"))` include from
   [config/urls.py](../../config/urls.py).

With the feature off the app page renders exactly as before. If a full teardown is needed the
migration is reversible: `migrate subscriptions zero` drops `subscriptions_subscription` —
zero impact on other apps (design-for-deletion; subscriptions owns its own table, and the
only outside read is the additive, no-migration `catalog.get_catalogued_apps`).
