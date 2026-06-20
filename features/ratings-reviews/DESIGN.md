# DESIGN — ratings-reviews

*Stage 2 artifact (Software Architect). Status: **AWAITING APPROVAL** (DN-12). Inputs:
the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md), the codebase, [CODEMAP.md](../../CODEMAP.md),
and the global contracts [D-3](../../DECISIONS.md)/[D-4](../../DECISIONS.md)/[D-5](../../DECISIONS.md)/[D-6](../../DECISIONS.md)/[D-7](../../DECISIONS.md).
Produced via the 14-step protocol ([phase-2-architect.md](../../process/personas/phase-2-architect.md)).*

> **What this feature is, in one line:** a new Django app `apps/ratings/` with **its own
> mutable store** for one rating (+ optional review) per user per app, that **records the
> curated-rating gate as data** — reading [D-7](../../DECISIONS.md) impression evidence to
> stamp each rating *weight-eligible or not* — and fills the empty `app-pages` **AP-1**
> reviews slot. It computes **no** score (RR-1). The only schema touch outside its own app
> is one **additive, reversible** index on `signals.Impression`.

---

## 1. Protocol summary (steps 1–14)

The reasoning trace; the contracts below are its output. Each step ends with its output.

1. **SCOPE.** *Problem:* there is nowhere to rate/review an accepted app, and the platform's
   §4.1 integrity rule — only organically-curated raters may affect a score — has no
   implementation. *Stakeholders:* signed-in raters, readers (incl. anonymous), developers
   (as readers), the platform integrity premise + the future Quality Score (a downstream
   consumer of the eligibility-tagged corpus). *Out:* any scoring/weighting/averaging,
   anomaly/abuse defence, the curated surface that *makes* a user curated, dev feedback
   inbox, rating prompts/timing, moderation tooling, app-page restyling (brief §6). *Lifespan:*
   **platform** (a permanent capture surface + the gate substrate the score is backtested on
   — H3). Effort matches: rigor on the gate contract and the store, minimalism everywhere else.
   → *Output:* a permanent, capture-only feature; the expensive decision is the gate's data shape.
2. **REQUIREMENTS.** *Functional:* AC1–AC9 (brief §4). *Non-functional:* server-rendered over
   D-4 sessions; gate determination present on **100%** of stored ratings (AC5); **zero**
   score/weight/rank computed or stored (AC6); reads the catalog only via D-6 and impression
   evidence only via the D-7 read surface; one active rating per user×app; the page must still
   render anonymously (AC3/AP-1). *Assumptions resolved here:* A1 (scale 1–N + optional text →
   §4 limits, config), A2 (one-per-user → unique constraint), A5/OQ-4 (own store + freeze-vs-
   derive → §4/§6). A4 (curated = DIGEST impression) is **verified** (DN-11). → *Output:* the
   requirement ledger below (§13 maps each AC to a design element).
3. **CONTEXT.** Reuse, do not rebuild: `catalog.selectors.get_catalogued_app` (D-6 accepted-only),
   `signals` impression corpus + its read surface (D-7), `accounts` auth + `login_required` +
   `LOGIN_URL=/auth/signin`, `apps/pages` (the uniform page + the AP-1 slot it left fillable),
   `apps/core` (config, observability, request-context logging). No new stack (D-4). →
   *Output:* this feature is a thin new app over existing contracts; §3 current-state.
4. **MODULES.** `models` (the store) · `gate` (the eligibility determination + the curated-
   surface definition) · `services` (the one write path) · `selectors` (the one display read
   path) · `views` + `urls` (thin HTTP) · `templatetags` + one partial (the AP-1 slot fill) ·
   `admin` (read surface). Cross-cutting concerns reused from `apps/core` (config, metrics,
   logging) — defined once, not duplicated. → *Output:* §3 component table.
5. **INTERFACES.** Defined before internals in §5 (service, gate, selector, signals-selector,
   view, template-tag contracts) — inputs, outputs, errors, invariants. → *Output:* §5.
6. **DATA & STATE.** One `Rating` row per (user, app_id); **mutable** (editable/removable —
   unlike append-only signals, because a rating is editable user opinion); the eligibility
   determination is **frozen on the row** (AC5) yet **re-derivable** from retained inputs (R1).
   → *Output:* §4.
