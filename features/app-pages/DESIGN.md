# DESIGN — app-pages

*Stage 2 artifact (Software Architect). Status: **draft — awaiting approval** (CONTROL.md
DN-10). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (DN-9 → approved), the
global contracts [D-4](../../DECISIONS.md) (stack), [D-5](../../DECISIONS.md) (`resolve_tag`),
[D-6](../../DECISIONS.md) (`get_catalogued_app`), [D-7](../../DECISIONS.md) (`signals.capture.*`),
and the existing code in `apps/catalog`, `apps/signals`, `apps/core`.*

> **This design introduces NO new global decision.** It is a pure downstream **consumer**:
> it reads the catalog through the D-6 selectors and emits behavioral signal through the
> D-7 capture path. The one place it touches a global vocabulary — adding `Surface.APP_PAGE`
> to `apps/signals/kinds.py` — is the **additive extension D-7 already pre-authorizes**
> (kinds.py docstring names `app_page` explicitly), not a contract change. See §11.

---

## 0. Reasoning trace (14-step protocol — condensed)

1. **SCOPE.** Give every accepted app **one openly-accessible, structurally-uniform public
   page** that renders its media/description/categories/try-it, doubles as its web home,
   and captures try-it + share as behavioral signal. OUT: rating capture/gate (reviews =
   empty slot), search/browse, impression generation/curation, follows, dev analytics,
   content editing, native links, any scoring. Lifespan: **platform** (the public face every
   later user/dev surface points at) → full rigor.
2. **REQUIREMENTS.** Functional = AC1–AC9. Non-functional: open/anonymous read (no auth
   wall); server-rendered (D-4/C1); render cost ~one selector call (target p95 < 200 ms
   server-render, **observable not an SLA** — D-2/A5); accessibility-leaning (alt text,
   semantic markup, keyboard-reachable — A4). Assumptions verified in §1; the two unverified
   forks (OQ-2 attribution, anonymous capture) are resolved in §5/§6 and raised in DN-10.
3. **CONTEXT.** Reuse-first: `catalog.selectors.get_catalogued_app` (the accepted-only D-6
   read, already returns resolved tags + ordered media), `signals.capture.*` (the D-7 write
   path), `core.observability.increment`, the server-rendered-template pattern already used
   by `apps/catalog` (views → selectors/services, thin views, per-app `templates/`). **No
   new model, no migration owned by this feature.**
4. **MODULES.** One new Django app `apps/pages/` with a single responsibility — *present an
   accepted app and emit its engagement*. Three thin views + one small fail-soft emission
   helper + templates. It owns **no data**; it is a leaf consumer (trivially deletable, §12).
5. **INTERFACES.** Three HTTP routes (§5a) + one internal emission contract (§5b) that wraps
   `signals.capture.*` with the surface's non-blocking policy. No new cross-feature surface
   is published (app-pages is a terminal consumer, not a substrate).
6. **DATA & STATE.** Stateless. The only persisted facts are the D-7 rows written *through*
   `signals.capture.*` (owned by `apps/signals`, not here). One source of truth for app
   content = the catalog (read-only via D-6). No app-pages table exists to drift.
7. **FAILURE.** The catalog read failing is a **loud 500** (core dependency). The *capture*
   path failing is **non-blocking** (AC7): the page renders and the actions work; the loss
   is counted via D-7's `capture_error` and the surface's own fail-soft counter — never
   swallowed silently, never blocking the visitor (§5b/§7).
8. **CHANGE.** Likely to change: page layout/copy (lives in one template), the set of emitted
   event kinds (each is one `capture.*` call behind the emission helper). Irreversible-ish:
   the public **URL shape** (`/apps/<App.id>/`) and the `Surface.APP_PAGE` enum value once
   impressions carry it — both justified in §5a/§11. No speculative abstraction added.
