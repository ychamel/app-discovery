# DESIGN — widget-conversion-attribution

*Stage 2 (Software Architect). How it works end to end. **Status: PENDING APPROVAL**
(DN-WCA-DESIGN). Drafted against the **APPROVED** [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(AC1–AC6, M1–M6; WCA-1/2/3 RESOLVED). Resolves the three Stage-2 OQs —
[OQ-WCA-2](OPEN_QUESTIONS.md) (token-carry mechanism), OQ-WCA-3 (cross-domain identity),
OQ-WCA-4 (consent envelope) — under the **AC4 no-PII** + **AC5 firewall (M5 = 0, no
`signals` import)** envelope.*

---

## 0. The 14-step protocol (condensed)

The reasoning that produced this design; each step ends with its output. Full detail is
folded into the sections below.

1. **SCOPE** — Close the developer-wedge funnel: credit a downstream **conversion** (new
   follow of the clicked-through app; new account) to the **widget click-through** that
   preceded it, **aggregate-only, source-keyed, no PII, firewalled from the score**.
   Stakeholders: the developer (sees the payoff), the platform operator (holds the
   no-PII + firewall posture). Out: per-person tracking, install attribution, charging,
   retroactive attribution. Lifespan: **feature** (a durable measurement surface beside
   the shipped reach slot) — effort matches.
2. **REQUIREMENTS** — Functional: AC1–AC6. Non-functional: O(1) hot-path cost on the
   conversion (one cookie read + at most one rollup increment); no PII at rest; M5 = 0
   structural; fail-soft on the conversion path. **The one unverified assumption from the
   brief (§8) is resolved here:** a no-PII source-only marker *can* be carried without a
   third-party cookie, because the click-through is a **first-party top-level navigation
   to the platform origin** (Step 3 / §4). Aggregate-only is therefore **feasible** — it
   does **not** return to the user as a relaxation (OQ-WCA-4).
3. **CONTEXT** — Reuse, don't rebuild: the shipped `apps/widget` (its rollup-table +
   atomic-increment + selector + dashboard-slot patterns), `subscriptions.services.
   follow_app` (returns `created`), the `accounts` register view, `core.config` /
   `core.observability`, Django's first-party signed-cookie primitives
   (`django.core.signing`). The click-through redirect already runs on the platform
   origin — the marker rides that, no new infra.
4. **MODULES** — One new table (`widget_conversion_count`) + one new source-marker codec
   (`apps/widget/source.py`) + two thin, fail-soft **conversion hooks** at the existing
   conversion view boundaries. All attribution logic lives in `apps/widget`; the firewall
   stays structural (§3.1).
5. **INTERFACES** — §7. The marker is a signed, source-only cookie; the writer/selectors
   mirror the reach ones; the hooks expose a 2-function surface to the conversion views.
6. **DATA & STATE** — §6. One source of truth per fact: reach in `widget_reach_count`
   (unchanged), conversion in the new `widget_conversion_count`. The marker is transient
   client state (no server-side per-person row).
7. **FAILURE** — §9. Attribution is **best-effort to the user, loud to operators**: a
   failure never breaks a follow / a registration / the reach counts (AC6).
8. **CHANGE** — The window + touch model are config (`widget_attribution_window_days`).
   The conversion vocabulary is a closed enum (additive). The marker payload is versioned.
9. **TRADE-OFFS** — §11: first-party cookie vs third-party/fingerprint vs server-side
   per-person row; view-hook vs middleware vs Django-signal; separate table vs reusing
   `widget_reach_count`. Chosen options stated with what they sacrifice.
10. **SECURITY** — §8: the marker is signed (tamper-evident) + windowed; no PII; no open
    redirect added; forging confers no ranking gain (firewalled) — only vanity-count
    distortion, bounded + reported.
11. **OPERATIONS** — §10: new `WIDGET_CONVERSION_*` metrics; M3 coverage and M6 error rate
    are computed from them; rollback = `git revert` of the build commit + optional table
    drop.
12. **TESTS** — §12: every AC → ≥1 verification; the firewall AST test extends to the new
    module; edge cases (no marker / expired / tampered / cross-device / dedup) enumerated.
13. **SELF-CRITIQUE** — §13: cross-device registration gap, register-act-vs-confirmed
    account, cookie-vs-ePrivacy nuance, dedup-without-a-person-key — each surfaced
    honestly, none silently relaxed.
14. **DELIVER** — §14: smallest first version + increments; decisions to revisit on real
    data; the DN-WCA-DESIGN gate.

---

## 1. Current-state summary (what exists to build on)

