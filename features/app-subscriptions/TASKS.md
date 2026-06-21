# TASKS — app-subscriptions

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-13 → approved) and the approved [DESIGN.md](DESIGN.md) (DN-14 → approved; reuses
[D-3](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md) as-is — **no new
global ADR**). Produces an ordered, independently-verifiable task list; full per-AC verification
is written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a
> contract or decision the design does not already make. The only schema touch is one **additive**
> migration creating `subscriptions_subscription` inside the new `apps/subscriptions/` (DESIGN §4);
> the only touch outside the new app is one **additive** `catalog.selectors.get_catalogued_apps(ids)`
> read (DESIGN §4.3, no migration) and the one sanctioned Follow-slot insertion in `app_page.html`
> (DESIGN §5f). This feature is **a near-twin of the closed-out `apps/ratings/`** — match its
> conventions (CLAUDE.md §5.5) with the three DESIGN §1 deliberate contrasts: **CASCADE** deletion
> (T-02), the **one atomic** follow-write + `subscribe` emit (T-03), and the **empty-until-producer
> notice seam** (T-05).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces → UI → telemetry → docs.** Spine: the additive bulk
   catalog read the feed depends on (T-01) → the feature's own `Subscription` store (T-02) → the
   integrity core, the single write path with its atomic coupling (T-03) → the single read path
   (T-04) → the notice seam (T-05) → the thin HTTP views + feed template + activation include
   (T-06) → the app-page Follow slot that surfaces the control (T-07) → read-only admin + docs
   (T-08).
2. **Risk first.** The two genuinely coupling-heavy seams the design front-loads (DESIGN §1/§14)
   land early and are verified in isolation before any UI work: **(1)** the new mutable
   **CASCADE** store (T-02 — the AS-5/AC9 contrast with ratings' SET_NULL, verified by a
   deletion test); **(2)** the **atomic follow-write + its one `subscribe` emit** (T-03 — M5 1:1
   by construction, AS-DESIGN-2, verified with a forced-capture-failure rollback test). The
   closed-out-template edit (the third self-critique target) is isolated to **T-07**, a
   content-only one-section insertion with a one-section rollback.