9. **TRADE-OFFS.** Two genuinely different attribution models compared in §6 (page-view *is*
   an `app_page` impression that conversions link to — chosen — vs. impression-less
   click-through requiring a D-7 contract change — rejected). Two render models in §13.
10. **SECURITY.** Open read is deliberate (vision §4.1 — nothing secret on the page). The
    try-it redirect target is the app's **server-side stored URL**, never a query param → no
    open-redirect. The impression id passed to the try/share endpoints is **ownership-validated
    by capture** → a forged id yields no event, never another user's attribution (§10).
11. **OPERATIONS.** New counters `app_page_rendered` / `app_page_not_available` + the reused
    D-7 funnel counters; render latency logged; rollback = remove the URL include (§9/§12).
12. **TESTS.** Each view testable in isolation against fake selector/capture seams; AC1–AC9
    each map to a concrete test (§14, full plan deferred to Stage 4 `TEST_PLAN.md`).
13. **SELF-CRITIQUE.** §13 — attacks the page-view-impression volume concern, the anonymous
    boundary, the GET-with-side-effect choice, and the build-before-emitter risk (R2).
14. **DELIVER.** Smallest first version = the three routes + uniform template + fail-soft
    emission; increments (page_reengagement, anonymous capture, richer press kit) named and
    deferred. Decisions + rejected alternatives in §13 and feature `DECISIONS.md` (AP-3/4/5).

---

## 1. Current-state summary

What already exists and is reused **as-is** (nothing below is modified except the one
additive `Surface` value in §11):

| Component | What it gives app-pages | Reuse |
|-----------|-------------------------|-------|
| `catalog.selectors.get_catalogued_app(app_id) -> CatalogApp \| None` ([D-6](../../DECISIONS.md)) | The accepted-only app shape: `id, name, description, url, tags[resolved], media[ordered]`. Returns `None` for pending/rejected/withdrawn/unknown. | Sole catalog read. |
| `catalog.selectors.CatalogApp/CatalogTag/CatalogMedia` | Frozen read DTOs — **already tag-resolved (D-5) and media-ordered**; carry **no owner / paid / team field**. | Render straight from these. |
| `signals.capture.record_impression / record_click_through / record_share` ([D-7](../../DECISIONS.md)) | The single write path. `record_impression` needs a `surface`; `record_click_through` **requires** an originating impression; `record_share` takes an optional one. All fail loud + counted. | Sole signal write. |
| `signals.kinds.Surface` | Closed surface vocabulary — **only `DIGEST` today**; docstring pre-authorizes `app_page`. | Add `APP_PAGE` (§11). |
| `core.observability.increment(metric, **tags)` + metric constants | The counter seam (never raises). | Add two constants (§9). |
| `apps/catalog` server-rendered pages (`views.py` thin views → `templates/catalog/*.html`) | The house pattern for a server-rendered surface (thin view, per-app template dir, `render`). | Mirror it. |

Key facts that shape the design:
- The `CatalogApp` DTO **structurally has no developer-identity, team, or paid field** — so a
  uniform template that renders only it **cannot** vary by those (AC3 is structural, not a
  convention). This is the cleanest possible realization of the fairness premise.
- `signals.capture` writes are keyed `user × App.id` and **require an authenticated `user`**
  (it stores `user=user` and validates `impression.user_id == user.pk`). This is the crux of
  both the OQ-2 attribution fork (§6) and the anonymous boundary (§6c).
- `record_click_through` **requires** an impression. A page reached by direct/search link has
  no *digest* impression — the resolution is to treat the **page view itself** as the
  originating impression (§6).

## 2. Tech stack & project layout  *(reuses global [D-4](../../DECISIONS.md) — no new stack decision)*

Server-rendered Django templates over the existing stack (D-4/C1). New Django app under the
shared-code root `apps/`:

