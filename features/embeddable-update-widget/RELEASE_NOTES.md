# RELEASE_NOTES — embeddable-update-widget

*Stage 5 artifact (Release Engineer). Status: **RELEASED to local/dev** 2026-06-26.
Production promotion + the live-metrics window defer until a prod target/traffic exists (as
the prior eleven features).*

Traces to [DESIGN §13 Rollout & rollback](DESIGN.md) · [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
success metrics M1–M6 · [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9).

---

## 1. What changed

The platform now has the **bring-your-own-audience capture widget** — the one missing
load-bearing piece of the developer-wedge cold start ([D-10](../../DECISIONS.md)). A developer
drops a one-line `<iframe>` **inside their own running app**; it renders that app's most-recent
**published notices** (the same `developer-updates` source of truth) plus a labeled "view on
platform" link back to the app's page, where the existing follow / sign-up paths are reachable.
It renders to **anonymous** end users (no platform account needed), reads only already-public
notice content, and is **rate-limited** per IP with a cached TTL so it stays fast and robust
inside someone else's page.

The headline integrity property is the **firewall (brief AC6 / R1, vision §5.4/§5.6)**: a
widget impression or click-through is a **non-curated surface** and can never confer
[D-8](../../DECISIONS.md) curated-rating eligibility or move the Quality Score. This is
**structural, not merely measured** — `apps/widget` **imports nothing from `apps/signals`**
(AST-enforced), so a widget interaction creates **zero** corpus rows and cannot be curated
evidence (**M5 = 0 by construction**). Reach is still attributed (AC9) through a dedicated,
PII-free daily-rollup store that the developer sees on their dashboard — independent of, and not
weakening, the firewall.

**Shipped components:**

- **NEW app `apps/widget/`** owning **one table** `widget_reach_count`
  (`widget/0001_initial`; UUID pk; soft [D-6](../../DECISIONS.md) `app_id`; `kind ∈
  {impression, click_through}`; `count_date`; `count`; unique `(app_id, kind, count_date)` +
  `widget_reach_app_kind_date_idx`; **no `user`/IP/UA/referrer/geo/device/score/weight/rank
  column** — the AC6 no-score + AC10 PII-free posture is structural in the schema):
  - [`attribution.py`](../../apps/widget/attribution.py) — the **single writer**: an atomic
    `F()`+1 increment on today's rollup row, with a unique-constraint **create-race retry**
    inside a nested `transaction.atomic()` savepoint (**EUW-IMPL-1** — a bare
    `except IntegrityError` poisons the Postgres transaction). Imports **no** `signals.capture`.
  - [`selectors.py`](../../apps/widget/selectors.py) — the **single reader**: `widget_reach`
    (windowed `SUM…GROUP BY`, zero-filled, **one query**) + `widget_reach_for_apps` (bulk,
    **one query regardless of app count** — no N+1, for the dashboard list).
  - [`content.py`](../../apps/widget/content.py) — `build_widget_view` → the pure view-model:
    capped newest-first notices via `updates.selectors`, the server-derived
    `reverse("pages:app-page", [id])` link, a `notices_degraded` fail-soft split; `None` on a
    non-accepted id (D-6 gate).
  - Two **AllowAny** views ([`views.py`](../../apps/widget/views.py)): `widget_render`
    (`@xframe_options_exempt`, `Cache-Control: public, max-age=<config>`, per-IP rate-limited,
    fail-soft impression count) and `widget_view_redirect` (fail-soft click-through count + a
    **302 to the server-derived app page** — no open redirect, the destination is never a
    request param). Self-contained server-rendered templates — **no JS, inline CSS,
    auto-escaped, no build step** (AC7).
  - Ten `WIDGET_*`/`DASHBOARD_WIDGET_DEGRADED` observability counters
    ([`apps/core/observability.py`](../../apps/core/observability.py)); three `widget_*` config
    tunables ([`apps/core/config.py`](../../apps/core/config.py), in `validate_all`).

- **Additive, reusable `apps/core` GET rate limiter**
  ([`apps/core/ratelimit.py`](../../apps/core/ratelimit.py)): `ip_rate_limited_get` generalizes
  the existing limiter internals by one `window_seconds` parameter (429-no-call; **fail-open**
  on a cache error so the host page never breaks; metric names injected so core stays
  feature-agnostic). The existing auth `rate_limited` path is **unchanged**.

- **ONE additive, fail-soft change on the closed `apps/dashboard/`**: a **"Widget reach"** slot
  (AC9) — `reception.WidgetReachView` + `ReceptionSummary.widget_impressions` (one bulk
  `widget_reach_for_apps` read, no N+1) + `AppReception.widget_reach`. It degrades **only that
  slot** (`DASHBOARD_WIDGET_DEGRADED`) while the core on-platform signals read keeps its
  loud-500 posture; it is **labeled off-platform**, rendered distinct from the on-platform
  per-`Surface` breakdown (one source of truth per fact). This is the only `dashboard → widget`
  import edge.

**Verified before ship (this session, independently re-run):** **893 tests** green (+65 over
the 828 baseline), `ruff check` clean, `python manage.py check` no issues, `makemigrations
--check` → no drift; `widget/0001_initial` reversible (up→down→up rehearsed on a real
PostgreSQL DB — see §5).

## 2. Who is affected

- **Developers** (the `developer` role) with an **accepted** app — they gain a free, drop-in way
  to surface their changelog + a path back to the platform **where their users already are**, and
  a dashboard "Widget reach" readout of the resulting reach.
- **End users of a host app** — including **anonymous** (not-logged-in) ones — now see an app's
  public notices and can click through to its platform page without authenticating. Only
  already-public notice content + the link is exposed.
- **No one else, and no regression.** The widget app is a new, self-contained surface; the
  `core` limiter is additive (the auth path is untouched); the dashboard change is additive +
  fail-soft (inert until the slot reads). An unknown / non-accepted app id ⇒ a neutral
  `unavailable` (404 on render, 404 on `/view`); over the rate limit ⇒ 429 with no render and
  **no impression counted**.

## 3. How to use it

A developer copies a **one-line embed** from `apps/widget/README.md` into their own app's HTML:

```html
<iframe src="https://<platform-host>/widget/<app-id>/" title="What's new"
        style="border:0;width:100%;height:480px"></iframe>
```

It renders that app's recent published notices (newest-first, capped at
`widget_notice_limit()`, default 5) and a "view on platform" link; an empty app shows a neutral
empty state and still offers the link. No platform build toolchain, no JS, no API key. Notices
stay in sync automatically — the widget reads the live `developer-updates` source of truth, so
publishing or withdrawing a notice there changes the next render. The render is cached
(`widget_cache_max_age_seconds()`, default 60s) and rate-limited
(`widget_render_rate_limit_per_ip_per_minute()`, default 5/min/IP).

