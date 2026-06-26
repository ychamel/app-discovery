# DESIGN — embeddable-update-widget

_Status: **DRAFT — awaiting DN-EUW-DESIGN** (Stage 2, Software Architect). Implements the
APPROVED [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (6 stories / **AC1–AC9** / M1–M6). Resolves
OQ-EUW-1 (embedding mechanism), OQ-EUW-2 (how widget-source attribution is emitted + read),
OQ-EUW-3 (the public-read abuse limits). **AC6 (the firewall) and AC9 (source attribution)
are binding brief inputs**, honored here, not re-decided._

> Reuses the existing stack ([D-4](../../DECISIONS.md): Python / Django + PostgreSQL) and the
> `apps/` shared-code root — **no new global ADR**. Reinforces, never contradicts,
> [D-7](../../DECISIONS.md) (the signal corpus), [D-8](../../DECISIONS.md) (the curated-rating
> gate), [D-9](../../DECISIONS.md)/[D-10](../../DECISIONS.md) (firewall + developer wedge).

---

## 1. Scope (protocol step 1)

**The problem, in one sentence:** give a developer a paste-one-line, no-build "what's new"
box they embed **inside their own app**, which shows that app's published update notices and a
labeled link back to its platform page — so their existing (often not-yet-platform-member)
users see the changelog and click through onto the platform — with **zero** ability for that
embed to buy or confer ranking, and with the **widget-attributed reach made visible to the
developer**.

- **Stakeholders:** the embedding developer (adopts it, reads the attribution); their end
  users (read notices anonymously, click through); the platform (cold-start fill via
  bring-your-own-audience; integrity firewall held).
- **Out of scope** (from the brief §7, unchanged): in-widget authoring/auth, paid promotion
  placements ([D-9](../../DECISIONS.md)), update re-boosts / impression allocation, email/push,
  deep theming, cross-app discovery inside the widget, mobile/desktop SDK install attribution,
  and **per-account conversion attribution** (M3's "which signup came from which widget click")
  — see §11 (deferred, with the named reason).
- **Lifespan:** platform feature (load-bearing for the wedge) — full design rigor.

## 2. Requirements (protocol step 2)

**Functional** (each traces to an AC):

| # | Requirement | AC |
|---|-------------|----|
| F1 | Render an app's most-recent published notices (kind/title/summary/date), newest-first, capped. | AC1 |
| F2 | Neutral empty state when there are no notices; the link is still offered. | AC2 |
| F3 | Reflect publish/withdraw made through `developer-updates` — read the same source of truth, author nothing. | AC3 |
| F4 | A labeled "view on platform" link landing on the app's `App.id`-keyed app page. | AC4 |
| F5 | Render to anonymous (no account) end users; expose only already-public content. | AC5 |
| F6 | Every widget impression + click-through is firewalled: outside `CURATED_SURFACES`, confers no D-8 eligibility, **by construction**. | AC6 / M5 |
| F7 | Drop-in embed, **no platform build toolchain**. | AC7 |
| F8 | Rate-limit the unauthenticated read; serve only public content. | AC8 |
| F9 | Attribute every impression + click-through (anonymous included) to the widget as source; surface widget-attributed reach on the developer dashboard. | AC9 / M2 / M4 |

**Non-functional:** low render latency + robustness (it lives inside someone else's app — M6);
safe cross-origin embedding; bounded write cost on an anonymous, scrape-prone, potentially
high-traffic surface (it is *designed* to sit in third-party apps that may have far more
traffic than the platform); no PII collection (honor the [D-7](../../DECISIONS.md) AC10
posture); scalable to 100× embed/traffic growth.

**Hard constraints (binding brief inputs — not design choices):** AC6 firewall (EUW-4); AC9
attribution required for **all** end users incl. anonymous (EUW-6); ACCEPTED apps only
([D-6](../../DECISIONS.md)); reuse the `developer-updates` notice source of truth (EUW-1).

**Assumptions** (verified against code in §12):
- `updates.selectors.published_notices_for_apps([app_id], limit=…)` returns the bounded,
  newest-first `PublishedNotice` set for one app — **[verified]**.
- `pages:app-page` (`/apps/<app_id>/`) is the stable `App.id`-keyed destination — **[verified]**.
- `catalog.get_catalogued_app(app_id)` returns the ACCEPTED app (name + content) or `None` —
  **[verified]**.
- `ratings.gate.CURATED_SURFACES = {DIGEST}`; nothing the widget does is in it — **[verified]**.
- The D-7 `Impression`/`EngagementEvent` corpus is **keyed `user × App.id`** and its sole
  writer `signals.capture` requires an **authenticated actor** + forbids PII columns —
  **[verified]** (this is the crux that shapes §5/§6).

## 3. The central design tension (and how it is resolved)

AC9 requires attributing **anonymous** widget reach. The existing D-7 corpus cannot host that
cleanly: every `Impression`/`EngagementEvent` row is keyed to a `user`, `signals.capture`'s
documented invariant is *"the actor is always the caller's authenticated account"*, and the
schema deliberately forbids any anonymous-actor / device / referrer column (the AC10 privacy
whitelist). Forcing anonymous widget rows into `signals` would (a) break that invariant and
overload the meaning of `user IS NULL` (today: deletion-anonymized), (b) pour anonymous,
high-volume, scrape-prone third-party traffic into the platform's integrity-critical corpus,
and (c) make the firewall a *runtime* property ("this surface is outside `CURATED_SURFACES`")
rather than a structural one.

**Resolution — a dedicated, firewalled-by-absence attribution store owned by `apps/widget`.**
Widget impressions and click-throughs are counted in a small store the new app owns; they
**never create a `signals` row** and `apps/widget` **imports nothing from `signals`**
(AST-enforced, the established `discovery`/`dashboard`/`updates` precedent). The firewall (AC6 /
M5 = 0) is then **structural by total absence from the corpus** — a widget interaction cannot be
`signals.has_impression(surfaces=CURATED_SURFACES)` evidence because it does not exist there.
This is a *stronger* satisfaction of AC6 than "a `Surface` outside `CURATED_SURFACES`," and it
keeps the corpus authenticated + PII-free. The developer dashboard reads widget reach from this
store as a clearly-labeled, distinct **off-platform reach** slot (not merged into the on-platform
per-`Surface` breakdown — they are different facts; see §9).

> This resolves OQ-EUW-2. The brief's illustrative "`Surface.WIDGET`" (brief §8) is **not**
> adopted: widget reach is its own fact in its own store, not a `signals` surface. AC9's binding
> requirement ("source tracked as the widget, reach visible on the dashboard") is fully met.
> The chosen vs rejected alternative is logged as **EUW-8**.

## 4. Current-state summary (protocol step 3 — reuse before building)

| Existing component | What the widget reuses | Boundary respected |
|--------------------|------------------------|--------------------|
| `apps/updates/selectors.py` `published_notices_for_apps(app_ids, *, limit)` → `[PublishedNotice]` | The **only** notice read (F1/F3). Single app → `[app_id]`. | Read-only; the widget authors nothing (EUW-1). |
| `apps/catalog/selectors.py` `get_catalogued_app(app_id)` → `CatalogApp \| None` | Validate ACCEPTED (D-6) + app `name` for the widget heading. | Accepted-only; `None` ⇒ neutral not-available. |
| `apps/pages/urls.py` `pages:app-page` | The click-through destination (F4), via `reverse(...)` — never a request param (no open redirect). | Stable `App.id` link. |
| `apps/ratings/gate.py` `CURATED_SURFACES` | Nothing to call — the firewall is satisfied by **not** touching `signals`. | Single D-8 source untouched. |
| `apps/dashboard/reception.py` | Gains one additive **widget-reach** slot (AC9 display). | Additive, fail-soft; same posture as the reviews slot. |
| `apps/core/ratelimit.py`, `core/config.py`, `core/observability.py` | A reusable per-IP GET limiter (AC8), config tunables, metric constants. | Cross-cutting concerns stay in `core` (one home). |

No existing component is rewritten. The two touched closed apps (`dashboard`, `core`) take
**additive** changes only.

## 5. Proposed architecture — modules (protocol steps 4–5)

A new Django app **`apps/widget/`** (house convention: `pages`/`discovery`/`dashboard`/
`updates`). It owns exactly one small table and a narrow read/write/render surface. Each module
has one job; dependencies point only toward stable, already-shipped reads.

```
apps/widget/
  kinds.py        WidgetEventKind (impression | click_through) — closed vocabulary
  models.py       WidgetReachCount — the one owned table (daily rollup; no user, no PII)
  attribution.py  the SINGLE writer: record_widget_impression / _click_through (atomic ++)
  selectors.py    the SINGLE reader: widget_reach[/ _for_apps] -> WidgetReach (windowed)
  content.py      build_widget_view(app_id) -> WidgetView | None  (notices + page link)
  views.py        widget_render (iframe target) + widget_view_redirect (click → app page)
  urls.py         widget:render, widget:view
  templates/widget/  widget.html (framable), unavailable.html (neutral, framable)
  tests/test_imports.py  AST: apps/widget imports nothing from apps.signals (AC6 structural)
```

**Dependency DAG** (all edges point to shipped, stable surfaces; no cycle):

```
widget.views ─→ widget.content ─→ updates.selectors      (notices, F1/F3)
            │                  └─→ catalog.selectors       (accepted + name, D-6)
            ├─→ widget.attribution ─→ widget.models        (the count write, AC9)
            ├─→ core.ratelimit (AC8)   ├─→ pages reverse() (the link, F4)
            └─→ core.observability
dashboard.reception ─→ widget.selectors ─→ widget.models   (the AC9 read; additive edge)
```

`apps/widget` imports **nothing** from `apps.signals` (the firewall, §3) and nothing from
`apps.dashboard` (the dashboard depends on the widget, never the reverse).

### 5.1 Embedding mechanism — a server-rendered `<iframe>` (resolves OQ-EUW-1)

The developer pastes **one line** of HTML, no script, no build:

```html
<iframe src="https://<platform>/widget/4f3c…-<app_id>/"
        title="What's new" width="340" height="420"
        style="border:0" loading="lazy"></iframe>
```

The platform serves a complete, self-contained HTML page at `GET /widget/<app_id>/` (inline
CSS, no external assets, no JavaScript). Inside it the "View on <platform>" control is a plain
link that **breaks out of the frame**:

```html
<a href="https://<platform>/widget/<app_id>/view" target="_top">View on <platform></a>
```

Why the iframe is the right boring choice (vs a `<script>` injector or a JSON-render-yourself
endpoint — see §10 alternatives): **zero-build** (AC7 — pure HTML paste); **cross-origin-safe
by construction** (the browser sandboxes the frame; the host page's CSS/JS cannot collide with
ours, and ours cannot touch theirs); **the platform controls exactly what renders** (no XSS
injection surface in the host page, and the firewall content is ours end-to-end); **server-side
capture with no client JS** — the iframe `GET` *is* the impression, and the `target="_top"`
link routed through `/widget/<app_id>/view` *is* the click-through, both recorded on the server.

Cross-origin framing requires the render response to **not** send `X-Frame-Options: DENY`
(Django's default). The render view is therefore `@xframe_options_exempt`; this is safe and
intended — the widget exposes **only already-public content and a single public link**, with no
authenticated action, so there is no clickjacking value in framing it (§10).

### 5.2 Interface contracts (no "TBD")

**Routes** (`apps/widget/urls.py`, `app_name = "widget"`, mounted at `widget/`):

| Route | Method | Auth | Behavior |
|-------|--------|------|----------|
| `widget:render` `/widget/<uuid:app_id>/` | GET | AllowAny | Per-IP rate-limited (AC8). Renders the framable widget for an ACCEPTED app; counts one **impression** (fail-soft). `Cache-Control: public, max-age=<config>`. `@xframe_options_exempt`. Unknown/non-accepted ⇒ neutral `unavailable.html` (404). |
| `widget:view` `/widget/<uuid:app_id>/view` | GET | AllowAny | Validates ACCEPTED; counts one **click_through** (fail-soft); `302` to `reverse("pages:app-page", [app_id])`. Unknown/non-accepted ⇒ `unavailable.html` (404). Never an open redirect (target is server-derived). |

**Write surface** (`attribution.py` — the single writer of `widget_reach_count`):

```python
def record_widget_impression(app_id: UUID) -> None      # ++ today's impression row
def record_widget_click_through(app_id: UUID) -> None    # ++ today's click_through row
```

Atomic per-day increment (see §6). These trust an `app_id` the **view already validated as
accepted** (the view is the single caller and the validation boundary — re-reading the catalog
on every count would double the hot-path cost for no gain; documented as **EUW-11**). Raise on
a DB failure; the **caller wraps fail-soft** so counting can never break the host's page.

**Read surface** (`selectors.py` — the single reader; returns frozen DTOs, never ORM rows):

```python
@dataclass(frozen=True)
class WidgetReach:
    impressions: int
    click_throughs: int           # click-through *rate* (M2) is derived at display, not stored

def widget_reach(app_id: UUID, *, start: datetime, end: datetime) -> WidgetReach
def widget_reach_for_apps(app_ids: list[UUID], *, start, end) -> dict[UUID, WidgetReach]
```

Both are one grouped query (`SUM(count) GROUP BY [app_id,] kind`) over the window's day range,
zero-filled, `[]`/empty for empty input — **no N+1** for the dashboard's K-app summary (the
established `funnel_for_apps`/`impression_breakdown_for_apps` discipline).

**Render contract** (`content.py`):

```python
@dataclass(frozen=True)
class WidgetNotice:  kind: str; title: str; summary: str; published_at: datetime
@dataclass(frozen=True)
class WidgetView:
    app_name: str
    app_page_path: str            # reverse("pages:app-page", [app_id])
    notices: list[WidgetNotice]   # capped at config.widget_notice_limit(), newest-first
    notices_degraded: bool        # True ⇒ the notice read errored → link-only, not a fake "no updates"

def build_widget_view(app_id: UUID) -> WidgetView | None   # None ⇒ unknown/non-accepted
```

`notices_degraded` keeps F2's *truthful* empty state (`notices == []`, no error) distinct from a
*read failure* (link still works, but we do not assert "no updates" we could not verify).

## 6. Data design (protocol step 6)

One new table, owned solely by `apps/widget`. **No `user` FK and no IP/UA/referrer/geo column**
— anonymity and the PII-free posture are *structural* (an actor or PII is unrepresentable here),
matching the D-7 AC10 discipline without entering the D-7 corpus.

```python
# apps/widget/kinds.py
class WidgetEventKind(models.TextChoices):
    IMPRESSION    = "impression",    "widget render"
    CLICK_THROUGH = "click_through", "view-on-platform click"

# apps/widget/models.py
class WidgetReachCount(models.Model):
    id         = UUIDField(primary_key=True, default=uuid4, editable=False)
    app_id     = UUIDField()                                   # soft D-6 ref (no DB FK)
    kind       = CharField(max_length=16, choices=WidgetEventKind.choices)
    count_date = DateField()                                   # the UTC day
    count      = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    class Meta:
        db_table = "widget_reach_count"
        constraints = [UniqueConstraint(fields=["app_id","kind","count_date"],
                                        name="widget_reach_count_unique")]
        indexes = [Index(fields=["app_id","kind","count_date"],
                         name="widget_reach_app_kind_date_idx")]
```

**One source of truth per fact:** the count of widget impressions/click-throughs for an
(app, day) lives **only** here. The notices it shows are *not* stored — they are read live from
`updates` (EUW-1, F3), so a publish/withdraw is reflected with no widget-side duplication.

**Lifecycle & concurrency.** Append-by-increment, never edited by hand, never deleted in normal
operation. The single writer increments today's row atomically:

```python
with transaction.atomic():
    updated = WidgetReachCount.objects.filter(
        app_id=app_id, kind=kind, count_date=today
    ).update(count=F("count") + 1)          # DB-atomic; correct under concurrency
    if not updated:
        try:
            WidgetReachCount.objects.create(
                app_id=app_id, kind=kind, count_date=today, count=1)
        except IntegrityError:               # lost the create race → the row now exists
            WidgetReachCount.objects.filter(
                app_id=app_id, kind=kind, count_date=today
            ).update(count=F("count") + 1)
```

`F("count") + 1` is evaluated in the database, so concurrent increments do not lose updates;
the unique constraint turns a create race into a caught retry. No cache/queue infra (the
`developer-updates` "durable, table-derived" precedent).

**Why a daily rollup, not append-per-event** (the §5.2 "assume 100× growth" call): the widget is
*designed* to live in third-party apps that may dwarf platform traffic; an append row per
anonymous load would grow unboundedly on a scrape-prone surface. The rollup bounds growth to
`apps × 2 × days`, and it stores **exactly** the daily shape the dashboard reads (M4 = loads per
app over time). Per-event granularity buys nothing any AC needs (M2 rate = clicks/loads = counts;
M3 conversion is deferred — §11). **Bounded trade-off:** a popular app's single
`(app, impression, today)` row is a write-hot row; the per-IP rate limit (AC8) + the
`Cache-Control` TTL throttle the increment rate, and the named growth path is per-day **counter
sharding** / async write-behind (not built — no speculative abstraction). Recorded as **EUW-9**.

**Retention** mirrors the corpus posture (no auto-purge — A3); pruning old day-rows is a future
op, not MVP.

## 7. UX flow (protocol step 4)

- **Populated widget:** a compact card — app name heading, up to `widget_notice_limit()` notices
  (a small "update"/"early access" kind chip, title, summary, relative date), newest-first, and a
  footer "View on <platform>" link. Self-contained inline CSS, neutral light styling, responsive
  within the frame.
- **Empty (F2/AC2):** "No updates yet." + the same footer link. Truthful, not an error.
- **Notices degraded (read error):** the heading + footer link render; the notice list shows a
  quiet "Updates are temporarily unavailable." — never a fabricated "no updates."
- **Unavailable (unknown / non-accepted / catalog read error):** `unavailable.html`, a neutral
  framable "This app isn't available." Never leaks whether an id exists vs is unaccepted (D-6).
- **Click-through:** the footer link navigates the **top** window to `/widget/<id>/view` → 302 to
  the app page, where the platform's existing follow / sign-up paths take over (EUW-2).
- **Developer view (AC9):** on `dashboard:app` (Screen B), a **"Widget reach"** slot for the
  selected window — widget impressions, click-throughs, and the derived click-through rate —
  clearly labeled as off-platform widget reach, distinct from the on-platform per-`Surface`
  breakdown. The `dashboard:my-apps` summary (Screen A) gains a widget-impressions column via the
  bulk read.

## 8. Failure modes (protocol step 7) — fail-soft to the host, loud to operators

The governing rule (the `apps/pages/emission` precedent): the widget sits inside someone else's
page, so a failure must **never** 500 into the host — it degrades visibly-but-gracefully and is
**counted + logged** for operators.

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| Notice read (`updates`) | slow/down/raises | exception in `content` | Render with `notices_degraded=True` (link-only); count `WIDGET_NOTICES_DEGRADED`; **render still 200**. |
| Catalog validate (`catalog`) | raises | exception in view wrapper | Render `unavailable.html` (200, degraded); count `WIDGET_RENDER_DEGRADED`. Returns `None` (unknown/unaccepted) ⇒ `unavailable.html` 404 + `WIDGET_NOT_AVAILABLE`. |
| Attribution write | raises | exception in the view's soft wrapper | Swallow after counting `WIDGET_COUNT_DEGRADED` + log; the render/redirect **always proceeds** (AC9 is best-effort to the user, loud to ops). |
| Rate limiter (`core.cache`) | unavailable | exception | **Fail open** (serve the widget) + count `WIDGET_LIMITER_DEGRADED`; availability of a public read beats strict limiting during a cache outage (documented). |
| Over the rate limit | abuse/scrape | `exceeds_ip_rate` true | `429`, no render, no count; `WIDGET_RATE_LIMITED` (AC8). |
| Dashboard widget slot (`widget.selectors`) | raises | exception in `reception._build_widget_reach` | Degrade **only that slot** (`available=False`) + `DASHBOARD_WIDGET_DEGRADED`; the rest of the dashboard stays 200 (the reviews-slot precedent). |

The **core reception read** in the dashboard (signals) keeps its existing loud-500 posture
(§7 of dashboard DESIGN) — only the *added widget slot* is soft.

## 9. Non-functional handling (protocol steps 10–11)

**Security / threat model.**
- **Firewall (AC6/M5):** structural — `apps/widget` imports nothing from `signals`; widget
  interactions create no corpus row, so they cannot confer D-8 eligibility (AST test, §12).
- **No open redirect:** `/view` targets `reverse("pages:app-page", [app_id])`, never a param.
- **XSS:** server-rendered, auto-escaped Django templates; notice `title`/`summary` escaped.
- **Cross-origin framing:** `@xframe_options_exempt` on the render only; safe because the widget
  is read-only public content with no authenticated action (no clickjacking value). Optionally a
  `Content-Security-Policy: frame-ancestors *` may be added later; X-Frame exemption is the
  boring Django-native minimum.
- **Data exposure (AC5/AC8):** serves only the app's own public notices (public-by-nature
  changelog, EUW-5) + name + link. No subscriber counts, no dashboard data, no private fields.
- **Abuse (AC8):** per-IP fixed-window GET limit on the render; `Cache-Control` TTL lets
  browsers/CDN absorb repeat loads.
- **PII (AC10 posture):** the attribution store has no actor/IP/UA/referrer column — over-
  collection is unrepresentable.

**Performance (M6).** Render = two indexed reads (catalog by id, `published_notices_for_apps`
one query) + one increment; the redirect = one indexed read + one increment. The dashboard read
is one grouped query (windowed, indexed). `Cache-Control` removes most repeat origin hits.

**Observability** (new `core/observability.py` constants): `WIDGET_RENDERED` (M4),
`WIDGET_EMPTY` (rendered, no notices), `WIDGET_CLICK_THROUGH` (M2), `WIDGET_NOT_AVAILABLE`,
`WIDGET_RATE_LIMITED` (AC8), `WIDGET_NOTICES_DEGRADED`, `WIDGET_RENDER_DEGRADED`,
`WIDGET_COUNT_DEGRADED`, `WIDGET_LIMITER_DEGRADED`, and `DASHBOARD_WIDGET_DEGRADED`. **The one
actionable alert** is `WIDGET_COUNT_DEGRADED` sustained (attribution silently lossy → AC9/M2–M4
under-count); the `*_DEGRADED` reads are fail-soft trends; `WIDGET_RATE_LIMITED` is an
expected-under-abuse trend, not an alert. `M5` needs no counter — it is 0 by construction.

**Config tunables** (new in `core/config.py`, validated loud at startup like the rest):

| Tunable | Default | Purpose |
|---------|---------|---------|
| `widget_notice_limit()` | 5 | Max notices rendered in the widget (F1). |
| `widget_render_rate_limit_per_ip_per_minute()` | 60 | The AC8 abuse bound on the public render. |
| `widget_cache_max_age_seconds()` | 60 | `Cache-Control` TTL — bounds origin load; within-TTL reloads are not re-counted (accepted; reach is approximate). |

## 10. Alternatives considered (protocol step 9)

- **Attribution via a new `signals` `Surface.WIDGET`** (the brief's illustrative option).
  *Rejected:* would force anonymous, high-volume, scrape-prone third-party traffic into the
  authenticated, PII-free integrity corpus, break `signals.capture`'s authenticated-actor
  invariant, overload `user IS NULL`, and make the firewall a runtime rather than structural
  property. The dedicated store (§3) is the simpler, safer, structurally-firewalled choice
  (**EUW-8**). Sacrifice: widget reach is shown as a *separate* off-platform figure, not merged
  into the on-platform per-`Surface` breakdown — which is in fact more honest (anonymous
  off-platform reach is a different fact than authenticated on-platform impressions).
- **`<script>`-tag DOM injector** instead of an iframe. *Rejected:* needs client JS (a build/asset
  to ship + maintain), opens an XSS/style-collision surface in the host page, and is fragile
  cross-origin — it loses on AC7 (zero-build), security, and simplicity (**EUW-7**).
- **JSON endpoint the developer renders themselves.** *Rejected:* violates AC7 (the niche won't
  build a renderer) and would move firewall-relevant rendering into untrusted host code.
- **Append-per-event attribution table.** *Rejected:* unbounded growth on an anonymous open
  surface for per-event granularity no AC needs (§6, **EUW-9**).
- **Re-validating the app in `attribution`** on every count. *Rejected:* doubles the hot-path
  catalog read; the view is the single caller and validation boundary (**EUW-11**).

## 11. Deferred: per-account conversion attribution (M3)

AC9's binding requirement is **reach**: impressions + click-throughs attributed to the widget,
visible on the dashboard — fully delivered. **M3** ("which new account/follow came from which
widget click-through") additionally requires carrying a widget-source token through an
*anonymous* click → app page → sign-up across sessions/domains, which entangles cookie consent,
cross-domain identity, and the no-PII posture — a materially harder problem the brief itself
flags as aspirational ("attribution mechanism = Stage 2") and adjacent to the out-of-scope
"install attribution." **Deferred** to a follow-up, logged as **EUW-10** / re-opened as
OQ-EUW-5, so it is traceable, not silently dropped. The click-through count is the honest MVP
"reached the platform from the widget" measure; account conversion is the downstream payoff
measured once a token-carry design exists.

## 12. Verification (protocol step 12) — every AC → a concrete check

| AC | Verified by |
|----|-------------|
| AC1 | `build_widget_view` returns notices newest-first, capped at `widget_notice_limit()`; template renders kind/title/summary/date. |
| AC2 | Empty notices ⇒ empty-state template + footer link; `notices_degraded=False`. |
| AC3 | Render reads `updates.selectors` live (no widget-side store of notices); a post/withdraw changes the next render. Integration test over ORM-seeded notices. |
| AC4 | `/view` 302s to `reverse("pages:app-page", [app_id])`; never a request param. |
| AC5 | Render view is AllowAny; anonymous request renders fully; exposes only public fields. |
| **AC6** | **`tests/test_imports.py` AST-asserts `apps/widget` imports nothing from `apps.signals`**; an integration test asserts a render+click-through writes **0** `signals` rows and leaves `has_impression(..., surfaces=CURATED_SURFACES)` False (M5 = 0 structural). |
| AC7 | The documented one-line `<iframe>` embed; no platform build step (doc + render-route test). |
| AC8 | Over `widget_render_rate_limit_per_ip_per_minute()` ⇒ 429, no render; only public content served. |
| AC9 | A render increments the impression count, a `/view` the click-through count; `widget_reach` returns them; the dashboard widget slot shows them. End-to-end test. |
| M1/M2/M4 | `WIDGET_RENDERED` / `WIDGET_CLICK_THROUGH` counters + `widget_reach` over windows. |
| M5 | The AC6 structural test (0 corpus rows). |
| M6 | Latency log + the `*_DEGRADED` counters; fail-soft tests (notice read down → still 200). |

Each module is testable in isolation: `attribution` (increment concurrency), `selectors`
(windowed aggregation, zero-fill, no N+1), `content` (assembly + degraded flag), `views`
(rate-limit / xframe / fail-soft / redirect), and the dashboard slot (soft-degrade).

## 13. Rollout & rollback (protocol step 14)

**Activation** = three additive parts (the `developer-updates` shape, since this app owns a
table *and* touches a closed app):
1. `"apps.widget"` in `INSTALLED_APPS` + its one migration (the `widget_reach_count` table).
2. `path("widget/", include("apps.widget.urls"))` in `config/urls.py` (own prefix; `/widget/`
   is free — no collision with `pages` `/apps/`).
3. The additive dashboard widget-reach slot (`reception.py` + `app_reception.html` +
   `my_apps.html`) and the `core` additions (the GET rate limiter, config tunables, metric
   constants).

**Rollback** is the honest multi-part revert — cleanest as **`git revert` of the build commit**
(the **DU-REL-1** precedent: the dashboard now imports `widget.selectors`, so simply pulling the
`INSTALLED_APPS` line would break the dashboard import; the revert must drop the dashboard edit
*and* the include *and* the `INSTALLED_APPS` line together). The table down-migration is
independent and optional (the data is inert once the routes/imports are gone). No feature flag;
the include + `INSTALLED_APPS` line are the switch. No backward-compat concern (all changes
additive; no existing contract altered).

## 14. Self-critique (protocol step 13)

- *"Is leaving widget reach out of the per-`Surface` breakdown a regression in the dashboard's
  'one place for reach'?"* No — they are different facts (authenticated on-platform vs anonymous
  off-platform). One source of truth per fact is preserved; the dashboard *presents* both, clearly
  labeled. Merging them would mislead.
- *"GET with a side effect (counting on render)."* Accepted and house-consistent — `apps/pages`
  already emits an impression on a GET app-page view. Counting is idempotent-in-spirit and
  fail-soft; the `/view` GET is a navigation link (target=_top), not a state-mutating form, so no
  CSRF concern.
- *"Hot-row write contention at scale."* The real bounded trade-off (§6/EUW-9); throttled by the
  rate limit + cache TTL, with a named growth path. Not pre-built.
- *"Cache TTL undercounts reach."* Accepted — reach is an approximate signal; protecting the origin
  and the host page's performance (M6) outweighs exact counts. The TTL is config.
- **Simplification pass:** no widget-side notice cache (read live — F3 truth + one query); no
  per-event rows; no client JS; no new global ADR; the rate limiter generalizes the *existing*
  `core.ratelimit` internals by one parameter rather than adding a new framework.

## 15. Decisions logged

Feature-local **EUW-7 … EUW-11** in [DECISIONS.md](DECISIONS.md) (PROPOSED — ratified on
DN-EUW-DESIGN). No new global ADR (reuses D-4/D-6/D-7/D-8/D-9/D-10). Open follow-up: **OQ-EUW-5**
(M3 per-account conversion attribution, deferred — §11).
