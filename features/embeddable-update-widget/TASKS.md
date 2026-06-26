# TASKS — embeddable-update-widget

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-EUW-BRIEF → approved; AC1–AC9 / M1–M6) and the **ratified** [DESIGN.md](DESIGN.md)
(DN-EUW-DESIGN → approved; **EUW-7…11 ratified**; reuses
[D-4](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md)/[D-8](../../DECISIONS.md)/[D-9](../../DECISIONS.md)/[D-10](../../DECISIONS.md)
— **no new global ADR**). Produces an ordered, independently-verifiable task list; full per-AC
verification is the Senior Engineer's `TEST_PLAN.md` at Stage 4. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a contract
> or decision the design does not already make. Four kinds of change exist:
> 1. **A new feature-owned app `apps/widget/`** (DESIGN §5, the `pages`/`discovery`/`dashboard`/
>    `updates` house convention) that **owns exactly one table `widget_reach_count`** (a daily
>    rollup; **no `user` FK, no IP/UA/referrer/geo column** — anonymity + PII-free are *structural*,
>    DESIGN §6). It **imports nothing from `apps.signals`** ⇒ the AC6 firewall (M5 = 0) is
>    **structural by absence** (DESIGN §3/§9, the `discovery`/`dashboard`/`updates` AST precedent).
> 2. **One additive read on the closed [developer-dashboard](../developer-dashboard/)
>    (`apps/dashboard`)** — a fail-soft **"Widget reach"** slot (DESIGN §7/§9, AC9) that reads
>    `widget.selectors`; the only new cross-app edge (`dashboard → widget`, never the reverse).
>    Additive, same posture as the existing reviews slot — no existing contract altered.
> 3. **Additive `apps/core` changes** — a reusable **per-IP GET** rate limiter generalising the
>    existing `core.ratelimit` internals by parameters (DESIGN §14), three `widget_*` config
>    tunables (DESIGN §9), and the `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` observability constants
>    (DESIGN §9). Cross-cutting concerns stay in `core` (one home).
> 4. **The activation wiring** — `"apps.widget"` in `INSTALLED_APPS` (+ its one migration) and the
>    `path("widget/", include("apps.widget.urls"))` include (DESIGN §13).
>
> Read-only **reuse** (no edits): `updates.selectors.published_notices_for_apps` (the notice read,
> EUW-1/F1/F3), `catalog.selectors.get_catalogued_app` (ACCEPTED + name, D-6), `pages:app-page` via
> `reverse(...)` (the click-through destination, F4 — never a request param, no open redirect).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces/API → UI → telemetry → docs.** The spine is: the
   `widget_reach_count` table + app registration (**T-01**) → the single-writer `attribution` +
   single-reader `selectors` over that table, with the AC6 structural firewall proven (**T-02**) →
   the `core` cross-cutting additions: the per-IP GET limiter + three `widget_*` tunables + the
   `WIDGET_*` metric constants (**T-03**) → the `content` view-model assembler (**T-04**) → the two
   HTTP views + framable templates + the `config/urls` activation include (**T-05**) → the additive
   fail-soft dashboard "Widget reach" slot on the closed `apps/dashboard` (**T-06**) → docs/CODEMAP/
   DECISIONS close-out (**T-07**).
2. **Risk first (DESIGN §3/§9/§13 — front-load the load-bearing uncertainty).** The single
   load-bearing, integrity-critical property is the **AC6 firewall = structural by absence**: a
   widget interaction must create **zero** `signals` rows and `apps/widget` must import **nothing**
   from `apps.signals` (DESIGN §3, the headline tension). It is proven at **T-02** — the moment the
   write path (`attribution`) and its store exist — by **(a)** the AST import-absence test
   (`apps/widget` imports nothing matching `signals`, the `discovery` precedent) and **(b)** an
   integration test that a record-impression + record-click-through writes **0**
   `Impression`/`EngagementEvent` rows and leaves `signals.has_impression(..., surfaces=CURATED_SURFACES)`
   **False** (M5 = 0). The second-order risk — **write correctness under concurrency on a hot daily
   rollup row** (DESIGN §6, the scrape-prone third-party surface) — is proven in the **same** task
   (the `F("count")+1` atomic increment + the unique-constraint create-race retry). Both land before
   any HTTP, view-model, or dashboard surface is built.
