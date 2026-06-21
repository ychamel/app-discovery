# DESIGN — app-subscriptions

*Stage 2 artifact (Software Architect). Status: **DRAFT — awaiting approval (DN-14)**.
Reads the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md) + codebase; produces architecture,
data model, contracts, UX, failure modes, and rollout. Honors [CLAUDE.md](../../CLAUDE.md)
§5. Reuses [D-3](../../DECISIONS.md) (identity), [D-6](../../DECISIONS.md) (catalogued app),
[D-7](../../DECISIONS.md) (event schema incl. the `subscribe` kind) **as-is — no new global
decision proposed**.*

> **One-line shape:** a new Django app `apps/subscriptions/` owning **one mutable table**
> (`subscriptions_subscription`, one current follow per user×app). It is a near-twin of the
> closed-out `apps/ratings/` (own mutable store + single write path + single read path + a
> fail-soft inclusion tag on the app page + an activation include), with **three deliberate
> contrasts**: deletion **CASCADE**s (follow state is a live relationship, not corpus — AS-5),
> the follow-write and its one `subscribe` corpus emit are **one atomic transaction** (M5
> 1:1 by construction), and it ships a **forward-compatible, empty-until-producer notice
> seam** (AS-3 = option A).

---

## 1. Design protocol summary (the 14 steps, condensed)

The full reasoning is folded into the sections below; this is the audit trail.

1. **SCOPE** — Give a signed-in user a durable follow relationship to accepted apps and a
   personal return surface, so the platform *generates* the return/re-engagement signal the
   Quality Score consumes — without scoring it here. Out: notice *authoring*, delivery
   channels, developer-follow, collections, public counts, re-implementing visit/re-engagement
   capture. Lifespan: **platform** (a load-bearing engagement primitive) → full rigor.
2. **REQUIREMENTS** — §3 below. Functional = AC1–AC9; non-functional = bounded reads (no
   N+1 at 100× follows), fail-loud capture, fail-soft display, private follow state. All
   assumptions verified against the repo (§3.3) except the two this design *resolves*: OQ-3
   (unfollow corpus repr) and OQ-4 (follow-control placement).
3. **CONTEXT** — §2. Everything needed already exists: `signals.capture.record_subscribe`
   (the `subscribe` write path), `catalog.get_catalogued_app` (D-6), the `apps/pages` slot/
   inclusion-tag pattern, `accounts.delete_account` (CASCADE-on-delete), `apps/core` config +
   observability. The build is *reuse + one small table*, not net-new infrastructure.
4. **MODULES** — §4/§5. `models` (the store) · `services` (the single write path) ·
   `selectors` (the single read path) · `notices` (the empty-until-producer seam) · `views` +
   `urls` (thin HTTP) · `templatetags` (the fail-soft follow control) · `feed` template ·
   `admin`. Single responsibility each; the store is replaceable/testable in isolation.
5. **INTERFACES** — §6. Every function signature, its errors, and its invariants are pinned —
   no "TBD".
6. **DATA & STATE** — §4. One source of truth: the *current* follow is the mutable
   `Subscription` row; the *act of following* is the append-only D-7 `subscribe` event; they
   are written in one transaction so they cannot disagree.
7. **FAILURE** — §9. Per component: loud where correctness depends on it (the follow write +
   capture), soft where availability matters more (the feed, the inclusion tag, the notice
   seam). Every failure is counted.
8. **CHANGE** — §10. What changes cheaply: the feed page-size, the notice producer (a one-seam
   repoint when `developer-updates` ships). What is irreversible: the choice *not* to add a
   D-7 `unfollow` kind (OQ-3) — justified in §8 and reversible additively if a consumer ever
   needs it.
9. **TRADE-OFFS** — §11. ≥2 genuinely different approaches, compared against §3, with the
   sacrifices named.
10. **SECURITY** — §8. `login_required` for all mutations; own-data-only is *structural* (no
    subscription id in any URL → no IDOR); follow state private to the user.
11. **OPERATIONS** — §9.4. Metric→signal→alert map tied to brief M1–M6; the one actionable
    alert is subscribe-capture failure (M5).
12. **TESTS** — §12. Each module isolated; AC1–AC9 each mapped to a concrete verification;
    edge cases enumerated.
13. **SELF-CRITIQUE** — §14. Attacks the transactional coupling, the bulk-read N+1 risk, the
    empty notice seam, and the template touch; runs a simplification pass.
14. **DELIVER** — §13 (AC map) + §15 (smallest-useful-first + revisit flags). Decisions with
    rationale + rejected alternatives recorded in [DECISIONS.md](DECISIONS.md).

---

## 2. Current-state summary (what already exists, diff-able against reality)