3. **Each task leaves the system working and releasable.** T-01 is an inert additive read. T-02 is
   a new model + migration with no routes. T-03/T-04/T-05 add unreached code paths. The feed
   becomes reachable at T-06 (the `config/urls.py` include) but is not yet linked from the app
   page; the follow control appears only at T-07. **The activation switch** is the `config/urls.py`
   include (T-06) **plus** the one `{% app_follow app %}` section in `app_page.html` (T-07) —
   "off" = remove both (DESIGN §15).

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/core/observability.py` is touched by **T-03** (`SUBSCRIPTION_FOLLOWED`/`_UNFOLLOWED`/
  `_FOLLOW_NOOP`), **T-06** (`SUBSCRIPTION_FEED_DEGRADED`/`_NOTICE_DEGRADED`) and **T-07**
  (`SUBSCRIPTION_CONTROL_DEGRADED`); they run in order, never concurrently.
- `apps/core/config.py` is touched once (**T-04**: `followed_feed_page_size`).
- `apps/catalog/selectors.py` once (**T-01**); `config/settings.py` `INSTALLED_APPS` once
  (**T-02**); `config/urls.py` once (**T-06**); `apps/pages/templates/pages/app_page.html` once
  (**T-07** — independent of the existing ratings slot; no shared state, no collision).
- The reused `signals.capture.record_subscribe` write path and `signals` SC-10 deletion posture
  are **unchanged** — this feature only *calls* them (T-03).

---

## T-01 — Additive bulk catalog read `catalog.get_catalogued_apps(ids)` (no N+1 feed primitive)

- **Description.** Add `get_catalogued_apps(app_ids: list[UUID]) -> list[CatalogApp]` to
  `apps/catalog/selectors.py` exactly per the DESIGN §4.3 contract — a **bulk, accepted-only**
  by-ids read over the same base queryset as `list_catalogued_apps`/`get_catalogued_app`, reusing
  the existing `_resolve_tag_labels` + `_to_catalog_app` helpers and `prefetch_related("media",
  "app_tags")` so resolving N followed apps is **2 queries, not O(N)**. Non-accepted/unknown ids
  are silently absent (the caller orders + handles gaps — T-04). This is an **additive D-6
  read-surface extension** (AS-DESIGN-3): it preserves the accepted-only guarantee and the
  `CatalogApp` shape, mirrors `signals.funnel_for_apps` (bulk) beside `app_funnel` (single), and is
  **not a new global ADR**. No migration, no model change.
- **Dependencies.** none (foundational — the feed read in T-04 consumes it).
- **Definition of done.**
  - `catalog.selectors.get_catalogued_apps` exists and is unit-tested: given a mix of accepted,
    non-accepted (`pending`/`rejected`/`withdrawn`), and unknown ids, returns **only** the accepted
    apps as `CatalogApp`; unknown/non-accepted ids are silently absent; an empty input → `[]`.
  - Returned `CatalogApp`s carry the same resolved fields (name, tags via D-5, media, url) as
    `get_catalogued_app` for the same app (shape parity).
  - **No N+1:** a fixture with N accepted apps resolves in a **bounded** query count independent of
    N (a `assertNumQueries` test).
  - Existing `apps/catalog` suite green; `ruff` clean; full suite green; `makemigrations --check`
    reports **no** new migration (pure read).
- **Estimated size.** S.
- **Files/areas touched.** `apps/catalog/selectors.py`, `apps/catalog/tests/` (a new
  `get_catalogued_apps` test).

## T-02 — Scaffold `apps/subscriptions` + the `Subscription` store (CASCADE) + migration

- **Description.** Create the new Django app per DESIGN §2/§4.1: `__init__.py`, `apps.py`
  (`AppConfig`, `name="apps.subscriptions"`), `tests/`. Register `"apps.subscriptions"` in
  `INSTALLED_APPS`. Implement `apps/subscriptions/models.py` exactly to the DESIGN §4.1/§4.2
  contract — **the first deliberate contrast with ratings (CASCADE):**
  - `Subscription` — `id` (UUID pk, default `uuid4`), `user` FK **`on_delete=CASCADE`** (the
    AS-5/AC9 contrast with ratings' SET_NULL — a follow is live relationship state, removed when
    the account is, with **no edit to `accounts`** — DESIGN §4.2), `app_id` (`UUIDField`, **soft
    D-6 ref, no DB FK** — a later app withdrawal must not cascade-erase the follow), `created_at`
    (`auto_now_add`).
  - **Structural absences (AC5/CLAUDE.md §5.3):** **no** `score`/`weight`/`rank` column (AC5
    structural); **no** `updated_at` (a follow has no mutable attribute); **no** `unfollowed_at`/
    soft-delete (unfollow is a hard delete — the store is exactly the current relationship).
  - `Meta`: `db_table="subscriptions_subscription"`; `ordering=["-created_at"]`; the **unique
    constraint** `subscriptions_one_per_user_app` on `(user, app_id)` (AC1 — one follow per
    user×app; CASCADE means no `user=NULL` rows, so this is a clean composite unique); the feed
    index `subscriptions_user_created_idx` on `(user, created_at)`.
  - **No business logic in the model** — all invariants (idempotency, the corpus emit) are enforced
    by the write path (T-03). The model declares shape only.
  - Generate `subscriptions/0001_initial`.
- **Dependencies.** none (independent of T-01; both precede T-03/T-04).
- **Definition of done.**
  - `apps.subscriptions` imports and appears in `INSTALLED_APPS`; `python manage.py check` clean.
  - `makemigrations subscriptions` produces `0001_initial` creating `subscriptions_subscription`
    with the unique constraint + index; `makemigrations --check` clean after commit.
  - A **structural test** asserts: the unique constraint on `(user, app_id)` is present (AC1); the
    `user` FK `on_delete` is **CASCADE** (DESIGN §4.2); the table has **no**
    score/weight/rank/updated_at/unfollowed_at column (AC5 / one-job).
  - **AC9 deletion test:** create follow rows for a user via the ORM, call
    `accounts.delete_account(account)` ([accounts/services.py:58](../../apps/accounts/services.py)),
    assert the user's `Subscription` rows are **gone** (CASCADE) with no edit to `accounts` — and
    (since this test creates no events) the assertion is purely about follow-state removal; the
    `subscribe`-event SC-10 anonymize-not-purge half is verified in T-03's deletion test.
  - The migration is reversible: `migrate subscriptions 0001` → `migrate subscriptions zero` →
    `migrate subscriptions 0001` all succeed (DESIGN §15).
  - `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/subscriptions/` (new package: `__init__.py`, `apps.py`,
  `models.py`, `migrations/0001_initial.py`, `tests/__init__.py`, `tests/test_models.py`),
  `config/settings.py` (`INSTALLED_APPS`).

## T-03 — The single write path: `services.py` (`follow_app`/`unfollow_app`) + `errors.py` + the atomic emit

- **Description.** Implement `apps/subscriptions/services.py` (+ `apps/subscriptions/errors.py`)
  exactly to the DESIGN §5a/§6.1/§6.2 contract — **the only place `Subscription` rows are
  created/deleted, and the only module that imports `signals.capture`.** This is the second
  deliberate contrast and the riskiest seam (AS-DESIGN-2 / DESIGN §14 — the transactional
  coupling); build and verify it before any UI work:
  - `follow_app(user, app_id: UUID) -> bool` — returns `True` iff a **new** follow was created:
    1. `_require_catalogued_app(app_id)` via `catalog.selectors.get_catalogued_app`; `None` →
       raise `UnknownAppError` (AC1; view → 404). A catalog read that **raises** (DB down)
       propagates loud.
    2. **`with transaction.atomic()`**: `Subscription.objects.get_or_create(user, app_id)`; **iff
       `created`** call `signals.capture.record_subscribe(user, app_id)` ([capture.py:214](../../apps/signals/capture.py))
       **inside the same transaction** — so a committed follow ⟺ a committed `subscribe` event
       (M5 1:1 **by construction**, AC5), and a capture failure rolls back the follow row too (no
       orphan state). `record_subscribe` is called **without** an impression link at MVP (DESIGN
       §6.1 — optional in D-7, additive later; flagged §15, not built).
    3. **Outside** the txn (so a rolled-back follow never counts): increment
       `SUBSCRIPTION_FOLLOWED` if `created` else `SUBSCRIPTION_FOLLOW_NOOP`.
  - `unfollow_app(user, app_id) -> bool` — `Subscription.objects.filter(user, app_id).delete()`;
    hard, idempotent (no row → no-op, AC3); **no app-validity check** (allow cleaning up a
    withdrawn app); **no corpus event** (OQ-3 = no D-7 `unfollow` kind — DESIGN §8); increment
    `SUBSCRIPTION_UNFOLLOWED` only when a row existed (M6).
  - `errors.py`: `UnknownAppError` (raised before any write).
  - Add `SUBSCRIPTION_FOLLOWED`/`SUBSCRIPTION_UNFOLLOWED`/`SUBSCRIPTION_FOLLOW_NOOP` constants to
    `apps/core/observability.py` (DESIGN §9.4). The `CAPTURE_ERROR{kind=subscribe}` metric is
    already owned by `signals` — **reused, not re-added.**
- **Dependencies.** T-01 (the catalog read surface), T-02 (`Subscription` store).
- **Definition of done.** Tests against the **real catalog + real `signals.capture`** (catalog
  fixtures; capture patched only to force the failure case):
  - **AC1** signed-in follow of an accepted app → one `Subscription` row keyed `(user, app_id)`
    **and exactly one** `subscribe` `EngagementEvent`; `follow_app` returns `True`;
    `SUBSCRIPTION_FOLLOWED` emitted.
  - **AC1 idempotent** re-follow of an already-followed app → **no** second row, **no** second
    event, returns `False`, `SUBSCRIPTION_FOLLOW_NOOP` emitted.
  - **re-follow after unfollow** (row was deleted) → a genuine new follow → one new event (each act
    of following is its own corpus fact — append-only D-7).
  - **AC5/AC7 atomic rollback** — with `record_subscribe` patched to raise: `follow_app` propagates,
    **no `Subscription` row persists** (the get_or_create rolled back), and
    `CAPTURE_ERROR{kind=subscribe}` was counted by `capture._guard` — the durable state is
    correctly *not-followed*.
  - **AC1 unknown/withdrawn app** → `UnknownAppError`, nothing stored, no event.
  - **AC3** `unfollow_app` deletes the row, returns `True`, emits **no** event, increments
    `SUBSCRIPTION_UNFOLLOWED`; `unfollow_app` when absent → returns `False`, no-op.
  - **AC9 (corpus half)** delete a user who has follows **and** emitted `subscribe` events; assert
    the events are **anonymized-not-purged** (signals SET_NULL / SC-10) while the follow rows are
    gone (CASCADE) — confirms the two-owner split.
  - `ruff` clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/subscriptions/services.py` (new), `apps/subscriptions/errors.py`
  (new), `apps/core/observability.py` (three constants),
  `apps/subscriptions/tests/test_services.py`.