```
apps/pages/
  __init__.py
  apps.py                      # AppConfig (name="apps.pages")
  urls.py                      # 3 routes (§5a), app_name = "pages"
  views.py                     # 3 thin views: page / try-redirect / share
  emission.py                  # fail-soft-but-counted wrapper over signals.capture.* (§5b)
  templates/pages/
    base.html                  # minimal public chrome (own base → deletable, no coupling)
    app_page.html              # THE uniform template (every accepted app, same slots)
    not_available.html         # the AC8 not-a-live-catalog-entry response body
```

**No `models.py`, no migration owned here.** app-pages persists nothing of its own; the only
DB writes it triggers are D-7 rows created *inside* `apps/signals`. This is deliberate
design-for-deletion (§12) and one-source-of-truth (catalog owns content, signals owns events).

Wired in `config/urls.py`: `path("apps/", include("apps.pages.urls"))` and
`"apps.pages"` added to `INSTALLED_APPS`. (`/apps/…` at the project root is free — the
catalog's developer pages live under `catalog/apps/…`.)

## 3. Proposed architecture (components & responsibilities)

```
        visitor (authenticated OR anonymous)
                     │  GET /apps/<app_id>/
                     ▼
        ┌───────────────────────────────┐     get_catalogued_app(app_id)
        │  views.app_page (AllowAny)     │ ───────────────────────────────► catalog.selectors (D-6)
        │  - None → 404 not_available    │ ◄───────── CatalogApp | None
        │  - else render uniform template│
        │  - emit page-view impression   │ ──┐
        └───────────────────────────────┘   │  (authenticated only, fail-soft)
                     │ renders app_page.html  │
                     ▼                        ▼
        try-it link  GET /apps/<id>/try?imp=… │   emission.record_page_view
        share button POST /apps/<id>/share    │ ───────────────────────────► signals.capture.* (D-7)
                     │                        │   emission.record_try_click   record_impression
                     ▼                        │   emission.record_share       record_click_through
        ┌───────────────────────────────┐    │                               record_share
        │ views.try_redirect / share     │ ───┘
        │ - emit click_through / share   │
        │ - try → 302 to app.url (server)│
        └───────────────────────────────┘
```

- **`views.app_page`** — owns: resolving the page (D-6), the 404 boundary (AC8), rendering the
  uniform template (AC1/AC2/AC3/AC5/AC9), triggering the page-view impression. Hides: capture
  failure (degrades, AC7). Open/anonymous (`AllowAny`, no role gate).
- **`views.try_redirect`** — owns: recording the click-through then 302-ing to the app's
  stored URL (AC6). The redirect target is read **server-side from the catalog**, never from
  the request → no open redirect.
- **`views.share`** — owns: recording a share (AC6), returns 204. POST + CSRF.
- **`emission`** — owns the **surface-side non-blocking policy** (AC7): each function calls one
  `signals.capture.*` recorder inside a try/except that counts + logs the loss and **never
  re-raises into the request**. It is the one place the "capture is best-effort *to the
  visitor*, loud *to operators*" rule lives (the complement of D-7 §5d, which makes capture
  loud *inside* signals). Single responsibility, trivially testable with a fake capture.

Coupling: views depend only on the two selector/capture contracts + `emission`; `emission`
depends only on `signals.capture` + `observability`. Each is replaceable/testable in
isolation. Dependencies point toward the stable cross-feature contracts (D-6/D-7).

## 4. Data design

**app-pages owns no schema.** It is stateless. For completeness, the facts it *causes* to be
written (all owned and validated by `apps/signals` under D-7, not by this feature):

| Fact | Table (owned by signals) | When app-pages causes it |
|------|--------------------------|--------------------------|
| Page-view shown instance | `signals_impression` (`surface = app_page`) + frozen `signals_impression_tag` | An **authenticated** visitor loads `/apps/<id>/` and capture succeeds. |
| Try-it conversion | `signals_engagement_event` (`kind = click_through`, `impression =` the page view) | Authenticated visitor follows the try-it link with a valid `imp`. |
| Share | `signals_engagement_event` (`kind = share`, optional `impression`) | Authenticated visitor triggers the share action. |

