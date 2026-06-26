# apps/widget — the embeddable "what's new" widget

The bring-your-own-audience capture widget (developer-wedge pivot, [D-10](../../DECISIONS.md)). A
developer pastes **one line** of HTML inside their **own** app; it renders that app's published
[`apps/updates/`](../updates/) notices and a labeled "view on platform" link, so their existing
(often not-yet-platform-member) users see the changelog and click through onto the platform. The
app **owns one table** (`widget_reach_count`) — a daily rollup that counts the reach the widget
drives, surfaced to the developer on their dashboard (AC9).

## The embed (AC7 — drop-in, no build toolchain)

One line of HTML, no `<script>`, no build step:

```html
<iframe src="https://<platform>/widget/<app_id>/"
        title="What's new" width="340" height="420"
        style="border:0" loading="lazy"></iframe>
```

The platform serves a complete, self-contained HTML page (inline CSS, no JavaScript, no external
assets) at `GET /widget/<app_id>/`. Inside it the "View on platform" control is a plain link that
**breaks out of the frame** (`target="_top"`) and routes through `/widget/<app_id>/view`.

## Routes

- **Render** (`GET /widget/<uuid:app_id>/`, name `widget:render`): the framable widget for an
  ACCEPTED app. **AllowAny** (anonymous end users, AC5); per-IP rate-limited (AC8);
  `@xframe_options_exempt` (cross-origin framing — safe: read-only public content, no
  authenticated action); `Cache-Control: public, max-age=<config>`. Counts one **impression**
  (fail-soft). Unknown/non-accepted id → neutral `unavailable.html` (404).
- **View redirect** (`GET /widget/<uuid:app_id>/view`, name `widget:view`): counts one
  **click_through** (fail-soft), then **302** to `reverse("pages:app-page", [app_id])` — a
  **server-derived** target, never a request param (no open redirect, F4). Unknown id → 404.

## Design guarantees

- **The firewall (AC6 / M5 = 0) is structural by absence.** This app **imports nothing from
  `apps.signals`** — enforced by [`tests/test_imports.py`](tests/test_imports.py). A widget
  interaction creates **no** D-7 corpus row, so it can never be
  `signals.has_impression(surfaces=CURATED_SURFACES)` evidence: it confers **no D-8 curated-rating
  eligibility** because it does not exist in the corpus to be read. This is stronger than "a
  `Surface` outside `CURATED_SURFACES`", and keeps the corpus authenticated + PII-free.
- **PII-free + anonymous by construction (AC10 posture).** `widget_reach_count` has **no `user`
  FK and no IP/UA/referrer/geo/device/score column** — over-collection is *unrepresentable*, not
  merely avoided.
- **Daily rollup, atomic increment (EUW-9).** The single writer ([`attribution.py`](attribution.py))
  increments today's `(app_id, kind, count_date)` row with a DB-evaluated `F("count") + 1` inside
  `transaction.atomic()`; the unique constraint turns a concurrent create into a caught
  `IntegrityError` resolved by re-incrementing (the create is wrapped in a nested savepoint so a
  failed create never poisons the transaction — EUW-IMPL-1). No cache/queue infra (the
  `developer-updates` durable-table precedent). The rollup bounds growth to `apps × 2 × days`; the
  named growth path past a write-hot row is per-day counter sharding (not built — no speculative
  abstraction).
- **Fail-soft to the host, loud to ops (§8).** The widget lives inside someone else's page, so a
  failure must never 500 into the host. The notice read degrades to link-only
  (`WIDGET_NOTICES_DEGRADED`); a catalog/build error renders the neutral unavailable page at 200
  (`WIDGET_RENDER_DEGRADED`); an attribution write error is swallowed after
  `WIDGET_COUNT_DEGRADED` (**the one actionable alert** — sustained ⇒ attribution silently
  lossy); a rate-limiter cache outage **fails open** (`WIDGET_LIMITER_DEGRADED`). Over the limit ⇒
  429 with no render or count (`WIDGET_RATE_LIMITED`).
- **XSS.** Server-rendered, auto-escaped templates; notice `title`/`summary` are untrusted
  developer input shown cross-origin → never `|safe`/`mark_safe`.

## Modules

| File | Responsibility |
|---|---|
| [`kinds.py`](kinds.py) | `WidgetEventKind` (`impression` \| `click_through`) — the closed vocabulary. |
| [`models.py`](models.py) | `WidgetReachCount` / `widget_reach_count` — the daily-rollup shape only (no logic); unique constraint + `widget_reach_app_kind_date_idx`. |
| [`attribution.py`](attribution.py) | The **single writer**: `record_widget_impression` / `record_widget_click_through` — the atomic per-day increment. Imports no `signals`. |
| [`selectors.py`](selectors.py) | The **single reader** → frozen `WidgetReach` DTO: `widget_reach(app_id, *, start, end)` + `widget_reach_for_apps(app_ids, …)` (one grouped query, zero-filled, no N+1). |
| [`content.py`](content.py) | `build_widget_view(app_id) -> WidgetView \| None` — the pure render assembler (notices + server-derived link + `notices_degraded`). |
| [`views.py`](views.py) / [`urls.py`](urls.py) | Thin HTTP: rate-limit, call `content`/`attribution`, render/redirect. No ORM, no business logic. |
| `templates/widget/` | `widget.html` (framable card) + `unavailable.html` (neutral) — self-contained, no JS, inline CSS, auto-escaped. |

## Configuration ([`apps/core/config.py`](../core/config.py))

`widget_notice_limit` (5), `widget_render_rate_limit_per_ip_per_minute` (60),
`widget_cache_max_age_seconds` (60) — all validated at startup by `validate_all`.

## Observability ([`apps/core/observability.py`](../core/observability.py))

`WIDGET_RENDERED` (M4), `WIDGET_EMPTY`, `WIDGET_CLICK_THROUGH` (M2), `WIDGET_NOT_AVAILABLE`,
`WIDGET_RATE_LIMITED` (AC8), `WIDGET_NOTICES_DEGRADED`, `WIDGET_RENDER_DEGRADED`,
`WIDGET_COUNT_DEGRADED` (**the one alert**), `WIDGET_LIMITER_DEGRADED`, and
`DASHBOARD_WIDGET_DEGRADED` (the dashboard slot). M5 (reach beyond the firewall = 0) is
structural — no counter.

## Deferred — per-account conversion attribution (M3, OQ-EUW-5)

AC9's binding requirement is **reach** (impressions + click-throughs, visible on the dashboard) —
fully delivered. **M3** ("which signup came from which widget click") additionally requires
carrying a widget-source token through an anonymous click → app page → sign-up across
sessions/domains (cookie consent + cross-domain identity + the no-PII posture) — a materially
harder problem. Deferred to a follow-up (DESIGN §11 / OQ-EUW-5), traceable, not dropped. The
click-through count is the honest MVP "reached the platform from the widget" measure.

## Rollback (DESIGN §13 — honest)

Rollback is **`git revert` of the build commit**, not a single include-removal. The closed
[`apps/dashboard/`](../dashboard/) now imports `widget.selectors` for its widget-reach slot, so
pulling only the `"apps.widget"` `INSTALLED_APPS` line would break the dashboard import. The
revert drops the dashboard slot **and** the `path("widget/", include("apps.widget.urls"))` line
**and** the `INSTALLED_APPS` line together (the DU-REL-1 precedent). The `widget_reach_count`
table down-migration (`migrate widget zero`) is independent and optional — the data is inert once
the routes/imports are gone.