| Component | What it does today | Relevance |
|-----------|--------------------|-----------|
| [apps/widget/views.py](../../apps/widget/views.py) `widget_view_redirect` | `GET /widget/<id>/view` → counts a click-through (fail-soft) → **302 to `reverse("pages:app-page")`**. A **top-level navigation that lands on the platform origin.** | **The marker is set here** — it is the one first-party touchpoint the anonymous click already passes through. |
| [apps/widget/attribution.py](../../apps/widget/attribution.py) | The single writer of `widget_reach_count`: atomic per-day `F("count")+1` + create-race retry (nested savepoint). Imports nothing from `signals`. | The conversion writer **reuses this exact concurrency pattern** (extracted to a shared helper, §6.2). |
| [apps/widget/selectors.py](../../apps/widget/selectors.py) | Single reader: windowed `SUM…GROUP BY`, zero-filled, no N+1, frozen `WidgetReach` DTO. | The conversion reader is its **sibling** (`WidgetConversion`). |
| [apps/widget/models.py](../../apps/widget/models.py) `WidgetReachCount` | `(app_id, kind, count_date, count)` rollup; **no `user`/IP/score column** (AC6/AC10 structural). | The conversion table is the **same shape, separate table** (§6.1). |
| [apps/subscriptions/services.py](../../apps/subscriptions/services.py) `follow_app` | Creates the follow + its one D-7 `record_subscribe` corpus event in one txn; **returns `created`** (True iff a genuinely new follow). | The **follow conversion** is exactly `created == True`. Attribution reads `created`; it **adds nothing** to `record_subscribe` (AC5). |
| [apps/subscriptions/views.py](../../apps/subscriptions/views.py) `follow` | `POST …/follow` → `follow_app` → PRG to the app page. Has the `request` (marker) + builds the redirect response. | **Hook site #1** (§5.2). |
| [apps/accounts/views.py](../../apps/accounts/views.py) `register` | `POST /auth/register` → creates the account (202) / 400 / 409-taken / 503. | **Hook site #2** (§5.3) — credit only the **202 new-account** path. |
| [apps/dashboard/reception.py](../../apps/dashboard/reception.py) `WidgetReachView` + `_build_widget_reach` | The fail-soft off-platform widget-reach slot (Screen B); reads `widget.selectors`. | **Extended** with the conversion funnel stage (AC3), reach numbers untouched. |
| [apps/core/config.py](../../apps/core/config.py), [observability.py](../../apps/core/observability.py) | Typed tunables (validated at startup) + the `increment` metric seam + `WIDGET_*` constants. | One new tunable + four new `WIDGET_CONVERSION_*` metrics. |
| `ratings.gate.CURATED_SURFACES = {DIGEST}`; `apps/widget` imports-no-`signals` AST test | The firewall, structural by absence. | **Preserved** — all new attribution code lives in `apps/widget` and imports no `signals`; the AST test covers the new module automatically. |

**The decisive current-state fact:** the click-through redirect (`/widget/<id>/view`)
already executes **on the platform's own origin** (the iframe's "view on platform" link is
a `target="_top"` navigation to `platform/widget/<id>/view`). The marker therefore never
needs to cross an origin boundary or live in a third-party cookie — it is **first-party
from birth**. This is what makes the no-PII, cookieless-cross-domain posture achievable
rather than the hard problem the brief flagged (§8 unverified assumption).

---

## 2. Proposed architecture (overview)

```
 Third-party host page                    Platform origin (first-party throughout)
 ┌─────────────────────┐
 │  <iframe src=        │   click "view    GET /widget/<X>/view
 │   platform/widget/X> │── on platform" ─▶ widget_view_redirect
 │   (anonymous user)   │   target=_top     │  1. count click-through (existing)
 └─────────────────────┘                    │  2. source.set_marker(resp, src=X)  ◀── NEW
                                            └─ 302 → /apps/X/  (Set-Cookie: widget_src)
                                                          │
                  visitor browses, later …                ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  CONVERSION 1: follow            POST /subscriptions/apps/<A>/follow   │
   │    follow_app(user,A) → created   ─▶ subscriptions.views.follow        │
   │    if created: source.attribute_follow(req, resp, followed_app_id=A) ──┼─▶ apps/widget
   │      (credits source X iff X==A and within window, once)               │   .source
   │                                                                        │      │
   │  CONVERSION 2: new account       POST /auth/register  (202 created)    │      ▼
   │    accounts.views.register        ─▶ source.attribute_account(req,resp)┼─▶ attribution
   │      (credits source X for an account, within window, once)            │   .record_widget_
   └──────────────────────────────────────────────────────────────────────┘   conversion(X,kind)
                                                                                    │
                                                       ┌────────────────────────────▼─────────┐
                                                       │ widget_conversion_count (NEW table)   │
                                                       │ (app_id, kind∈{follow,account}, day)  │
                                                       │  ↑ no user / IP / score column        │
                                                       │  ↑ apps/widget imports no signals      │
                                                       └────────────────────────────┬──────────┘
                                                                                    │ read
   developer dashboard (Screen B widget slot)  ◀── widget.selectors.widget_conversions ┘
     reach (unchanged) + conversions funnel stage + M2 rate (derived at display), fail-soft
```

**Components added / modified (single responsibilities):**