| Existing component | What it gives this feature | Reused how |
|---|---|---|
| `signals.capture.record_subscribe(user, app_id, *, impression=None, …)` | The **only** D-7 write path for a follow; validates the app (D-6), counts `SUBSCRIBE_CAPTURED`, fails loud + counts `CAPTURE_ERROR{kind=subscribe}` ([capture.py:214](../../apps/signals/capture.py)) | Called from `services.follow_app`, inside the follow transaction (AC5/AC7) |
| `catalog.get_catalogued_app(id) -> CatalogApp \| None` (D-6) | Accepted-app validity + the render shape (name, tags, media, url) ([selectors.py:154](../../apps/catalog/selectors.py)) | Write-boundary app check; feed render shape |
| `catalog.list_catalogued_apps()` (D-6) | The bulk accepted-apps read; **but there is no by-ids bulk** | §4.3 adds an additive `get_catalogued_apps(ids)` over the same base queryset (no N+1) |
| `apps/pages` slot + inclusion-tag pattern | The app page (`pages:app-page`) renders six fixed slots; `ratings` filled slot 6 via `{% app_reviews app %}` ([app_page.html](../../apps/pages/templates/pages/app_page.html)) | OQ-4: a new fail-soft `{% app_follow app %}` tag in a new Follow slot (§5f) |
| `accounts.delete_account(account)` → `account.delete()` (CASCADE) ([services.py:58](../../apps/accounts/services.py)) | Account deletion already cascades to FKs that point at it | AC9: our `user` FK is **CASCADE**, so deletion removes follow state with **no edit to accounts** |
| `signals` SC-10 (`EngagementEvent.user` is SET_NULL) | Already-emitted `subscribe` events anonymize-not-purge on deletion ([models.py:103](../../apps/signals/models.py)) | AC9: corpus side needs **no change** — owned by signals |
| `apps/core` config + observability + `PlatformVisitMiddleware` | Tunables, metric constants, and the **existing** return-tick + re-engagement seams | AC6: we *cause* returns; the existing seams *capture* them — we add nothing here |
| `apps/ratings` (closed out) | The exact template: own mutable store, single write/read path, thin `login_required` PRG views keyed on user+App.id (no IDOR), fail-soft inclusion tag, activation include | Structural blueprint — match its conventions (CLAUDE.md §5.5) |

**Nothing in the corpus, the catalog, or accounts needs to *change*** beyond the one additive
catalog read (§4.3). app-subscriptions is overwhelmingly a *consumer* plus one small owned
table.

---

## 3. Requirements & assumptions

### 3.1 Functional (verifiable) — the brief's AC1–AC9
Restated as the design's obligations; full map in §13.

- Follow / unfollow an accepted app, idempotent single state (AC1/AC3).
- Anonymous cannot follow; the page still renders for them (AC2).
- A personal followed-apps feed listing current follows via D-6 data, with an empty state
  that never errors (AC4).
- Exactly one D-7 `subscribe` event per *new* follow, via `signals.capture.*`, keyed
  user×App.id, with **no score/weight/rank** anywhere in this feature (AC5).
- Return / re-engagement captured by the **existing** signal-capture seams — not
  re-implemented (AC6).
- Capture failure surfaced + counted; follow state never claims success it did not store
  (AC7).
- A forward-compatible notice surface with an empty state, never erroring on "no producer"
  (AC8).
- Account deletion removes follow state; emitted events follow SC-10 (AC9).

### 3.2 Non-functional
- **Scale (CLAUDE.md §5.2):** every read is bounded and N+1-free at 100× follows-per-user
  (the feed is the only fan-out — §4.3 bulk read + a config page-size).
- **Integrity:** M5 (subscribe events == follows) must be **1:1 by construction**, not merely
  measured — see §6.1 the transactional coupling.
- **Privacy:** follow state is private to the user (no public counts/social graph — out of
  scope); deletion removes it (AC9).
- **Availability:** a follow/notice/feed-read fault must never 500 the app page (fail-soft
  display) — but a follow that did not durably store must never look successful (fail-loud
  write).

### 3.3 Assumption ledger (✓ verified in repo / → resolved by this design)
- **AS-1 ✓** `subscribe` is a live D-7 `EventKind`; `record_subscribe` exists ([capture.py:214](../../apps/signals/capture.py)).
- **AS-2 ✓** the app page + slot/inclusion-tag pattern exist ([app_page.html](../../apps/pages/templates/pages/app_page.html)).
- **AS-3 ✓ (option A)** notice *generation* is out; the *surface* ships now — §5g.
- **AS-4 → resolved** the follow store is this feature's own **mutable** table; the corpus
  event is append-only — §4 + §6.1.
- **AS-5 ✓** deletion removes follow state (CASCADE, §4.2); events follow SC-10.
- **OQ-3 → resolved (§8):** *unfollow needs **no** D-7 corpus kind* at MVP.
- **OQ-4 → resolved (§5f):** the follow control is a fail-soft inclusion tag in a new app-page
  Follow slot.

---

## 4. Data design — the one owned table

A new Django app `apps/subscriptions/` owns exactly one table. Like ratings (and unlike the
append-only D-7 corpus) it is **deliberately mutable**: a follow is created and removed, never
versioned.