7. **FAILURE.** Catalog read = **loud** (the rating has no subject without it); gate (signals)
   read = **fail-closed to not-eligible + loud metric** (never silently grant weight, never
   block the rating); display selector = **fail-soft degraded slot** (never 500 the page).
   → *Output:* §8.
8. **CHANGE.** Likely-to-change → config: scale max, review length, display limit, **the
   curated-surface set** (`gate.CURATED_SURFACES`, the one place the gate definition lives).
   Irreversible → the published `Rating` shape + the D-8 gate semantic (justified §9/§11).
   No speculative abstraction (one `Rating`, one write path, one read path). → *Output:* §10.
9. **TRADE-OFFS.** ≥2 alternatives per major axis (store, eligibility freeze, gate-predicate
   location, slot fill, global promotion) in §11. → *Output:* §11.
10. **SECURITY.** Auth-required writes, own-rating-only (no rating id in any URL → no IDOR),
    boundary validation, Django autoescape (XSS), CSRF on forms, server-validated app ref.
    → *Output:* §7.
11. **OPERATIONS.** Metrics (gate split, rejections, gate-unverified), request-context logs,
    two-line rollback, one actionable alert. → *Output:* §8.4/§12.
12. **TESTS.** Each module isolated; §13 maps every AC to a verification. → *Output:* §13.
13. **SELF-CRITIQUE.** §14 — attacked the freeze decision, the signals coupling, the slot edit,
    and the "summary" vs AC6, and ran a simplification pass.
14. **DELIVER.** Decisions + rejected alternatives in §11; smallest-useful-first in §12; the
    proposed global **D-8** + feature-local **RR-4/RR-5**; OQ-2/3/4 resolved (§15).

---

## 2. Real problem & success criteria

Fill the AP-1 reviews slot **and** make the §4.1 curated-rating gate real — by **recording,
for every rating, whether its author was organically curated to that app** (a DIGEST
impression), so a bought/farmed rating can never silently count, while keeping the platform
openly participatory (outside ratings displayed, unweighted). Success = AC1–AC9 met, the §5
metrics observable, no score computed, and the eligibility-tagged corpus that H3/the Quality
Score consume exists from the first rating.

---

## 3. Current-state summary

| Existing component | What it gives this feature | How used |
|---|---|---|
| `catalog.selectors.get_catalogued_app(id)` (D-6) | accepted-app validity + content, by `App.id` | write boundary (AC9) + the page that hosts the slot |
| `apps/signals` impression corpus + `signals.selectors` (D-7) | the DIGEST-impression evidence the gate reads | the gate predicate (new factual selector, §5d) |
| `apps/pages` — `pages:app-page` view + `app_page.html` slot 6 | the uniform public page + the **empty AP-1 reviews slot** | the slot the inclusion tag fills (§6) |
| `accounts` — `login_required`, `LOGIN_URL=/auth/signin`, `Account` (D-3) | the authenticated rater + sign-in redirect | view auth (AC3); `Rating.user` FK |
| `apps/core` — `config`, `observability.increment` + constants, request-context middleware | tunables, metrics, contextual logs | scale/length/limit config; the §5 gate-split + rejection metrics |

Nothing is removed or restructured. The only edits outside `apps/ratings/` are: **one slot's
content** in `app_page.html`, **one URLconf include** in `config/urls.py`, a handful of
**config tunables + metric constants** in `apps/core`, and **one additive index** on
`signals.Impression` (§4.3).

---

## 4. Data design

### 4.1 The store — `apps/ratings/models.py`

One feature-owned table (A5 — distinct from the D-7 behavioral tables; a rating is *explicit,
mutable* opinion, not an append-only behavioral fact).

```python
class EligibilityBasis(models.TextChoices):
    # WHY a rating got its determination — the recorded reason (R1 auditability, §5 metric).
    CURATED_DIGEST_IMPRESSION = "curated_digest_impression", "curated — DIGEST impression"
    NO_CURATED_IMPRESSION     = "no_curated_impression",     "not curated — no qualifying impression"
    CURATION_UNVERIFIED       = "curation_unverified",       "curation unverified (gate read failed)"

class Rating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # SET_NULL = anonymize-on-deletion, mirroring signals SC-10/D-7: the eligibility-tagged
    # corpus the score is backtested on survives a deleted account, unlinked from the person.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, related_name="ratings")
    app_id = models.UUIDField()                       # SOFT D-6 ref; validated at write (AC9)
    score = models.PositiveSmallIntegerField()        # 1..rating_scale_max(); validated at boundary
    review_text = models.TextField(blank=True, default="")   # optional (A1)
    # --- the curated-rating gate, RECORDED not computed (AC5/RR-1) ---
    weight_eligible = models.BooleanField()           # THE gate determination (queryable; never null)
    eligibility_basis = models.CharField(max_length=32, choices=EligibilityBasis.choices)
    eligibility_determined_at = models.DateTimeField()  # as-of instant the determination used
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ratings_rating"
        constraints = [
            models.UniqueConstraint(fields=["user", "app_id"],
                                    name="ratings_one_active_per_user_app"),   # AC8
        ]
        indexes = [models.Index(fields=["app_id", "created_at"],
                                name="ratings_app_created_idx")]                # display read
```