## T-04 — The single read path: `selectors.py` (`is_following`/`followed_apps`) + the feed page-size config

- **Description.** Implement `apps/subscriptions/selectors.py` exactly to the DESIGN §5c/§6.2
  contract — the one read surface (no write, no scoring):
  - `is_following(user, app_id) -> bool` — `False` for anonymous/`None`; one indexed `EXISTS` for a
    signed-in user (backs the inclusion tag, AC1).
  - `followed_apps(user, *, limit) -> list[CatalogApp]` — (1) the most-recent `limit` `app_id`s
    (`Subscription.filter(user).order_by("-created_at")[:limit]`); (2) **bulk** D-6 resolve via
    `catalog.get_catalogued_apps(app_ids)` (T-01); (3) re-order to follow-recency and **silently
    drop** any non-accepted (withdrawn) app. **Bounded (`limit`) + 2 queries total → no N+1 at
    100× follows** (DESIGN §3.2).
  - Add `config.followed_feed_page_size() -> int` (default 100) to `apps/core/config.py` (DESIGN
    §10) using the existing `_positive_int` precedence pattern; add its `validate_all()` entry. The
    feed view (T-06) passes `limit=config.followed_feed_page_size()`.
- **Dependencies.** T-01 (`get_catalogued_apps`), T-02 (`Subscription` store).
- **Definition of done.** Tests over fixtures:
  - **AC1** `is_following` → `True`/`False` for a signed-in user; `False` for anonymous/`None`.
  - **AC4** `followed_apps` returns the user's current follows **most-recent-first**; a withdrawn
    (non-accepted) followed app is **silently absent**; a user with no follows → `[]` (the
    empty-state data); honors `limit` (a fixture with > limit follows returns exactly `limit`).
  - **no N+1:** `followed_apps` runs in a **bounded** query count independent of follow count
    (`assertNumQueries`).
  - `config.followed_feed_page_size()` returns the default and is covered by `validate_all()`.
  - `ruff` clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/subscriptions/selectors.py` (new), `apps/core/config.py` (one
  tunable + `validate_all`), `apps/subscriptions/tests/test_selectors.py`.

## T-05 — The notice seam: `notices.py` (`Notice` DTO + `notices_for_apps` → `[]`)

- **Description.** Implement `apps/subscriptions/notices.py` exactly to the DESIGN §5d/§6.3
  contract — the **third deliberate contrast**, the empty-until-producer seam (AS-DESIGN-4 /
  AS-3 = option A):
  - `Notice` — a `@dataclass(frozen=True)` with `app_id: UUID`, `kind: str` (`"update"` |
    `"early_access"`), `title: str`, `summary: str`, `published_at: datetime`. **This is the
    render contract `developer-updates` (Phase 3) must honor — pinned now, no "TBD".**
  - `notices_for_apps(app_ids: list[UUID]) -> list[Notice]` — returns `[]` today (no producer
    exists). **This is the one place to repoint** when `developer-updates` ships; the feed template
    renders `Notice`s unchanged. **No** producer/registry/pluggable-provider machinery is built
    (that would be speculative — CLAUDE.md §5.5; one repointable function is the right seam).
- **Dependencies.** none (pure shape; the feed in T-06 consumes it). May proceed in parallel after
  T-02, but sequenced here for the spine.
- **Definition of done.**
  - `notices_for_apps([...])` returns `[]` for any input (including an empty list).
  - The `Notice` dataclass is frozen and exposes exactly the five fields above (a shape test —
    the contract is stable so `developer-updates` can build against it).
  - `ruff` clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/subscriptions/notices.py` (new),
  `apps/subscriptions/tests/test_notices.py`.