### 4.1 `Subscription` (`db_table = "subscriptions_subscription"`)

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField` pk (default `uuid4`) | own identity (house convention) |
| `user` | `FK(AUTH_USER_MODEL, on_delete=CASCADE)` | **CASCADE** = the AS-5/AC9 contrast with ratings' SET_NULL — see §4.2 |
| `app_id` | `UUIDField` | **soft D-6 ref** (no DB FK), validated at the write boundary via `get_catalogued_app` — a later withdrawal must not cascade-erase the follow |
| `created_at` | `DateTimeField(auto_now_add=True)` | when followed — drives feed ordering (most-recent first) and the M1/M3/M6 windows |

**No `score`/`weight`/`rank` column (AC5 — structural).** **No `updated_at`** — a follow has
no mutable attribute; it exists or it does not (one job, CLAUDE.md §5.3). **No `unfollowed_at`/
soft-delete** — unfollow is a hard delete so the store is *exactly the current relationship*
(one source of truth); churn (M6) is read from the `SUBSCRIPTION_UNFOLLOWED` metric, and the
deeper "unfollow as a behavioral fact" question is OQ-3 (§8 — deferred, not built).

```python
class Meta:
    db_table = "subscriptions_subscription"
    ordering = ["-created_at"]
    constraints = [
        # AC1 — one follow per user per app; following an already-followed app is a no-op.
        # CASCADE means no anonymized user=NULL rows, so (unlike ratings) this constraint has
        # no NULL-collision subtlety — it is a clean composite unique.
        models.UniqueConstraint(fields=["user", "app_id"],
                                name="subscriptions_one_per_user_app"),
    ]
    indexes = [
        # Backs the feed read (selectors.followed_apps), most-recent-followed first.
        models.Index(fields=["user", "created_at"], name="subscriptions_user_created_idx"),
    ]
```

### 4.2 Lifecycle & deletion (AC9 — the deliberate contrast with ratings)
- **Create:** `get_or_create(user, app_id)` in `services.follow_app` (§6.1). The `created`
  flag is the idempotency gate: `created=True` → emit one `subscribe`; `created=False` →
  no-op, no event.
- **Delete (unfollow):** `filter(user, app_id).delete()` in `services.unfollow_app` — hard,
  idempotent (no row → no-op, AC3).
- **Delete (account):** the `user` FK is **CASCADE**, so `account.delete()`
  ([accounts/services.py:58](../../apps/accounts/services.py)) removes all of the user's follow
  rows automatically. **No edit to `accounts.delete_account` is required** (design-for-deletion
  — the boundary is owned by the FK). The already-emitted `subscribe` events are owned by
  signals and anonymize-not-purge under SC-10 — **unchanged**. This is the principled split the
  brief demands: live relationship state is *removed*, behavioral corpus is *retained-but-
  unlinked*, each by its owner, with no new corpus-deletion behavior invented here.

> **Why CASCADE here but SET_NULL in ratings?** A rating is *eligibility-tagged corpus the
> future Quality Score backtests on* (it must survive, unlinked — SC-10). A follow is *live
> relationship state* with no standalone analytic value once the person is gone; the
> behavioral residue of "they once followed X" already lives in the retained `subscribe`
> corpus event. Keeping a dangling user=NULL follow row would be meaningless state. CASCADE is
> the correct, simpler choice and AC9 mandates it.

### 4.3 Additive catalog read (no N+1) — `catalog.get_catalogued_apps(ids)`
The feed resolves N followed `app_id`s to their D-6 render shape. Calling `get_catalogued_app`
per follow is O(N) queries; reading `list_catalogued_apps()` (the whole catalog) is unbounded
in catalog size. Neither scales (§3.2). The correct primitive is a **by-ids bulk** selector,
added to `apps/catalog/selectors.py`:

```python
def get_catalogued_apps(app_ids: list[UUID]) -> list[CatalogApp]:
    """Accepted apps among ``app_ids`` as their D-6 shape — bulk, accepted-only, no N+1.
    Non-accepted/unknown ids are silently absent (the caller orders + handles gaps)."""
    apps = list(
        App.objects.filter(pk__in=app_ids, status=App.Status.ACCEPTED)
        .prefetch_related("media", "app_tags")
    )
    resolved = _resolve_tag_labels(apps)
    return [_to_catalog_app(app, resolved) for app in apps]
