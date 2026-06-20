# RELEASE_NOTES — app-pages

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway database (2026-06-20).*
Sources: the verified Stage-4 build, [DESIGN.md §9/§11/§12](DESIGN.md) (observability +
the additive `Surface` touch + rollout/rollback), [FEATURE_BRIEF.md §5](FEATURE_BRIEF.md)
(success metrics / error conditions), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9 coverage),
and the reused global contracts [D-4](../../DECISIONS.md) (stack), [D-5](../../DECISIONS.md)
(`resolve_tag`), [D-6](../../DECISIONS.md) (`get_catalogued_app`), [D-7](../../DECISIONS.md)
(`signals.capture.*`).

---

## 1. What this release is

The catalog's **public face** — one openly-accessible, structurally-uniform page per
**accepted** app (its media, description, `resolve_tag`'d categories, and a try-it action),
usable as the app's web home / press kit, with try-it and share captured as behavioral
signal. It is the first Phase-1 surface and the **widest downstream unblock** (every later
user/dev surface — `weekly-digest`, `open-search-browse`, `ratings-reviews`,
`app-subscriptions` — points at an app *page*).

It ships as a **new Django app, `apps/pages/`**, that is a **pure D-6/D-7 consumer owning
NO model and NO migration of its own** — it reads the catalog through the
[D-6](../../DECISIONS.md) selectors and emits through the [D-7](../../DECISIONS.md) capture
path. It changes no existing feature's behavior. It satisfies all nine acceptance criteria
AC1–AC9 (mapping in [TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since the catalog had no public face)

- **New app `apps/pages/`, owning no schema** — three thin views + a fail-soft emission
  helper + one uniform template. There is no `models.py` and no `apps/pages/migrations/`
  (asserted by `test_scaffold.test_app_owns_no_model` + `makemigrations --check` clean).
  Content lives in the catalog (read-only via D-6); events live in signals (written via
  D-7). Nothing here can drift.
- **Three HTTP routes** under `/apps/` ([DESIGN §5a](DESIGN.md)):
  - `GET /apps/<uuid:app_id>/` (`pages:app-page`, **AllowAny**) — renders the uniform page
    for an accepted app; for an **authenticated** visitor it emits a page-view
    `app_page`-surface impression (fail-soft). A `pending`/`rejected`/`withdrawn`/unknown id
    → **404** `not_available.html` (AC8); a non-UUID path → 404 at routing; a genuine
    catalog read failure → **loud 500** (DESIGN §7).
  - `GET /apps/<id>/try` (`pages:try`, AllowAny) — emits `click_through` (authenticated +
    valid `imp` only, fail-soft) then **302**s to the app's **server-side stored** `url`
    (no open redirect — the target is never a request param).
  - `POST /apps/<id>/share` (`pages:share`, AllowAny, **CSRF-protected**) — emits `share`
    (authenticated, fail-soft); **204**. GET → 405.
- **The page-view-as-impression attribution model (AP-3)** — an authenticated page view is
  recorded as an `Impression` with **`surface = app_page`**; the try-it click is a
  `click_through` **linked to it**, and a share links to it too. This is what makes the
  brief's "click-through *rate* per page view" measurable (the impression is the
  denominator) and is fully [D-7](../../DECISIONS.md)-faithful — `click_through` gets the
  impression it requires with **no contract change**. It does **not** run the curated-feed
  allocator (that stays out of scope, owned by `weekly-digest`); the `surface` field keeps
  app-page shows segregated from digest shows. *(Confirmed by DN-10.)*
- **Authenticated-only capture, fully anonymous render (AP-4)** — the page renders with no
  auth wall for anyone (AC5); capture gates on `request.user.is_authenticated` because the
  D-7 corpus is `user × App.id`-keyed. An anonymous view/try/share still works (page
  renders, redirect fires, URL is shareable) but writes **no** event. This also **bounds R5**
  — crawlers are anonymous, so they generate no impressions and no signal inflation.
  *(Confirmed by DN-10.)*
- **`apps/pages/emission.py` — the surface-side non-blocking policy (AC7)** — each of
  `record_page_view` / `record_try_click` / `record_share` calls exactly one
  `signals.capture.*` recorder inside a `try/except`, increments `app_page_capture_degraded`
  + logs with request context, and **never re-raises into the request**. This is the
  complement of D-7 §5d: capture is loud *inside* signals (counts `capture_error` + raises),
  silent *to the visitor* (the surface catches, counts, degrades). No business logic / no
  ORM here — app validity, tag snapshot, and impression-ownership all stay enforced inside
  `signals.capture` (one source of truth). A forged/foreign `imp` raises
  `ImpressionMismatchError` inside capture → caught → **no event, still redirects** (no
  cross-user attribution, DESIGN §10).
- **The one shared-vocabulary touch — `Surface.APP_PAGE` (additive, no new ADR)** — added
  `APP_PAGE = "app_page", "app page"` to `apps/signals/kinds.Surface`, the **additive
  extension D-7 already pre-authorizes** (`kinds.py` names `app_page` explicitly). It lands
  as **`signals/0002_alter_impression_surface`**, a **choices-metadata-only, reversible**
  migration — no schema change, no data change. Every existing D-7 reader ignores the new
  value (they filter by app/kind/time, not surface), so backward compatibility is total.
- **Shared-surface touches** — three constants added to `apps/core/observability.py`
  (`app_page_rendered`, `app_page_not_available`, `app_page_capture_degraded`; §7 below);
  `apps.pages` added to `INSTALLED_APPS`; the `path("apps/", include("apps.pages.urls"))`
  include added to `config/urls.py` (the **activation switch** — DESIGN §12).
  `apps/accounts`, `apps/taxonomy`, `apps/catalog`, `apps/signals` reused **as-is**
  (except the one additive `Surface` value). **No new `.env` key.** No existing behavior
  changed.

## 3. Who is affected

- **End users / visitors** — there is now a public, openly-accessible page for every
  accepted app, reachable by direct link with **no account required** (AC5). Authenticated
  visitors' try-it and share interactions are captured as behavioral signal (AC6); anonymous
  visitors get the identical page and working actions, with nothing recorded. No PII is
  collected — capture writes only `user × App.id × impression` through the D-7 whitelist (no
  IP/UA/referrer is even representable in the schema).
- **Developers of accepted apps** — every accepted app now has a structurally-identical
  public home / press kit at a **stable, `App.id`-keyed URL** that survives metadata edits
  (AC4/AP-5). A solo dev's page is structurally identical to a studio's — uniformity is
  **structural**, not a convention (the `CatalogApp` DTO has no identity/team/paid field, so
  the template literally cannot vary by them — AC3).
- **The platform / data team** — the `app_page` surface now produces real
  impression→click-through→share signal into the D-7 corpus (read via
  `signals.selectors.*`, segmentable by `surface = app_page`). This is the **first live
  emitter of D-7 impressions** — until now the only writer was the visit middleware.
- **Downstream feature teams** (`weekly-digest`, `open-search-browse`, `ratings-reviews`,
  `app-subscriptions`) — app-pages is the public surface they point users at; its routes
  (`pages:app-page` / `pages:try` / `pages:share`) and the `App.id`-keyed URL are the stable
  handles to link to. The **reviews slot** is a defined empty state (AC9) — `ratings-reviews`
  fills it later without churning the uniform layout (AP-1).
- **Support** — no support-facing change at this release (local/dev target).

## 4. How to use it (operators)

The rollout is the ordered, additive steps from [DESIGN.md §12](DESIGN.md) — no new env
var, no feature flag, no recurring job:

1. `python manage.py migrate signals` — applies `signals/0002_alter_impression_surface`
   (choices metadata only; no table/data change). **Adopt before you emit** (D-7 §12):
   capture must understand `app_page` before any page emits one.
2. `python manage.py check` — must report no issues before the surface is considered live.
3. Deploy the build (which includes `apps.pages` in `INSTALLED_APPS` and the
   `path("apps/", include("apps.pages.urls"))` activation switch in `config/urls.py`). The
   `/apps/<App.id>/` pages go live on deploy. In production, the web server / object store
   fronts `MEDIA_URL` for screenshots (DESIGN §8); in `DEBUG` Django serves them.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with
> `identity-accounts`, `interest-taxonomy`, `submission-intake`, and `signal-capture`
> ([CONTROL.md](../../CONTROL.md)); the platform is still mid-development. The feature is
> verified locally (417 tests green, `check` clean, the additive migration applies and is
> reversible). **Production promotion and a live-metrics monitoring window are deferred**
> until there is a production target and real traffic.

This is an **additive new app**: nothing existing changes behavior, so there is **no
pre-existing surface to ramp against and nothing to feature-flag off** (an honest deviation
from the internal→%→full template — DESIGN §12). "Off" = don't include the URLconf. Safety
comes from the **removable URL include** + a **reversible, choices-only migration**, not a
kill switch.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Surface vocabulary live | `migrate signals` applied through `0002`; `Surface.APP_PAGE` present; `manage.py check` clean; `capture_error` reads 0. |
| Pages live | `/apps/<App.id>/` renders an accepted app (200) and 404s a non-accepted/unknown id; `/health` → 200. |
| Coverage = 100% | every accepted app in the D-6 selector resolves to a page (structural — one route over the selector); `app_page_rendered{app_id}` observed across the catalog. |
| Capture live | an authenticated page view records exactly one `app_page` impression; a try-it click records a linked `click_through`; `app_page_capture_degraded` and `capture_error` both read 0. |
| First funnel readable | at least one app with ≥1 app-page impression returns non-zero `click_through` / `share` counts from `signals.selectors.app_funnel` (the H1 impression→click-through rate becomes measurable here). |
| Stable at target | the above holds with `capture_error` = 0 and no sustained rise in `app_page_capture_degraded` through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**One action: remove the `config/urls.py` include** (`path("apps/", include("apps.pages.urls"))`)
— the pages vanish with **zero data migration**, because app-pages owns no schema. This is
the primary, design-for-deletion rollback; deleting the `apps/pages/` directory + the
`INSTALLED_APPS` entry fully removes the feature.

The one shared-schema footprint is the additive `signals/0002` migration. It is reversible,
but the `Surface.APP_PAGE` value should **stay** once any `app_page` impression exists
(removing an enum choice in use would orphan rows) — it is inert when unused, so there is no
reason to reverse it in a real rollback. If the schema state must nonetheless be undone (safe
only while no `app_page` impression exists):

```bash
python manage.py migrate signals 0001    # reverses the choices-only Surface alter
```

**Rehearsed 2026-06-20** on a throwaway PostgreSQL database (`app_pages_release_rehearsal`,
dropped afterward): `migrate` applied through `signals/0002` → `Surface.APP_PAGE` present
(`['digest', 'app_page']`) → `manage.py check` clean; then `migrate signals 0001` unapplied
`0002` cleanly (`check` still clean) and a re-`migrate signals` re-applied it (confirmed
reversible); `makemigrations --check` reported no drift. Confirmed `apps/pages` has **no
migrations** (primary rollback is pure code) and the three routes resolve. **Who can
trigger:** any operator with deploy access (URL-include removal) — the DB step additionally
needs DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; DB reachability is covered by
the existing `GET /health`. The three new constants live in `apps/core/observability.py`;
the funnel counters are **reused from D-7** (not duplicated). Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#5-success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| **Page coverage = 100%** (H2) | every accepted app resolves to a page (structural — one route over the D-6 selector); `app_page_rendered{app_id}` observed across the catalog. | Trend — a gap means an accepted app has no live page. |
| **Uniformity = 0 variants** (fairness) | structural — one template, `CatalogApp` carries no identity/team/paid field. **No metric can be nonzero.** | None possible (structural). |
| **Open-access = 100%** | structural — `AllowAny`, no auth branch in render. | None possible (structural). |
| **Click-through count + rate per page view** (H1) | `click_through_captured` ÷ `impression_captured{surface=app_page}` (the page-view impression is the denominator — AP-3). | Trend — the H1 impression→click-through link, measurable here for the first time. |
| **Share count** | `share_captured` per app that received app-page impressions. | Trend. |
| **Page render latency** | logged per render (a timing log line, not a counter); observable, not an SLA (D-2/A5). | Watch for regressions; no global ceiling. |
| **Non-accepted leakage = 0** | structural — render only via the D-6 accepted-only selector. `app_page_not_available` counts *attempts* (which 404), informational. | Renders of non-accepted = 0 by construction; the counter is **not** an alert (people share dead links). |
| **Capture degradation** (AC7 safety) | `app_page_capture_degraded` (surface fail-soft loss) + inherited D-7 `capture_error`. | **`capture_error` nonzero → page** (inherited D-7 alert — a half-written corpus is a defect); a sustained rise in `app_page_capture_degraded` means signals is unhealthy. |

## 8. Verification at release (2026-06-20)

- **417 automated tests pass** (374 baseline + 43 new app-pages / signals tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model
  drift (confirms `apps/pages` adds no migration of its own).
- Rollout→rollback **rehearsed** on a throwaway DB (§6): `migrate` → `signals/0002` applied,
  `Surface.APP_PAGE` live → `check` clean → `migrate signals 0001` reverses cleanly →
  re-`migrate signals` re-applies (reversible). Throwaway DB dropped after.
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 (plus the DESIGN §6/§7/§10/§11
  guarantees) to tests; the capture-failure / forged-impression / open-redirect / CSRF cases
  are each exercised.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §13](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **Cross-surface attribution not yet exercisable (R2).** No `weekly-digest` exists, so no
  *digest* impressions are created — the digest→click-through funnel cannot be exercised
  end-to-end. The **app-page** impression→click-through→share funnel **is** fully exercisable
  now (the page view is its own impression, AP-3), which is what AC6 and the H1 metric need.
  Verified end-to-end once an impression source ships.
- **Anonymous / sessionless capture not built (AP-4).** Anonymous visitors render and act but
  produce no signal (the D-7 corpus is user-keyed). Extending D-7 with an anonymous actor id
  is a named **growth path, deferred** — not a defect (it bounds crawler inflation, R5).
- **No `page_reengagement` emission.** Available in D-7, required by no AC — a named,
  deferred increment, not built (no speculative scope).
- **No cached D-6 projection.** The page reads the catalog live on every render (no N+1 — the
  selector prefetches media + resolves tags). A materialized projection is the documented
  D-6 **100×** growth path, additive, not built now.
- **Share capture needs JS.** The page is always *shareable* (the canonical URL is copyable —
  AC4 met); only the share *signal* needs the POST. A no-JS share-capture fallback was
  rejected as awkward for marginal signal; named as a later option.
- **No live-metrics window measured.** Deferred with the local/dev target until a production
  target and real traffic exist (mirrors the prior four closed-out features).
- **Richer press-kit apparatus out of scope (AP-2/AP-3 of the brief).** "Press kit" = the page
  + a stable link + submission media; no separate press-asset bundle, contact field, or
  embargo controls.

## 10. Stakeholder notification

On the first real (production) promotion: notify downstream feature owners that the public
app-page surface is live and linkable, and that it is the **first live emitter of D-7
`app_page`-surface impressions** — the impression→click-through→share funnel is now readable
through `signals.selectors.*`, segmentable by `surface = app_page`. Remind emitting/reading
surfaces of the D-7 contract (emit only through `signals.capture.*`; read only raw counts
through `signals.selectors.*`; never score in this layer). Hand `ratings-reviews` the reviews
slot boundary (AP-1 — the slot is a defined empty state, the content is theirs). No
support-facing change at this release — the local/dev target carries no production traffic.