**Invariants (enforced by the one write path, §5a):**
- `1 ≤ score ≤ rating_scale_max()`; `len(review_text) ≤ review_text_max_length()`.
- `weight_eligible == (eligibility_basis == CURATED_DIGEST_IMPRESSION)` — set together from one
  computation, so they cannot drift (one source of truth; the boolean is the SQL-queryable AC5
  field, the basis is its recorded reason).
- Exactly **one** row per living `(user, app_id)` (the unique constraint; deleted-user rows go
  `user=NULL`, which Postgres treats as distinct, so they never collide — AC8 holds for the living).
- **No score/weight/rank/average column exists** → AC6 is *structural*, not a convention.
  `weight_eligible` is an *eligibility boolean*, not a quality value.

### 4.2 Lifecycle

| Event | Effect |
|---|---|
| **Create** (first submit) | one row; `score`/`review_text` set; eligibility determined as-of `now` (§5b). |
| **Edit** (re-submit) | same row updated in place (`update_or_create` on user+app_id); eligibility **re-determined as-of the edit instant** (AC8 — the user may have become curated since). |
| **Remove** | the row is **hard-deleted** (design-for-deletion; AC8 "retracted from display"). The eligibility-corpus concern (brief §1) is about *stored* ratings carrying a determination, not about retaining user-retracted ones. |
| **Account deletion** | `user` → NULL (anonymize-retain, SC-10 posture): rating + eligibility survive for H3, unlinked. Review text is retained as "by a former user" (mirrors signals retain-anonymized); a stronger purge-the-text posture is a one-line deletion-hook addition — **noted, not built** (no PII-collection column; deferred with the integrity/privacy hardening, OQ-3). |

The store is **mutable** by design — the deliberate contrast with the append-only signals
corpus (D-7). A rating is the user's current opinion; signals are immutable behavioral history.

### 4.3 Migrations (order)

1. `ratings/0001_initial` — create `ratings_rating`.
2. `signals/0003_impression_user_app_idx` — **additive, reversible** `Index(["user_id","app_id"],
   name="signals_imp_user_app_idx")` on `Impression`, to index the new per-user-per-app
   existence query (§5d). Mirrors the app-pages precedent of touching `signals` additively; the
   index-only change applies and reverses cleanly (rehearsed at release).

No data migration, no backfill. Rollback drops both (`migrate ratings zero`, `migrate signals 0002`).

---

## 5. Interface contracts (defined before internals)

### 5a. Write path — `apps/ratings/services.py` (the single mutate surface)

```python
def submit_rating(user, app_id: UUID, *, score: int, review_text: str = "") -> Rating
    # 1. app = catalog.get_catalogued_app(app_id); if None -> raise UnknownAppError      (AC9)
    # 2. _validate(score, review_text); on failure -> raise RatingValidationError, NOTHING stored (AC2)
    # 3. determination = gate.determine_eligibility(user, app_id, as_of=now)             (AC5/AC7)
    # 4. atomic update_or_create on (user, app_id) writing score/text/eligibility fields (AC1/AC8)
    # 5. increment RATING_SUBMITTED|RATING_UPDATED with tags {weight_eligible, basis}    (§5 metric)
    # returns the stored Rating

def remove_rating(user, app_id: UUID) -> bool
    # delete the caller's row for this app; returns whether one existed. increment RATING_REMOVED. (AC8)
```

- **Errors:** `UnknownAppError` (app not accepted/unknown → view 404s, AC9); `RatingValidationError`
  (bad score/over-length text → view re-shows the page with the error, AC2). Both raised **before**
  any write; the write is atomic (no partial state).