```

This is an **additive D-6 read-surface extension**, not a contract change: it preserves the
accepted-only guarantee, returns the same `CatalogApp` shape, and mirrors how `signals` gained
`funnel_for_apps` alongside `app_funnel`, and how `ratings` added `signals.has_impression`. It
is **recorded as a feature-local note, not a new global ADR** — D-6 explicitly anticipates
"a new consumer need is a one-line selector over the same base queryset" and is additive-only
by design. Recorded in [DECISIONS.md](DECISIONS.md) (AS-DESIGN-1).

---

## 5. Proposed architecture (components, single responsibilities)

```
apps/subscriptions/
  models.py        (a) Subscription — the one mutable store; shape only, no logic
  services.py      (b) follow_app / unfollow_app — THE single write path (+ the txn coupling)
  selectors.py     (c) is_following / followed_apps — THE single read path
  notices.py       (d) notices_for_apps — the empty-until-producer notice seam (AS-3)
  errors.py        (e) UnknownAppError — loud write-boundary failure
  views.py + urls.py  (f) thin login_required PRG views: follow, unfollow, feed
  templatetags/subscriptions_tags.py + templates/  (g) {% app_follow app %} fail-soft control
  templates/subscriptions/feed.html  (h) the followed-apps feed (apps region + notices region)
  admin.py         (i) read-only follow visibility (operability)
config/urls.py     (+) the activation include  path("subscriptions/", include(...))
apps/pages/templates/pages/app_page.html  (Δ) +1 Follow section calling {% app_follow app %}
apps/catalog/selectors.py  (Δ) + get_catalogued_apps(ids) — additive bulk read (§4.3)
apps/core/config.py + observability.py  (Δ) + 1 tunable + the metric constants
```

Dependencies point only toward stable, closed-out modules (signals, catalog, accounts, core,
pages) — never the reverse. Each component is replaceable/testable in isolation (§12).

### 5a. `services.py` — the single write path
Owns *all* `Subscription` mutation **and** the corpus emit. Exposes `follow_app` /
`unfollow_app`; hides the store and the transaction. The only module that imports
`signals.capture`. (§6.1.)

### 5c. `selectors.py` — the single read path
Owns *all* `Subscription` reads. Exposes `is_following(user, app_id) -> bool` and
`followed_apps(user, *, limit) -> list[CatalogApp]`; hides the ORM and the bulk-catalog join.
No write, no scoring. (§6.2.)

### 5d. `notices.py` — the empty-until-producer seam (AS-3 = option A)
Owns the *shape* the feed renders notices in, and the single call site that produces them.
Today it returns `[]` (no producer); when `developer-updates` (Phase 3) ships, it is the one
place repointed to read real notices — **no feed rework** (§5g, §6.3).

### 5f. `templatetags/subscriptions_tags.py` — `{% app_follow app %}` (resolves OQ-4)
The **only** coupling between the closed-out app-page template and this feature, exactly
mirroring `{% app_reviews app %}`. It renders, for the **current viewer**:
- **anonymous** → a "Sign in to follow" prompt linking to the auth flow (AC2); no follow
  button. The app page still renders fully (pages owns the render; this tag adds one section).
- **signed-in, not following** → a one-click **Follow** POST form (CSRF) → `subscriptions:follow`.
- **signed-in, following** → an **Unfollow** POST form → `subscriptions:unfollow` (AC1/AC3
  state reflected).

**Fail-soft (mirrors ratings §5f):** any selector error renders a degraded slot (no control)
and increments `SUBSCRIPTION_CONTROL_DEGRADED` — it never raises into the page render, so a
subscriptions outage can never take down the app page (preserves app-pages AC5).

**Placement (OQ-4 resolved):** a **new `<section aria-label="Follow">` immediately after the
`<header>`** in `app_page.html` (so Follow becomes slot 2; media→3, …, Reviews→7). Rationale:
follow is a relationship action on the whole app and belongs beside its identity (the name);
high visibility drives M1 adoption (R2: one-click follow from the page). It is **viewer-state-
driven, not app-state-driven**, so the page-uniformity invariant (every accepted app renders
the same slots — AC3 of app-pages) is preserved: the slot is identical for every app; only the
*viewer's* auth/follow state varies. It does **not** disturb the existing six slots' content
(the ratings slot-6 fill is untouched); it inserts one section. **Rollback** = remove the one
`{% app_follow app %}` section + the `{% load subscriptions_tags %}` line (one-section revert).
**Interaction with the ratings slot:** independent inclusion tags, no shared state, no
collision — each fails soft on its own.

### 5g. The feed template (`feed.html`) — two regions
- **Notices region** (top — the "reason to come back"): renders `notices` if any, else a clear
  **"No news yet"** empty state (AC8). Today always empty (no producer) — by design, honest,
  never an error.
- **Followed-apps region:** the user's current follows (most-recent first), each linking to
  `pages:app-page` (so a click flows through the *existing* re-engagement/visit seams — AC6).
  Empty → a clear **"You're not following any apps yet"** state with a pointer to browse
  (AC4). Never an error.

---

## 6. Interface contracts (no "TBD")

### 6.1 `services.follow_app(user, app_id: UUID) -> bool` — the transactional coupling
Returns `True` iff a **new** follow was created (so the view/metrics can distinguish a real
follow from an idempotent no-op).

```python
def follow_app(user, app_id: UUID) -> bool:
    _require_catalogued_app(app_id)            # D-6: UnknownAppError if not accepted (AC1)
    with transaction.atomic():                 # the follow row + its corpus event are ONE unit
        sub, created = Subscription.objects.get_or_create(user=user, app_id=app_id)
        if created:
            # Same DB, same transaction: if capture raises, BOTH the row and the (savepointed)
            # event roll back — never a follow without its event, never an event without a
            # follow. M5's 1:1 is structural, not just measured (AC5/AC7).
            signals_capture.record_subscribe(user, app_id)
    observability.increment(                   # OUTSIDE the txn: a rolled-back follow never counts
        observability.SUBSCRIPTION_FOLLOWED if created
        else observability.SUBSCRIPTION_FOLLOW_NOOP
    )
    return created