## T-06 — Thin HTTP views (`follow`/`unfollow`/`feed`) + `urls.py` + feed template + activation include

- **Description.** Implement `apps/subscriptions/views.py` + `apps/subscriptions/urls.py` +
  `apps/subscriptions/templates/subscriptions/feed.html` exactly to the DESIGN §5g/§6.4 contract,
  then add `path("subscriptions/", include("apps.subscriptions.urls"))` to `config/urls.py` — the
  first half of the activation switch (DESIGN §15; its own prefix, no collision). Views hold **no
  business logic and no ORM access** (parse → call service/selector → redirect/render — the
  pages/ratings house pattern):
  - `subscriptions:follow` → `subscriptions/apps/<uuid:app_id>/follow` (POST, `login_required`,
    CSRF): `services.follow_app` → **PRG redirect** to `pages:app-page`. `UnknownAppError` → **404**
    (AC1). Capture/DB failure → `messages.error("Couldn't complete that — please try again")` +
    PRG; the durable state is **not-followed** (AC7 — the slot still shows Follow). Anonymous POST →
    `login_required` redirect to the sign-in flow with `next=` (AC2).
  - `subscriptions:unfollow` → `subscriptions/apps/<uuid:app_id>/unfollow` (POST, `login_required`,
    CSRF): `services.unfollow_app` → PRG redirect to `pages:app-page` (AC3).
  - `subscriptions:feed` → `subscriptions/feed` (GET, `login_required`): render `feed.html` with
    `followed_apps(request.user, limit=config.followed_feed_page_size())` +
    `notices.notices_for_apps([...])`. **Both reads wrapped fail-soft (DESIGN §9):** a
    `followed_apps` error → degraded/empty feed + `SUBSCRIPTION_FEED_DEGRADED`; a `notices_for_apps`
    error → "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`; **never a 500** (AC4 "never an error").
  - `feed.html` — **two regions** (DESIGN §5g): a **notices region** (renders `notices`, else a
    clear "No news yet" empty state — AC8) and a **followed-apps region** (current follows
    most-recent-first, **each linking to `pages:app-page`** so a click flows through the *existing*
    re-engagement/visit seams — AC6; empty → "You're not following any apps yet" + a browse pointer
    — AC4). All app-supplied text rendered through Django auto-escaping (no `|safe`).
  - **No IDOR (DESIGN §8):** no subscription id in any URL — a follow is addressed by
    `request.user` + `app_id`. CSRF on both POSTs.
  - Add `SUBSCRIPTION_FEED_DEGRADED` + `SUBSCRIPTION_NOTICE_DEGRADED` to
    `apps/core/observability.py` (DESIGN §9.4).