- **Invariant:** the only place `Rating` rows are created/updated/deleted. Every write stamps a
  non-null `weight_eligible` + `basis` (AC5 — 100% present is guaranteed by the code path, and
  the columns are `NOT NULL`).

### 5b. Gate — `apps/ratings/gate.py` (the eligibility determination + the gate definition)

```python
CURATED_SURFACES: frozenset[str] = frozenset({Surface.DIGEST})   # THE gate definition (D-8).
                                                                 # APP_PAGE / open views excluded (§4.1).

@dataclass(frozen=True)
class EligibilityDetermination:
    weight_eligible: bool
    basis: EligibilityBasis
    determined_at: datetime

def determine_eligibility(user, app_id: UUID, *, as_of: datetime) -> EligibilityDetermination:
    # weight-eligible IFF the user has an impression of this app on a CURATED_SURFACES surface
    # at/before `as_of` (a DIGEST impression). Reads ONLY via signals.selectors (D-7), §5d.
    # signals read raises -> fail CLOSED: not-eligible, basis=CURATION_UNVERIFIED, loud metric
    #   RATING_GATE_UNVERIFIED (never silently grant weight; never block the rating).
```

- **One source of truth for "what counts as curation":** `CURATED_SURFACES`. Changing the gate
  (e.g. adding an editorial-assignment surface) is **one line here** (D-8 / §10).
- **Re-derivable (R1):** every input (the rater, the app, the rating timestamp) is retained and
  the signals corpus is append-only, so a historical determination can be recomputed if the gate
  definition changes or a `DIGEST` emitter ships. A `recompute_eligibility(app_id|all)`
  management path is the documented growth lever — **noted, not built** (no consumer needs it yet).

### 5c. Display read path — `apps/ratings/selectors.py`

```python
@dataclass(frozen=True)
class ReviewRow:        # one displayed review — no eligibility field (eligibility is internal, not public)
    score: int; review_text: str; author_display: str; created_at: datetime

@dataclass(frozen=True)
class AppReviews:
    app_id: UUID
    total_count: int
    distribution: dict[int, int]    # raw count per score value — DESCRIPTIVE, not an average (AC6)
    reviews: list[ReviewRow]        # most-recent first, capped at reviews_display_limit()

def reviews_for_app(app_id: UUID, *, limit: int) -> AppReviews   # 2 queries: grouped counts + capped list
def user_rating(user, app_id: UUID) -> Rating | None             # the viewer's own row, to prefill the form
```

- **No average / no quality number** is produced (AC6). The "rating summary" (AC4) is the
  **count + the raw score distribution** — the underlying data displayed, never a computed score.
  Showing a naive public average is exactly the gameable number the gate exists to neutralize, so
  it is deliberately absent (vision §3.2).
- All ratings are displayed regardless of `weight_eligible` (AC7 — openly participatory). The
  eligibility flag is internal substrate for the future score, **not** a public badge.

### 5d. New factual selector on `signals` — `signals.selectors.has_impression` (additive D-7 read surface)

```python
def has_impression(user_id, app_id: UUID, *, surfaces: Iterable[str],
                   as_of: datetime | None = None) -> bool:
    """Does this user have an impression of this app on one of `surfaces`, at/before `as_of`?
    Raw existence — no scoring, no judgement (D-7 raw-only). Indexed by signals_imp_user_app_idx."""
    qs = Impression.objects.filter(user_id=user_id, app_id=app_id, surface__in=list(surfaces))
    if as_of is not None:
        qs = qs.filter(occurred_at__lte=as_of)
    return qs.exists()
```

- **Why it belongs in `signals`, not in `ratings`:** D-7 mandates that nothing reads `signals_*`
  directly past the selector surface. This is the missing per-user existence read; it is **purely
  factual** (an `EXISTS`), so it fits the signals "raw, never scored" mandate. The **judgement**
  ("a DIGEST impression *is* curation") stays in `ratings.gate.CURATED_SURFACES` — signals stays
  neutral. This is an **additive** extension of the D-7 read surface (additive-only by contract),
  **not** a new global ADR for the schema.

### 5e. HTTP views — `apps/ratings/views.py` + `urls.py`