```

- **Invariants:** a committed `Subscription(user, app_id)` ⟺ a committed `subscribe`
  `EngagementEvent` for the same (user, App.id). Idempotent: re-follow of a current follow
  emits nothing. Re-follow *after* an unfollow (the row was deleted) is a genuine new follow →
  one new event (each act of following is its own corpus fact — append-only D-7).
- **Errors:** `UnknownAppError` (app not accepted — view → 404). Any capture/DB failure
  propagates *after* `capture._guard` has counted `CAPTURE_ERROR{kind=subscribe}` and rolled
  the transaction back; the view surfaces it as a user-visible failure (AC7) — the durable
  state is correctly *not-followed*.
- **MVP simplicity (deliberate):** `record_subscribe` is called **without** an impression link.
  The event keyed `user × App.id` satisfies AC5 and every metric (M1/M3/M5); attributing
  *which shown instance* caused the follow is optional in D-7 and adds mismatch-handling
  complexity for no MVP requirement. `record_subscribe` already accepts an optional
  `impression`, so linking it later is purely additive — recorded as a revisit flag (§15), not
  wired now (no speculative abstraction — CLAUDE.md §5.5).

### 6.2 `services.unfollow_app(user, app_id) -> bool` / read selectors
```python
def unfollow_app(user, app_id: UUID) -> bool:        # AC3 — hard delete, idempotent
    deleted, _ = Subscription.objects.filter(user=user, app_id=app_id).delete()
    existed = deleted > 0
    if existed:
        observability.increment(observability.SUBSCRIPTION_UNFOLLOWED)
    return existed
```
- No app-validity check (a user may unfollow an app that was later withdrawn — let them clean
  up). **No corpus event** (OQ-3 = no — §8).

```python
def is_following(user, app_id) -> bool                # for the inclusion tag (AC1)
    # False for anonymous/None; one indexed EXISTS query for a signed-in user.

def followed_apps(user, *, limit) -> list[CatalogApp] # the feed (AC4)
    # 1) most-recent `limit` app_ids: Subscription.filter(user).order_by("-created_at")[:limit]
    # 2) bulk D-6 resolve: catalog.get_catalogued_apps(app_ids)  (accepted-only, §4.3)
    # 3) re-order to follow-recency and drop any non-accepted (withdrawn) app silently.
    # Bounded (limit) + 2 queries total → no N+1 at 100× follows (§3.2).
```

### 6.3 `notices.notices_for_apps(app_ids: list[UUID]) -> list[Notice]` — the AS-3 seam
```python
@dataclass(frozen=True)
class Notice:                  # THE render contract developer-updates must honor (no "TBD")
    app_id: UUID               # which followed app the news is about
    kind: str                  # "update" | "early_access"
    title: str
    summary: str
    published_at: datetime

def notices_for_apps(app_ids: list[UUID]) -> list[Notice]:
    """Notices for followed apps, newest first. No producer exists yet (developer-updates,
    Phase 3) → returns []. This is the ONE place to repoint when that producer ships; the feed
    template renders `Notice`s unchanged. Fail-soft at the call site (§9)."""
    return []