- **Dependencies.** T-03 (`follow_app`/`unfollow_app`), T-04 (`followed_apps` + the page-size
  config), T-05 (`notices_for_apps`).
- **Definition of done.** Integration tests (Django test client, project URLconf with the include):
  - **AC1** signed-in POST `.../follow` on an accepted app → row stored + PRG redirect to the app
    page; POST on an unknown/non-accepted app → **404**.
  - **AC2** anonymous POST `.../follow` → redirect to the sign-in flow with `next=`; **no write**.
  - **AC3** signed-in POST `.../unfollow` → row removed + PRG redirect.
  - **AC4** `subscriptions:feed` for a user with ≥1 follow → lists exactly the current follows
    (most-recent-first), each linking to `pages:app-page`; for a user with no follows → the defined
    empty state, **no error**.
  - **AC6** the feed's app links target `pages:app-page` (so re-engagement is captured by existing
    seams — this feature emits no return/re-engagement event).
  - **AC7** with `follow_app` forced to fail capture → the view shows an error message and the user
    is **not** following (state honest).
  - **AC8** the feed renders the notices region with the "No news yet" empty state (no producer).
  - **fail-soft:** with `followed_apps` patched to raise → the feed view renders a degraded/empty
    feed (no 500) and increments `SUBSCRIPTION_FEED_DEGRADED`; with `notices_for_apps` patched to
    raise → "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`.
  - wrong method (GET on follow/unfollow) → 405; POST without CSRF → 403.
  - `manage.py check` clean; `ruff`/template lint clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/subscriptions/views.py` (new), `apps/subscriptions/urls.py` (new),
  `apps/subscriptions/templates/subscriptions/feed.html` (new), `config/urls.py` (the include),
  `apps/core/observability.py` (two constants), `apps/subscriptions/tests/test_views.py`.

## T-07 — The app-page Follow slot: the `app_follow` inclusion tag + partial + the one `app_page.html` edit

- **Description.** Implement the Follow-slot integration exactly to the DESIGN §5f contract
  (resolves OQ-4) — the third self-critique target (the closed-out-template edit), isolated here
  and **content-only**:
  - `apps/subscriptions/templatetags/subscriptions_tags.py` —
    `@register.inclusion_tag("subscriptions/_follow_slot.html", takes_context=True) def
    app_follow(context, app)`: for the **current viewer** computes
    `is_following(request.user, app.id)` and returns `{request, app, is_following}`. **Fail-soft
    (DESIGN §5f/§9):** any selector error → a degraded slot (no control) + `SUBSCRIPTION_CONTROL_DEGRADED`,
    **never raises into the page render** (preserves `app-pages` AC5 — the page renders even if
    subscriptions degrade).
  - `apps/subscriptions/templates/subscriptions/_follow_slot.html` — renders, inside a **new**
    `<section aria-label="Follow">`: **anonymous** → a "Sign in to follow" link to the auth flow
    with `next=<this page>` (AC2), no button; **signed-in, not following** → a one-click **Follow**
    POST form (CSRF) → `subscriptions:follow`; **signed-in, following** → an **Unfollow** POST form
    → `subscriptions:unfollow` (AC1/AC3 state reflected). The page still renders fully for an
    anonymous viewer (pages owns the render; this tag adds one section).
  - The **one sanctioned edit** to `apps/pages/templates/pages/app_page.html` (DESIGN §5f): insert a
    **new `<section aria-label="Follow">` immediately after the `<header>`** (so Follow becomes slot
    2; media→3 … Reviews→7) calling `{% app_follow app %}`, and add `{% load subscriptions_tags %}`
    near the top. The existing six slots' **content is unchanged** (the ratings slot-6 fill is
    untouched); this **inserts** one section. **Viewer-state-driven, not app-state-driven**, so the
    page-uniformity invariant (every accepted app renders the same slots — app-pages AC3) holds: the
    slot is identical for every app; only the viewer's auth/follow state varies. **Rollback** =
    remove the one section + the `{% load %}` line (one-section revert).
  - Add `SUBSCRIPTION_CONTROL_DEGRADED` to `apps/core/observability.py` (DESIGN §9.4).
- **Dependencies.** T-04 (`is_following`), T-06 (the `subscriptions:follow`/`unfollow` route names
  the forms target).
- **Definition of done.** Render tests (the tag in isolation + the `app_page` page via the test
  client, with `apps.subscriptions.urls` included):
  - **AC2** anonymous render → the Follow section shows "Sign in to follow" (link with `next=`),
    **no form**; the page renders fully.
  - **AC1** signed-in, not-following render → a **Follow** form posting to `subscriptions:follow`.
  - **AC1/AC3** signed-in, following render → an **Unfollow** form posting to
    `subscriptions:unfollow` (state reflected).
  - **fail-soft:** with `is_following` patched to raise → the slot renders degraded (no control),
    `SUBSCRIPTION_CONTROL_DEGRADED` incremented, and **the rest of the page still renders** (no
    500); the ratings slot is unaffected (independent tags).
  - **uniformity:** a structural test confirms the app page renders the Follow section after the
    header for every app and the existing Reviews/other slots' `aria-label`s/headings/order are
    intact (app-pages AC3 preserved).
  - `ruff`/template lint clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/subscriptions/templatetags/__init__.py` + `subscriptions_tags.py`
  (new), `apps/subscriptions/templates/subscriptions/_follow_slot.html` (new),
  `apps/pages/templates/pages/app_page.html` (the one Follow-section insertion + `{% load %}`),
  `apps/core/observability.py` (one constant), `apps/subscriptions/tests/test_templatetags.py`.