## 4. Operator rollout

- **Stack:** reuse **D-4** (Python/Django + PostgreSQL, server-rendered templates) — no new
  global ADR; the app lives at `apps/widget/`.
- **Activation switch = three additive parts + one migration, all in place** (DESIGN §13):
  1. `"apps.widget"` in `INSTALLED_APPS` ([`config/settings.py`](../../config/settings.py)) +
     its one migration `widget/0001_initial` (the `widget_reach_count` table).
  2. `path("widget/", include("apps.widget.urls"))` in [`config/urls.py`](../../config/urls.py)
     (own `/widget/` prefix; no collision with `pages` `/apps/`) — **the effective on-switch**:
     until this include lands, the surface is unreachable.
  3. The additive dashboard widget-reach slot + the `core` additions (the GET limiter, the three
     `widget_*` tunables, the `WIDGET_*` counters).
- **No feature flag, no data backfill.** All changes are additive; no existing contract altered.
  Deploy the migration before the include goes live (the views need the table).
- **Promotion table:**

  | Stage | Target | Promotion criterion |
  |-------|--------|---------------------|
  | local/dev | **done (2026-06-26)** | 893 tests green; routes resolve; the migration reversible; rollback rehearsed (§5) |
  | internal | _deferred_ | no error spike; `WIDGET_RENDER_DEGRADED` / `WIDGET_COUNT_DEGRADED` ≈ 0 and `DASHBOARD_WIDGET_DEGRADED` flat for the soak window; M6 render latency sane |
  | prod (% → full) | _deferred_ | **M5 = 0** (structural, asserted); `WIDGET_RENDER_DEGRADED` / `WIDGET_COUNT_DEGRADED` below threshold for the soak window; M1/M2/M4 reach trends visible — **deferred: no prod target/traffic** |

## 5. Rollback (rehearsed)

Like `developer-updates`, this feature **touches a closed app** — `apps/dashboard` now imports
`widget.selectors` for the reach slot. So rollback is **not** a single include-removal: simply
pulling the `INSTALLED_APPS` line or the `widget/` include would leave the dashboard importing a
vanished module and break it. **The clean, atomic operational rollback is therefore `git revert`
of the build commit** (`b7db60f` *embeddable-update-widget/ development*) — the **DU-REL-1**
precedent — which drops the dashboard edit **and** the include **and** the `INSTALLED_APPS` line
together in one reversible step. The manual equivalent, if reverting by hand:

1. **Dashboard** — revert the additive "Widget reach" slot in
   [`apps/dashboard/reception.py`](../../apps/dashboard/reception.py) (and its
   `app_reception.html` / `my_apps.html` display) **and remove its `from apps.widget import
   selectors` import** — otherwise importing `dashboard.reception` fails once `apps.widget`
   leaves `INSTALLED_APPS`.
2. **Route** — remove the `path("widget/", …)` include from `config/urls.py`.
3. **App** — remove `"apps.widget"` from `INSTALLED_APPS`, and the additive `core` limiter /
   `widget_*` tunables / `WIDGET_*` counters.
4. **Data (optional)** — `widget_reach_count` may stay inert (it holds only PII-free reach
   counts) or be migrated down: `python manage.py migrate widget zero`.

→ The widget surface is instantly gone (404 if anything still requests `/widget/…`); the
dashboard returns to its pre-feature reception view; the catalogue, corpus, and notices are
untouched.