| Route (`app_name="ratings"`) | Method | Auth | Behaviour |
|---|---|---|---|
| `ratings:submit` → `apps/<uuid:app_id>/rating` | POST | `login_required` | parse `score`,`review_text` → `services.submit_rating` → **PRG redirect** to `pages:app-page`; `RatingValidationError` → message + redirect (AC2), `UnknownAppError` → 404 (AC9). Anonymous → redirect to `/auth/signin?next=…` (AC3). |
| `ratings:remove` → `apps/<uuid:app_id>/rating/remove` | POST | `login_required` | `services.remove_rating` → redirect to `pages:app-page` (AC8). |

Mounted under its **own prefix** `path("ratings/", include("apps.ratings.urls"))` (no collision/
fall-through ambiguity with the pages `apps/` include — the boring, unambiguous choice). The
view holds no business logic and no ORM access (mirrors the pages/catalog house pattern): parse →
call service → redirect. Own-rating-only is structural — the URL carries **no rating id**; the
row is keyed by `request.user` + `app_id`, so a user can never address another's rating (no IDOR).

### 5f. The AP-1 slot fill — `apps/ratings/templatetags/ratings_tags.py` + `templates/ratings/_reviews_slot.html`

```python
@register.inclusion_tag("ratings/_reviews_slot.html", takes_context=True)
def app_reviews(context, app):
    # fail-SOFT: any selector error -> degraded slot + RATING_DISPLAY_DEGRADED metric, never raises
    # into the page render (preserves app-pages AC5 / AP-1: the page renders even if reviews degrade).
    # returns {request, app, reviews: AppReviews, own_rating, scale_max} for the partial.
```

The partial renders, inside the **unchanged** `<section aria-label="Reviews">` slot:
- the **summary** (total count + score distribution) and the **reviews list** (or the AC4 **empty
  state** when count = 0) — for everyone, anonymous included;
- for an **authenticated** viewer: the rating form (prefilled with `own_rating` if present) +
  a remove button when they already have one;
- for an **anonymous** viewer: a "Sign in to rate" link to `accounts:signin?next=<this page>`
  (AC3) — the page itself still renders fully (AP-1 preserved).

### 5g. The one edit to `app-pages` (sanctioned AP-1 slot fill)

`apps/pages/templates/pages/app_page.html` slot 6 changes **content only** — the section, its
`aria-label`, its heading, and its position are unchanged, so page uniformity (AC3/AP-1) holds:

```django
{# 6. Reviews — the AP-1 slot, filled by the ratings-reviews feature (its inclusion tag). #}
<section aria-label="Reviews">
  <h2>Reviews</h2>
  {% app_reviews app %}          {# was: <p>Reviews coming soon.</p> #}
</section>
```

