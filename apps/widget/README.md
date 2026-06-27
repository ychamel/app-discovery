# apps/widget — the embeddable "what's new" widget

The bring-your-own-audience capture widget (developer-wedge pivot, [D-10](../../DECISIONS.md)). A
developer pastes **one line** of HTML inside their **own** app; it renders that app's published
[`apps/updates/`](../updates/) notices and a labeled "view on platform" link, so their existing
(often not-yet-platform-member) users see the changelog and click through onto the platform. The
app **owns two daily-rollup tables**: `widget_reach_count` (impressions + click-throughs the
widget drives) and `widget_conversion_count` (the downstream follows + new accounts a click-through
led to — widget-conversion-attribution), both surfaced to the developer on their dashboard (AC9/AC3).

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
| [`kinds.py`](kinds.py) | `WidgetEventKind` (`impression` \| `click_through`) + `WidgetConversionKind` (`follow` \| `account`) — the two **disjoint** closed vocabularies. |
| [`models.py`](models.py) | `WidgetReachCount` / `widget_reach_count` **and** `WidgetConversionCount` / `widget_conversion_count` — the daily-rollup shapes only (no logic); each with its unique constraint + `(app_id, kind, count_date)` index. |
| [`rollup.py`](rollup.py) | `_increment_daily(model, app_id, kind)` — the **one** concurrency-correct atomic per-day increment (create-race retry), shared by both writers. Imports no `signals`. |
| [`attribution.py`](attribution.py) | The **single writers**: `record_widget_impression` / `record_widget_click_through` (reach) + `record_widget_conversion(app_id, kind)` (conversion). Delegate to `rollup`. Imports no `signals`. |
| [`source.py`](source.py) | The **only** module that knows the `widget_src` cookie format: `set_marker` (arm on the click 302) + `attribute_follow` / `attribute_account` (decode, window + dedup, credit). Signed `{v, src, credited}`, no PII. Imports no `signals`. |
| [`selectors.py`](selectors.py) | The **single readers** → frozen `WidgetReach` / `WidgetConversion` DTOs: `widget_reach[_for_apps]` + `widget_conversions[_for_apps]` (one grouped query each, zero-filled, no N+1). |
| [`content.py`](content.py) | `build_widget_view(app_id) -> WidgetView \| None` — the pure render assembler (notices + server-derived link + `notices_degraded`). |
| [`views.py`](views.py) / [`urls.py`](urls.py) | Thin HTTP: rate-limit, call `content`/`attribution`, render/redirect; `/view` also arms the source marker fail-soft. No ORM, no business logic. |
| `templates/widget/` | `widget.html` (framable card) + `unavailable.html` (neutral) — self-contained, no JS, inline CSS, auto-escaped. |

The two **conversion hooks** live in the converting apps (the DAG points `subscriptions → widget`
and `accounts → widget`; `apps/widget` imports neither): `subscriptions.views.follow` credits a
follow on a genuinely new follow, `accounts.views.register` credits an account on the 202 path —
each a one-line `widget.source` call wrapped fail-soft.

## Configuration ([`apps/core/config.py`](../core/config.py))

`widget_notice_limit` (5), `widget_render_rate_limit_per_ip_per_minute` (60),
`widget_cache_max_age_seconds` (60), `widget_attribution_window_days` (30 — the last-touch
conversion window) — all validated at startup by `validate_all`.

## Observability ([`apps/core/observability.py`](../core/observability.py))

Reach: `WIDGET_RENDERED` (M4), `WIDGET_EMPTY`, `WIDGET_CLICK_THROUGH` (M2), `WIDGET_NOT_AVAILABLE`,
`WIDGET_RATE_LIMITED` (AC8), `WIDGET_NOTICES_DEGRADED`, `WIDGET_RENDER_DEGRADED`,
`WIDGET_COUNT_DEGRADED` (**the one reach alert**), `WIDGET_LIMITER_DEGRADED`, and
`DASHBOARD_WIDGET_DEGRADED` (the dashboard slot). Conversion: `WIDGET_CONVERSION_ATTRIBUTED` (M1,
tagged `kind`), `WIDGET_CONVERSION_NO_SOURCE` / `_EXPIRED` (M3 coverage), `WIDGET_CONVERSION_DEGRADED`
(**the one conversion alert**, M6). M4/M5 (firewall = 0, PII fields = 0) are structural — no counter.

## Conversion attribution (M3 — delivered, widget-conversion-attribution)

The deferred OQ-EUW-5 — *which signup/follow came from which widget click* — is now delivered,
**aggregate-only and no-PII**. The click-through 302 is a top-level navigation onto the **platform
origin**, so a marker set there is **first-party from birth** (no third-party cookie, no
cross-domain identity). [`source.py`](source.py) signs a source-only `widget_src` cookie carrying
just `{version, source app-id, credited-kinds}`; at a later **follow** of the clicked app or a new
**account** (within a 30-day last-touch window), the matching view hook decodes it and bumps the
separate `widget_conversion_count` rollup keyed by the *source* app — never a person. Dedup is the
per-marker `credited` set (no person key). The firewall holds: `apps/widget` still imports no
`signals`, and conversions have no score column, so a credited conversion confers **no** D-8
eligibility (M5 = 0, structural). See the feature
[DESIGN.md](../../features/widget-conversion-attribution/DESIGN.md).

## Rollback (DESIGN §13 — honest)

Rollback is **`git revert` of the build commit**, not a single include-removal. `apps/dashboard`,
`apps/subscriptions`, and `apps/accounts` now import `widget` (the dashboard slot + the two
conversion hooks), so pulling only the `"apps.widget"` `INSTALLED_APPS` line would break those
imports. The revert drops the dashboard slot, the conversion hooks, the `widget/` URL include, and
the `INSTALLED_APPS` line together (the DU-REL-1 precedent). The `widget_reach_count` /
`widget_conversion_count` table down-migrations (`migrate widget zero`) are independent and
optional — the PII-free aggregate data is inert once the routes/imports are gone.