| Component | Type | Single responsibility |
|-----------|------|-----------------------|
| `widget.models.WidgetConversionCount` + table `widget_conversion_count` | **new** | Hold the per-`(app_id, kind, day)` attributed-conversion rollup. Shape only. |
| `widget.kinds.WidgetConversionKind` | **new** | The closed conversion vocabulary `{follow, account}` (distinct from `WidgetEventKind`). |
| `widget.rollup._increment_daily(model, app_id, kind)` | **new (extracted)** | The one concurrency-correct daily-increment, shared by the reach writer + the conversion writer. |
| `widget.attribution.record_widget_conversion(app_id, kind)` | **new** | The single writer of `widget_conversion_count`. Trusts a validated `app_id`; raises on DB error. |
| `widget.source` (`apps/widget/source.py`) | **new** | The **source-marker codec + the credit logic**: set the signed cookie; on a conversion, decode it, enforce window + dedup, and call the writer. The only module that knows the cookie format. |
| `widget.selectors.widget_conversions[ _for_apps]` | **new** | Windowed conversion reads (frozen `WidgetConversion{follows, accounts}`), sibling of the reach reads. |
| `widget_view_redirect` (views.py) | **modified** | Also calls `source.set_marker` on the 302 (fail-soft). |
| `subscriptions.views.follow` | **modified** | On a **new** follow, calls `source.attribute_follow` (fail-soft). |
| `accounts.views.register` | **modified** | On the **202 new-account** path, calls `source.attribute_account` (fail-soft). |
| `dashboard.reception` (`WidgetReachView` → `WidgetFunnelView`) + template | **modified** | Add the conversion funnel stage + M2 rate beside the unchanged reach. Fail-soft. |
| `core.config.widget_attribution_window_days()` | **new** | The WCA-2 window (default 30), config. Drives cookie max-age, signing max_age, and the server-side window check. |
| `core.observability.WIDGET_CONVERSION_*` (×4) | **new** | M1/M3/M6 metric names. |

**Coupling check.** All attribution behavior is concentrated in `apps/widget`
(`source` + `attribution` + the table). The two conversion apps each gain **one** new
import edge (`subscriptions → widget`, `accounts → widget`) and **one** call line.
`apps/widget` imports neither `subscriptions` nor `accounts` (nor `signals`), so the
dependency graph stays a **DAG** and the firewall stays structural. The feature is
**deletable** by reverting those two call lines + the dashboard slot extension and
dropping one table (§10 rollback; the `embeddable-update-widget` DU-REL-1 precedent).

---

## 3. The token-carry mechanism — resolving OQ-WCA-2 / OQ-WCA-3 / OQ-WCA-4

### 3.1 The marker (OQ-WCA-2: mechanism)

A **first-party, signed, source-only HTTP cookie** named `widget_src`, set by the
platform on the 302 from `/widget/<id>/view`.

- **First-party.** It is set on, and read on, the **platform origin** only. The third-party
  iframe context never sets or reads it. (This is the crux — see §3.2.)
- **Payload (signed, not encrypted — there is no secret to hide, only tamper to detect):**
  `django.core.signing.dumps({"v": 1, "src": "<source app_id>", "credited": []})`.
  - `src` — the **app whose widget was clicked** (a public `App.id`). Identifies the
    **widget source, never the person** (AC4).
  - `credited` — the subset of `{follow, account}` already credited from this marker
    (dedup, §3.4). Starts empty.
  - `v` — payload version (forward-compat; an unknown version is treated as "no marker").
  - **No** user id, session id, email, IP, device, referrer, or any person-linked field
    (AC4 / M5 = 0 by construction — there is nowhere in the payload to put one).
- **The click timestamp is NOT stored in the payload** — it is the signer's own timestamp.
  `signing.loads(value, max_age=window_seconds)` makes the **window** a property of the
  signature itself (a marker older than the window fails to load → "expired"). One source
  of truth for the window; no hand-rolled timestamp arithmetic.
- **Cookie attributes:** `Max-Age = window_days × 86400`, `SameSite=Lax`, `Secure`,
  `HttpOnly`, `Path=/`. `Lax` is sufficient and correct: every post-click step
  (the 302 to the app page, browsing, the follow **POST**, the register **POST**) is a
  **same-site** request to the platform, so `Lax` sends the cookie; we deliberately do
  **not** use `SameSite=None` (which would make it a cross-site cookie — unnecessary and
  consent-triggering). `HttpOnly` keeps it out of page JS (no XSS exfiltration, defense in
  depth — it is never read client-side).

### 3.2 Cross-domain identity (OQ-WCA-3) — dissolved, not solved

The brief feared a cross-domain identity problem: carrying a source from a
third-party-hosted widget across an origin boundary without a tracking cookie. **There is
no such boundary to cross.** The widget's "view on platform" control is a
`target="_top"` link to `platform/widget/<id>/view` — clicking it performs a **top-level
browser navigation onto the platform origin**. From that instant the visitor is
first-party on the platform for the entire click → app-page → conversion chain. The
source marker is therefore **created and read entirely first-party**; the iframe (the only
third-party context) never participates in attribution at all. No third-party cookie, no
fingerprint, no cross-site identifier, no cross-domain handoff. **OQ-WCA-3 is resolved by
construction.**

### 3.3 Consent envelope (OQ-WCA-4) — confirmed: no PII processed

Per OQ-WCA-4's instruction ("confirm in design that the chosen mechanism actually
processes no personal data; if it can't, the consent obligation returns as a decision"):