3. **Each task leaves the system working and releasable.** **T-01** adds an inert, unrouted table
   (no view references it). **T-02** adds the un-routed writer/reader (reachable only by tests).
   **T-03** adds inert `core` helpers/constants (no caller yet). **T-04** adds the pure view-model
   assembler (no route). The widget surface becomes user-reachable **only at T-05** — the single
   `config/urls` `widget/` include is the activation switch (the `INSTALLED_APPS` line landed at
   T-01 is inert without the include). **T-06** adds the dashboard slot (additive, fail-soft — the
   dashboard renders identically if it errors). **T-07** is docs only.

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/widget/__init__.py` / `apps.py` / `kinds.py` / `models.py` / `migrations/0001_initial.py` —
  **T-01** only (the package scaffold + `WidgetEventKind` + the `WidgetReachCount` model + its
  initial migration).
- `apps/widget/attribution.py` / `selectors.py` / `tests/test_imports.py` — **T-02** only (the
  single writer, the single reader, the AC6 AST firewall test).
- `apps/core/ratelimit.py` — **T-03** only (the additive per-IP GET limiter; the existing
  `rate_limited` decorator + `_exceeds_limit`/`_client_ip` internals are **reused**, not rewritten).
- `apps/core/config.py` (+ `validate_all`) — **T-03** only (the three `widget_*` tunables).
- `apps/core/observability.py` — **T-03** only (declares **all** `WIDGET_*` +
  `DASHBOARD_WIDGET_DEGRADED` constants in one place; T-05's views reference the render/click/limit
  ones, T-06's dashboard references `DASHBOARD_WIDGET_DEGRADED`).
- `apps/widget/content.py` + `tests/test_content.py` — **T-04** only.
- `apps/widget/views.py` / `urls.py` / `templates/widget/*.html` / `tests/test_views.py` — **T-05**
  only (new); `config/urls.py` — **T-05** only (the one `widget/` include = the activation step).
- `apps/dashboard/reception.py` / `templates/dashboard/{app_reception,my_apps}.html` /
  `apps/dashboard/tests/` — **T-06** only (the additive widget-reach slot).
- `config/settings.py` `INSTALLED_APPS` — **T-01** only (`"apps.widget"`, needed for the T-01
  migration; the table is harmless/unrouted until T-05).

---

## T-01 — Scaffold `apps/widget/` + the `widget_reach_count` table + app registration (schema)

- **Description.** Create the new feature-owned app and its one table exactly per DESIGN §5/§6
  (EUW-8/EUW-9). Scaffold the package (`__init__.py`, `apps.py` with
  `AppConfig(name="apps.widget", label="widget")` mirroring `apps/updates/apps.py`,
  `tests/__init__.py`) and add `"apps.widget"` to `INSTALLED_APPS` (required for the migration; the
  table is unrouted/inert until the T-05 include).
  - **`apps/widget/kinds.py`** — `WidgetEventKind(models.TextChoices)` = exactly
    `IMPRESSION = "impression"` | `CLICK_THROUGH = "click_through"` (the closed vocabulary,
    DESIGN §6). The single source of truth for the two kinds.
  - **`apps/widget/models.py`** — `WidgetReachCount` (`db_table = "widget_reach_count"`) with
    **exactly** the columns in DESIGN §6: `id` (UUID pk, `uuid4`, non-editable); `app_id`
    (`UUIDField`, a **soft D-6 ref — no DB FK**, validated at the write boundary, mirroring
    `updates`/`subscriptions`); `kind` (`CharField(max_length=16, choices=WidgetEventKind.choices)`);
    `count_date` (`DateField` — the UTC day); `count` (`PositiveIntegerField(default=0)`);
    `created_at` (`auto_now_add`); `updated_at` (`auto_now`).
  - **Structural absences (DESIGN §3/§6/§9 — the PII-free + anonymity posture made *unrepresentable*):**
    **no `user` FK**, **no IP/UA/referrer/geo/device column**, **no score/weight/rank column**. These
    absences *are* the AC6/AC10 guarantee — do not add them.
  - **Constraint + index (DESIGN §6):** `UniqueConstraint(fields=["app_id","kind","count_date"],
    name="widget_reach_count_unique")` (one row per app×kind×day — turns a create race into a caught
    retry, T-02) and `Index(fields=["app_id","kind","count_date"],
    name="widget_reach_app_kind_date_idx")` (backs the atomic per-day increment **and** the
    windowed dashboard read).
  - `migrations/0001_initial.py` — the table + constraint + index; additive, reversible
    (`migrate widget zero` drops it cleanly).
- **Dependencies.** none (foundational).
- **Definition of done.**
  - `makemigrations` produces exactly `widget/0001_initial`; `makemigrations --check --dry-run` then
    reports **no** further changes (model matches migration); `migrate` applies it and
    `migrate widget zero` reverses it cleanly (up→down→up) on a test DB.
  - Model-level tests: a `WidgetReachCount` row persists all fields; `kind` accepts only the two
    `WidgetEventKind` values; `db_table == "widget_reach_count"`; the unique constraint rejects a
    second `(app_id, kind, count_date)` row (`IntegrityError`); the
    `widget_reach_app_kind_date_idx` index is present (introspection or `Meta.indexes`); the model
    has **no** `user`/IP/referrer/score attribute (assert the field set, locking the AC10 posture).
  - The app is in `INSTALLED_APPS`; the package imports cleanly; the runner discovers
    `apps/widget/tests/`. `ruff` clean; full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/widget/__init__.py`, `apps/widget/apps.py`, `apps/widget/kinds.py`,
  `apps/widget/models.py`, `apps/widget/migrations/0001_initial.py` + `migrations/__init__.py`,
  `apps/widget/tests/__init__.py` + `tests/test_models.py` (new), `config/settings.py`
  (`INSTALLED_APPS += "apps.widget"`).

## T-02 — `attribution` (the single writer) + `selectors` (the single reader) + the AC6 firewall proof (the risk centerpiece)

- **Description.** Add the write/read surface over `widget_reach_count` exactly per DESIGN §5.2/§6,
  and **prove the firewall here** — the load-bearing, integrity-critical slice (DESIGN §3). Both
  modules **import nothing from `apps.signals`**; that absence (AST-proven) *is* the AC6 firewall.
  - **`apps/widget/attribution.py` — the SINGLE writer (DESIGN §5.2/§6):**
    - `record_widget_impression(app_id: UUID) -> None` and
      `record_widget_click_through(app_id: UUID) -> None` — each does the **atomic per-day
      increment** verbatim per DESIGN §6: `with transaction.atomic():` an `update(count=F("count")+1)`
      on today's `(app_id, kind, count_date)` row; if `0` rows updated → `create(..., count=1)`
      wrapped in `try/except IntegrityError` → on the caught create-race, re-`update(F("count")+1)`.
      `F("count")+1` is evaluated **in the DB** (no lost updates under concurrency); the unique
      constraint (T-01) is what turns the create race into a retry. **No cache/queue infra** (the
      `developer-updates` durable-table precedent).
    - These **trust an `app_id` the view already validated as ACCEPTED** (EUW-11 — the view is the
      single caller and validation boundary; re-reading the catalog here would double the hot-path
      cost). They **raise on a DB failure**; the **caller wraps fail-soft** (T-05) so counting can
      never break the host's page.
  - **`apps/widget/selectors.py` — the SINGLE reader (DESIGN §5.2; returns frozen DTOs, never ORM
    rows):**
    - `@dataclass(frozen=True) WidgetReach: impressions: int; click_throughs: int` (the click-through
      *rate*, M2, is derived at display — **not** stored).
    - `widget_reach(app_id: UUID, *, start: datetime, end: datetime) -> WidgetReach` and
      `widget_reach_for_apps(app_ids: list[UUID], *, start, end) -> dict[UUID, WidgetReach]` — each
      **one grouped query** (`SUM(count) GROUP BY [app_id,] kind`) over the window's `count_date`
      range, **zero-filled** (a kind/app with no rows ⇒ `0`), `[]`/empty input ⇒ empty result.
      **No N+1** for the dashboard's K-app summary (the established `funnel_for_apps`/
      `impression_breakdown_for_apps` discipline).
- **Dependencies.** T-01 (the model + constraint + index).
- **Definition of done.**
  - **AC6 firewall — structural (the headline risk, DESIGN §3/§9):**
    - `apps/widget/tests/test_imports.py` (mirroring `apps/discovery/tests/test_imports.py`) walks
      every `apps.widget` module (excluding `tests`) via `pkgutil` + `ast` and asserts **none**
      imports anything matching `signals`.
    - An integration test: `record_widget_impression(app_id)` + `record_widget_click_through(app_id)`
      writes **0** `signals.Impression`/`EngagementEvent` rows (query the corpus directly) and
      `signals.has_impression(user=..., app_id=app_id, surfaces=CURATED_SURFACES)` stays **False**
      (M5 = 0 by construction — a widget interaction is not curated-surface evidence because it does
      not exist in the corpus).
  - **Write correctness (DESIGN §6):** a first `record_widget_impression` creates today's row with
    `count == 1`; subsequent calls **increment** the same `(app_id, impression, today)` row (not new
    rows); impression and click_through are **separate** rows; a second app/day is a separate row.
    Concurrency: N increments (e.g. via `assertNumQueries`-bounded sequential calls plus a simulated
    create-race forcing the `IntegrityError` branch — patch/`get_or_create`-style or seed the row
    between filter and create) yield `count == N` with no lost update.
  - **Read correctness (DESIGN §5.2):** `widget_reach` returns the windowed
    `(impressions, click_throughs)` summed across days, **zero-filled** when a kind has no rows;
    rows **outside** the `[start, end]` day range are excluded; `widget_reach_for_apps([a,b,...])`
    returns one entry per requested app (zero-filled for an app with no rows), `[]` ⇒ `{}`, and is
    **one grouped query** regardless of K (`assertNumQueries`, constant vs 50 seeded rows).
  - `ruff` clean; full suite green; `makemigrations --check` clean (no model change here).
- **Estimated size.** M.
- **Files/areas touched.** `apps/widget/attribution.py` (new), `apps/widget/selectors.py` (new),
  `apps/widget/tests/test_imports.py` + `tests/test_attribution.py` + `tests/test_selectors.py`
  (new).

## T-03 — `apps/core` additions: the per-IP GET rate limiter + three `widget_*` tunables + the `WIDGET_*` observability constants

- **Description.** Add the cross-cutting `core` pieces the widget HTTP layer needs, exactly per
  DESIGN §9/§14 — **generalising the existing `core.ratelimit` internals by parameters, not adding a
  new framework** (the §14 simplification). No widget code calls these yet (inert until T-05/T-06).
  - **`apps/core/ratelimit.py` — a reusable per-IP GET limiter (DESIGN §4/§8/§9, AC8):** add a
    decorator (e.g. `ip_rate_limited_get(limit_fn, *, window_seconds=60)`) that, for a **GET**,
    enforces a **per-IP fixed-window** limit reusing the existing `_client_ip` + `_exceeds_limit`
    internals (the limit comes from a passed `config` callable — never hardcoded). Over the limit ⇒
    `429`, **no** wrapped-view call (so no render, no count — DESIGN §8). The existing auth
    `rate_limited` decorator (which *skips* GET) and its internals are **reused unchanged** — this is
    an additive sibling that applies the same window mechanism to GETs. **Fail-open on a cache
    error** (the limiter must not take down a public read — DESIGN §8 `WIDGET_LIMITER_DEGRADED`
    posture); the counting of that degrade lives in the view wrapper (T-05), the limiter just does
    not raise into the request path.
  - **`apps/core/config.py`** — add via the house `_positive_int` pattern, each registered in
    `validate_all()`: `widget_notice_limit()` (default 5, DESIGN §9/F1), 
    `widget_render_rate_limit_per_ip_per_minute()` (default 60, AC8),
    `widget_cache_max_age_seconds()` (default 60, the `Cache-Control` TTL, DESIGN §9).
  - **`apps/core/observability.py`** — declare **all** widget counter constants in one place
    (DESIGN §9): `WIDGET_RENDERED` (M4), `WIDGET_EMPTY`, `WIDGET_CLICK_THROUGH` (M2),
    `WIDGET_NOT_AVAILABLE`, `WIDGET_RATE_LIMITED` (AC8), `WIDGET_NOTICES_DEGRADED`,
    `WIDGET_RENDER_DEGRADED`, `WIDGET_COUNT_DEGRADED` (**the one actionable alert** — sustained ⇒
    attribution silently lossy), `WIDGET_LIMITER_DEGRADED`, and `DASHBOARD_WIDGET_DEGRADED` (the
    T-06 slot). (M5 needs **no** counter — it is 0 by construction.)
- **Dependencies.** none strictly (independent of T-01/T-02), but ordered after the data/logic slice
  so the risk centerpiece lands first; the limiter has no widget consumer until T-05.
- **Definition of done.**
  - **Rate limiter:** under the limit a GET passes through unchanged; the `(limit)+1`-th GET from
    the same IP within the window ⇒ `429` and the wrapped view is **not** called; a different IP is
    unaffected; the window resets after `window_seconds`; the limit is **config-driven**
    (`override_settings` changes it with no code change); a cache backend raising ⇒ **fail-open**
    (the view still runs), not a 500. The existing auth `rate_limited` behaviour is unchanged
    (its test suite stays green — regression).
  - **Config:** the three `widget_*` tunables resolve to their defaults, honor env/settings
    overrides via `_positive_int`, and are each covered by `validate_all()` (a test asserting
    `validate_all()` evaluates them, the house pattern).
  - **Observability:** all ten constants exist and are unique strings; referenced by name (no
    duplicates with existing constants). `ruff` clean; full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/core/ratelimit.py` (the additive per-IP GET limiter),
  `apps/core/config.py` (three `widget_*` tunables + `validate_all`), `apps/core/observability.py`
  (the ten `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` constants), `apps/core/tests/` (limiter + config
  cases).

## T-04 — `content.build_widget_view` — the pure view-model assembler (notices + link + degraded flag)

- **Description.** Add the render contract assembler exactly per DESIGN §5.2/§7/§8 — pure (no HTTP,
  no ORM beyond the two reused reads), so it is unit-testable in isolation and the view stays thin.
  - **`apps/widget/content.py`:**
    - `@dataclass(frozen=True) WidgetNotice: kind: str; title: str; summary: str; published_at: datetime`.
    - `@dataclass(frozen=True) WidgetView: app_name: str; app_page_path: str;
      notices: list[WidgetNotice]; notices_degraded: bool`.
    - `build_widget_view(app_id: UUID) -> WidgetView | None`:
      1. `catalog.get_catalogued_app(app_id)` — `None` (unknown/non-accepted) ⇒ return **`None`**
         (the view renders `unavailable.html`, D-6: never leaks exists-vs-unaccepted).
      2. `app_page_path = reverse("pages:app-page", args=[app_id])` — **server-derived**, never a
         request param (no open redirect, F4/§9).
      3. notices via `updates.selectors.published_notices_for_apps([app_id],
         limit=config.widget_notice_limit())`, mapped to `WidgetNotice`, newest-first, capped (F1/AC1).
         **Wrap this read fail-soft:** on an exception ⇒ `notices=[]`, `notices_degraded=True`
         (link-only — DESIGN §8), and count `WIDGET_NOTICES_DEGRADED`. A *truthful* empty
         (`notices == []`, `notices_degraded == False`, AC2) stays **distinct** from a read failure.
      - The catalog read raising is **not** caught here — it surfaces to the view wrapper, which
        renders `unavailable.html` + counts `WIDGET_RENDER_DEGRADED` (DESIGN §8). `content` only
        soft-handles the *notice* read.
- **Dependencies.** T-03 (`config.widget_notice_limit()`, `WIDGET_NOTICES_DEGRADED`). Reuses
  `updates.selectors` + `catalog.selectors` + `pages` `reverse` as-is (no edit to those).
- **Definition of done.** Unit tests (real ORM-seeded catalog + `updates_notice` rows; no HTTP):
  - **AC1:** with N seeded notices, `build_widget_view` returns them **newest-first**, **capped** at
    `widget_notice_limit()`, with `app_name` + `app_page_path == reverse("pages:app-page", [app_id])`.
  - **AC2:** an accepted app with **no** notices ⇒ `notices == []`, `notices_degraded == False`
    (truthful empty, not an error).
  - **AC3:** a notice posted/withdrawn through `updates` changes the next `build_widget_view`
    (read live, no widget-side notice store) — assert via seeding then deleting a row.
  - **degraded:** `published_notices_for_apps` patched to raise ⇒ `notices == []`,
    `notices_degraded == True`, `WIDGET_NOTICES_DEGRADED` counted, **app_name + link still present**.
  - **not available:** `get_catalogued_app` ⇒ `None` (unknown / non-accepted id) ⇒
    `build_widget_view` returns `None`.
  - `ruff` clean; full suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/widget/content.py` (new), `apps/widget/tests/test_content.py` (new).

## T-05 — `apps/widget/` HTTP: `widget_render` + `widget_view_redirect` + framable templates + the `config/urls` include (the activation switch)

- **Description.** Add the thin HTTP layer + the two framable templates + wire the **final activation
  step** exactly per DESIGN §5.1/§5.2/§7/§8 — the views hold **no ORM and no business logic** beyond
  rate-limiting, calling `content`/`attribution`, and rendering/redirecting (the pages/discovery
  house pattern). Both routes are **AllowAny** (anonymous end users, AC5) and serve **only public
  content**.
  - **Routes (`app_name="widget"`, mounted at `widget/`, DESIGN §5.2):**
    - `GET /widget/<uuid:app_id>/` → `views.widget_render`:
      - Per-IP rate-limited via the T-03 limiter (AC8) — over the limit ⇒ **429**, no render, no
        count, `WIDGET_RATE_LIMITED`; a limiter cache error ⇒ **fail-open** + `WIDGET_LIMITER_DEGRADED`.
      - `@xframe_options_exempt` (cross-origin framing — safe: read-only public content, no
        authenticated action, no clickjacking value, DESIGN §5.1/§9). Sets
        `Cache-Control: public, max-age=<widget_cache_max_age_seconds()>`.
      - Calls `content.build_widget_view(app_id)`. `None` ⇒ render `unavailable.html` with **404** +
        `WIDGET_NOT_AVAILABLE` (D-6 indistinguishable). A `build_widget_view`/catalog **exception** ⇒
        render `unavailable.html` with **200** (degraded) + `WIDGET_RENDER_DEGRADED` (DESIGN §8 —
        never 500 into the host). Otherwise render `widget.html` (**200**); count one **impression**
        via `attribution.record_widget_impression(app_id)` wrapped **fail-soft** (swallow after
        `WIDGET_COUNT_DEGRADED` + log — the render always proceeds, AC9 best-effort to the user, loud
        to ops); count `WIDGET_RENDERED` (M4), and `WIDGET_EMPTY` when `notices == []`.
    - `GET /widget/<uuid:app_id>/view` → `views.widget_view_redirect`:
      - Validates ACCEPTED (`catalog.get_catalogued_app` ⇒ `None` ⇒ `unavailable.html` 404 +
        `WIDGET_NOT_AVAILABLE`). Otherwise count one **click_through** via
        `attribution.record_widget_click_through(app_id)` wrapped **fail-soft**
        (`WIDGET_COUNT_DEGRADED`); count `WIDGET_CLICK_THROUGH` (M2); **302** to
        `reverse("pages:app-page", [app_id])` — **server-derived target, never an open redirect**
        (F4/§9).
  - **Templates (DESIGN §5.1/§7) — self-contained, framable, server-rendered, no JavaScript, no
    external assets, **inline CSS**, all text auto-escaped (no `|safe`/`mark_safe` — notice
    title/summary are developer input shown cross-origin, §9 XSS):**
    - `templates/widget/widget.html` — a compact card: app-name heading; up to
      `widget_notice_limit()` notices (a small kind chip `update`/`early access`, title, summary,
      relative date), newest-first; a footer **"View on <platform>"** link
      `<a href="{% url 'widget:view' app_id %}" target="_top">` (breaks out of the frame, §5.1).
      Empty state (AC2): "No updates yet." + the same footer link. Degraded
      (`notices_degraded`): a quiet "Updates are temporarily unavailable." + heading + link — never
      a fabricated "no updates."
    - `templates/widget/unavailable.html` — a neutral, framable "This app isn't available." (no leak
      of exists-vs-unaccepted, D-6).
  - **Activation switch (DESIGN §13):** add `path("widget/", include("apps.widget.urls"))` to
    `config/urls.py` (own prefix; `/widget/` is free — no collision with `pages` `/apps/`). This is
    the **final** activation step (the `INSTALLED_APPS` line shipped at T-01); the documented
    rollback is `git revert` of the build commit (T-07 / DESIGN §13).
- **Dependencies.** T-04 (`content`), T-02 (`attribution`), T-03 (the limiter + tunables + the
  `WIDGET_*` constants).
- **Definition of done.** Integration tests (Django test client, project URLconf with the `widget/`
  include):
  - **AC5 (anonymous):** an unauthenticated `GET /widget/<id>/` for an accepted app renders
    `widget.html` **200** with the notices + the link; exposes only public fields (no subscriber
    count, no dashboard data).
  - **AC7 (embed/no-build):** the render route returns a self-contained HTML page (no `<script>`, no
    external asset reference); the documented one-line `<iframe>` is captured in the README (T-07).
  - **AC1/AC2/AC3:** the rendered page lists seeded notices newest-first capped at the limit; an
    app with no notices shows the empty state + link; a withdrawn notice is gone on the next render
    (live read).
  - **AC4 (click-through):** `GET /widget/<id>/view` **302**s to `reverse("pages:app-page", [id])`
    (assert the `Location`); never reads a redirect target from the request.
  - **AC6 (firewall, HTTP path):** a full render + `/view` round-trip writes **0**
    `Impression`/`EngagementEvent` rows and leaves `has_impression(..., surfaces=CURATED_SURFACES)`
    **False** (re-asserted end-to-end over the live routes; complements the T-02 unit/AST proof).
  - **AC8 (rate limit):** over `widget_render_rate_limit_per_ip_per_minute()` GETs from one IP ⇒
    **429**, **no** render, **no** impression counted, `WIDGET_RATE_LIMITED`; `Cache-Control:
    public, max-age=<config>` present on a normal render.
  - **AC9 (attribution):** a render increments the **impression** count and a `/view` the
    **click_through** count for that `(app, day)` (read back via `widget.selectors.widget_reach`);
    `xframe_options_exempt` present (no `X-Frame-Options: DENY`).
  - **fail-soft (§8):** `record_widget_impression` patched to raise ⇒ the render **still 200**s +
    `WIDGET_COUNT_DEGRADED` (host page never breaks); `build_widget_view`/catalog patched to raise ⇒
    `unavailable.html` **200** + `WIDGET_RENDER_DEGRADED`; an unknown/non-accepted id ⇒
    `unavailable.html` **404** + `WIDGET_NOT_AVAILABLE`; the limiter's cache patched to raise ⇒
    **fail-open** render + `WIDGET_LIMITER_DEGRADED`.
  - **method gate:** `POST` to either GET route ⇒ **405**. `manage.py check` clean;
    `makemigrations --check` clean; `ruff`/template lint clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/widget/views.py` (new), `apps/widget/urls.py` (new),
  `apps/widget/templates/widget/{widget,unavailable}.html` (new),
  `apps/widget/tests/test_views.py` (new), `config/urls.py` (the `widget/` include).

## T-06 — Additive fail-soft "Widget reach" slot on the closed `apps/dashboard/` (AC9 display)

- **Description.** Add the AC9 developer-facing display exactly per DESIGN §7/§8/§9 — the only edit
  to the **closed** [developer-dashboard](../developer-dashboard/). It is **additive + fail-soft**
  (the reviews-slot precedent): the dashboard renders identically if the widget read errors, and the
  **core signals reception read keeps its existing loud-500 posture** — only the *added* widget slot
  is soft.
  - **`apps/dashboard/reception.py`:**
    - A new `@dataclass(frozen=True) WidgetReachView: available: bool; impressions: int;
      click_throughs: int` (the click-through **rate** is derived at display from these — not
      stored, DESIGN §5.2/§7). `available=False` ⇒ the slot degraded.
    - `_build_widget_reach(app_id, window) -> WidgetReachView` — calls
      `widget.selectors.widget_reach(app_id, start=window.start, end=window.end)`; on **any
      exception** ⇒ `WidgetReachView(available=False, 0, 0)` + count `DASHBOARD_WIDGET_DEGRADED`
      (degrade **only this slot**, DESIGN §8 — the rest of Screen B stays 200). Add it to
      `build_app_reception` as a new `AppReception.widget_reach` field (Screen B), **after** the
      loud reach/funnel reads.
    - `build_my_apps_summaries` (Screen A) gains a **widget-impressions** column via **one bulk**
      `widget.selectors.widget_reach_for_apps(app_ids, start, end)` (no N+1) — add
      `widget_impressions: int` to `ReceptionSummary`, fail-soft to `0` for the whole column on a
      bulk-read error (+ `DASHBOARD_WIDGET_DEGRADED`).
  - **Templates:** `templates/dashboard/app_reception.html` — a new **"Widget reach"** section
    (impressions, click-throughs, derived rate), **clearly labeled as off-platform widget reach**,
    rendered **distinct** from the on-platform per-`Surface` breakdown (different facts — DESIGN
    §9/§14 self-critique); when `available == False`, a quiet "Widget reach is temporarily
    unavailable." `templates/dashboard/my_apps.html` — a widget-impressions column in the summary
    table.
- **Dependencies.** T-02 (`widget.selectors`), T-03 (`DASHBOARD_WIDGET_DEGRADED`). The `dashboard →
  widget` import edge is the only new cross-app edge (DESIGN §5; the dashboard depends on the
  widget, never the reverse).
- **Definition of done.** Tests (extend `apps/dashboard/tests/`):
  - **AC9 (Screen B):** an owned accepted app with seeded `widget_reach_count` rows shows the
    "Widget reach" section with the correct impressions/click-throughs + derived rate over the
    selected window; the section is **labeled off-platform** and **separate** from the per-`Surface`
    breakdown.
  - **AC9 (Screen A):** `build_my_apps_summaries` includes a `widget_impressions` per app via **one**
    `widget_reach_for_apps` call (no N+1 — `assertNumQueries` constant vs K apps).
  - **fail-soft (§8):** `widget.selectors.widget_reach` patched to raise ⇒ Screen B still **200**s
    with `WidgetReachView.available == False` + the quiet message + `DASHBOARD_WIDGET_DEGRADED`, and
    the **rest** of the reception (reach/funnel/reviews) renders unchanged; `widget_reach_for_apps`
    raising ⇒ Screen A still **200**s with the widget column at `0` + `DASHBOARD_WIDGET_DEGRADED`.
  - **Regression:** the **core** signals reception read keeps its loud-500 posture (a signals error
    still raises, unchanged); the full `apps.dashboard` suite stays green (additive only); `ruff`
    clean; full suite green; `makemigrations --check` clean (no schema change in `dashboard`).
- **Estimated size.** M.
- **Files/areas touched.** `apps/dashboard/reception.py` (the additive `WidgetReachView` +
  `_build_widget_reach` + the `ReceptionSummary`/`AppReception` fields),
  `apps/dashboard/templates/dashboard/{app_reception,my_apps}.html`, `apps/dashboard/tests/`.

## T-07 — README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: docs + the shared-code index — no behavioural change (DESIGN §13/§15).
  - `apps/widget/README.md` — the app's single responsibility (the embeddable, paste-one-line
    "what's new" widget: **owns `widget_reach_count`**; renders an app's published `updates` notices
    + a labeled "view on platform" link; **never imports `apps.signals`**, so a widget interaction
    confers **no D-8 curated-rating eligibility** — the AC6 firewall is structural by absence); the
    **documented one-line `<iframe>` embed snippet** (AC7, DESIGN §5.1); the two routes; the daily
    rollup + atomic increment; the per-IP GET limit + `Cache-Control` TTL (AC8); the fail-soft
    failure modes; the deferred M3 per-account conversion (OQ-EUW-5); and the **rollback** = **`git
    revert` of the build commit** (DESIGN §13 — the dashboard imports `widget.selectors`, so dropping
    only the `INSTALLED_APPS` line would break the dashboard import; the revert drops the dashboard
    slot **and** the `widget/` include **and** the `INSTALLED_APPS` line together; the table
    down-migration is independent/optional).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared surfaces: the new `apps/widget/` (its two
    routes, the `attribution` writer + `selectors` reader + `WidgetReach` DTO, the `content`
    assembler + `WidgetView`/`WidgetNotice` DTOs, the `WidgetReachCount` model/`widget_reach_count`
    table, `WidgetEventKind`); the additive `core.ratelimit` per-IP GET limiter; the three `widget_*`
    config tunables; the ten `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` observability constants; the
    additive `dashboard.reception` widget-reach slot (`WidgetReachView`).
  - [features/embeddable-update-widget/DECISIONS.md](DECISIONS.md) — mark **EUW-7…11** as **built**.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit
    artifact, produced alongside the build, **not** in this task.
- **Dependencies.** T-01…T-06.
- **Definition of done.** `apps/widget/README.md` matches the shipped routes/embed snippet/rollback;
  `CODEMAP.md` lists every new shared surface above; `DECISIONS.md` marks EUW-7…11 built;
  `makemigrations --check` clean; **full suite green, `ruff` clean, no drift** (the close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/widget/README.md` (new), [CODEMAP.md](../../CODEMAP.md),
  `features/embeddable-update-widget/DECISIONS.md`.

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §5/§6 new table-owning app `apps/widget/` + `INSTALLED_APPS` registration | **T-01** |
| §6 `widget_reach_count` table + `WidgetEventKind`: columns, **structural absences** (no `user`/IP/referrer/score), unique constraint + `widget_reach_app_kind_date_idx` (EUW-9, AC10 posture) | **T-01** |
| §5.2/§6 `attribution` single writer — atomic `F()`-increment + unique-constraint create-race retry (EUW-9, concurrency-correct) | **T-02** |
| §5.2 `selectors` single reader — `WidgetReach` DTO, windowed `SUM…GROUP BY`, zero-fill, no N+1 (`widget_reach[/_for_apps]`) | **T-02** |
| §3/§9 **AC6 firewall = structural by absence** — `apps/widget` imports no `signals` (AST test) + 0 corpus rows + `has_impression(CURATED_SURFACES)` False (M5 = 0) (EUW-8) | **T-02** (+ re-asserted end-to-end in **T-05**) |
| §4/§14 reusable per-IP **GET** rate limiter (AC8) — generalises `core.ratelimit`, fail-open | **T-03** |
| §9 three `widget_*` config tunables (no magic numbers) | **T-03** |
| §9 the ten `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` observability constants (M5 needs none) | **T-03** (declare) + **T-05**/**T-06** (fire) |
| §5.2/§7/§8 `content.build_widget_view` — `WidgetView`/`WidgetNotice`, capped newest-first notices (AC1), truthful empty (AC2), live read (AC3), `notices_degraded` split, server-derived link (F4) | **T-04** |
| §5.1/§5.2 `widget_render` — AllowAny (AC5), `@xframe_options_exempt`, `Cache-Control` TTL, impression count fail-soft, rate-limited (AC8), `unavailable` 404/degraded 200 | **T-05** |
| §5.1/§5.2 `widget_view_redirect` — click_through count + **302 to `reverse(pages:app-page)`**, no open redirect (AC4) | **T-05** |
| §5.1/§7 framable templates — self-contained, no JS, inline CSS, auto-escaped; populated/empty/degraded/unavailable states; `target="_top"` breakout link (AC7, §9 XSS) | **T-05** |
| §13 activation = `INSTALLED_APPS` (T-01) + `widget/` include (T-05); `/widget/` free of `pages` | **T-01** + **T-05** |
| §7/§9 AC9 dashboard **"Widget reach"** slot — additive, fail-soft, off-platform-labeled, distinct from per-`Surface`; Screen A bulk column (no N+1) | **T-06** |
| §8 failure modes — `WIDGET_NOTICES_DEGRADED`/`_RENDER_DEGRADED`/`_COUNT_DEGRADED`/`_LIMITER_DEGRADED`/`_NOT_AVAILABLE`/`_RATE_LIMITED`; `DASHBOARD_WIDGET_DEGRADED` (slot-only soft; core stays loud) | **T-04** (notices) + **T-05** (render/count/limiter/avail/rate) + **T-06** (dashboard slot) |
| §11 deferred M3 per-account conversion (OQ-EUW-5) — named, not silently dropped | **T-07** (README) |
| §13 rollback = `git revert` of the build commit (DU-REL-1 precedent); design-for-deletion | **T-07** (note) + structurally **T-01/T-05/T-06** (the three additive switches) |
| §15 docs/CODEMAP + EUW-7…11 built | **T-07** |
| §12 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-04+T-05; AC2 → T-04+T-05; AC3 → T-04+T-05; AC4 → T-05; AC5 → T-05;
**AC6 → T-02 (AST + 0-corpus, the structural proof) + T-05 (end-to-end re-assert)**; AC7 → T-05+T-07;
AC8 → T-03+T-05; AC9 → T-02 (store) + T-05 (count) + T-06 (display). **M1/M2/M4** (`WIDGET_RENDERED`/
`WIDGET_CLICK_THROUGH` + `widget_reach` windows) → T-03+T-05+T-06; **M3** (per-account conversion) →
**deferred** (OQ-EUW-5, T-07 note); **M5** (reach beyond the firewall = 0) → **structural**, asserted
in T-02+T-05; **M6** (latency + `*_DEGRADED` fail-soft) → T-05+T-06. All nine acceptance criteria are
covered; **no `L` tasks** (all S/M); every task has a checkable definition of done and declared files;
every task leaves the system green and releasable (the surface goes live only at the T-05 `config/urls`
include; the dashboard slot at T-06 is additive + fail-soft).
