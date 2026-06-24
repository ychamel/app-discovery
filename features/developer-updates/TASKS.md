# TASKS — developer-updates

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-20 → approved) and the **ratified** [DESIGN.md](DESIGN.md) (DN-DU-DESIGN → approved;
DU-DESIGN-1…6 ratified; reuses
[D-3](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md) + the **AS-3**
producer contract as-is — **no new global ADR**). Produces an ordered, independently-verifiable
task list; full per-AC verification is written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`.
See [phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a contract
> or decision the design does not already make. Three kinds of change exist here:
> 1. **A new feature-owned app `apps/updates/` that owns one table `updates_notice`** (DESIGN
>    §4/§5.1, DU-DESIGN-3 — unlike the model-less `pages`/`discovery`/`dashboard` consumers, this
>    app *owns* durable authored content, so it needs a table and an `INSTALLED_APPS` line). It is
>    the single **AS-3 producer**. It **imports nothing from `signals.capture`** (AC6 structural —
>    DESIGN §8, the `apps/discovery` precedent).
> 2. **The AS-3 seam repoint** — `subscriptions.notices.notices_for_apps` changes its *body* (not
>    its signature or call site) to delegate to `updates.selectors` and map `PublishedNotice → the
>    `subscriptions`-owned `Notice` (the single adapter, DU-DESIGN-2). This is exactly the one repoint
>    AS-3 promised; the feed template renders `Notice`s unchanged.
> 3. **One additive, contract-preserving edit to the closed [app-subscriptions](../app-subscriptions/)
>    (`apps/subscriptions`)** — the reverse-audience selector `subscriber_count(app_id)` + its backing
>    `subscriptions_app_idx` index (DESIGN §5.2/§6.3, DU-DESIGN-6). Additive and reversible; **no new
>    column, no behaviour change** to existing follow reads/writes (the open-search-browse precedent of
>    adding indexes to the closed `catalog`).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces → UI → telemetry → docs.** The spine is: the
   `updates_notice` table + app registration (**T-01**) → the producer read selectors **and** the
   AS-3 seam repoint adapter (**T-02**) → the write path (services: post/withdraw, owner-gate,
   validation, durable rate-limit) (**T-03**) → the additive reverse-audience read + index on the
   closed `apps/subscriptions` (**T-04**) → the HTTP views + templates + the `config/urls` activation
   include + observability (**T-05**) → docs/CODEMAP/DECISIONS (**T-06**).
2. **Risk first (CONTROL.md hand-off; DESIGN §4/§10/§13).** The single load-bearing, most-uncertain
   piece is the **AS-3 producer seam on the *closed* `apps/subscriptions`** — the `PublishedNotice →
   Notice` adapter that must (a) keep the cross-package dependency a strict **DAG with no import
   cycle** (DESIGN §4/§13 — the headline self-critique), (b) preserve the feed's existing fail-soft
   wrapper (`_notices_fail_soft` → `SUBSCRIPTION_NOTICE_DEGRADED`, AC4/AC7 "the feed never errors"),
   and (c) render `Notice`s unchanged. It lands at **T-02**, immediately after the table exists, and
   is proven by an **import-cycle-absence test** + a **feed-integration test seeding `updates_notice`
   rows directly via the ORM** (no write path needed yet) — so the cycle/seam surprise surfaces as
   early as possible, before any UI is built. The `apps.subscriptions` suite stays green in its DoD
   (regression on the closed app).