No retention/lifecycle logic lives here (D-7 owns append-only + the SET_NULL anonymize-on-
deletion posture). The catalog content rendered is read-only and never copied/cached by this
feature (one source of truth — a later cached projection is the documented D-6 growth path,
not built here).

## 5. Interface contracts

### 5a. HTTP routes  (mounted under `apps/`)

| Route | Method | Auth | Behavior | Errors |
|-------|--------|------|----------|--------|
| `apps/<uuid:app_id>/` (name `pages:app-page`) | GET | **AllowAny** | Render the uniform page for the accepted app; emit a page-view impression (authenticated, fail-soft). | `app_id` not accepted/unknown → **404** `not_available.html` (AC8). Non-UUID → 404 at routing. Catalog read failure → **500** (loud). |
| `apps/<uuid:app_id>/try` (name `pages:try`) | GET | AllowAny | Emit `click_through` (authenticated + valid `imp` only, fail-soft) then **302** to the app's **stored** `url`. | App not accepted → 404. App URL missing → 404 (cannot occur: D-6 requires it). |
| `apps/<uuid:app_id>/share` (name `pages:share`) | POST | AllowAny (capture authed-only) | Emit `share` (authenticated, fail-soft); **204**. CSRF-protected. | App not accepted → 404. Anonymous → 204 no-op (nothing captured). |

- **Query param `imp`** (try/share): the page-view impression id the rendered page embeds in
  its try-it/share affordances, so a conversion links to the exact shown instance (§6).
  Optional; absent/invalid → the event is recorded without a link where the kind allows
  (share) or skipped where it requires one (click_through) — never an error to the visitor.
- **URL shape (OQ-4 resolved — AP-5):** keyed on the **`App.id` UUID**, so the link is
  **stable across metadata edits** (AC4 — name/description/url changes never change it). A
  human-readable slug is rejected (it mutates with the name; the brief requires edit-stable).
  Pages are **indexable** (no `noindex`; canonical `<link>` = this URL) to serve open
  discovery (A1) — robots/rate-limit posture is the ops note in §9/§10, not a route concern.

### 5b. Internal emission contract (`apps.pages.emission`) — surface-side non-blocking policy

```python
def record_page_view(request, app_id: UUID) -> UUID | None:
    """Emit an app_page-surface impression for an AUTHENTICATED visitor; return its id.
    Anonymous → returns None (nothing captured). Any capture failure → counted + logged,
    returns None (page still renders, AC7). Never raises into the request."""

def record_try_click(request, app_id: UUID, impression_id: UUID | None) -> None:
    """Emit click_through for an authenticated visitor when impression_id resolves to that
    user's page-view impression. Missing/anonymous/mismatch → no event, no raise (AC7)."""

def record_share(request, app_id: UUID, impression_id: UUID | None) -> None:
    """Emit share for an authenticated visitor (optional impression link). Never raises (AC7)."""
```

Invariants: (1) **authenticated-only** — `request.user.is_authenticated` is the gate; D-7
capture requires a real `user` (§6c). (2) **fail-soft-but-counted** — wraps every
`signals.capture.*` call in `try/except Exception`, increments a surface counter and logs with
request context, returns normally. The complement of D-7 §5d: capture is loud to operators (it
counts + raises *inside* signals), the surface is silent to the visitor (it catches + counts +
degrades). (3) **no business logic / no ORM** — it only calls capture; app validity, tag
snapshot, impression linkage all stay enforced inside `signals.capture` (one source of truth).

### 5c. UI states (the uniform template — AC1/AC2/AC3/AC9)

`app_page.html` renders the **same slots in the same order for every app**, driven only by
`CatalogApp` (no identity/paid input — AC3):