```
This is the minimum that satisfies AC8: the *shape* and the *call site* exist and render; only
the *data* is empty — the honest-MVP pattern (mirrors D-8's gate that is ~always not-eligible
until a `DIGEST` emitter exists). It builds **no** producer, registry, or pluggable provider
(that would be speculative — the producer is one named future feature, so a single repointable
function is the right seam).

### 6.4 HTTP routes (mirror ratings — keyed on user + App.id, no IDOR)
| Route name | Method | Path | View behavior |
|---|---|---|---|
| `subscriptions:follow` | POST | `subscriptions/apps/<uuid:app_id>/follow` | `login_required`, CSRF → `follow_app` → PRG to `pages:app-page`; `UnknownAppError`→404; capture failure → `messages.error` + PRG (state not-followed, AC7) |
| `subscriptions:unfollow` | POST | `subscriptions/apps/<uuid:app_id>/unfollow` | `login_required`, CSRF → `unfollow_app` → PRG to `pages:app-page` |
| `subscriptions:feed` | GET | `subscriptions/feed` | `login_required` → render `feed.html` (followed apps + notices) |

Own-data-only is **structural**: no subscription id appears in any URL — a follow is addressed
by `request.user` + `app_id`, so a user can only ever touch their own (no id to tamper with).

---

## 7. UX flow (states incl. empty / error)

**App page, Follow slot** (`{% app_follow app %}`):
- anonymous → "Sign in to follow" link; page otherwise fully rendered (AC2).
- signed-in not-following → **Follow** button.
- signed-in following → **Unfollow** button (AC1/AC3 reflected).
- degraded (selector error) → no control; page intact (fail-soft).

**Followed-apps feed** (`subscriptions:feed`):
- has follows → notices region (or "No news yet") + list of followed apps, each linking to its
  page.
- no follows → "You're not following any apps yet" + a browse pointer (AC4 empty state).
- a followed app later withdrawn → silently absent from the list (D-6 accepted-only); never an
  error.

**Follow action result:** PRG back to the app page → the slot now shows Unfollow. On capture
failure → an error message ("Couldn't complete that — please try again") and the slot still
shows **Follow** (honest: nothing was stored — AC7).

---

## 8. Security + OQ-3 resolution (unfollow corpus representation)

- **Authn/authz:** all three routes `login_required`; `record_subscribe` always uses
  `request.user` (capture never accepts an arbitrary actor). Anonymous follow attempts redirect
  to sign-in (AC2).
- **IDOR:** none possible — no subscription id in any URL (§6.4).
- **Privacy / least data:** the store holds only `(user, app_id, created_at)` — no PII beyond
  the user FK. Follow state is private to the user (no public counts/social graph — out of
  scope, R4). Deletion removes it (§4.2).
- **Injection / trust boundary:** `app_id` is a typed `uuid` URL kwarg; the app is validated
  via D-6 before any write. No free text is stored.
- **Attributability:** every follow is one `subscribe` corpus event keyed to the actor (until
  SC-10 anonymization).

### OQ-3 — Does *unfollow* need a D-7 corpus representation? **Resolved: NO (at MVP).**
D-7 reserves a `subscribe` kind but **no `unfollow` kind**; adding one is a global-contract
change. We do **not** add it, because:
1. **The current relationship is already the source of truth** — the mutable store *is* the
   present state; "is the user following X now?" is answered there.
2. **Unfollow is an *absence*, and D-7 already models absences by read-time derivation, not a
   stored row** (return-to-platform / "did-not-return" is derived, never an event — D-7). A
   stored "unfollow event" would invent the same representation D-7 deliberately avoids.
3. **No consumer needs it yet.** M6 (unfollow rate) is read from the `SUBSCRIPTION_UNFOLLOWED`
   metric over a window; no Quality-Score input consumes unfollow-as-corpus. Building it now
   is speculative abstraction (CLAUDE.md §5.5).
4. **It stays additive if ever needed.** D-7 is additive-only by design — a future churn
   consumer can add an `unfollow` `EventKind` + recorder without touching this feature. Flagged
   as a revisit (§15), not built.

---

## 9. Failure modes (per component — detect → respond, never silent)

| Component | Failure | Detection | Response |
|---|---|---|---|
| `services.follow_app` — store write | DB error on `get_or_create` | exception | inside `atomic()` → full rollback; propagates; view shows error (AC7) |
| `services.follow_app` — corpus emit | `record_subscribe` raises (app gone, DB) | exception | `capture._guard` counts `CAPTURE_ERROR{kind=subscribe}`; outer `atomic()` rolls back the follow row too → **no orphan state**; view surfaces failure (AC5/AC7) |
| `services.follow_app` — partial-commit risk | crash between row + event | one transaction | impossible — both in one `atomic()`; on crash, neither commits |
| `services.unfollow_app` | DB error | exception | propagates; idempotent retry is safe (delete-by-filter) |
| `selectors.followed_apps` — bulk catalog read | catalog/DB slow or error | exception in the view | the **feed view** wraps the read fail-soft: render the empty/degraded feed + count `SUBSCRIPTION_FEED_DEGRADED`; never a 500 (AC4 "never an error") |
| `notices.notices_for_apps` | producer (future) slow/error | exception at the seam | the feed wraps it fail-soft → "No news yet" + `SUBSCRIPTION_NOTICE_DEGRADED`; today it can only return `[]` (AC8) |
| `{% app_follow app %}` inclusion tag | `is_following` error | exception | fail-soft: degraded slot (no control) + `SUBSCRIPTION_CONTROL_DEGRADED`; app page never 500s (preserves app-pages AC5) |
| account deletion | — | — | CASCADE removes follow rows; signals SC-10 anonymizes events — both automatic, no code here |

**The split rule:** the *write* fails **loud** (correctness — a follow must be real or look
failed); *display* fails **soft** (availability — the page/feed must survive a subscriptions
fault). This mirrors ratings (loud gate read → not-eligible; soft display).

### 9.4 Operations — metric → signal → alert (brief M1–M6)
| Metric constant | Brief metric | Alert? |
|---|---|---|
| `SUBSCRIPTION_FOLLOWED` | M1 adoption, M2 depth | no (trend) |
| `SUBSCRIPTION_UNFOLLOWED` | M6 unfollow rate | no (trend; high churn = product signal) |
| `SUBSCRIPTION_FOLLOW_NOOP` | idempotency health | no |
| `signals.CAPTURE_ERROR{kind=subscribe}` | M5 capture integrity | **yes — the one actionable alert** (corpus incomplete / write path unhealthy) |
| `SUBSCRIPTION_FEED_DEGRADED` / `_NOTICE_DEGRADED` / `_CONTROL_DEGRADED` | display health | page-error alert if sustained |

M3 (follow-driven return @3d/@14d) and M4 (feed→re-engagement) are **derived by analysts** from
the D-7 corpus (`signals.selectors.*`) joined to the follow store — **not computed here** (no
scoring in this layer). Expected thin until adoption grows + `developer-updates` ships (R1) —
visible, not hidden.

---

## 10. Non-functional handling
- **Performance:** writes are O(1) (one upsert + one insert); the feed is 2 bounded queries
  (the indexed follow read + the bulk catalog read); `is_following` is one indexed EXISTS.
  No N+1 at 100× follows (§3.2). Growth path if a user follows thousands: the existing
  `limit`/page-size becomes cursor pagination — a one-place change in `followed_apps` + the
  template (named, not built).
- **Config (what changes cheaply):** `apps/core/config.py` gains
  `followed_feed_page_size() -> int` (default 100), evaluated by the existing `validate_all()`.
- **Observability:** the metric constants above in `apps/core/observability.py`.
- **Rollback:** §15.

---

## 11. Alternatives considered (≥2 genuinely different; sacrifices named)

- **(A) Derive follow state from the append-only corpus** (no owned table — read the latest
  `subscribe`/`unfollow` events to compute "is following"). **Rejected:** D-7 is append-only,
  raw, and has **no `unfollow` kind**; reconstructing mutable current-state from an event log
  is exactly the complexity AS-4 avoids, forces OQ-3's global change, and couples display to a
  scan. The mutable store is the boring, correct choice (mirrors ratings).
- **(B) Add a D-7 `unfollow` kind now** (OQ-3 = yes). **Rejected:** §8 — speculative, no
  consumer, and D-7 models absences by derivation. Additive later if ever needed.
- **(C) Defer the notice surface entirely** (AS-3 = option B). **Rejected by DN-13** (option A
  chosen) — and a forward-compatible empty seam costs almost nothing while preserving the
  feed's "reason to return" framing.
- **(D) Store follows as a `ManyToMany` on `Account` (or a JSON list).** **Rejected:** not
  independently queryable for M1–M6, no per-follow `created_at` for the return windows, and it
  fights the soft-`App.id`-ref convention (D-6/D-7). A first-class table is the one source of
  truth.
- **(E) Read the whole catalog (`list_catalogued_apps`) and filter in Python** instead of a
  by-ids bulk. **Rejected:** unbounded in catalog size — worse at 100× than the O(follows) it
  replaces. The additive `get_catalogued_apps(ids)` (§4.3) is the right primitive.

**What the chosen design sacrifices:** no first-class record of *when/whether* a user unfollowed
beyond a metric counter (OQ-3 trade — accepted, additively reversible); the `subscribe` event
carries no impression attribution at MVP (§6.1 — additively addable); and it adds one section to
the closed-out app-page template (the sanctioned slot pattern, one-section rollback).

---

## 12. Test strategy (each module isolated; AC-mapped)
- **services** (the contract core): follow creates row + exactly one `subscribe` event;
  idempotent re-follow = no second event; **capture failure rolls back the follow** (assert no
  row persists + `CAPTURE_ERROR` counted — AC5/AC7); unfollow deletes + emits no event;
  unfollow-absent = no-op (AC3); unknown/withdrawn app on follow → `UnknownAppError` (AC1).
- **selectors:** `is_following` true/false/anonymous; `followed_apps` ordering (recency),
  accepted-only filtering of a withdrawn follow, empty list, and **2-query bound** (no N+1).
- **notices:** `notices_for_apps` returns `[]`; the `Notice` shape is stable.
- **views:** anonymous follow → redirect to sign-in, page renders (AC2); PRG on success; 404 on
  unknown app; capture failure → error message + not-followed (AC7); feed empty state (AC4);
  no-IDOR (no id in URL).
- **inclusion tag:** three viewer states render correctly; selector error → degraded, no 500
  (fail-soft).
- **deletion (AC9):** `delete_account` on a user with follows removes the rows (CASCADE) and
  leaves the `subscribe` events anonymized-not-purged (SET_NULL).
- **catalog `get_catalogued_apps`:** accepted-only, ignores unknown ids, no N+1.

Every AC1–AC9 maps to ≥1 test above (the build phase produces the `TEST_PLAN.md` table).

---

## 13. AC → design-element map (exit criterion)

| AC | Design element |
|---|---|
| AC1 follow + idempotent | `services.follow_app` (`get_or_create`, `created` gate) + `Subscription` unique(user,app_id) + `{% app_follow %}` reflects state |
| AC2 anonymous boundary | `login_required` on follow view (→ sign-in) + inclusion tag's anonymous "Sign in to follow"; page render owned by pages |
| AC3 unfollow + idempotent | `services.unfollow_app` (filter.delete, no-op when absent) |
| AC4 feed + empty state | `subscriptions:feed` view + `selectors.followed_apps` (bulk D-6, accepted-only) + feed empty state; fail-soft (never errors) |
| AC5 one subscribe via capture, keyed user×App.id, no score | `follow_app` emits `record_subscribe` iff `created`, in-txn; store has **no score column** (structural) |
| AC6 return/re-engagement via existing seams | feed links → `pages:app-page`; capture by the **existing** `PlatformVisitMiddleware` + pages emission; this feature emits **only** `subscribe` |
| AC7 fail loud | capture `_guard` counts `CAPTURE_ERROR`; outer `atomic()` rollback → no orphan state; view surfaces failure |
| AC8 notice surface forward-compatible | `notices.notices_for_apps` (Notice DTO, returns `[]`) + feed notices region + "No news yet" empty state |
| AC9 deletion removes follow state | `user` FK **CASCADE** (auto on `account.delete()`); events follow SC-10 (signals SET_NULL) — no code here |

Every AC maps to ≥1 element; all interfaces are specified; every component has a documented
failure behavior (§9). **Exit criteria met.**

---

## 14. Self-critique (skeptical senior engineer)

- **"Wrapping the global capture write path in your own transaction violates D-7's single-write-
  path / append-only rule."** No: `record_subscribe` *is* the single write path — we call it, we
  don't bypass it. `capture` already opens its own `transaction.atomic()`; nesting it in ours
  makes it a savepoint. Append-only forbids mutating/deleting *committed* events; rolling back an
  *uncommitted* event in the same transaction (because its sibling write failed) is not a
  violation — it is the only way to keep the follow and its event consistent (M5 by construction).
  This is the right coupling; documented in §6.1 so the build doesn't "fix" it into two
  transactions.
- **"What if capture succeeds but the outer commit fails?"** Then both roll back together — there
  is no window where the event commits without the follow. One transaction, one fate.
- **"The feed N+1."** Closed by the additive bulk `get_catalogued_apps` (§4.3) + the page-size
  cap; asserted by a query-count test (§12).
- **"An empty notice seam is dead code."** It is required scope (DN-13 = option A) and is the
  minimum honest surface — a single repointable function, no speculative provider machinery.
- **"Touching the closed-out app-page template is risky."** It is the *sanctioned* slot pattern
  (ratings did the same for AP-1); one added section, viewer-state-driven so uniformity holds,
  one-section rollback, fail-soft so it can't 500 the page.
- **Simplification pass:** dropped `updated_at`, soft-delete, an `unfollow` corpus kind, impression
  linkage, and any notice producer/registry — each tied to no current requirement. What remains
  is one table, two write functions, two read functions, one empty seam, three thin views, one
  inclusion tag, one template, one additive catalog read.

---

## 15. Rollout, first version, and revisit flags

**Tech stack:** unchanged — Django + DRF + PostgreSQL, `apps/` root (D-4). **No new global
decision.** Reuses D-3/D-6/D-7 as-is. The two surface touches (additive `get_catalogued_apps`;
the CASCADE-deletion posture) are **feature-local** ([DECISIONS.md](DECISIONS.md)), not ADRs.

**Smallest useful first version (one increment):** the whole MVP is small enough to ship as one
feature — store + write path + read path + feed + follow control + notice empty seam. There is no
half-feature worth shipping (a follow with no feed gives no return reason; a feed with no follow
has nothing to list).

**Rollout (additive, no flag — mirrors ratings/pages):**
1. `subscriptions/0001` creates `subscriptions_subscription` (additive; reversible up→down→up —
   rehearsed at release on a throwaway DB).
2. `catalog` gains `get_catalogued_apps` (pure additive read — no migration).
3. The **activation switch** is the `config/urls.py` include `path("subscriptions/", …)` + the
   one `{% app_follow app %}` section in `app_page.html`. **"Off" = remove the include + the
   section** (zero data migration; the table can be dropped separately by reversing `0001`).
   Backward-compatible: with the feature off, the app page renders exactly as today.

**Revisit once real usage exists (flagged, not built):**
- **OQ-3 / `unfollow` corpus kind** — add a D-7 `EventKind` + recorder *if* a churn consumer
  ever needs unfollow-as-corpus (§8). Additive.
- **Impression linkage on `subscribe`** — pass the originating `imp` so follows attribute to a
  shown instance (§6.1). Additive.
- **Feed pagination** — cursor pagination if follows-per-user grows large (§10).
- **Notice producer** — repoint `notices.notices_for_apps` to `developer-updates` when it ships
  (§6.3). One-place change, no feed rework.