3. **Each task leaves the system working and releasable.** **T-01** adds an inert, unrouted table
   (no view references it; the seam still returns `[]`). **T-02** repoints the seam to read
   `updates_notice` — in production there are **zero rows** until the write path ships, so the feed
   shows its existing empty state, identical to today (releasable, inert-until-rows). **T-03** adds
   the write path as un-routed services (reachable only by tests). **T-04** adds an inert selector +
   index to the closed app (no existing consumer changes). The surface becomes user-reachable **only
   at T-05** — the single `config/urls` `updates/` include is the last activation step (the
   `INSTALLED_APPS` line landed at T-01 for the migration, and the seam repoint at T-02, are both
   inert without the include). **T-06** is docs only.

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/updates/__init__.py` / `apps.py` / `models.py` / `migrations/0001_initial.py` — **T-01** only
  (the package scaffold + the `Notice` model + its initial migration).
- `apps/updates/selectors.py` — **T-02** only (`PublishedNotice` DTO + `published_notices_for_apps` +
  `notices_for_channel`).
- `apps/subscriptions/notices.py` — **T-02** only (the seam *body* repoint; the `Notice` DTO + the
  single call site in `subscriptions/views.py` are **untouched**).
- `apps/updates/services.py` / `errors.py` — **T-03** only (the only writer + its typed errors).
- `apps/subscriptions/selectors.py` + `apps/subscriptions/models.py` + `apps/subscriptions/migrations/0002_*`
  — **T-04** only (the additive `subscriber_count` read + the `subscriptions_app_idx` index +
  its migration).
- `apps/updates/views.py` / `urls.py` / `templates/updates/*.html` / `tests/test_imports.py` — **T-05**
  only (new).
- `apps/core/config.py` (+ `validate_all`) — **T-02** adds `updates_feed_notice_limit` (its only
  consumer is the seam adapter); **T-03** adds the four write-boundary tunables
  (`updates_max_posts_per_window` / `updates_post_window_hours` / `updates_title_max_length` /
  `updates_summary_max_length`). Two **sequential** edits, never concurrent.
- `apps/core/observability.py` — **T-03** only (declares all **six** `UPDATES_*` counter constants
  in one place; services increments three, T-05's views reference the other three — the feed-producer
  health signal reuses the **existing** `SUBSCRIPTION_NOTICE_DEGRADED`, not re-added).
- `config/urls.py` — **T-05** only (the one `updates/` include = the final activation step).
- `config/settings.py` `INSTALLED_APPS` — **T-01** only (`"apps.updates"`, needed for the T-01
  migration; the table is harmless/unrouted until T-05).

---

## T-01 — Scaffold `apps/updates/` + the `updates_notice` table + app registration (schema)

- **Description.** Create the new feature-owned app and its one table exactly per DESIGN §5.1
  (DU-DESIGN-3). Scaffold the package (`__init__.py`, `apps.py` with
  `AppConfig(name="apps.updates", label="updates")` mirroring `apps/subscriptions/apps.py`,
  `tests/__init__.py`) and add `"apps.updates"` to `INSTALLED_APPS` (required for the migration; the
  table is unrouted/inert until the T-05 include).
  - `models.Notice` (`db_table = "updates_notice"`, `ordering = ["-published_at"]`) with exactly the
    columns in DESIGN §5.1: `id` (UUID pk, `uuid4`, non-editable); `app_id` (`UUIDField`, a **soft D-6
    ref — no DB FK**, validated at the write boundary, mirroring `subscriptions`/`ratings`); `author`
    (`FK → AUTH_USER_MODEL`, **`on_delete=CASCADE`**, `related_name="notices"` — a notice is
    withdrawable content, not retained corpus, so account deletion removes it with no edit to
    `accounts`, the AS-5 pattern); `kind` (`CharField(choices=...)` over a `NoticeKind` choices class
    = exactly `"update"` | `"early_access"`, the pinned `subscriptions.notices.Notice.kind` enum,
    DU-1); `title` (`CharField(max_length=200)` — a **defensive DB cap**; the *product* limit is the
    config tunable validated at the boundary in T-03); `summary` (`TextField`); `published_at`
    (`DateTimeField(auto_now_add=True)`).
  - **Structural absences (DESIGN §5.1):** **no score/weight/rank column** (posting confers no corpus
    value, AC6), no `updated_at` (notices are immutable — edit is out of scope), no `withdrawn_at`
    (withdraw = hard delete; the store is *exactly* the currently-published set).
  - **Index:** `updates_app_published_idx` on `(app_id, published_at)` — backs all three reads (the
    AS-3 feed read, the owner manage list, the rate-limit window count), since `app_id` leads every
    query (DESIGN §5.1). (The global-`published_at` cross-app-ordering index is a **named growth seam,
    not built** — §5.1/§5.5.)
  - `migrations/0001_initial.py` — the table + the index; additive, reversible (`migrate updates
    zero` drops it cleanly).
- **Dependencies.** none (foundational).
- **Definition of done.**
  - `makemigrations` produces exactly `updates/0001_initial`; `makemigrations --check --dry-run`
    then reports **no** further changes (the model matches the migration); `migrate` applies it and
    `migrate updates zero` reverses it cleanly (reversible up→down→up) on a test DB.
  - Model-level tests: a `Notice` row persists all fields; `kind` accepts only the two `NoticeKind`
    values; `ordering` is newest-first; `db_table == "updates_notice"`; the
    `updates_app_published_idx` index is present (introspection or `Meta.indexes`); deleting the
    author account **cascades** to remove the notice (`account.delete()` removes the row, no edit to
    `accounts`).
  - The app is in `INSTALLED_APPS`; the package imports cleanly; the test runner discovers
    `apps/updates/tests/`. `ruff` clean; full suite green; **the existing `subscriptions` feed seam
    still returns `[]`** (unchanged — the seam is repointed in T-02).
- **Estimated size.** S.
- **Files/areas touched.** `apps/updates/__init__.py`, `apps/updates/apps.py`, `apps/updates/models.py`,
  `apps/updates/migrations/0001_initial.py` + `migrations/__init__.py`, `apps/updates/tests/__init__.py`
  + `tests/test_models.py` (new), `config/settings.py` (`INSTALLED_APPS += "apps.updates"`).

## T-02 — `updates.selectors` (the producer reads) + the AS-3 seam repoint adapter (the risk centerpiece)

- **Description.** Add the read API on the new app **and** repoint the AS-3 seam to it — the single
  vertical slice that makes `updates_notice` the AS-3 producer, exactly per DESIGN §6.1/§6.4
  (DU-DESIGN-1/DU-DESIGN-2). This is the **load-bearing, cycle-sensitive seam**; it lands here,
  immediately after the table exists, and is proven before any write path or UI.
  - **`apps/updates/selectors.py`:**
    - `PublishedNotice` (`@dataclass(frozen=True)`): `id: UUID` (for the owner's withdraw control,
      AC7; dropped by the feed adapter), `app_id: UUID`, `kind: str`, `title: str`, `summary: str`,
      `published_at: datetime`. Returns frozen DTOs, **never ORM rows**.
    - `published_notices_for_apps(app_ids: list[UUID], *, limit: int) -> list[PublishedNotice]` — the
      AS-3 producer read: `filter(app_id__in=...).order_by("-published_at")[:limit]`, **one query**,
      newest-first, `[]` for empty input; **bounded by `limit` and independent of follower count**
      (R3).
    - `notices_for_channel(owner, app_id: UUID) -> list[PublishedNotice]` — the owner's own notices
      for one app, newest-first (the AC7 manage list), **one query** (used by the T-05 channel view;
      added here with the other read since both are pure selectors).
  - **`apps/subscriptions/notices.py` — the seam repoint (the single adapter, DU-DESIGN-2):** change
    **only the body** of `notices_for_apps(app_ids) -> list[Notice]` to delegate to
    `updates.selectors.published_notices_for_apps(app_ids, limit=config.updates_feed_notice_limit())`
    and map each `PublishedNotice → the existing frozen `Notice` (drop `id`; carry `app_id`/`kind`/
    `title`/`summary`/`published_at`). The `Notice` DTO and its single call site
    (`subscriptions/views.py::_notices_fail_soft`) are **untouched**. Update the module docstring to
    note the producer now exists (the seam is no longer "empty-until-producer").
  - **`apps/core/config.py`:** add `updates_feed_notice_limit()` (default 50) following the house
    `_positive_int` pattern, and register it in `validate_all()`. Its **only** consumer is the seam
    adapter above.
- **Dependencies.** T-01 (the `Notice` model + table).
- **Definition of done.**
  - **Cycle-absence (the headline risk, DESIGN §4/§13):** a test asserts the cross-package
    dependency stays a DAG — `subscriptions.notices → updates.selectors → updates.models` and
    `subscriptions.selectors`/`models` import nothing from `updates`. Concretely: importing
    `apps.subscriptions.notices` and `apps.updates.selectors` in either order succeeds (no circular
    import at module load), and an AST/`pkgutil` check confirms no `apps.updates` module imports
    `apps.subscriptions` and `apps.subscriptions.selectors`/`models` import no `apps.updates`.
  - **Producer read:** seed `updates_notice` rows directly via the ORM (no write path needed yet) →
    `published_notices_for_apps([a, b], limit=n)` returns them newest-first, capped at `limit`, only
    for the given `app_id`s; `[]` for empty input; **one query** (`assertNumQueries`), constant at 5
    vs 50 seeded rows (R3, `limit`-bounded).
  - **Seam integration (AC4):** with seeded rows, `subscriptions.notices.notices_for_apps([app_ids])`
    returns `Notice` instances (not `PublishedNotice`) newest-first with the fields mapped and `id`
    dropped; `GET /subscriptions/feed` for a user following those apps renders the notices in the
    existing `feed.html` region (auto-escaped, no `mark_safe`); **zero rows → the existing "No news
    yet" empty state** (the AS-3 promise: feed renders `Notice`s unchanged).
  - **Fail-soft preserved (AC4/AC7, §7):** a `published_notices_for_apps` that raises is caught by the
    **existing** `_notices_fail_soft` → empty notice region + `SUBSCRIPTION_NOTICE_DEGRADED`, the feed
    still **200**s (the wrapper is unchanged; the producer changes the body, not the wrapper).
  - `notices_for_channel(owner, app_id)` returns that owner's notices for that app newest-first, one
    query. `config.updates_feed_notice_limit()` resolves + `validate_all()` covers it.
  - **Regression:** the full `apps.subscriptions` suite stays green (the seam signature + call site
    unchanged); `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/updates/selectors.py` (new), `apps/updates/tests/test_selectors.py`
  + `tests/test_seam.py` (new), `apps/subscriptions/notices.py` (body repoint only),
  `apps/subscriptions/tests/` (a seam-integration/fail-soft regression case), `apps/core/config.py`
  (`updates_feed_notice_limit` + `validate_all`).

## T-03 — `updates.services` (the only writer): post / withdraw + owner-gate + validation + durable rate-limit

- **Description.** Add the **single write path** exactly per DESIGN §6.2/§5.3/§7 — the only place a
  `Notice` is created or withdrawn; it owns the owner-gate, boundary validation, and the durable
  rate-limit. It **imports no `signals.capture`** (AC6 — the structural transparency line, asserted
  by the AST test added in T-05).
  - **`apps/updates/errors.py`:** `AppNotOwnedError`, `InvalidNoticeError`, `RateLimitedError`
    (mirroring `apps/ratings/errors.py` — raised **before** any write, so a rejected post never
    leaves a partial row).
  - **`post_notice(author, app_id, *, kind, title, summary) -> PublishedNotice` (AC1/AC2/AC3/AC8):**
    1. **Owner gate (AC1):** `catalog.get_owned_app(author, app_id)` is `None` → `AppNotOwnedError`
       (the view 404s; no ownership oracle, indistinguishable from not-found).
    2. **Validation (AC2/AC3):** `kind` not in `NoticeKind` → `InvalidNoticeError`; blank-after-strip
       or over-length `title`/`summary` vs `config.updates_title_max_length()` /
       `config.updates_summary_max_length()` → `InvalidNoticeError`. Nothing written on any reject.
    3. **Durable rate-limit (AC8, DU-DESIGN-4):** count this author's own `updates_notice` rows for
       this `app_id` with `published_at >= now - updates_post_window_hours()`; if
       `>= updates_max_posts_per_window()` → `RateLimitedError`, nothing created. (Exact +
       multi-worker-correct from the durable rows; **no cache infra** — the design's rejected alt 5.)
       The benign count→create TOCTOU is an **accepted** bounded spam-guardrail trade-off (DESIGN
       §5.3) — **no** `SELECT FOR UPDATE`.
    4. On success: create one `updates_notice` row (`published_at = now`); increment
       `UPDATES_NOTICE_POSTED{kind}`; return the `PublishedNotice`.
  - **`withdraw_notice(author, app_id, notice_id) -> bool` (AC7):** **hard-delete** the author's own
    notice scoped by `author` + `app_id` + `id` (no IDOR). **Idempotent:** returns `False` (no
    increment) when no row matches a non-owner/unknown id; on a real delete returns `True` +
    increments `UPDATES_NOTICE_WITHDRAWN`.
  - **`apps/core/config.py`:** add `updates_max_posts_per_window()` (default 5),
    `updates_post_window_hours()` (default 24), `updates_title_max_length()` (default 120),
    `updates_summary_max_length()` (default 4000) via the house `_positive_int` pattern, each
    registered in `validate_all()`.
  - **`apps/core/observability.py`:** declare all **six** `UPDATES_*` counters in one place —
    `UPDATES_NOTICE_POSTED`, `UPDATES_NOTICE_WITHDRAWN`, `UPDATES_POST_REJECTED`, `UPDATES_POST_FAILED`,
    `UPDATES_CHANNEL_DEGRADED`, `UPDATES_AUDIENCE_DEGRADED` (DESIGN §11). Services increments POSTED /
    WITHDRAWN / `UPDATES_POST_REJECTED{reason=invalid|rate_limited}` (counted at the reject point,
    mirroring `ratings`' `RATING_REJECTED`); the other three are incremented by the T-05 views.
- **Dependencies.** T-01 (the model), T-02 (the `PublishedNotice` DTO it returns).
- **Definition of done.** Service-level tests (real ORM + seeded `catalog` apps; no HTTP):
  - **AC1 owner gate:** posting to an app the caller does not own → `AppNotOwnedError`, **no** row
    created.
  - **AC2/AC3 validate + post:** `post_notice(kind="update")` and `kind="early_access")` each create
    exactly one row honoring the pinned shape; an unknown `kind`, a blank/whitespace title or summary,
    and an over-length title/summary each raise `InvalidNoticeError` with **nothing created**;
    boundary lengths (exactly at the cap vs one over) behave correctly.
  - **AC8 rate-limit:** after `updates_max_posts_per_window()` posts for one app inside the window,
    the next raises `RateLimitedError` (nothing created); a post **outside** the window succeeds;
    the limit is **per author + per app** (a second app, or a second author, is unaffected); driven
    by config (`override_settings` changes the threshold/window with no code change).
  - **AC7 withdraw:** `withdraw_notice` deletes the author's own row (returns `True`) and it is gone;
    a foreign/unknown `notice_id`, or another author's notice, deletes nothing (returns `False`, no
    leak, no error — idempotent).
  - Counters fire on their paths (`UPDATES_NOTICE_POSTED{kind}`, `UPDATES_NOTICE_WITHDRAWN`,
    `UPDATES_POST_REJECTED{reason}`); the four new config tunables resolve + `validate_all()` covers
    them. `ruff` clean; full suite green; `makemigrations --check` clean (no model change here).
- **Estimated size.** M.
- **Files/areas touched.** `apps/updates/services.py` (new), `apps/updates/errors.py` (new),
  `apps/updates/tests/test_services.py` (new), `apps/core/config.py` (the four write-boundary
  tunables + `validate_all`), `apps/core/observability.py` (the six `UPDATES_*` constants).

## T-04 — Additive reverse-audience read on the closed `apps/subscriptions/`: `subscriber_count` + `subscriptions_app_idx`

- **Description.** Add the **additive, contract-preserving** reverse-audience read exactly per DESIGN
  §5.2/§6.3 (DU-DESIGN-6, the OQ-DU-1 reporting half) — the only edit to the **closed**
  `app-subscriptions` feature. It backs the post-form audience hint and the M2 metric; it is **not**
  needed for delivery (the AS-3 seam is pull — DESIGN §13).
  - **`apps/subscriptions/selectors.py`:** `subscriber_count(app_id: UUID) -> int` — one indexed
    `Subscription.objects.filter(app_id=app_id).count()`. Bounded and follower-count-independent in
    query terms; the reverse of the existing user-scoped `is_following`/`followed_apps`. Existing
    reads are **untouched**.
  - **`apps/subscriptions/models.py`:** add one **additive** index `subscriptions_app_idx` on
    `(app_id)` to `Subscription.Meta.indexes` (an `app_id`-only COUNT is unindexed today — L5; the
    existing unique `(user, app_id)` index leads with `user`). **No new column, no behaviour change.**
  - `migrations/0002_*` — adds the index only; additive, reversible.
- **Dependencies.** T-01 (logically independent of the new app, but ordered after the core slice so
  the closed-app edit lands once the producer is proven; could run any time after T-01).
- **Definition of done.**
  - `subscriber_count(app_id)` returns the exact current follower count for that app; `0` for an app
    with no followers; counts **only** that app (a second app's followers are excluded); reflects
    follow/unfollow (a hard-deleted follow drops the count).
  - **Bounded:** `subscriber_count` is **one query**, constant at 2 vs 50 followers
    (`assertNumQueries`).
  - `makemigrations` produces exactly `subscriptions/0002` adding `subscriptions_app_idx`;
    `makemigrations --check` then clean; `migrate` applies and reverses it cleanly (the index is
    present after up, absent after down — introspection); existing follow data untouched.
  - **Regression:** the full `apps.subscriptions` suite stays green (additive only); `ruff` clean;
    full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/subscriptions/selectors.py` (the new read), `apps/subscriptions/models.py`
  (the additive index), `apps/subscriptions/migrations/0002_*.py` (new),
  `apps/subscriptions/tests/` (the `subscriber_count` + index cases).

## T-05 — `apps/updates/` HTTP: the four views + templates + the `config/urls` include (the activation switch) + the AST transparency test

- **Description.** Add the thin HTTP layer + wire the **final activation step** exactly per DESIGN
  §6.5/§7/§8/§12 — the views hold **no ORM and no business logic** beyond gating, calling
  `services`/`selectors`, and rendering/redirecting (the pages/ratings/subscriptions house pattern).
  All four routes are `@require_role(roles.DEVELOPER)` (D-3, fail-closed) + `@login_required`; the two
  mutations are POST + CSRF, addressed by `request.user` + `app_id` (+ scoped `notice_id`) so there is
  **no IDOR**. The app **imports nothing from `signals.capture`** (AC6, AST-enforced).
  - **Routes (`app_name="updates"`, DESIGN §4/§6.5):**
    - `GET /updates/` → `views.my_channels` (the developer's owned **accepted** apps).
    - `GET /updates/apps/<uuid:app_id>/` → `views.channel` (the post form + audience hint + the
      owner's notices, each with a Withdraw control).
    - `POST /updates/apps/<uuid:app_id>/post` → `views.post` (create a notice).
    - `POST /updates/apps/<uuid:app_id>/notices/<uuid:notice_id>/withdraw` → `views.withdraw`.
  - **`my_channels` (DESIGN §6.5):** `catalog.list_owned_apps(request.user)` filtered to
    `status == ACCEPTED`; render `my_channels.html` (each app links to its channel; the **own-nothing**
    empty state → **200**, "You have no accepted apps yet"). Non-developers → **403** via `require_role`.
  - **`channel` (DESIGN §6.5/§7):** `get_owned_app(request.user, app_id)` is `None` → **404**
    (`Http404`, indistinguishable, AC1). Otherwise render `channel.html` with: the post form
    (kind/title/summary); an **audience hint** ("Reaches N current followers" via
    `subscriptions.selectors.subscriber_count`, wrapped **fail-soft** → hide the hint +
    `UPDATES_AUDIENCE_DEGRADED` on error, never blocks posting); the owner's notices via
    `updates.selectors.notices_for_channel` wrapped **fail-soft** → render the form + a "couldn't load
    your notices" affordance + `UPDATES_CHANNEL_DEGRADED` (the dev can still post). Empty-notices state:
    "No notices yet — post your first update."
  - **`post` (DESIGN §6.5/§7):** call `services.post_notice(...)`; success → **PRG** to the channel
    with a success message; `AppNotOwnedError` → **404**; `InvalidNoticeError`/`RateLimitedError` → PRG
    back with a clear error message, **nothing created** (services already counted
    `UPDATES_POST_REJECTED{reason}`); an unexpected `Exception` → **fail-soft** message + PRG (durable
    state = *not posted*) + `UPDATES_POST_FAILED` (the `subscriptions.follow` view contract — never a
    500, no corpus coupling).
  - **`withdraw` (DESIGN §6.5):** call `services.withdraw_notice(...)`; **PRG** to the channel (the
    notice is gone from the list and from every follower's feed on its next read — AC7, no dangling
    ref). A no-op (foreign/unknown id) still PRGs cleanly.
  - **Templates (DESIGN §6.5) — server-rendered, no JS, all text auto-escaped (no `|safe`/`mark_safe`;
    title/summary are untrusted developer input shown to followers, §8):** `templates/updates/base.html`
    (mirrors `subscriptions`/`discovery` base); `my_channels.html`; `channel.html` (post form + audience
    hint + notices list with per-notice Withdraw POST). Keyboard-navigable controls.
  - **AC6 transparency test (structural):** add `apps/updates/tests/test_imports.py` mirroring
    `apps/discovery/tests/test_imports.py` — walk every `apps.updates` module (excluding `tests`) and
    assert **none imports anything matching `signals`** (a notice is content, never a D-7 emit). Posting
    is inert to the corpus; only a follower's own return via the existing `apps/pages`
    `APP_PAGE`/`page_reengagement` kinds counts (DESIGN §8, not this feature's emit).
  - **Activation switch (DESIGN §12):** add `path("updates/", include("apps.updates.urls"))` to
    `config/urls.py`. This is the **final** activation step (the `INSTALLED_APPS` line shipped at T-01,
    the seam repoint at T-02); removing this include + the seam revert + the `INSTALLED_APPS` line is
    the documented rollback (T-06 / DESIGN §12).
- **Dependencies.** T-03 (services), T-02 (`updates.selectors`), T-04 (`subscriber_count`).
- **Definition of done.** Integration tests (Django test client, project URLconf with the `updates/`
  include):
  - **AC1 gate:** a non-developer → **403** on all four routes; a developer → `/updates/` lists their
    accepted apps only; another dev's `app_id` (or an unknown id) on the channel/post/withdraw routes
    → **404** (indistinguishable from not-found, no ownership oracle).
  - **AC2/AC3 post:** a valid `update` and a valid `early_access` post each create one notice and PRG
    to the channel with a success message; the notice then appears in the channel list **and** in a
    follower's `/subscriptions/feed`.
  - **AC4/AC5 producer + audience scope:** the posted notice appears in the feed of a user **following**
    that app and **never** in a non-follower's feed (M5 = 0, asserted); viewing the feed injects **no**
    `Impression`/`EngagementEvent` row.
  - **AC6 read-only-to-corpus:** the AST test confirms no `signals` import anywhere in the app; a `post`
    or `withdraw` writes **no** `Impression`/`EngagementEvent` row.
  - **AC7 manage/withdraw:** the channel lists the owner's notices newest-first; withdraw removes it
    from the channel **and** from a follower's feed on the next request; withdrawing a foreign/unknown
    id is a harmless no-op PRG.
  - **AC8 rate-limit (HTTP):** posting past the window limit PRGs back with the rate-limit message,
    nothing created (`UPDATES_POST_REJECTED{reason=rate_limited}`).
  - **method gate:** `POST` to a GET route or `GET` to a POST route → **405**.
  - **failure split (§7):** `subscriber_count` patched to raise → the channel **200**s with the hint
    hidden + `UPDATES_AUDIENCE_DEGRADED`; `notices_for_channel` patched to raise → the channel **200**s
    with the post form + the degraded affordance + `UPDATES_CHANNEL_DEGRADED`; an unexpected
    `post_notice` error → PRG + message + `UPDATES_POST_FAILED` (never a 500); a producer-read raise in
    the **feed** is caught by the existing wrapper → feed still 200 + `SUBSCRIPTION_NOTICE_DEGRADED`.
  - the three view-side `UPDATES_*` counters fire on their paths. `manage.py check` clean;
    `makemigrations --check` clean; `ruff`/template lint clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/updates/views.py` (new), `apps/updates/urls.py` (new),
  `apps/updates/templates/updates/{base,my_channels,channel}.html` (new),
  `apps/updates/tests/test_views.py` + `tests/test_imports.py` (new), `config/urls.py` (the `updates/`
  include).

## T-06 — README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: docs + the shared-code index — no behavioural change (DESIGN §12).
  - `apps/updates/README.md` — the app's single responsibility (the single AS-3 producer: a
    developer→follower **update / early-access** channel; **owns `updates_notice`**; **never imports
    `signals.capture`**, so posting emits no D-7 signal — only a follower's own return counts), the
    four routes, the pull-delivery model (M5 = 0 structural), the durable rate-limit, the fail-soft
    failure modes, and the **rollback** (DESIGN §12 — honest: this is the first feature to repoint a
    *closed* app's seam, so rollback = **revert `subscriptions/notices.py::notices_for_apps` to
    `return []` + remove the `config/urls` `updates/` include + the `"apps.updates"` `INSTALLED_APPS`
    line**; the `updates_notice` table + `subscriptions_app_idx` index may remain inert or be migrated
    down).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: the new `apps/updates/`
    producer (its four routes, `services` write path, `selectors` reads + the `PublishedNotice` DTO,
    the `Notice` model/`updates_notice` table); the **repointed** AS-3 seam
    `subscriptions.notices.notices_for_apps` (now the `PublishedNotice → Notice` adapter); the additive
    `subscriptions.selectors.subscriber_count` + the `subscriptions_app_idx` index; the five
    `updates_*` config tunables; the six `UPDATES_*` observability constants (feed health reuses
    `SUBSCRIPTION_NOTICE_DEGRADED`).
  - [features/developer-updates/DECISIONS.md](DECISIONS.md) — mark **DU-DESIGN-1…6** as **built**.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit artifact,
    produced alongside the build, **not** in this task.
- **Dependencies.** T-01…T-05.
- **Definition of done.** `apps/updates/README.md` matches the shipped routes/rollback; `CODEMAP.md`
  lists every new shared surface above; `DECISIONS.md` marks DU-DESIGN-1…6 built; `makemigrations
  --check` clean; **full suite green, `ruff` clean, no drift** (the close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/updates/README.md` (new), [CODEMAP.md](../../CODEMAP.md),
  `features/developer-updates/DECISIONS.md`.

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §5.1 `updates_notice` table (DU-DESIGN-3): columns, structural absences (no score/`updated_at`/`withdrawn_at`), CASCADE author, `updates_app_published_idx` | **T-01** |
| §5.1 `apps/updates/` is a table-owning app (C6, not model-less) + `INSTALLED_APPS` registration | **T-01** |
| §6.1 `PublishedNotice` DTO + `published_notices_for_apps` (AS-3 producer read, R3-bounded) + `notices_for_channel` (AC7 list) | **T-02** |
| §6.4/§4 AS-3 seam repoint = the single `PublishedNotice → Notice` adapter (DU-DESIGN-2); feed renders `Notice`s unchanged | **T-02** |
| §4/§13 strict-DAG / no import cycle (the load-bearing self-critique) | **T-02** (cycle-absence test) |
| §7 feed fail-soft preserved (`_notices_fail_soft` → `SUBSCRIPTION_NOTICE_DEGRADED`, AC4/AC7) | **T-02** |
| §6.2 `services.post_notice` — owner gate (AC1) + kind/length validation (AC2/AC3) + durable rate-limit (AC8) | **T-03** |
| §6.2 `services.withdraw_notice` — hard delete, scoped, idempotent (AC7, no IDOR) | **T-03** |
| §5.3/§5.1/§10 durable table-derived rate-limit (DU-DESIGN-4); accepted TOCTOU, no lock | **T-03** |
| §11 the five `updates_*` config tunables (no magic numbers) | **T-02** (`feed_notice_limit`) + **T-03** (the four boundary tunables) |
| §5.2/§6.3 additive `subscriber_count` + `subscriptions_app_idx` on the closed app (DU-DESIGN-6 / OQ-DU-1 reporting half) | **T-04** |
| §6.5 the four role+owner-gated views + routes; my-channels (accepted-only); audience hint; PRG | **T-05** |
| §6.5 templates — server-rendered, no JS, auto-escaped; own-nothing/empty states | **T-05** |
| §8 transparency line / AC6 structural — `apps/updates` imports no `signals.capture` (AST test); posting inert to corpus | **T-05** (AST import-absence test) |
| §4/§5/§8 audience-scoped pull delivery, M5 = 0 structural; no impression injected (AC5) | **T-02** (producer read) + **T-05** (feed/non-follower assertions) |
| §7 failure modes — post fail-soft (`UPDATES_POST_FAILED`); channel/audience degraded (soft); rejects (`UPDATES_POST_REJECTED`) | **T-03** (rejects) + **T-05** (fail-soft/degraded) |
| §11 observability — the six `UPDATES_*` counters; feed health reuses `SUBSCRIPTION_NOTICE_DEGRADED` | **T-03** (declare + 3 service-side) + **T-05** (3 view-side) |
| §12 activation = `INSTALLED_APPS` + seam repoint + `updates/` include; rollback = the honest 3-part revert; design-for-deletion | **T-01** (INSTALLED_APPS) + **T-02** (seam) + **T-05** (include) + **T-06** (rollback note) |
| §14 docs/CODEMAP + DU-DESIGN-1…6 built | **T-06** |
| §9 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-03+T-05; AC2 → T-03+T-05; AC3 → T-03+T-05; AC4 → T-02+T-05;
AC5 → T-02+T-05; AC6 → T-05 (AST) + T-03 (no-capture write path); AC7 → T-02+T-03+T-05;
AC8 → T-03+T-05. **M1** (`UPDATES_NOTICE_POSTED`) → T-03; **M2** (analyst-derived from
`subscriber_count`) → T-04; **M3/M4** (existing `signal-capture` returns, not this feature's emit) →
n/a here (consumed, not produced); **M5** (reach beyond followers = 0) → **structural**, asserted in
T-02+T-05; **M6** (`UPDATES_POST_REJECTED{reason=rate_limited}` + post rate) → T-03+T-05. All eight
acceptance criteria are covered; **no `L` tasks** (all S/M); every task has a checkable definition of
done and declared files; every task leaves the system green and releasable (the surface goes live only
at the T-05 `config/urls` include).