(`{% load ratings_tags %}` is added once near the top of the template.) This is the exact
"adding reviews later is not a uniformity-breaking change" extension app-pages designed the slot
for; it is **in scope** by the brief ("Displaying reviews … in the existing app-pages reviews
slot (AP-1)"). Rollback = restore the one `<p>` line.

---

## 6. UX flow & states

Single surface: the existing app page (`pages:app-page`). The reviews slot now shows:

| State | Render |
|---|---|
| **Anonymous, any app** | summary + reviews list (read-only) + "Sign in to rate" link. Page renders fully (AC3). |
| **Signed-in, not yet rated** | summary + list + the rating form (score 1–N + optional review). |
| **Signed-in, already rated** | as above, form **prefilled** with their rating + a Remove button (AC8). |
| **0 reviews** | the defined empty state ("No reviews yet — be the first") + (if signed-in) the form (AC4). |
| **Submit invalid** (out-of-range / over-length) | PRG back to the page with a clear inline error; nothing stored (AC2). |
| **Reviews read degraded** (selector error) | "Reviews are temporarily unavailable" in the slot; the rest of the page is unaffected (§8). |

No new top-level page, no SPA. Errors surface via the Django messages framework (PRG pattern).

---

## 7. Security model

- **AuthN/AuthZ:** writes require authentication (`login_required` → `/auth/signin`); any signed-in
  account may rate (RR-3 — base USER role; no special role). Reads are public (AP-1).
- **No IDOR / own-data-only:** no rating id in any URL; the row is addressed by `request.user` +
  `app_id`, so a user can only ever create/edit/remove *their own* rating.
- **Input validation at the boundary:** `score` integer-and-range-checked, `review_text`
  length-checked, in `services` before any write (AC2). The `app_id` is a UUID path converter,
  then server-validated via `get_catalogued_app` (never trusts the client for app validity, AC9).
- **XSS:** `review_text` is rendered through Django's auto-escaping (no `|safe`, no raw HTML).
- **CSRF:** the submit/remove forms are POST with `{% csrf_token %}` (Django middleware).
- **PII:** the only personal datum is the `Account` link (D-3) + whatever a user types into
  `review_text`. Deletion = SET_NULL anonymize (§4.2). No IP/UA/device column (mirrors the
  signals privacy whitelist).
- **Abuse (R4):** authenticated-only + one-per-user (structural volume cap: a user cannot pile
  many ratings on one app) + the gate (outside brigades land **unweighted**). Full anomaly/graph
  defence is explicitly **OUT** (OQ-3, later integrity system); request rate-limiting is available
  (`apps/core/ratelimit`) but unnecessary at MVP given the structural one-per-user cap — noted, not wired.

---

## 8. Failure modes (per component)

| Component | Dependency / fault | Detection | Response |
|---|---|---|---|
| `services.submit_rating` — catalog read | `get_catalogued_app` raises (DB down) | exception | **Loud** — propagates (a rating has no subject without it); request 500s, like the pages "catalog = loud" rule. A *None* (not accepted/unknown) is the AC9 `UnknownAppError` → 404. |
| `gate.determine_eligibility` — signals read | `has_impression` raises | try/except in `gate` | **Fail closed**: `weight_eligible=False`, `basis=CURATION_UNVERIFIED`, increment `RATING_GATE_UNVERIFIED` + log; the rating **still stores** (AC5 holds — a determination is present), integrity-safe (never grants weight it could not verify), re-derivable later. |
| `services` — DB write | write error mid-transaction | `transaction.atomic` | rollback; nothing partial; error propagates loud. |
| `selectors` via the `app_reviews` tag — display read | selector raises | try/except in the tag | **Fail soft**: degraded slot + `RATING_DISPLAY_DEGRADED`; the page still renders (preserves AP-1/AC5). |
| `views` — anonymous POST | unauthenticated write attempt | `login_required` | redirect to sign-in (AC3); never a partial write. |
| validation — bad input | out-of-range / over-length / missing | `_validate` at boundary | `RatingValidationError` → clear error, nothing stored (AC2); `RATING_REJECTED` metric. |

Principle applied throughout: **the gate never fails silently** (closed + counted), **the page
never fails because reviews degraded** (soft), **a bad write never half-commits** (atomic + loud).

### 8.4 Observability (new `apps/core/observability` constants)

- `RATING_SUBMITTED` / `RATING_UPDATED` — tagged `{weight_eligible, basis}` → **this is the §5
  gate-split metric** (share eligible vs not — expected ~all not-eligible at MVP, R3).
- `RATING_REMOVED`, `RATING_REJECTED` (the AC2 boundary-rejection rate), `RATING_GATE_UNVERIFIED`
  (gate read failed — **the one actionable alert**: a spike means the signals read is degraded),
  `RATING_DISPLAY_DEGRADED`.
- Logs carry app_id + the request-context account UUID (existing `RequestContextMiddleware`).

---

## 9. Non-functional handling

- **Performance:** submit ≈ 4 small indexed queries (catalog read, gate `EXISTS`, `update_or_create`);
  slot render ≈ 3 (grouped counts, capped reviews list, own rating). The reviews list is **bounded**
  by `reviews_display_limit()` so render stays O(limit) at 100× data (no unbounded slot). The gate
  `EXISTS` is backed by `signals_imp_user_app_idx`. Targets: submit p95 < 200 ms; slot adds < 50 ms
  to page render.
- **Scale (§5.2):** bounded display + indexed reads + config-driven limits; the documented growth
  levers (a cached review projection; a materialized eligibility recompute job) are *named, not built*.
- **Security/observability/rollback:** §7, §8.4, §12.

---

## 10. What changes cheaply vs irreversibly (step 8)

| Likely to change | Made cheap by |
|---|---|
| rating scale max | `config.rating_scale_max()` (default 5) |
| review length cap | `config.review_text_max_length()` (default 4000) |
| reviews shown in the slot | `config.reviews_display_limit()` (default 20) |
| **the gate definition** (which surfaces = curation) | `gate.CURATED_SURFACES` — one line; the single source of the §4.1 rule |

| Irreversible / high-rigor | Justification |
|---|---|
| the published `Rating` shape + `services`/`selectors`/`gate` surface | the future Quality Score + `developer-dashboard` read it; additive-only by design (a new field, never a change) |
| the **D-8 gate semantic** (curated = DIGEST impression) | cross-feature integrity; §11 + the proposed ADR carry the rationale |

No speculative abstraction: one `Rating`, one write path, one read path, one gate predicate.

---

## 11. Alternatives considered (rejected)

1. **Store ratings as a new `signals` `EngagementEvent` kind** (vs a feature-owned `Rating` table).
   Rejected: a rating is *explicit, mutable, one-per-user*, and carries a score + free text +
   eligibility — none of which fit the signals schema's *append-only, raw-behavioral, no-score-
   column* invariants (D-7). Folding it in would violate D-7's no-score rule and its append-only
   contract. The own store (A5) is the faithful choice; the two stores stay cleanly separated.
2. **Derive eligibility at read only** (vs freeze it on the row). Rejected: **AC5 mandates** the
   determination be *stored and present on 100% of ratings, queryable later* — a derive-only model
   leaves it absent until something asks. Freezing satisfies AC5; re-derivability (inputs retained +
   append-only corpus) preserves the R1 "correctable" property, so freezing costs nothing derive-
   only would have given. (Resolves OQ-4 → **freeze + re-derivable**.)
3. **Put the "DIGEST = curation" judgement inside `signals`** (vs a factual `has_impression` selector
   + the judgement in `ratings.gate`). Rejected: signals is the **neutral raw store** ("never
   scored"); encoding a curation judgement there leaks integrity semantics into the wrong layer.
   The selector stays a pure `EXISTS`; the judgement lives in `gate.CURATED_SURFACES`.
4. **Have the pages view fetch ratings data and pass it to the template** (vs an inclusion tag).
   Rejected: it couples the closed-out pages *view* to this feature's data shape. The inclusion
   tag confines the integration to **one template line** in the slot pages already designed to be
   fillable; pages stays ignorant of ratings internals.
5. **Keep the gate definition feature-local** (vs promote to a global ADR). Rejected →
   **promote (proposed D-8)**: "curated = an organic-curation-surface impression; an open page view
   never counts" is a cross-feature integrity rule — `editorial-curation-tools` (must *produce*
   such impressions), `developer-dashboard` ("reach = curated users"), and the Quality Score
   consumer all must agree on it; per the [DECISIONS.md](../../DECISIONS.md) rule of thumb, "a later
   feature would be wrong to contradict it" ⇒ global. The implementation stays minimal (one selector
   + one constant); the ADR records the *semantic*, not new abstraction.