## T-08 — Read-only admin, README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: a thin read surface + docs + index — no behavioural change to the
  feature paths (DESIGN §5 admin / §15).
  - `apps/subscriptions/admin.py` — a **read-only** `Subscription` admin (list `app_id`, `user`,
    `created_at`; no add/edit — writes go only through `services`, DESIGN §5a invariant). Mirrors
    the signals/ratings read-only admin pattern.
  - `apps/subscriptions/README.md` — the app's single responsibility (follow state + one
    `subscribe` emit, no scoring), the three routes, "owns one mutable table
    `subscriptions_subscription` (**CASCADE** on account delete)", the atomic follow+emit coupling,
    the empty-until-producer notice seam, and the **rollback** (remove the `config/urls`
    `subscriptions/` include + the `app_page.html` Follow section; if needed `migrate subscriptions
    zero`).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: `subscriptions.services.*`
    (the write path), `subscriptions.selectors.*` (`is_following`/`followed_apps`),
    `subscriptions.notices.*` (`Notice` DTO + `notices_for_apps` — the `developer-updates` seam),
    the **new** `catalog.selectors.get_catalogued_apps` (additive D-6 bulk read), the
    `subscriptions:*` route names, the `{% app_follow %}` tag, the new `followed_feed_page_size`
    config tunable, and the new observability constants.
  - [features/app-subscriptions/DECISIONS.md](DECISIONS.md) — mark **AS-DESIGN-1…4** and the
    OQ-3/OQ-4 resolutions as **built**. Note the named-not-built revisit flags (impression linkage
    on `subscribe`; the OQ-3 `unfollow` corpus kind; feed cursor pagination; the notice producer
    repoint) per DESIGN §15.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit
    artifact, produced alongside the build, not in this task.