- **The marker processes no personal data.** Its entire content is `{version, source
  app_id, credited-kinds}` — a public app identifier and two bookkeeping fields. It carries
  no identity, contact, IP, device, or behavioral history, and it is **never joined to a
  person**: it is read once at a conversion to bump an **aggregate, source-keyed** counter,
  and is otherwise inert. **No per-person cross-site profile is ever built** (AC4).
- **Aggregate-only is therefore feasible** (the central [unverified] §8 assumption is now
  **verified** in design). It does **not** return to the user as a forced relaxation.
- **Honest nuance, surfaced not buried (§13 / DN-WCA-DESIGN):** "no consent banner" rests
  on the chosen **no-PII, strictly-purpose-limited** posture (WCA-3). The cookie is
  *strictly necessary-adjacent*, not strictly necessary, so under a maximalist reading of
  ePrivacy a non-essential cookie can attract a consent requirement **regardless of PII**.
  That is a **legal/policy judgment, not an architecture one**, and WCA-3 already made the
  product call (no banner). The architecture (a) adds **zero** PII and **zero** per-person
  profile, satisfying AC4/M5; and (b) is built so that **if legal counsel later requires
  consent for the EU**, gating `source.set_marker` behind a consent check is a **one-call
  change at a single site** with no schema impact (§8 / §14 revisit). We do **not**
  silently assume the question away — we record it as the one residual judgment for the
  approver.

### 3.4 Window, touch model, and dedup (WCA-2 / R4)

- **Last-touch (WCA-2).** Each click-through **overwrites** `widget_src` with a fresh
  signature and the latest `src`. The most recent widget click before a conversion is the
  one credited — last-touch by construction, no comparison logic.
- **Bounded window (WCA-2).** Enforced **twice, belt-and-suspenders:** the cookie
  `Max-Age` (the browser drops it) **and** `signing.loads(max_age=…)` (the server rejects
  a stale signature even if the cookie survived). A conversion with no live marker → **not
  credited** (AC2: no fabricated links).