1. **Header** — `name` (always present), category tags (`resolve_tag`'d labels via D-6);
   *empty tag state*: a defined "Uncategorized"/absent treatment, slot still present (AC2).
2. **Media gallery** — ordered `media` (1–8); each `<img>` carries `alt_text` (A4). *Empty/one-
   image state*: a defined placeholder/single-image layout — the slot never collapses the
   layout differently from another app's (AC2).
3. **Description** — `description` (always present per D-6).
4. **Try-it action** — a clearly-labelled primary action linking to `pages:try` (→ the app's
   URL). Always present (D-6 guarantees a URL).
5. **Share action** — a share affordance (POSTs to `pages:share`; progressive-enhancement —
   see §13); the canonical URL is always copyable so the page is shareable even without JS
   (AC4).
6. **Reviews slot** — a **defined empty state** ("Reviews coming soon" / placeholder). Renders
   no rating data; app-pages captures/stores/displays no reviews (AC9 — owned by
   `ratings-reviews`). The slot exists so adding reviews later is non-uniform-churn-free (AP-1).

States: **loading** = server-rendered (no spinner); **empty/partial** = per-slot defined
states above (AC2); **error** = 404 `not_available.html` for a non-accepted/unknown app (AC8),
500 for a genuine catalog failure.

## 6. The attribution model — resolving OQ-2 (AP-3)

**The fork (OQ-2):** `record_click_through` **requires** an originating impression ([D-7]),
but a page reached by direct link / search has no *digest* impression. How is a try-it click
attributed?

**Resolution — the page view itself is the originating impression.** When an authenticated
visitor loads `/apps/<id>/`, app-pages records an `Impression` with **`surface = app_page`**
(the app *was* shown — on the app-page surface). The try-it click is then a `click_through`
**linked to that page-view impression**; a share links to it too. This is:

- **Fully D-7-faithful** — `click_through` gets the impression it requires; no contract change.
- **Additive-only** — it needs exactly one new `Surface` value (`APP_PAGE`), which D-7 and
  `kinds.py` already pre-authorize ("Extensible by adding a value (`app_page`, `feed`)").
- **Exactly what the brief's own metric needs** — the page-view impression is the
  **denominator** for "click-through *rate* per page view" (FEATURE_BRIEF §5, the H1 link);
  recording the conversion-less impression at view time is the only way that rate is
  measurable. Recording the impression only at click time would lose every viewed-not-clicked
  show (the denominator).

**Reconciliation with the brief's "impression generation is out of scope."** The brief
excludes app-pages from *generating curated-feed impressions* — i.e. running the impression
**allocator / the digest's matched-show** (`weekly-digest` / `editorial-curation-tools`).
app-pages does **none** of that: it neither selects an audience nor decides what to show whom.
It records that a page *was viewed* on the `app_page` surface — a different, surface-tagged
shown instance the D-7 schema is explicitly built to hold. The two are kept distinct by the
`surface` field, so a consumer segments digest CTR from app-page CTR rather than conflating
them. **Because this reinterprets an out-of-scope bullet, it is raised for confirmation in
DN-10** (it is not silently adopted).

**Rejected sub-options** (full record in `DECISIONS.md` AP-3): (b) record `click_through`
with no impression — requires making D-7's required-impression optional, a global-contract
change to an approved, additive-only schema, for a problem an additive enum value solves;
(c) a new event kind for "page click" — duplicates `click_through`'s meaning and fragments the
funnel; (d) capture nothing until `weekly-digest` exists — guts AC6 and the H1 metric at MVP
(every visit is impression-less today).

### 6c. The anonymous boundary — resolving AC5 ∩ AC6 (AP-4)

D-7 capture is keyed `user × App.id` and **requires an authenticated user**. AC5 requires the
page to render for a visitor with **no account**. Resolution:

- **Rendering is fully anonymous** (AC5) — the page is `AllowAny`; no capture is needed to
  render, so an anonymous visitor gets the complete page with no auth wall.
- **Signal capture is authenticated-only** (AC6 for the representable case) — an anonymous
  page view records **no** impression; an anonymous try-it/share still works (the redirect
  fires, the page is shareable) but writes **no** event, because there is no `user` the
  user-keyed corpus can attribute to. `emission` gates on `request.user.is_authenticated`.

This satisfies AC5 (renders), AC6 (captures for the visitors the corpus can represent), and
AC7 (anonymous actions still work). It also **bounds R5** — crawlers are anonymous, so they
generate **no** impressions (no signal inflation, no per-view write amplification from bots).
Anonymous/sessionless capture would require extending D-7 with an anonymous actor id — a named
**growth path, deferred** (no speculative build). **Raised in DN-10** as it interprets AC6.

## 7. Failure modes

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| `views.app_page` | catalog read raises (DB down) | exception | **500, loud** — core dependency, not hidden (this is *render*, not capture). |
| `views.app_page` | `get_catalogued_app` → `None` | return value | **404** `not_available.html` (AC8) + `app_page_not_available` counter — a non-accepted app is *never* rendered as live. |
| `emission.record_page_view` | `signals.capture` raises/down | try/except in `emission` | **Page still renders** (AC7); loss counted (capture's own `capture_error` + surface log); try-it/share simply carry no `imp`. |
| `views.try_redirect` | capture fails | try/except | **Still 302** to the app URL — the visitor reaches the app regardless (AC7). |
| `views.try_redirect` | `imp` forged / another user's | capture's `ImpressionMismatchError` | Caught in `emission` → no event, **still redirects** — never another user's attribution (§10). |
| `views.share` | capture fails / anonymous | try/except / auth gate | **Still 204**; no event. |
| Media file missing on disk | `<img>` 404 in browser | n/a | `alt_text` shows; slot still occupies layout (AC2) — no broken page. |

Principle: the **catalog read** (what makes the page a page) fails **loud**; the **capture**
(a side benefit to the corpus) fails **soft but counted** — exactly the AC7 split.

## 8. Non-functional handling

- **Performance.** A page render = one `get_catalogued_app` call (already prefetches media +
  resolves tags, no N+1) + one template render + one best-effort impression write. Target
  **p95 server-render < 200 ms** for ≤8 media — **observable, not an SLA** (D-2/A5); the
  impression write is off the render's critical path for failure (fail-soft) though
  synchronous on success (a durable async outbox is the documented growth path, inherited from
  D-7). Media are referenced by URL (served by the web server / object store), never inlined.
- **Accessibility (A4).** Semantic landmarks, `alt_text` on every image (carried by
  `CatalogMedia`), keyboard-reachable try-it/share, visible focus. WCAG-AA-leaning; exact
  audit is a build-time checklist item, not a new contract.
- **Observability (§9).** Two counters + reused D-7 funnel counters + a logged render duration.
- **Rollback (§12).** Remove the one URL include; the app owns no schema to migrate down.

## 9. Observability

New constants in `apps/core/observability.py` (1:1 with the brief's metrics):

```python
APP_PAGE_RENDERED       = "app_page_rendered"        # tags: app_id — page coverage / view volume
APP_PAGE_NOT_AVAILABLE  = "app_page_not_available"   # a non-accepted/unknown id was requested (→404)
```

Funnel counters are **reused from D-7** (not duplicated): `impression_captured` (with
`surface=app_page` distinguishable in logs), `click_through_captured`, `share_captured`, and
`capture_error` (the loud-loss alert). The brief's success metrics map:

| Brief metric | Source |
|--------------|--------|
| Page coverage = 100% | every accepted app resolves to a page (structural — one route over the D-6 selector); `app_page_rendered{app_id}` observed. |
| Uniformity = 0 variants | structural (one template, `CatalogApp` has no identity/paid field) — no metric can be nonzero. |
| Open-access = 100% | structural (`AllowAny`, no auth branch in render). |
| Click-through count + **rate per page view** | `click_through_captured` / `impression_captured{surface=app_page}` (§6). |
| Share count | `share_captured`. |
| Render latency | logged per render (a timing log line, not a counter). |
| Non-accepted leakage = 0 | structural (render only via D-6 accepted-only selector); `app_page_not_available` counts *attempts*, which 404 — renders of non-accepted = 0. |

Alert: `capture_error` nonzero (inherited D-7 alert). `app_page_not_available` is informational
(expected — people share dead links), not an alert.

## 10. Security & privacy posture

- **Open read is intentional** (vision §4.1) — the page exposes only already-public catalog
  content; no account, role, or secret is reachable. `AllowAny`, no enumeration concern beyond
  the deliberate open catalog (R5).
- **No open redirect.** `try_redirect` 302s to `CatalogApp.url` read **server-side**, never to
  a request-supplied target. The only request input on that route is `imp` (an impression id).
- **No attribution forgery.** A tampered `imp` is **ownership-validated inside capture**
  (`impression.user_id == request.user.pk` and `impression.app_id == app_id`); a mismatch
  raises `ImpressionMismatchError`, which `emission` catches → **no event written**. A visitor
  can never attribute a conversion to another user or app.
- **CSRF.** `share` is POST + Django CSRF. `try` is a GET navigation (an anchor) — its only
  effect is an append-only, self-attributed signal, the analytics-redirect norm (§13).
- **PII.** app-pages collects nothing; it writes only `user × App.id × impression` through the
  D-7 whitelist (no IP/UA/referrer — structurally unrepresentable in the schema). The actor is
  always `request.user`, never a caller-supplied id.

## 11. Cross-feature contract impact  *(no new global decision)*

app-pages **publishes no new cross-feature surface** — it is a terminal consumer. Its only
touch on a shared vocabulary:

> **Add `APP_PAGE = "app_page", "app page"` to `apps/signals/kinds.Surface`.** This is the
> **additive extension D-7 pre-authorizes** (D-7 ADR: "a new event kind is a new enum value +
> recorder, never a change to these"; `kinds.py` docstring names `app_page` explicitly). It
> adds one Django migration on `signals` that alters the `surface` field's **choices metadata
> only** — no schema change, no data change, reversible. It introduces **no** new global ADR;
> it is recorded feature-locally as **AP-3** and noted here so the Planner sequences the
> one-line `kinds.py` edit + its no-op migration before any `app_page` impression is written.

Consumed contracts, unchanged: D-4 (stack), D-5 (`resolve_tag`, via D-6), D-6
(`get_catalogued_app`), D-7 (`signals.capture.*`).

## 12. Rollout strategy

- **Additive only.** New app + new routes under `apps/`; nothing existing changes behavior
  (the `Surface` choice addition is metadata). **No feature flag** needed — the surface simply
  did not exist before; "off" = don't include the URLconf.
- **Migration order (for the Planner):** (1) add `Surface.APP_PAGE` + its no-op `signals`
  migration; (2) build `apps/pages` (no migration of its own); (3) add the `config/urls.py`
  include + `INSTALLED_APPS` entry. Capture must understand `app_page` (step 1) before any
  page emits (step 3) — D-7 §12 "adopt before you emit".
- **Backward compatibility:** total — no consumer of D-6/D-7 is affected; the new `Surface`
  value is ignored by every existing reader (they filter by app/kind/time, not surface).
- **Rollback:** remove the `config/urls.py` include (pages vanish, zero data migration). The
  `Surface.APP_PAGE` value stays once any `app_page` impression exists (removing an enum value
  in use would orphan rows) — the one semi-permanent footprint, and a cheap one (an unused
  choice is inert). **Design-for-deletion** otherwise holds: app-pages owns no schema, so
  deleting the app directory + include fully removes the feature.

## 13. Self-critique & alternatives

- **"A page view as an impression inflates the funnel."** Mitigated by the `surface` field:
  app-page shows and digest shows are segmentable, never summed blindly — and the brief
  *wants* app-page impression→click-through measured (§6/§9). Authenticated-only capture (§6c)
  further bounds volume (no bot/anon impressions). Accepted as faithful, not inflation.
- **Render model — server-rendered template (chosen) vs. a JS SPA / API + client.** Rejected
  the SPA: C1/D-4 mandate server-rendered; an SPA adds a second stack, a JS dependency for the
  *core* (a public page must render without JS), and an API surface for no MVP benefit. The
  page is fully functional with **zero JS**; share-capture is the only progressive enhancement.
- **GET with a side effect (try-it records a click).** A GET that writes an append-only,
  self-attributed signal is the analytics-redirect norm and is needed so a plain `<a>` works
  without JS. It is **idempotent-enough** (each click is a genuine, distinct conversion event;
  re-clicks are real re-clicks) and carries no destructive authority. Share — a less
  navigation-shaped action — is POST + CSRF.
- **Share without JS isn't captured.** Accepted: the page is still *shareable* (canonical URL
  is copyable — AC4 met); only the *signal* needs the POST. A no-JS share-capture fallback
  (a GET share-redirect) was rejected as awkward for marginal signal; named as a later option.
- **Built before its emitter (R2).** True — no `weekly-digest` impressions exist yet, so the
  *digest*→click-through funnel can't be exercised end-to-end here. But §6 makes the
  *app-page* impression→click-through funnel fully exercisable **now**, which is what AC6 and
  the H1 metric need. Cross-surface attribution is verified when an impression source ships.
- **Simplification pass.** Cut: no app-pages model, no config tunables, no cache layer, no
  `page_reengagement` emission (available in D-7, not required by any AC — deferred, not
  built), no press-asset apparatus (AP-2/DN-9). Every shipped piece traces to AC1–AC9.

## 14. Traceability — every acceptance criterion maps to a design element

| AC | Design element |
|----|----------------|
| **AC1** view | `views.app_page` + `app_page.html` slots 1–4 over `CatalogApp` (D-6) — §5a/§5c. |
| **AC2** empty/partial | per-slot defined empty states (tags/media/single-image) — §5c. |
| **AC3** uniformity | one template driven only by `CatalogApp` (no identity/paid field) — **structural**, §1/§5c. |
| **AC4** stable press-kit link | `App.id`-keyed URL, edit-stable; self-contained page; canonical copyable URL — §5a (AP-5). |
| **AC5** open access | `AllowAny`, no auth branch in render — §5a/§6c. |
| **AC6** signal capture | `emission` → `signals.capture.record_click_through/record_share`, keyed `App.id`, page-view impression — §5b/§6. |
| **AC7** capture non-blocking | `emission` fail-soft-but-counted; render/redirect proceed on capture failure — §5b/§7. |
| **AC8** only accepted apps | render only via `get_catalogued_app` (accepted-only); `None` → 404 `not_available` — §5a/§7. |
| **AC9** reviews slot boundary | reviews slot = defined empty state, no rating data captured/shown — §5c (AP-1). |

Full per-AC verification (Given/When/Then → test) is produced at Stage 4 in `TEST_PLAN.md`.

---

## Decisions logged (feature-local — see [DECISIONS.md](DECISIONS.md))
- **AP-3** — page-view = `app_page`-surface impression; try-it/share link to it (resolves OQ-2;
  adds `Surface.APP_PAGE` as the D-7 additive extension). *Raised for confirmation: DN-10.*
- **AP-4** — capture is authenticated-only; rendering is fully anonymous (resolves AC5 ∩ AC6).
  *Raised for confirmation: DN-10.*
- **AP-5** — public URL is `App.id`-keyed (edit-stable) and indexable (resolves OQ-4).

## Open questions resolved here
- **OQ-1** (reviews slot) — empty-state slot, confirmed by DN-9; realized in §5c.
- **OQ-2** (impression-less click-through) — resolved by §6 (AP-3).
- **OQ-3** (press-kit scope) — page-as-press-kit, confirmed by DN-9; no new apparatus.
- **OQ-4** (URL shape / indexability) — resolved by §5a (AP-5).