- **Dependencies.** T-01…T-07.
- **Definition of done.** `apps/subscriptions/admin.py` registers a read-only `Subscription` admin
  (a test or `check` confirms no add/change perms); `README.md` matches the shipped routes/store/
  rollback; `CODEMAP.md` lists every new shared surface above; `DECISIONS.md` marks AS-DESIGN-1…4 +
  OQ-3/OQ-4 built; `makemigrations --check` clean; **full suite green, `ruff` clean, no drift** (the
  close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/subscriptions/admin.py` (new), `apps/subscriptions/README.md`
  (new), [CODEMAP.md](../../CODEMAP.md), `features/app-subscriptions/DECISIONS.md`,
  `apps/subscriptions/tests/test_admin.py` (optional read-only assertion).

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §4.3 additive bulk read `catalog.get_catalogued_apps(ids)` (no N+1, no migration) | **T-01** |
| §4.1 `Subscription` store + unique constraint + feed index; structural no-score/no-updated_at (AC5) | **T-02** |
| §4.2 lifecycle + **CASCADE** on account delete (the AS-5/AC9 contrast) | **T-02** (shape + deletion) + **T-03** (create/delete) |
| §5a/§6.1 single write path `follow_app` + the **atomic** follow + `record_subscribe` emit (M5 1:1) | **T-03** |
| §6.2 `unfollow_app` (hard-delete, idempotent, no corpus event — OQ-3) + `errors.UnknownAppError` | **T-03** |
| §5c/§6.2 single read path `is_following`/`followed_apps` (bulk D-6, accepted-only, no N+1) | **T-04** |
| §5d/§6.3 the notice seam `notices_for_apps` → `[]` + the `Notice` DTO (AS-3 = A) | **T-05** |
| §5g/§6.4 thin views (`follow`/`unfollow`/`feed`) + `urls` + `config/urls` include; feed template two regions; no-IDOR | **T-06** |
| §5f the `{% app_follow %}` inclusion tag + partial (fail-soft) + the one `app_page.html` Follow-slot insertion (OQ-4) | **T-07** |
| §8 security (login_required, own-data-only/no IDOR, typed uuid boundary, CSRF, autoescape) | **T-03** (boundary) + **T-06** (auth/CSRF/no id) + **T-07** (autoescape) |
| §9 failure modes (loud write/atomic rollback · fail-soft feed/notice/control) | **T-03** + **T-06** + **T-07** |
| §9.4 observability constants (`FOLLOWED`/`UNFOLLOWED`/`FOLLOW_NOOP`/`FEED_DEGRADED`/`NOTICE_DEGRADED`/`CONTROL_DEGRADED`) | **T-03** + **T-06** + **T-07** |
| §10 config tunable `followed_feed_page_size` | **T-04** |
| §5 read-only admin surface | **T-08** |
| §15 rollout/rollback (additive, no flag, design-for-deletion) + CODEMAP/docs + AS-DESIGN-1…4 / OQ-3/OQ-4 built | **T-08** |
| §13 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-02+T-03+T-06+T-07; AC2 → T-06+T-07; AC3 → T-03+T-06+T-07; AC4 → T-04+T-06;
AC5 → T-02+T-03; AC6 → T-06 (feed links via existing seams); AC7 → T-03+T-06; AC8 → T-05+T-06;
AC9 → T-02 (CASCADE)+T-03 (corpus SC-10 half). All nine acceptance criteria are covered; **no `L`
tasks**; every task has a checkable definition of done and declared files.
