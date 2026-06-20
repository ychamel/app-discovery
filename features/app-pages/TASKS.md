# TASKS — app-pages

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-9 → approved) and the approved [DESIGN.md](DESIGN.md) (DN-10 → approved). Produces an
ordered, independently-verifiable task list; full per-AC verification is written by the
Senior Engineer at Stage 4 in `TEST_PLAN.md`. See [phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a
> contract or decision the design does not already make. app-pages introduces **no new
> global decision** — it is a pure D-6/D-7 consumer (DESIGN §0/§9/§11).

---

## Ordering rationale (sequencing rules → this order)

1. **Adopt before you emit (the one hard ordering constraint).** `Surface.APP_PAGE` and its
   no-op `signals` migration land **first** (T-01): capture must understand the surface
   before any page emits an `app_page` impression (DESIGN §12, D-7 §12). Nothing that emits
   may precede it.
2. **Schema/data → core logic → interfaces → UI → telemetry → docs.** app-pages owns no
   schema, so the spine is: vocabulary (T-01) → scaffold (T-02) → the emission policy
   helper, the feature's core logic and its riskiest piece (T-03) → the views + routing that
   expose it (T-04) → the uniform presentation template (T-05) → docs/finalize (T-06).
3. **Risk first.** The genuinely uncertain pieces — the **AP-3 page-view-as-impression**
   attribution wiring and the **AP-4/AC7 fail-soft-but-counted** policy — are concentrated in
   **T-03 + T-04** and verified there with a fake capture seam, before any presentation work.
4. **Each task leaves the system working and releasable.** T-01/T-02 are inert additions
   (a choices-only migration; an app with no routes wired). From T-04 the pages are reachable
   and behaviorally complete; T-05 enriches presentation; T-06 is docs. The activation switch
   is the one `config/urls.py` include (added in T-04, removed to roll back — DESIGN §12).

**File-collision note (no two tasks edit the same file in parallel — tasks are sequential):**
`apps/core/observability.py` is touched by **T-03** (one degraded counter) and **T-04** (two
view counters); they run in order, never concurrently. `config/urls.py` + `config/settings*`
are touched once each (T-02 `INSTALLED_APPS`; T-04 the URL include). `apps/pages/urls.py` is
created whole in T-04. `apps/pages/templates/pages/app_page.html` is created as a minimal stub
in T-04 and fleshed out in T-05 (sequential, declared).

---

## T-01 — Add `Surface.APP_PAGE` + its no-op `signals` migration

- **Description.** Add `APP_PAGE = "app_page", "app page"` to `apps/signals/kinds.Surface`
  (DESIGN §11 — the **additive extension D-7 pre-authorizes**; the docstring already names
  `app_page`). Generate the accompanying `signals` migration, which alters the `surface`
  field's **choices metadata only** — no column change, no data change, reversible. This is
  the only touch on a global vocabulary the feature makes (DESIGN §0/§11).
- **Dependencies.** none.
- **Definition of done.**
  - `Surface.APP_PAGE` present; `Surface.values` includes `"app_page"`; `Surface.DIGEST`
    unchanged.
  - `python manage.py makemigrations signals` produces exactly one migration altering
    `Impression.surface` choices; `python manage.py makemigrations --check` reports no further
    drift after it is committed.
  - The migration is **reversible**: `migrate signals <new>` → `migrate signals 0001` →
    `migrate signals <new>` all succeed with no error (rehearsed; DESIGN §12).
  - `apps/signals/capture.record_impression(..., surface=Surface.APP_PAGE)` passes
    `_require_surface` (no `ValidationError`) — verified by a test.
  - Existing `apps/signals` suite (incl. `test_kinds.py`) green; `ruff` clean.
- **Estimated size.** S.
- **Files/areas touched.** `apps/signals/kinds.py`, `apps/signals/migrations/0002_*.py`,
  `apps/signals/tests/test_kinds.py` (assert the new value).

## T-02 — Scaffold the `apps/pages` Django app (no routes, no model)

- **Description.** Create the new app directory per DESIGN §2: `__init__.py`, `apps.py`
  (`AppConfig`, `name="apps.pages"`), and the `templates/pages/base.html` minimal public
  chrome (own base → deletable, no coupling — DESIGN §2/§12). Register `"apps.pages"` in
  `INSTALLED_APPS`. **No `models.py`, no migration, no `urls.py` wired into the project yet**
  — the app is inert until T-04 adds the URL include (DESIGN §2/§12 "off = don't include the
  URLconf"). Add the test package `apps/pages/tests/`.
- **Dependencies.** none (independent of T-01; both precede T-03).
- **Definition of done.**
  - `apps.pages` imports and appears in `INSTALLED_APPS`; `python manage.py check` is clean.
  - `python manage.py makemigrations --check` reports **no migration for `pages`** (it owns
    no model — DESIGN §2/§4).
  - `templates/pages/base.html` renders standalone (a trivial template test or `check`).
  - `ruff` clean; full existing suite still green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/pages/` (new package: `__init__.py`, `apps.py`,
  `templates/pages/base.html`, `tests/__init__.py`), `config/settings*.py` (`INSTALLED_APPS`).

## T-03 — `emission.py`: the surface-side non-blocking capture policy (AP-4 / AC7)

- **Description.** Implement `apps/pages/emission.py` exactly to the DESIGN §5b contract — the
  **core logic of the feature and its riskiest piece**. Three functions:
  `record_page_view(request, app_id) -> UUID | None`, `record_try_click(request, app_id,
  impression_id)`, `record_share(request, app_id, impression_id)`. They wrap
  `signals.capture.record_impression(surface=Surface.APP_PAGE)` / `record_click_through` /
  `record_share` and enforce the two surface invariants (DESIGN §5b/§6c/§7):
  1. **Authenticated-only (AP-4).** Gate on `request.user.is_authenticated`; anonymous →
     **no capture**, `record_page_view` returns `None` (the page still renders — AC5).
  2. **Fail-soft-but-counted (AC7).** Wrap every `signals.capture.*` call in
     `try/except Exception`; on failure increment a surface degraded counter, log with request
     context, and **return normally / never re-raise into the request** (the complement of
     D-7 §5d, which makes capture loud *inside* signals). `ImpressionMismatchError` from a
     forged/foreign `imp` is caught here → no event (DESIGN §7/§10).
  - `record_try_click` resolves `impression_id` to the user's page-view `Impression` and passes
    it to `record_click_through` (which **requires** it); a missing/mismatched id → no event,
    no raise. `record_share` passes the impression when present (optional for `share`).
  - **No business logic / no ORM** here beyond fetching the impression to link — app validity,
    tag snapshot, and linkage stay enforced inside `signals.capture` (one source of truth,
    DESIGN §5b invariant 3).
  - Add the surface degraded counter constant `APP_PAGE_CAPTURE_DEGRADED` to
    `apps/core/observability.py` (the "surface's own fail-soft counter", DESIGN §3/§7) and use
    it. Funnel counters (`impression_captured` etc.) are **reused from D-7**, not duplicated.
- **Dependencies.** T-01 (needs `Surface.APP_PAGE`), T-02 (needs the package).
- **Definition of done.** Unit tests against a **fake `signals.capture` seam** cover:
  - anonymous request → no capture call; `record_page_view` returns `None`.
  - authenticated success → `record_impression(surface=Surface.APP_PAGE)` called; returns the
    impression id; `record_try_click` with a valid id calls `record_click_through(impression=…)`.
  - capture raises (any `Exception`) → caught, `APP_PAGE_CAPTURE_DEGRADED` incremented, logged,
    function returns normally (`None` for `record_page_view`); **no exception propagates**.
  - `record_try_click` with a `None`/mismatched `impression_id` → `record_click_through` not
    called (or its `ImpressionMismatchError` caught) → no event, no raise.
  - `ruff` clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/pages/emission.py`, `apps/core/observability.py` (add one
  constant), `apps/pages/tests/test_emission.py`.

## T-04 — Routes + three thin views (render / try-redirect / share), wired and reachable

- **Description.** Implement `apps/pages/urls.py` (`app_name = "pages"`, the three routes of
  DESIGN §5a) and `apps/pages/views.py` (the three thin views of DESIGN §3/§5a), then add
  `path("apps/", include("apps.pages.urls"))` to `config/urls.py` — the activation switch
  (DESIGN §12). Mirror the catalog thin-view house pattern (`apps/catalog/views.py`
  `app_detail_page`: thin view → selector → `render`, `raise Http404`):
  - **`app_page` (GET, `AllowAny`)** — `get_catalogued_app(app_id)`; `None` → **404**
    `not_available.html` + `APP_PAGE_NOT_AVAILABLE` counter (AC8 — never render a non-accepted
    app as live); a catalog read that **raises** propagates as a **loud 500** (DESIGN §7 — this
    is *render*, the core dependency, not capture). On success: call
    `emission.record_page_view`, pass the returned impression id into the template so the
    try-it/share affordances embed it (`imp`), `render` the uniform page,
    increment `APP_PAGE_RENDERED{app_id}`, and log render duration (DESIGN §8/§9). Renders with
    a **minimal stub** `app_page.html` here (full slots are T-05).
  - **`try_redirect` (GET, `AllowAny`)** — `get_catalogued_app`; `None` → 404. Call
    `emission.record_try_click(request, app_id, imp)` (fail-soft) then **302 to the app's
    server-side `CatalogApp.url`** — the target is read from the catalog, **never** from a
    request param (DESIGN §5a/§10 — no open redirect). Redirect fires even if capture failed
    (AC7).
  - **`share` (POST, CSRF, `AllowAny`)** — `get_catalogued_app`; `None` → 404. Call
    `emission.record_share(request, app_id, imp)` (fail-soft); return **204**. Anonymous →
    still 204, no event.
  - Add `APP_PAGE_RENDERED` + `APP_PAGE_NOT_AVAILABLE` constants to
    `apps/core/observability.py` (DESIGN §9).
  - `not_available.html` = the AC8 not-a-live-catalog-entry body (returned with 404).
- **Dependencies.** T-03 (views call `emission`), T-02 (package + `base.html`), T-01 (Surface,
  transitively via emission).
- **Definition of done.** Integration tests (Django test client, project URLconf) cover:
  - **AC5** anonymous GET `apps/<accepted-id>/` → **200**, full page, no auth redirect.
  - **AC8** GET for a `pending`/`rejected`/`withdrawn`/unknown id → **404** `not_available`;
    `APP_PAGE_NOT_AVAILABLE` counted; non-UUID path → 404 at routing.
  - **AC6** authenticated GET emits an `app_page`-surface impression; authenticated
    `try?imp=<that impression>` records a `click_through` **linked to it** and **302s** to the
    app's stored URL; authenticated POST `share` records a `share` and returns **204**
    (assert via the real `signals.selectors`/DB or a capture spy).
  - **§10** `try?imp=<some other user's/app's impression>` → redirect still 302s, **no event
    written** (mismatch caught in emission); redirect `Location` is the catalog URL regardless
    of any request-supplied value (no open redirect).
  - **AC7** with `signals.capture` patched to raise → GET still 200, `try` still 302, `share`
    still 204; loss counted (`capture_error` and/or `APP_PAGE_CAPTURE_DEGRADED`).
  - `share` GET (wrong method) → 405; `share` without CSRF → 403.
  - `ruff` clean; `manage.py check` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/pages/urls.py` (new), `apps/pages/views.py` (new),
  `apps/pages/templates/pages/not_available.html` (new), `apps/pages/templates/pages/app_page.html`
  (minimal stub — fleshed out in T-05), `config/urls.py` (add the include),
  `apps/core/observability.py` (two constants), `apps/pages/tests/test_views.py`.

## T-05 — The uniform `app_page.html` template: slots, empty states, accessibility (AC1/AC2/AC3/AC9)

- **Description.** Flesh out `templates/pages/app_page.html` to the DESIGN §5c contract — the
  **same six slots in the same order for every app**, driven **only** by `CatalogApp` (which
  structurally carries no owner/team/paid field — so uniformity is structural, AC3, not a
  convention): (1) header — `name` + `resolve_tag`'d category labels, with a defined
  "Uncategorized"/absent treatment when tags are empty; (2) ordered media gallery (1–8), each
  `<img>` with `alt_text`, and a defined single-image/empty layout that never collapses
  differently than another app's; (3) `description`; (4) the try-it primary action (links to
  `pages:try` carrying `imp`); (5) the share affordance (POSTs to `pages:share`;
  progressive-enhancement — the canonical URL is always copyable so the page is shareable
  without JS, AC4); (6) the **reviews slot = a defined empty state** ("coming soon"), rendering
  no rating data (AC9 / AP-1 — owned by `ratings-reviews`). Accessibility (A4): semantic
  landmarks, `alt_text` on every image, keyboard-reachable + visibly-focusable try-it/share.
- **Dependencies.** T-04 (the view + route names + the stub it replaces).
- **Definition of done.** Template tests render the page for fixture apps and assert:
  - **AC1** name, description, all ordered media (with `alt_text`), `resolve_tag`'d category
    labels, and a try-it action linking to `pages:try` are all present.
  - **AC2** an app with **no tags** and an app with **one image** each render every slot in the
    same order with its defined empty/single state — no missing slot, no error, no
    layout-collapsing difference vs. a fully-populated app.
  - **AC3** two different fixture apps render **byte-structurally the same slots in the same
    order**; the template references no owner/team/paid field (assert it is not in the context
    and the DTO has no such attribute).
  - **AC9** the reviews slot shows the empty state and **no** rating value/field is rendered.
  - **AC4** the canonical page URL is present and copyable in the markup (shareable without JS).
  - A4: every `<img>` has non-empty `alt`; try-it/share are focusable controls (assert markup).
  - `ruff`/template lint clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/pages/templates/pages/app_page.html`,
  `apps/pages/templates/pages/base.html` (chrome only if needed),
  `apps/pages/tests/test_template.py`.

## T-06 — Docs, CODEMAP, rollback note, finalize

- **Description.** Documentation + index + close-out only — no behavior change (DESIGN
  §9/§11/§12). Add `apps/pages/README.md` (the app's single responsibility, the three routes,
  the emission policy, "owns no model", rollback = remove the `config/urls.py` include). Record
  the new shared touch-points in [CODEMAP.md](../../CODEMAP.md): `apps.pages.emission.*`
  (the surface-side non-blocking wrapper), the `pages:*` route names, and the three new
  observability constants. Add the rollback/operations note (DESIGN §12 — additive, no flag;
  `Surface.APP_PAGE` stays once any `app_page` impression exists). Confirm AP-3/AP-4/AP-5 in
  [DECISIONS.md](DECISIONS.md) as approved (DN-10). No `.env` keys are introduced (the feature
  has no config tunables — DESIGN §13 simplification pass).
- **Dependencies.** T-01…T-05.
- **Definition of done.** `apps/pages/README.md` exists and matches the shipped routes/policy;
  `CODEMAP.md` lists the emission helper, route names, and counters; `DECISIONS.md` marks
  AP-3/AP-4 confirmed (DN-10); `makemigrations --check` clean; **full suite green, `ruff`
  clean, no drift** (the close-out sweep). The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then →
  test) is the Senior Engineer's exit artifact, produced alongside the build, not in this task.
- **Estimated size.** S.
- **Files/areas touched.** `apps/pages/README.md` (new), [CODEMAP.md](../../CODEMAP.md),
  `features/app-pages/DECISIONS.md`.

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §11 `Surface.APP_PAGE` + no-op migration (adopt-before-emit) | **T-01** |
| §2 new `apps/pages` app, `INSTALLED_APPS`, base chrome, **no model/migration** | **T-02** |
| §5b emission contract (3 fns) · §6c AP-4 authenticated-only · §7 fail-soft-but-counted (AC7) | **T-03** |
| §3/§5a three thin views + routes; §6 AP-3 page-view-as-`app_page`-impression wiring | **T-04** |
| §5a `config/urls.py` include (activation switch) | **T-04** |
| §7 failure modes (loud 500 on catalog read; soft+counted on capture; 404 AC8) | **T-04** |
| §10 security (server-side redirect target; `imp` mismatch → no event; CSRF on share) | **T-04** |
| §9 observability counters (`APP_PAGE_RENDERED` / `_NOT_AVAILABLE` / `_CAPTURE_DEGRADED`; D-7 reuse) | **T-03 + T-04** |
| §8 render-latency log | **T-04** |
| §5c uniform template — 6 slots, empty/partial states (AC1/AC2/AC9); structural uniformity (AC3) | **T-05** |
| §5a AP-5 stable `App.id` URL / shareable canonical URL (AC4) | **T-04 (route) + T-05 (markup)** |
| §8 accessibility A4 (alt text, semantic markup, keyboard-reachable) | **T-05** |
| §12 rollout/rollback (additive, no flag, design-for-deletion) + §11 CODEMAP/docs | **T-06** |
| §14 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1/AC2/AC3/AC9 → T-05; AC4 → T-04+T-05; AC5/AC6/AC7/AC8 → T-04 (policy in
T-03). All nine acceptance criteria are covered; no `L` tasks; every task has a checkable
definition of done.