**What the chosen design sacrifices:** no public quality/average number on the page at MVP (by
design — the score is downstream); a deleted account's review text is retained-anonymized rather
than purged (the stronger purge is a noted deferral); the gate is ~always *not-eligible* until a
`DIGEST` emitter ships (R3 — correct, made visible by the gate-split metric).

---

## 12. Rollout strategy

- **Additive, no feature flag** (mirrors app-pages): "off" = don't include `apps.ratings.urls` and
  keep the slot's "coming soon" line. Activation = the URLconf include + the one slot edit.
- **Migration order:** `ratings/0001` then `signals/0003` (both additive, reversible; rehearsed
  up→down→up at release, per the app-pages/signals precedent).
- **Backward compatibility:** no existing contract changes. `signals.selectors.has_impression` and
  `Surface` are untouched-but-extended (additive); `app_page.html` keeps every other slot identical.
- **Rollback (two lines + reversible migrations):** revert the `app_page.html` slot to "coming
  soon", remove the `config/urls` ratings include; if needed, `migrate ratings zero` + `migrate
  signals 0002` drop the table and the index with zero impact on other apps (design-for-deletion —
  ratings owns its own table; the only outside touch is one reversible index).

---

## 13. Acceptance-criteria → design-element map (+ verification)

| AC | Design element(s) | Verification |
|---|---|---|
| **AC1** submit & reflected | `services.submit_rating` (create) + `selectors.reviews_for_app` + the slot partial | signed-in submit on accepted app → row stored keyed user×app_id, appears in the slot |
| **AC2** validation fail-loud, nothing stored | `_validate` at the boundary + atomic write + `RatingValidationError` | out-of-range score / over-length text / unknown app → rejected, DB unchanged, `RATING_REJECTED` |
| **AC3** auth required, page renders anon | `login_required` views + the tag's anon "sign in to rate" branch | anonymous POST → redirect to signin; anonymous GET of the page → full render, no form |
| **AC4** display + empty state | `selectors.reviews_for_app` (count + distribution + list) + the partial's empty state | app with ≥1 review → list + summary; 0 reviews → defined empty state, no broken layout |
| **AC5** gate recorded for 100% | `gate.determine_eligibility` called on every write + `NOT NULL` `weight_eligible`/`basis` | every stored rating has a non-null determination; `CURATION_UNVERIFIED` still counts as present |
| **AC6** no scoring in this layer | no score/rank/weight-quality column; `distribution` is raw counts; no average computed | grep/structural test: zero score/weight/rank fields; the summary is count+distribution only |
| **AC7** outside ratings displayed but marked | gate → `NO_CURATED_IMPRESSION`, `weight_eligible=False`; still in `reviews_for_app` | non-curated rater's rating stored not-eligible **and** shown in the list |
| **AC8** one active, editable, removable | unique `(user, app_id)` + `update_or_create` + `remove_rating` delete | re-submit updates the same row (no dup); remove deletes → gone from display |
| **AC9** accepted apps only | `get_catalogued_app` gate in `services`; the slot only renders for an app the page already resolved | pending/rejected/withdrawn/unknown → rating rejected; no reviews presented |

Every module is testable in isolation: `gate` with a fake `has_impression`; `services` with the real
catalog/gate; `selectors` over fixtures; views via the test client; the tag via render. The
`signals.has_impression` selector gets its own unit tests (surface filter, `as_of` boundary, index use).

---

## 14. Self-critique

- *"Freezing eligibility bakes in a wrong answer when a DIGEST emitter later ships."* — Mitigated:
  the determination is *re-derivable* (inputs retained, corpus append-only) and `basis` records the
  reason; a recompute path is the named lever. AC5 forces storing it regardless. Net: freeze is correct.
- *"Editing a closed-out app's template violates scope."* — It is the brief's explicit in-scope job
  (fill the AP-1 slot), it changes slot *content* only (uniformity preserved), and app-pages designed
  the slot for exactly this. Documented as sanctioned (§5g); rollback is one line.
- *"A public 'rating summary' is scoring (AC6 violation)."* — The summary is **count + raw
  distribution**, the underlying data shown, never a computed average/score. A naive public average is
  deliberately absent (it is the gameable number the gate neutralizes).
- *"Coupling ratings to signals re-introduces direct corpus reads."* — No: the read goes through a new
  `signals.selectors` function (D-7-compliant), factual only; the judgement stays in `ratings.gate`.
- **Simplification pass:** dropped a soft-delete `status` field (hard-delete on remove suffices for
  AC8), dropped a stored impression-evidence pointer (re-derivable from the corpus), dropped request
  rate-limiting (structural one-per-user cap suffices at MVP). Nothing remains that no AC needs.

---

## 15. Decisions & open-question resolutions (this stage)

- **Proposed global ADR — D-8** (the curated-rating gate semantic): see [/DECISIONS.md](../../DECISIONS.md)
  (marked PROPOSED, pending DN-12) — promotes "curated = an organic-curation (DIGEST) impression; an
  open `APP_PAGE` view never counts" to repo-wide, since `editorial-curation-tools`,
  `developer-dashboard`, and the Quality Score consumer share it.
- **Feature-local RR-4** (store + freeze-vs-derive) and **RR-5** (slot-fill via inclusion tag): see
  [DECISIONS.md](DECISIONS.md).
- **OQ-2 resolved** — rating shape: numeric **1..`rating_scale_max()`** (default 5) + **optional**
  `review_text` ≤ `review_text_max_length()` (default 4000); slot shows `reviews_display_limit()`
  (default 20) most-recent.
- **OQ-3 confirmed OUT** — moderation, anomaly/review-bomb detection, reputation/calibration:
  deferred to the later integrity system; this feature ships authenticated-only + one-per-user + the gate.
- **OQ-4 resolved** — own mutable store (`ratings_rating`), distinct from the D-7 append-only tables;
  the eligibility determination is **frozen on the row** (AC5) and **re-derivable** (R1).

---

## 16. Out of scope (unchanged from the brief)

No score/weight/rank/average/calibration/reputation (downstream); no anomaly/abuse/moderation system;
no creation of the curated surface; no dev feedback inbox / reply-to-review; no rating prompts/timing;
no app-page restyling beyond filling the AP-1 slot.