- **Dedup (R4), without a person key.** Aggregate-only means we hold **no per-person
  row**, so dedup cannot be server-side per person. Instead the **`credited` set in the
  marker** dedups **per browser, per marker**: crediting `follow` adds `"follow"` to the
  set and re-issues the cookie (preserving the original signature window — see below), so a
  re-follow (e.g. unfollow→refollow) in the same browser within the window is **not**
  counted again. Distinct kinds (`follow`, `account`) are each creditable **at most once**
  per marker — exactly WCA-1's "distinct counts". Cross-browser / cross-marker repeats are
  **not** dedup'd (no person key exists to do so) — an accepted, bounded over-count on a
  firewalled vanity metric, reported via M3 coverage (§13).
  - *Preserving the window on re-issue:* re-issuing after a credit would normally reset
    `max_age`. To keep the window anchored to the **click**, the re-issued cookie carries
    `Max-Age = remaining = window − age_of_signature`, where the age is read from
    `signing.loads`. (Django exposes the signer timestamp; if remaining ≤ 0 the marker is
    expired and we simply don't re-issue.) This keeps "last-touch + bounded window" exact.

---

## 4. UX flow (states)

This feature is **almost entirely invisible to the end user** (that is the no-PII point —
nothing is shown to or asked of the converting visitor). The only user-facing surface is
the **developer dashboard** (Screen B, the existing app-reception view).

| State | What the developer sees |
|-------|--------------------------|
| **Has reach + conversions** | The existing "Widget reach (off-platform)" slot now shows a **Conversions** funnel stage under reach: `Follows from widget: N`, `New accounts from widget: M`, and **Conversion rate: N+M ÷ click-throughs %** (derived at display). |
| **Has reach, no conversions yet** | Reach shown as today; conversions show `0` / `0` (the truthful zero state, not hidden). |
| **No widget activity** | Slot shows zeros (unchanged from today). |
| **Slot degraded** (read error) | "Widget reach is temporarily unavailable." — the **whole** widget slot (reach + conversions) degrades together, fail-soft; the rest of the reception still renders (existing `DASHBOARD_WIDGET_DEGRADED`). |

No change to the widget render, the click-through, the follow flow, or the registration
flow as the **end user** experiences them — attribution is a silent side effect (AC6).

---

## 5. Interface contracts (no TBD)

### 5.1 `widget.source` — the marker codec + credit logic (the new core surface)

```python
COOKIE_NAME = "widget_src"

def set_marker(response, source_app_id: UUID) -> None:
    """Set/refresh the first-party source cookie on `response` (called from the 302).

    Signs {"v":1,"src":str(source_app_id),"credited":[]} and sets widget_src with
    Max-Age=window, SameSite=Lax, Secure, HttpOnly, Path=/. Overwrites any prior marker
    (last-touch). Pure cookie write — no DB. Raises only on a programming error; the
    caller wraps it fail-soft so a marker failure never breaks the redirect.
    """

def attribute_follow(request, response, *, followed_app_id: UUID) -> None:
    """Credit a FOLLOW conversion iff the live marker's src == followed_app_id and FOLLOW
    not already credited. Increments widget_conversion_count once, marks FOLLOW credited,
    re-issues the cookie (remaining window). No marker / expired / mismatch / already-
    credited → a no-op with the matching ops counter. Raises on a DB write error (caller
    wraps fail-soft)."""

def attribute_account(request, response) -> None:
    """Credit an ACCOUNT conversion for the live marker's src iff ACCOUNT not already
    credited. Same shape as attribute_follow but not app-scoped (an account is platform-
    wide; it credits the source widget that drove the visit). Raises on a DB write error."""
```

**Invariants:** a missing/malformed/expired/tampered marker is a **normal "no source"
outcome** (no-op + counter), never an error to the visitor. A DB write failure **raises**
to the caller (which is fail-soft). `attribute_*` never touch `signals`, never write any
per-person row, and never mutate the conversion's own corpus event.

### 5.2 Hook site #1 — `subscriptions.views.follow` (modified)

```python
@login_required
@require_http_methods(["POST"])
def follow(request, app_id):
    try:
        created = services.follow_app(request.user, app_id)   # now binds `created`
    except UnknownAppError as exc:
        raise Http404(...) from exc
    except Exception:
        ...                                                    # unchanged: loud-in-service, try-again to user
        created = False
    response = redirect("pages:app-page", app_id=app_id)
    if created:                                                # only a genuinely NEW follow
        _attribute_follow_fail_soft(request, response, app_id) # NEW, fail-soft wrapper
    return response
```

`_attribute_follow_fail_soft` wraps `source.attribute_follow(request, response,
followed_app_id=app_id)` in `try/except` → on error: log + `WIDGET_CONVERSION_DEGRADED`,
return the redirect unaffected (**AC6**). The follow's own state + `record_subscribe`
event are already committed and **untouched** (**AC5**).

### 5.3 Hook site #2 — `accounts.views.register` (modified)

On the **202 success path only** (a new `Account` was created — not 400/409/503), after
building the `check_email.html` response, call `_attribute_account_fail_soft(request,
response)` → wraps `source.attribute_account`. Same fail-soft contract. (Decision
WCA-DESIGN-7 / §13: credited at the **register act** the brief names, where the marker is
reliably co-located in the submitting browser; the confirmed-account and cross-device
nuances are documented limitations, not correctness bugs — no fabricated links, AC2.)

### 5.4 `widget.attribution.record_widget_conversion` (modified module, new function)

```python
def record_widget_conversion(app_id: UUID, kind: str) -> None:
    """Add one to today's (app_id, kind, count_date) conversion rollup row. Concurrency-
    correct via the shared _increment_daily. Trusts a caller-validated app_id (the marker's
    src, which is only ever a value we ourselves signed). Raises on a DB error."""
    _increment_daily(WidgetConversionCount, app_id, kind)
```

### 5.5 `widget.selectors` (new reads, sibling of the reach reads)

```python
@dataclass(frozen=True)
class WidgetConversion:
    follows: int
    accounts: int

def widget_conversions(app_id, *, start, end) -> WidgetConversion: ...
def widget_conversions_for_apps(app_ids, *, start, end) -> dict[UUID, WidgetConversion]: ...
```

One grouped `SUM(count) … GROUP BY kind` over the window's UTC-day range, zero-filled, no
N+1 — identical discipline to `widget_reach`. The **M2 rate** is derived at display from
`(follows + accounts)` and the existing `click_throughs`, **never stored**.

### 5.6 `core.config` (new tunable)

`widget_attribution_window_days()` — default **30** (WCA-2), `_positive_int`, added to
`validate_all()` (loud at startup). One source of truth for the window: cookie max-age,
`signing` max_age, and the remaining-window re-issue all derive from it.

---

## 6. Data design

### 6.1 New table `widget_conversion_count` (one source of truth: attributed conversions)

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID pk | mirrors `WidgetReachCount`. |
| `app_id` | UUID | **soft D-6 ref** (no DB FK) — the **source** app credited. A later withdrawal must not cascade-erase history (D-7 posture). |
| `kind` | varchar(16) | `WidgetConversionKind` ∈ `{follow, account}`. |
| `count_date` | date | the UTC day this rollup aggregates. |
| `count` | positive int | incremented, never hand-edited. |
| `created_at` / `updated_at` | datetime | audit. |

**Structural guarantees (illegal states unrepresentable — the `WidgetReachCount`
precedent):** **no `user` FK, no IP/UA/referrer/device column** (AC4 / no-PII by absence),
**no score/weight/rank column** (AC6 firewall reinforced — nothing here a Quality Score
could read). Constraints: `UniqueConstraint(app_id, kind, count_date)` (turns a concurrent
create into the caught `IntegrityError` the writer retries) + an index on
`(app_id, kind, count_date)` (backs both the increment filter and the windowed grouped
read). Migration: `widget/0002_widgetconversioncount` (additive; up→down→up clean — drops
cleanly, no data coordination since rows are PII-free aggregates).

**Why a separate table, not more kinds on `widget_reach_count`:** reach and conversion are
"distinct facts, distinct counts" (brief §3); a separate table keeps the reach selector's
zero-fill vocabulary clean, keeps the model docstrings honest, and makes the feature
**deletable** by dropping one table (design-for-deletion). The *concurrency-hard* part is
**not** duplicated — it is extracted once (§6.2).

### 6.2 Shared increment (DRY where it matters)

Extract the existing `_increment_today` body (atomic `F()+1` + nested-savepoint
create-race retry, EUW-IMPL-1) into `widget.rollup._increment_daily(model, app_id, kind)`,
parameterized by the model class. Both `record_widget_impression/click_through` (reach)
and `record_widget_conversion` (conversion) call it. Two concrete callers justify the
extraction (not speculative). The reach writer's public surface is unchanged.

### 6.3 The marker (transient client state)

Lives **only** in the visitor's browser as the `widget_src` cookie. No server-side copy,
no per-person table. Lifecycle: **created/refreshed** on each click-through; **read +
possibly re-issued** at a conversion; **expires** by max-age / signature age; **deleted**
implicitly when the browser drops it. Crash/restart safe: the server holds no state about
it; a lost cookie just means "no source" (under-attribution, never a wrong attribution).

---

## 7. (folded into §5/§6 — interface contracts and data are specified there)

---

## 8. Security model

- **Authn/authz.** The marker is set on an **AllowAny** anonymous route (unchanged); the
  follow hook is `login_required` (unchanged); the register hook is anonymous (unchanged).
  Attribution adds **no** new authority and reads **no** user data.
- **Tamper.** The cookie is **signed** (`django.core.signing`, HMAC over the payload with
  `SECRET_KEY`). A forged/edited marker fails to load → treated as "no source". Forging is
  also **pointless for ranking**: the conversion counter is firewalled (M5 = 0), so the
  only effect of a forged marker is inflating a developer's **own vanity count** — bounded
  (one per kind per marker), reported (M3 coverage looks anomalous), and conferring **zero**
  ranking advantage. We accept it rather than add per-person anti-fraud (which would
  require the very PII we forbid).
- **PII / data leakage.** No PII at rest (§6.1 structural) and none in transit beyond a
  signed public app-id + flags. `HttpOnly` keeps the marker out of page JS. The marker is
  never logged in full (we log `src` app-id + outcome, never the signature).
- **Open redirect.** Unchanged — the 302 target stays the **server-derived**
  `reverse("pages:app-page")`; the marker never influences the redirect destination.
- **Least privilege / blast radius.** All attribution is in `apps/widget`; a bug there
  cannot reach the corpus (no `signals` import) or the score (no rank column). The hooks
  are fail-soft, so an attribution fault cannot degrade a follow or a registration.
- **Consent.** §3.3 — no PII processed; the residual ePrivacy judgment is surfaced for the
  approver, and a consent gate is a one-call change if later required.

---

## 9. Failure modes (detection → response; never silent)

| Component | Failure | Detection | Response |
|-----------|---------|-----------|----------|
| `source.set_marker` (on the 302) | cookie write / signing error | exception in the view wrapper | **Fail-soft:** log + `WIDGET_CONVERSION_DEGRADED`; the **302 still fires** (the click-through + its reach count are unaffected). Worst case: that visit isn't attributable (under-count). |
| `source.attribute_follow/account` | DB write error | exception raised to the hook wrapper | **Fail-soft:** log + `WIDGET_CONVERSION_DEGRADED`; the **follow / registration completes normally** (AC6). The conversion's own corpus event is already committed + untouched (AC5). |
| marker absent / malformed / expired / tampered | normal "no source" | `signing.loads` returns/raises BadSignature/SignatureExpired, or no cookie | **No-op** + the matching ops counter (`WIDGET_CONVERSION_NO_SOURCE` / `_EXPIRED`). **Not** an error (AC2 — no fabricated links). |
| `widget.selectors.widget_conversions` (dashboard) | DB read error | exception in `_build_widget_funnel` | **Fail-soft slot:** the **whole** widget slot (reach + conversions) degrades together (`available=False` + existing `DASHBOARD_WIDGET_DEGRADED`); the rest of the reception renders. The core signals reads stay **loud-500** (unchanged). |
| `record_widget_conversion` create-race | concurrent first-of-day insert | caught `IntegrityError` | Retry as an increment (the existing nested-savepoint pattern, reused). |

**Trust-boundary validation:** the marker is the only untrusted input; it is validated by
**signature + version + window** before use, and `src` is parsed as a UUID (a non-UUID →
"no source"). Idempotency: the dedup `credited` set makes a re-submitted conversion in the
same browser a no-op.

---

## 10. Operations

**Metrics (new `core.observability` constants):**

| Constant | Meaning | Maps to |
|----------|---------|---------|
| `WIDGET_CONVERSION_ATTRIBUTED` (tags: `kind`) | a conversion was credited to a widget source | **M1** (the headline payoff) |
| `WIDGET_CONVERSION_NO_SOURCE` | a conversion ran with no live marker | **M3** denominator |
| `WIDGET_CONVERSION_EXPIRED` | a marker existed but was outside the window | **M3** + AC2 evidence |
| `WIDGET_CONVERSION_DEGRADED` | **the one alert** — an attribution read/write failed (best-effort lost) | **M6** |

- **M1** = `WIDGET_CONVERSION_ATTRIBUTED` by kind (also the dashboard number).
- **M2** (rate) = dashboard-derived `(follows+accounts) ÷ click_throughs`.
- **M3** (coverage) = `ATTRIBUTED ÷ (ATTRIBUTED + NO_SOURCE + EXPIRED)` in monitoring — a
  mechanism-health signal, honestly lossy rather than a misleading per-app ratio (§13).
- **M4** (firewall = 0) and **M5** (PII fields = 0) are **structural** — asserted in tests
  (AST no-`signals` import; no per-person column), **no counter** (the `widget` precedent).
- **M6** = `WIDGET_CONVERSION_DEGRADED` rate; sustained nonzero ⇒ attribution silently
  lossy ⇒ alert.
- Reuse `DASHBOARD_WIDGET_DEGRADED` for the dashboard slot (no new dashboard counter).

**Debug:** existing request-id + account-UUID log context; attribution logs carry the
`src` app-id + outcome.

**Rollback (DU-REL-1 precedent — `subscriptions`/`accounts`/`dashboard` now import
`widget`):** a single `git revert` of the build commit removes the hooks + the slot
extension + the new module atomically (`manage.py check` clean — no dangling import).
Optional `migrate widget 0001` drops `widget_conversion_count` (PII-free aggregates, no
data coordination). Rehearsed at release (Stage 5).

---

## 11. Alternatives considered (≥1 genuinely different, with the sacrifice)

| # | Alternative | Why rejected |
|---|-------------|--------------|
| **A1** | **Third-party cookie / device fingerprint / cross-site ID** to bridge the iframe to the platform | Unnecessary (§3.2 — the click-through is already first-party) **and** it is exactly the covert cross-person tracking R1/AC4 forbid. The chosen first-party marker gets the same attribution with **no** cross-site identity. |
| **A2** | **Server-side per-person attribution row** (store "visitor V came from widget X", join at conversion) | Richer (true per-person dedup, cross-device) but it **is** the per-person profile + PII surface WCA-3 rejected; needs consent. **Sacrifice of the chosen design:** no cross-browser/cross-device dedup and only approximate coverage — accepted to hold AC4/M5 by construction. |
| **A3** | **Reuse `widget_reach_count`** with `follow`/`account` kinds | DRY on the table but conflates "distinct facts, distinct counts" (brief §3), muddies the reach selector's zero-fill, and breaks design-for-deletion. We reuse the **hard part** (the increment, §6.2) instead. |
| **A4** | **Middleware or a Django `post_save` signal** to credit conversions | Decoupled but **magic** (the prime directive — a reader can't see attribution by reading the conversion view) and signal handlers lack the `request`/`response` the cookie needs. The explicit view hook is readable, request-aware, and fail-soft-local. |
| **A5** | **Credit the account conversion at `verify`** (confirmed account) instead of at `register` | More "real" (confirmed) but the email link often opens in a **different browser** (no marker) → worse coverage, and it complicates the verify path. Chose the **register act** (the brief's named event, marker co-located); the confirmed-vs-act nuance is a documented revisit (§13/§14). |
| **A6** | **Carry the source as a URL query param** through the redirect chain | Can't survive the (up-to-30-day) click→conversion gap without device storage anyway, and a visible `?src=` is editable/shareable (forgeable, leak-prone). The signed cookie is the bounded, tamper-evident store. |

---

## 12. Tests (every AC → ≥1 verification)

| AC | Verification |
|----|--------------|
| **AC1** (conversion shows on dashboard) | E2E: set marker for app X → follow X / register → `widget_conversions(X)` and the Screen-B slot show the credited counts. |
| **AC2** (window + no-fabrication) | Convert **with** a live marker → credited; **no** marker → not credited (`NO_SOURCE`); marker **past the window** (`signing` max_age elapsed) → not credited (`EXPIRED`); marker for app Y, follow app X → no follow credit. |
| **AC3** (distinct funnel stage, reach unchanged) | Slot renders reach **and** conversions as separate lines + the derived rate; asserting reach integers are byte-identical to the pre-conversion slot (one-source-of-truth: separate tables). |
| **AC4** (no-PII) | The marker payload contains only `{v, src, credited}` (assert no person field); `widget_conversion_count` has **no** user/IP/device column (schema test); no per-person row is written on a conversion. |
| **AC5** (firewall) | **Extend the existing AST test** — every `apps/widget` module (incl. `source`) imports nothing from `signals`. A credited follow writes **the same** `record_subscribe` corpus row as an un-attributed follow (attribution adds nothing); `has_impression(CURATED_SURFACES)` stays False; **M5 = 0**. |
| **AC6** (fail-soft) | Force `record_widget_conversion` / `set_marker` to raise → the follow, the registration (202), and the reach counts all still succeed; `WIDGET_CONVERSION_DEGRADED` counted. |
| concurrency | Two concurrent first-of-day conversions for the same `(app, kind)` → count ends at 2 (create-race retry). |
| dedup (R4) | Re-follow (unfollow→refollow) in the same browser within the window → credited **once** (`credited` set); a fresh marker (new click) re-arms. |
| each module in isolation | `source` (codec round-trip, tamper/expiry), `attribution`/`selectors` (ORM-seeded), the hooks (mocked `source`), the dashboard slot (mocked selectors). |

Boundary/edge: empty (no conversions → zeros), huge (window grouped read stays O(days)),
malformed marker (bad base64/signature → no-op), version skew (`v:2` unknown → no-op).

---

## 13. Self-critique (attacking the design)

- **Cross-device registration / follow.** If the visitor clicks the widget on desktop but
  registers/confirms on mobile, the marker isn't present → under-attribution. **Accepted**
  — it never produces a *wrong* attribution (AC2), and it is reported via M3 coverage. The
  cross-device fix is A2 (per-person), which we rejected on no-PII grounds.
- **Register act vs confirmed account (A5).** Crediting at the register POST counts a
  registration that might never confirm → slight over-count of accounts. Bounded
  (`@rate_limited` register; one per marker) and reported (M3). Flagged to **revisit on
  real data** (§14) — switching to verify-time is a localized change.
- **Dedup without a person key.** Cross-browser repeats by one human aren't dedup'd. This
  is the unavoidable cost of aggregate-only; the metric is firewalled, so the worst case is
  vanity inflation, not ranking manipulation (R3 held structurally).
- **ePrivacy/consent (§3.3).** The one judgment I can't fully close in architecture. I did
  **not** silently relax WCA-3 — I confirmed no PII is processed (so WCA-3's premise
  holds) and surfaced the residual legal call to the approver, with a one-call consent gate
  designed in as the contingency.
- **Simplification pass.** Dropped: a separate conversion-degraded dashboard counter
  (reuse `DASHBOARD_WIDGET_DEGRADED`); a stored click timestamp (use the signer's);
  per-person anything; Screen-A conversion column (Screen B is where the full funnel lives —
  noted, not built, to avoid an N+1 read on the my-apps list). Nothing in the design is
  unattached to an AC.
- **Did I change the brief?** No. WCA-1/2/3 are honored; the privacy/firewall envelope is
  held; the only thing decided here is the *how* (OQ-WCA-2…4), which is this stage's job.

---

## 14. Deliver — decisions, first version, revisits

**Decisions (logged in [DECISIONS.md](DECISIONS.md) as WCA-DESIGN-1…8, PROPOSED → ratified
on DN-WCA-DESIGN approval):**

1. **WCA-DESIGN-1** — token-carry = a **first-party signed source-only cookie** set on the
   click-through 302 (OQ-WCA-2). 2. **WCA-DESIGN-2** — cross-domain identity **dissolved**:
   the click is a first-party top-level navigation; the iframe never participates
   (OQ-WCA-3). 3. **WCA-DESIGN-3** — **no PII processed** → aggregate-only feasible, no
   banner under WCA-3; ePrivacy consent is the surfaced residual judgment with a one-call
   gate as contingency (OQ-WCA-4). 4. **WCA-DESIGN-4** — **separate
   `widget_conversion_count` table** + **shared `_increment_daily`** helper. 5.
   **WCA-DESIGN-5** — **last-touch + bounded window** via cookie overwrite + signing
   max_age; **dedup via the `credited` set** (per-browser, no person key). 6.
   **WCA-DESIGN-6** — **explicit fail-soft view hooks** (not middleware/signals) at
   `subscriptions.views.follow` (on `created`) and `accounts.views.register` (202). 7.
   **WCA-DESIGN-7** — account credited at the **register act** (revisit vs verify-time on
   data). 8. **WCA-DESIGN-8** — dashboard slot extended with the conversion funnel stage +
   derived M2; reach untouched; fail-soft. **No new global ADR** (reuses D-3/D-4/D-6/D-7/
   D-8/D-9/D-10 + the carried-in AC6 firewall).

**Smallest useful first version → increments** (Stage-3 will decompose):
1. table + kinds + `_increment_daily` extraction + the conversion writer + the AST/firewall
   proof (risk-front-loaded, like EUW T-02);
2. `source` codec + window/dedup + unit tests (tamper/expiry/round-trip);
3. the `set_marker` call on the 302;
4. the two fail-soft conversion hooks;
5. the selectors + the dashboard slot extension + M2;
6. config tunable + metrics + docs/CODEMAP.

**Revisit once real usage exists:** the 30-day window length (M3 coverage will tell us if
it's too short/long); register-act vs verify-time for accounts (WCA-DESIGN-7); whether
cross-device coverage loss is material enough to reconsider A2 under an explicit consent
regime.

**Rollout:** no flag needed — the surface is inert until the build lands and is
behaviorally invisible to end users; the dashboard slot is additive + fail-soft. Migration
is additive (one table). Backward-compatible. Rollback = single `git revert` (§10).

---

> **Exit gate:** every AC1–AC6 maps to ≥1 design element (§5/§6/§9/§12); all interfaces
> are fully specified (no TBD); each component's failure behavior is documented (§9); the
> design honors CLAUDE.md §5 (scalable rollup, readable explicit hooks, partitioned in
> `apps/widget`, fail-loud-to-ops, one-source-of-truth per fact, design-for-deletion) and
> adds no speculative abstraction. **Raised as DN-WCA-DESIGN — awaiting approval; no Stage
> advance until approved.**
