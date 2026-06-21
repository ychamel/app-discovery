# RELEASE_NOTES — app-subscriptions

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway PostgreSQL database
(2026-06-21).* Sources: the verified Stage-4 build, [DESIGN.md §9/§10/§15](DESIGN.md)
(observability + rollout/rollback), [FEATURE_BRIEF.md §5](FEATURE_BRIEF.md) (success metrics /
error conditions), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9 coverage), and the reused contracts
[D-3](../../DECISIONS.md) (identity), [D-4](../../DECISIONS.md) (stack), [D-6](../../DECISIONS.md)
(`get_catalogued_app`), [D-7](../../DECISIONS.md) (the `subscribe` event kind + SC-10 deletion
rule). The `ratings-reviews` release ([ratings-reviews/RELEASE_NOTES.md](../ratings-reviews/RELEASE_NOTES.md))
is the precedent this mirrors — app-subscriptions is its near-twin.

---

## 1. What this release is

The platform's **user-side engagement loop** — the first thing that gives a signed-in user a
*reason to return* after their first visit (vision §3.1 / §5.4). Any signed-in user can
**follow** an accepted app ([D-6](../../DECISIONS.md)) from its page and return to a personal
**followed-apps feed** of those apps. Every new follow emits **exactly one** [D-7](../../DECISIONS.md)
`subscribe` `EngagementEvent` through the `signals.capture.*` write path — the on-platform
behavioral signal the future Quality Score consumes — recorded **raw, with no score, weight, or
rank** anywhere in this feature (AC5). It computes nothing on top of the corpus; it *causes* the
return/re-engagement signal and lets the **existing** `signal-capture` seams record it (AC6).