**Who can trigger it:** any operator with repo/deploy access (`git revert b7db60f` + redeploy;
the optional DB step needs no data coordination — the table holds only aggregate reach counts).

**Rehearsal (2026-06-26, performed this session — on a throwaway local PostgreSQL cluster):**
- **Up:** full suite **893 green**; `ruff` clean; `manage.py check` clean; `makemigrations
  --check` no drift. Migrated a fresh dev DB up — `widget/0001_initial` applies and the
  `widget_reach_count` table is present.
- **Migration down→up:** `migrate widget zero` drops the table cleanly; `migrate widget`
  re-applies it cleanly (the down-migration is sound).
- **Operational rollback:** `git revert --no-commit b7db60f` removed `apps/widget`, the
  `widget/` include, **and** the dashboard edit in one step; **`manage.py check` then passed
  with no dangling `dashboard → widget` import** (the load-bearing DU-REL-1 property — proven,
  not assumed). Restored to `b7db60f` (`git status` clean); full suite **893 green** again.

## 6. Monitoring — metrics → signals → alert

Ten counters in [`apps/core/observability.py`](../../apps/core/observability.py):

| Counter | Feeds | Notes |
|---------|-------|-------|
| `WIDGET_RENDERED{app_id}` | **M4** reach / **M1** adoption | a widget load was served |
| `WIDGET_EMPTY` | health | a render with no notices (the truthful empty state — expected, not an alert) |
| `WIDGET_CLICK_THROUGH{app_id}` | **M2** capture | a "view on platform" click |
| `WIDGET_NOT_AVAILABLE` | health | unknown / non-accepted id requested (→404) |
| `WIDGET_RATE_LIMITED` | **M6** abuse bound (AC8) | over the per-IP render limit (→429) — expected trend, not an alert |
| `WIDGET_NOTICES_DEGRADED` | health (fail-soft) | the notice read fell back → link-only render, still 200 |
| `WIDGET_RENDER_DEGRADED` | **actionable** | the catalog read raised → neutral `unavailable` 200; a rising rate is a render Sev signal |
| `WIDGET_COUNT_DEGRADED` | **actionable** | an attribution write failed → still 200 but reach is silently lossy; a rising rate is the attribution Sev signal |
| `WIDGET_LIMITER_DEGRADED` | health (fail-soft) | the rate-limiter cache failed → fail-open (the host page never breaks) |
| `DASHBOARD_WIDGET_DEGRADED` | health (fail-soft) | the dashboard reach slot fell back → that slot only; the core reception view is unaffected |

- **The two actionable signals are `WIDGET_RENDER_DEGRADED` and `WIDGET_COUNT_DEGRADED`.**
  Everything else is fail-soft, expected-trend, or a normal-traffic counter.
- **M5** (curated eligibilities conferred by a widget interaction) target = **0**, enforced
  **structurally** — `apps/widget` imports no `signals.capture` (AST-asserted), so no code path
  can write a corpus row. It is an asserted test invariant
  ([TEST_PLAN.md](TEST_PLAN.md) AC6/M5), not a runtime gauge — no "must-stay-0" alert is needed
  because no path can break it.
- **M1/M2/M4** are derived from the `WIDGET_RENDERED` / `WIDGET_CLICK_THROUGH` counters and the
  `widget_reach` windows surfaced on the developer dashboard.
- **M6** (render latency + error rate) → the request latency log + the `*_DEGRADED` counters;
  fail-soft tests prove a degraded dependency still returns 200, never a 500 into the host page.

## 7. Known limitations

- **No live metrics yet** — local/dev only, no prod traffic; M1–M6 are instrumented but the
  measurement window opens when a prod target/traffic exists (the prior-feature pattern).
- **M3 (per-account conversion attribution) is deferred** — counting *which* widget click-throughs
  become new accounts/follows needs a widget-source token carried through an anonymous
  click→signup; out of MVP (OQ-EUW-5, DESIGN §11). **AC9 *reach* ships now**; conversion does not.
- **Reach is approximate by design** — the per-IP rate limit + the cache TTL deliberately
  undercount loads to protect the origin and the host page's performance (M6). Reach is a signal,
  not an exact count (DESIGN §14, accepted).
- **A benign hot-row write-contention trade-off** — all reach for one app/kind/day lands on a
  single rollup row; the atomic increment + create-race retry are correct, but extreme
  concurrency on one row is throttled by the rate limit + TTL rather than sharded. A named growth
  path, not pre-built (DESIGN §6, accepted bounded trade-off).
- **Minimal theming** — a functional drop-in `<iframe>`; deep customization beyond minimal
  branding is out of scope.
- **No widget-side notice store** — the widget reads notices live every render (truth + one
  query); there is no widget-owned copy to drift.

---

*Reuses **D-4** (stack), **D-6** (accepted-only / soft `app_id`), **D-7** (corpus — *not*
extended; the firewall is by absence), **D-8** (the curated-rating gate it stays outside),
**D-9** (free tool, non-curated surface), **D-10** (developer wedge) — no new global ADR.
Feature-local decisions EUW-7…11 + EUW-IMPL-1 (**BUILT**) in [DECISIONS.md](DECISIONS.md).*