It ships as a **new Django app, `apps/subscriptions/`**, owning **one mutable table**
`subscriptions_subscription` (one current follow per `user × app` — the deliberate contrast with
the append-only D-7 behavioral corpus). It also ships a **forward-compatible, empty-until-producer
notice surface** in the feed (AS-3 = option A), ready for `developer-updates` (Phase 3) to fill
with no rework. It changes no existing feature's behavior and satisfies all nine acceptance
criteria AC1–AC9 (mapping in [TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since nothing pulled a user back after their first visit)

- **New app `apps/subscriptions/`, owning one mutable table `subscriptions_subscription`**
  ([DESIGN §4](DESIGN.md)) — one row per `(user, app_id)`, created on follow and **hard-deleted**
  on unfollow (the store is *exactly the current relationship* — one source of truth). Columns:
  `id` (UUID pk), `user` (FK), `app_id` (soft D-6 ref, no DB FK), `created_at`. **There is no
  `score`/`weight`/`rank` column** — AC5 is *structural*, not a convention (asserted by a
  no-scoring-field test). **No `updated_at`, no soft-delete** — a follow has no mutable attribute;
  it exists or it does not. The `(user, app_id)` **unique constraint** `subscriptions_one_per_user_app`
  makes the single follow state structural (AC1 idempotency). Migration **`subscriptions/0001_initial`**.
- **`user` FK is `on_delete=CASCADE`** ([DESIGN §4.2](DESIGN.md)) — **the deliberate contrast with
  ratings' `SET_NULL`**. A follow is *live relationship state*, not corpus, so `account.delete()`
  ([accounts/services.py:58](../../apps/accounts/services.py)) removes the user's follow rows
  automatically — **with no edit to `accounts`** (the deletion boundary is owned by the FK). The
  already-emitted `subscribe` corpus events are owned by `signals` and anonymize-not-purge under
  **SC-10** — unchanged. Live relationship state is *removed*; behavioral corpus is
  *retained-but-unlinked*; each by its owner, no new corpus-deletion behavior invented here (AC9).
- **The single write path + the transactional coupling** ([DESIGN §5a/§6.1](DESIGN.md)) —
  `services.follow_app` / `unfollow_app` are the only place `Subscription` rows are mutated **and**
  the only module that imports `signals.capture`. `follow_app` validates the app via D-6
  `get_catalogued_app` (`UnknownAppError` → 404 if not accepted), then in **one
  `transaction.atomic()`** does `get_or_create` + (only when `created`) `record_subscribe`. So a
  committed follow row ⟺ a committed `subscribe` event for the same `(user, App.id)`: **M5's 1:1 is
  by construction, not merely measured** (AC5). A capture failure rolls the follow row back too —
  **no orphan state** — and `capture._guard` counts `CAPTURE_ERROR{kind=subscribe}`; the view
  surfaces the failure and the durable state is correctly *not-followed* (AC7 — fail-loud write). A
  re-follow of a current follow emits nothing (idempotent); `unfollow_app` is a hard delete that
  emits **no** corpus event (OQ-3 — §below).
- **The single read path** ([DESIGN §5c/§6.2](DESIGN.md)) — `selectors.is_following(user, app_id)`
  is one indexed `EXISTS` (False for anonymous); `selectors.followed_apps(user, *, limit)` returns
  the user's current follows most-recent-first, resolved to their D-6 shape. It is **bounded and
  N+1-free**: two queries total (the indexed follow read capped at `followed_feed_page_size()`, then
  one bulk catalog read) regardless of follow count — asserted by a query-count test.
- **The additive bulk catalog read `catalog.get_catalogued_apps(ids)`** ([DESIGN §4.3](DESIGN.md))
  — accepted-only, same `CatalogApp` shape, the no-N+1 feed primitive. It is an **additive D-6
  read-surface extension** (mirrors how `signals` gained `funnel_for_apps` and `ratings` added
  `signals.has_impression`), **not** a contract change — **no migration, no new global ADR**;
  recorded as the feature-local note AS-DESIGN-1.
- **The empty-until-producer notice seam** ([DESIGN §5d/§6.3](DESIGN.md), AS-3 = option A) —
  `notices.Notice` (a frozen DTO: `app_id`, `kind`, `title`, `summary`, `published_at`) is **the
  render contract `developer-updates` must honor**, and `notices.notices_for_apps(ids)` is the
  single call site that produces them. Today it returns `[]` (no producer exists). It is the **one
  place** to repoint when `developer-updates` (Phase 3) ships — **no feed rework** (AC8). The
  *shape* and *call site* exist and render; only the *data* is empty — the honest-MVP pattern.
- **Thin `login_required` HTTP views** ([DESIGN §5f/§6.4](DESIGN.md)) —
  `POST /subscriptions/apps/<App.id>/follow` (`subscriptions:follow`),
  `POST /subscriptions/apps/<App.id>/unfollow` (`subscriptions:unfollow`), both PRG-redirecting
  back to `pages:app-page`; and `GET /subscriptions/feed` (`subscriptions:feed`). **No subscription
  id appears in any URL** — a follow is addressed by `request.user` + `app_id`, so a user can only
  ever touch their own (**no IDOR, structural**). Anonymous POST → redirect to sign-in (AC2). CSRF
  on every form. Mounted under its own `/subscriptions/` prefix (no fall-through with the pages
  `apps/` include). The feed view wraps both the catalog read and the notice read **fail-soft**:
  any fault renders the degraded/empty feed (+ `subscription_feed_degraded` / `_notice_degraded`)
  and never 500s (AC4 — "never an error").
- **The Follow slot — a fail-soft inclusion tag** ([DESIGN §5f/§7](DESIGN.md), resolves OQ-4) —
  `{% app_follow app %}` renders, for the current viewer: an anonymous "Sign in to follow" prompt
  (AC2), a one-click **Follow** form for a signed-in non-follower, or an **Unfollow** form if
  already following (AC1/AC3 state reflected). It is **fail-soft**: any selector error degrades only
  the slot (+ `subscription_control_degraded`) and **never** breaks the page render (preserving
  `app-pages` AC5). It lives in a **new `<section aria-label="Follow">` immediately after the
  `<header>`** in `app_page.html` (Follow becomes slot 2; the existing Reviews slot is untouched).
  It is **viewer-state-driven, not app-state-driven**, so the page-uniformity invariant holds — the
  slot is identical for every accepted app; only the *viewer's* auth/follow state varies.
- **Read-only admin** ([DESIGN §5i](DESIGN.md)) — follow visibility for operability; the admin
  offers **no** add/change/delete path (writes go only through `services`, so a follow can never
  exist without its `subscribe` event).
- **Shared-surface touches** — one config tunable (`followed_feed_page_size()` default 100,
  validated by the existing `validate_all()`) and six metric constants (§7 below) added to
  `apps/core`; `apps.subscriptions` added to `INSTALLED_APPS`; the
  `path("subscriptions/", include("apps.subscriptions.urls"))` **activation switch** added to
  `config/urls.py`; one **content-only** edit to `app_page.html` (the Follow section + a
  `{% load subscriptions_tags %}` line). `apps/accounts`, `apps/signals`, `apps/pages` reused
  **as-is**; `apps/catalog` gained only the additive `get_catalogued_apps` read. **No new `.env`
  key.** No existing behavior changed (the one sanctioned cross-feature regression update was
  `apps/pages` `test_template.py` slot-count 6→7 — the new Follow section; uniformity preserved).

## 3. Who is affected

- **Signed-in users** — can now follow any accepted app (one-click, from its page), unfollow it,
  and return to a personal followed-apps feed of those apps. The follow *action* requires sign-in;
  the *page* does not.
- **Any visitor (anonymous included)** — sees a "Sign in to follow" prompt on every accepted app
  page; the page renders fully either way (AC2 / app-pages AP-1 preserved).
- **The platform / the corpus** — from the **first** follow there now exists an on-platform
  return-driving relationship and, per follow, exactly one `subscribe` behavioral event. This is the
  signal the Quality Score's *primary* inputs (return rate @3d/@14d, retention — vision §3.1) are
  earned from; the whole `signal-capture` SC-7 pivot was predicated on this loop existing.
- **The future Quality Score + analysts** — M3 (follow-driven return) and M4 (feed→re-engagement)
  are **derived by analysts** from the D-7 corpus (`signals.selectors.*`) joined to the follow
  store — **not computed here** (no scoring in this layer).
- **`developer-updates` (Phase 3, unbuilt)** — inherits the `notices.Notice` render contract and
  the single `notices_for_apps` repoint seam. Until it ships, the feed's notices region always shows
  the **"No news yet"** empty state (R1 — correct, and the loop still drives return via the feed).
- **Support** — no support-facing change at this release (local/dev target).

## 4. How to use it (operators)

The rollout is the ordered, additive steps from [DESIGN.md §15](DESIGN.md) — no new env var, no
feature flag, no recurring job:

1. `python manage.py migrate subscriptions` — applies `subscriptions/0001_initial` (creates
   `subscriptions_subscription`). The additive `catalog.get_catalogued_apps` is a pure read — **no
   migration**.
2. `python manage.py check` — must report no issues before the surface is considered live.
3. Deploy the build (which includes `apps.subscriptions` in `INSTALLED_APPS`, the
   `{% app_follow app %}` Follow section in `app_page.html`, and the
   `path("subscriptions/", include("apps.subscriptions.urls"))` activation switch in
   `config/urls.py`). The Follow slot, the follow/unfollow routes, and the feed go live on deploy.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with `identity-accounts`,
> `interest-taxonomy`, `submission-intake`, `signal-capture`, `app-pages`, and `ratings-reviews`
> ([CONTROL.md](../../CONTROL.md)); the platform is still mid-development. The feature is verified
> locally (**552 tests green**, `check` clean, `subscriptions/0001` applies and reverses cleanly).
> **Production promotion and a live-metrics monitoring window are deferred** until there is a
> production target and real traffic.

This is an **additive new app**: nothing existing changes behavior, so there is **no pre-existing
surface to ramp against and nothing to feature-flag off** (an honest deviation from the
internal→%→full template — DESIGN §15). Safety comes from the **two-part activation switch** + the
**one reversible, additive migration**, not a kill switch. **"Off" = remove the `config/urls`
include + the `app_page.html` Follow section** (zero data migration; the table can be dropped
separately by reversing `0001`). Backward-compatible: with the feature off, the app page renders
exactly as today.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate subscriptions` applied through `0001`; `subscriptions_subscription`, `subscriptions_one_per_user_app` (unique), and `subscriptions_user_created_idx` present; `manage.py check` clean. |
| Surface live | the three `subscriptions:*` routes resolve; the Follow slot renders inside `app_page.html` for an accepted app; an anonymous page view still renders fully (AC2). |
| Write path correct | a signed-in follow on an accepted app stores exactly one row keyed user×app **and** emits exactly one `subscribe` event in one transaction (M5 1:1); a re-follow is a no-op (no second row, no second event — AC1); an unknown/withdrawn-app follow is rejected with nothing stored (`UnknownAppError` → 404). |
| Capture integrity = 1:1 | `subscription_followed` count == `subscribe` events emitted; `capture_error{kind=subscribe}` reads **0**. |
| Display correct | the feed lists current follows + the "No news yet" / "not following any apps yet" empty states (AC4/AC8); `subscription_feed_degraded` / `_notice_degraded` / `_control_degraded` read 0. |
| Stable at target | the above holds with `capture_error{kind=subscribe}` = 0 and no sustained `_degraded` metrics, through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**Two surface touches + one reversible migration** ([DESIGN §15](DESIGN.md)):

1. Remove the `<section aria-label="Follow">` `{% app_follow app %}` section (and the
   `{% load subscriptions_tags %}` line) from `app_page.html` — the Follow control vanishes, the page
   is unchanged otherwise.
2. Remove the `path("subscriptions/", include("apps.subscriptions.urls"))` include from
   `config/urls.py` — the follow/unfollow/feed routes vanish with **zero data migration**.

If the schema must also be undone (design-for-deletion — `subscriptions` owns its own table; the
only outside footprint is the additive `get_catalogued_apps` read, which has no schema):

```bash
python manage.py migrate subscriptions zero    # drops subscriptions_subscription
```

The already-emitted `subscribe` corpus events are owned by `signals` and are unaffected by this
rollback (append-only; they remain attributable until SC-10 anonymization) — correctly, the
behavioral fact that follows *happened* is not erased by removing the follow surface.

**Rehearsed 2026-06-21** on a throwaway PostgreSQL database (`subs_release_rehearsal`, dropped
afterward): `migrate` applied `subscriptions/0001` → `subscriptions_subscription`, the
`subscriptions_one_per_user_app` unique constraint, the `subscriptions_user_created_idx` index, and
the CASCADE `user` FK to `accounts_account` all present → `manage.py check` clean; then `migrate
subscriptions zero` **unapplied cleanly** (table confirmed gone) and a re-`migrate` **re-applied** it
(confirmed reversible **up→down→up**); `makemigrations --check` reports no drift. The three
`subscriptions:*` routes resolve. **Who can trigger:** any operator with deploy access (the two
surface touches) — the DB step additionally needs DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; the six new constants live in
`apps/core/observability.py`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| **M1 follow adoption / M2 follows per user** | `subscription_followed` — a new follow created. | Trend, not an alert (the baseline this feature establishes). |
| **M5 subscribe-capture integrity (AC5/AC7)** | `subscribe` events emitted == `subscription_followed`; `capture_error{kind=subscribe}` for the follow write path. The 1:1 is **structural** (one transaction). | **`capture_error{kind=subscribe}` nonzero → page** (the one actionable alert — the corpus is incomplete / the write path is unhealthy; a follow that didn't capture rolled back, so no *silent* gap, but a sustained rate means the capture dependency is degraded). |
| **M6 unfollow rate** | `subscription_unfollowed` — a follow removed. | Trend — sustained high churn is a product signal (weak per-app value), not an ops alert. |
| **Idempotency health** | `subscription_follow_noop` — a re-follow of a current follow (no row, no event). | Trend. |
| **M3 follow-driven return @3d/@14d (the headline) / M4 feed re-engagement** | **Derived by analysts** from the D-7 corpus (`signals.selectors.*`) joined to the follow store — *not computed here* (no scoring in this layer). Expected **thin** until adoption grows and `developer-updates` supplies notices (R1) — visible, not hidden. | None in this layer (analyst-derived). |
| **Feed / notice / control display health** | `subscription_feed_degraded` / `subscription_notice_degraded` / `subscription_control_degraded` — a read fell back to its degraded/empty state (fail-soft; the page/feed still rendered). | A sustained rise means a read dependency (catalog / future notice producer / `is_following`) is unhealthy; the page is unaffected. |

## 8. Verification at release (2026-06-21)

- **552 automated tests pass** (486 baseline + 66 new subscriptions tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model drift.
- Rollout→rollback **rehearsed** on a throwaway PostgreSQL DB (§6): `migrate` applied
  `subscriptions/0001` (table + unique constraint + index + CASCADE `user` FK confirmed present) →
  `check` clean → `migrate subscriptions zero` reversed it cleanly (table confirmed gone) →
  re-`migrate` re-applied it (reversible up→down→up). Throwaway DB dropped after.
- The three `subscriptions:follow` / `:unfollow` / `:feed` routes resolve; the six observability
  constants and the `followed_feed_page_size()` tunable exist; both halves of the activation switch
  (the `config/urls` include + the `app_page.html` Follow section) are present.
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 to tests; the transactional coupling
  (capture-failure rollback), no-IDOR, anonymous boundary, feed/control fail-soft, the no-scoring
  structural guarantee, the 2-query feed bound, and the AC9 CASCADE-deletion case are each exercised
  by a dedicated test.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §8/§11/§14/§15](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **The notice surface is empty at MVP (R1).** No producer exists yet (`developer-updates` is
  Phase 3), so the feed's notices region always shows **"No news yet"**. This is **correct behavior,
  not a bug** — the forward-compatible seam (`Notice` DTO + the single `notices_for_apps` repoint)
  is the value; the follow + feed still give a return reason and generate the `subscribe`/return
  signal. The loop's strongest pull (news) lands when `developer-updates` ships, with no feed rework.
- **Unfollow has no D-7 corpus representation (OQ-3, resolved NO at MVP).** D-7 has no `unfollow`
  kind; unfollow is modeled as the *absence* of a current follow (the mutable store is the source of
  truth) plus the `subscription_unfollowed` metric for M6. Adding an `unfollow` `EventKind` is a
  global-contract change with **no consumer today** — it stays **additive** if a future churn
  consumer ever needs it ([DESIGN §8](DESIGN.md)). Named, not built.
- **The `subscribe` event carries no impression attribution at MVP.** `record_subscribe` is called
  without an `impression` link; the event keyed `user × App.id` satisfies AC5 and every metric.
  Linking *which shown instance* drove the follow is purely additive (`record_subscribe` already
  accepts an optional `impression`) — named, not built ([DESIGN §6.1](DESIGN.md)).
- **No feed pagination.** The feed is capped at `followed_feed_page_size()` (default 100),
  most-recent-first. Cursor pagination is a one-place change in `followed_apps` + the template if a
  user follows thousands ([DESIGN §10](DESIGN.md)) — named, not built.
- **No public follower counts / social graph (by design, R4).** Follow state is private to the user;
  deletion removes it (AC9). Public counts are explicitly out of scope.
- **No live-metrics window measured.** Deferred with the local/dev target until a production target
  and real traffic exist (mirrors the six prior closed-out features).

## 10. Stakeholder notification

On the first real (production) promotion: notify downstream feature owners that the user-side
follow loop is **live and emitting** — every new follow now records one [D-7](../../DECISIONS.md)
`subscribe` event through `signals.capture.*`, keyed `user × App.id`, raw (no score/weight/rank).
Hand `developer-updates` (Phase 3) its two inheritances: the `notices.Notice` render contract and
the single `notices_for_apps` repoint seam — filling it requires **no feed rework**. Remind analysts
/ the future Quality Score that **M3 (follow-driven return) and M4 (feed re-engagement) are theirs
to derive** from the D-7 corpus joined to the follow store — **nothing is scored in this layer**
(AC5). No support-facing change at this release — the local/dev target carries no production traffic.
