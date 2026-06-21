# RELEASE_NOTES — ratings-reviews

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway PostgreSQL database
(2026-06-21).* Sources: the verified Stage-4 build, [DESIGN.md §8/§10/§12](DESIGN.md)
(observability + the additive `signals` index + rollout/rollback), [FEATURE_BRIEF.md §5](FEATURE_BRIEF.md)
(success metrics / error conditions), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9 coverage), the
global gate semantic [D-8](../../DECISIONS.md), and the reused contracts [D-3](../../DECISIONS.md)
(identity), [D-4](../../DECISIONS.md) (stack), [D-6](../../DECISIONS.md) (`get_catalogued_app`),
[D-7](../../DECISIONS.md) (`signals` impression evidence). The `app-pages` release
([app-pages/RELEASE_NOTES.md](../app-pages/RELEASE_NOTES.md)) is the precedent this mirrors.

---

## 1. What this release is

The platform's **explicit-signal surface** and the first implementation of its single most
important integrity rule — the **curated-rating gate** (vision §4.1). Any signed-in user can
rate (and optionally review) any **accepted** app from its page; every rating is stored raw
**together with a recorded determination of whether its author was organically curated to that
app** — a [D-7](../../DECISIONS.md) `DIGEST` impression ([D-8](../../DECISIONS.md)). It fills the
empty `app-pages` **AP-1** reviews slot, and it computes **no** score, weight, rank, or average
(AC6 — that is the downstream Quality Score's job, and the gameable number this gate exists to
neutralize).

It ships as a **new Django app, `apps/ratings/`**, owning **one mutable table** `ratings_rating`
(one row per user×app — the deliberate contrast with the append-only D-7 behavioral corpus). The
only schema touch outside its own app is **one additive, reversible index** on `signals.Impression`.
It changes no existing feature's behavior and satisfies all nine acceptance criteria AC1–AC9
(mapping in [TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since there was nowhere to rate an app)

- **New app `apps/ratings/`, owning one mutable table `ratings_rating`** ([DESIGN §4](DESIGN.md))
  — one row per `(user, app_id)`, editable and removable. Columns: `score`, optional
  `review_text`, and the recorded gate — `weight_eligible` (the SQL-queryable boolean),
  `eligibility_basis` (its recorded reason), `eligibility_determined_at` (the as-of instant).
  **There is no score/weight/rank/average column** — AC6 is *structural*, not a convention
  (asserted by a no-scoring-field test). `weight_eligible` and `eligibility_basis` are
  `NOT NULL`, so the gate determination is present on **100%** of stored ratings (AC5) by the
  schema, not by hope. Migration **`ratings/0001_initial`**.
- **The curated-rating gate, recorded not computed** ([DESIGN §5b](DESIGN.md), [D-8](../../DECISIONS.md))
  — `apps/ratings/gate.py` holds `CURATED_SURFACES = frozenset({Surface.DIGEST})`, the **one
  place** the §4.1 definition of "what counts as curation" lives. `determine_eligibility(user,
  app_id, as_of)` is weight-eligible **iff** the user has a `DIGEST` impression of that app at or
  before the rating instant; an open `APP_PAGE` view never counts. The determination is **frozen
  on the row** (AC5) yet **re-derivable** (inputs retained + the corpus is append-only) — so a
  rating recorded *not-eligible* today becomes correctable when a `DIGEST` emitter ships (R3).
- **The single write path** ([DESIGN §5a](DESIGN.md)) — `services.submit_rating` /
  `remove_rating` are the only place `Rating` rows are created/updated/deleted. Every submit
  validates the app via [D-6](../../DECISIONS.md) `get_catalogued_app` (AC9) and the score/text at
  the boundary (AC2) **before** any write, stamps the gate determination, and writes atomically
  via `update_or_create` on `(user, app_id)` — so `weight_eligible`/`basis` can never drift from
  the score, and a re-rate updates the same row (no duplicate, AC8).
- **The single display read** ([DESIGN §5c](DESIGN.md)) — `selectors.reviews_for_app` returns a
  **count + raw score distribution** (the underlying data, **never an average** — AC6) plus a
  bounded, most-recent-first list of reviews; `user_rating` prefills the form. **All** ratings are
  shown regardless of eligibility (AC7 — openly participatory); the eligibility flag is internal
  substrate for the future score, not a public badge. Two queries, no N+1, capped at
  `reviews_display_limit()`.
- **The new factual `signals.selectors.has_impression`** ([DESIGN §5d](DESIGN.md)) — a pure
  `EXISTS` ("does this user have an impression of this app on one of these surfaces, at/before
  `as_of`?"), the missing per-user existence read the gate needs. It is **raw, never scored** — it
  stays D-7-faithful (the *judgement* "a DIGEST impression is curation" lives in `ratings.gate`,
  not in signals). This is an **additive** extension of the D-7 read surface, **not** a new ADR.
- **One additive, reversible index — `signals/0003_impression_user_app_idx`** — `Index(["user_id",
  "app_id"], name="signals_imp_user_app_idx")` on `Impression`, backing the gate's per-user
  existence query. Pure additive DDL (no data change); every existing D-7 reader is unaffected.
- **Thin `login_required` HTTP views** ([DESIGN §5e](DESIGN.md)) — `POST /ratings/apps/<App.id>/rating`
  (`ratings:submit`) and `POST /ratings/apps/<App.id>/rating/remove` (`ratings:remove`), both
  PRG-redirecting back to `pages:app-page`. **No rating id appears in any URL** — the row is keyed
  by `request.user` + `app_id`, so a user can never address another's rating (no IDOR, structural).
  Anonymous POST → redirect to `/auth/signin?next=…` (AC3). Mounted under its own `/ratings/`
  prefix — the unambiguous choice, no fall-through with the pages `apps/` include.
- **The AP-1 slot fill — a fail-soft inclusion tag** ([DESIGN §5f/§5g](DESIGN.md)) — `{% app_reviews
  app %}` renders the summary + reviews list + (for a signed-in viewer) the rating form, all inside
  the **unchanged** `<section aria-label="Reviews">` slot. It is **fail-soft**: any selector error
  degrades only the slot (+ `rating_display_degraded` metric) and **never** breaks the page render
  (preserving `app-pages` AC5 / AP-1). The one edit to the closed-out `app-pages` template is
  **content-only** — slot 6's `<p>Reviews coming soon.</p>` became `{% app_reviews app %}`, plus one
  `{% load ratings_tags %}` line; the six slots, the section, its `aria-label`, and its heading are
  unchanged (a structural test asserts this). This is exactly the extension app-pages designed the
  slot for.
- **Shared-surface touches** — three config tunables (`rating_scale_max` default 5,
  `review_text_max_length` default 4000, `reviews_display_limit` default 20) and six metric
  constants (§7 below) added to `apps/core`; `apps.ratings` added to `INSTALLED_APPS`; the
  `path("ratings/", include("apps.ratings.urls"))` **activation switch** added to `config/urls.py`.
  `apps/accounts`, `apps/catalog`, `apps/signals`, `apps/pages` reused **as-is** (except the one
  additive `has_impression` selector + its index). **No new `.env` key.** No existing behavior changed.

## 3. Who is affected

- **Signed-in users** — can now rate any accepted app (1–`rating_scale_max()`) with an optional
  review, edit it (one active rating per app — re-submitting updates in place), and remove it. The
  rating *action* requires sign-in; the *page* does not.
- **Any visitor (anonymous included)** — sees the reviews list + the rating summary (count + score
  distribution) on every accepted app page, with a defined empty state ("be the first") when there
  are none (AC4). An anonymous viewer gets a "Sign in to rate" link; the page renders fully either
  way (AC3 / AP-1 preserved).
- **The platform / integrity** — from the **first** rating there now exists an eligibility-tagged
  corpus: every rating records whether its author was curated to that app at capture time, so a
  bought/farmed rating can never *silently* count. Outside (non-curated) ratings are accepted and
  displayed, recorded **not-weight-eligible** — never silently dropped, never silently counted (AC7).
- **The future Quality Score + `developer-dashboard`** — these are the downstream consumers of the
  `weight_eligible` corpus and the [D-8](../../DECISIONS.md) gate semantic. This release produces
  the substrate the H3 backtest runs on; it computes nothing on top of it.
- **`editorial-curation-tools` / `weekly-digest`** — these will be the **first emitters of `DIGEST`
  impressions**, which is what flips ratings from *not-eligible* to *eligible*. Until one ships,
  ~all ratings record *not-eligible* (R3 — correct, and visible via the gate-split metric).
- **Support** — no support-facing change at this release (local/dev target).

## 4. How to use it (operators)

The rollout is the ordered, additive steps from [DESIGN.md §12](DESIGN.md) — no new env var, no
feature flag, no recurring job:

1. `python manage.py migrate ratings` — applies `ratings/0001_initial` (creates `ratings_rating`).
2. `python manage.py migrate signals` — applies `signals/0003_impression_user_app_idx` (the
   additive index backing the gate's existence query). **Adopt before you read** — the gate's
   `has_impression` query wants the index in place before live traffic.
3. `python manage.py check` — must report no issues before the surface is considered live.
4. Deploy the build (which includes `apps.ratings` in `INSTALLED_APPS`, the `{% app_reviews %}`
   slot fill in `app_page.html`, and the `path("ratings/", include("apps.ratings.urls"))`
   activation switch in `config/urls.py`). The reviews slot and the rate/remove routes go live on
   deploy.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with `identity-accounts`,
> `interest-taxonomy`, `submission-intake`, `signal-capture`, and `app-pages`
> ([CONTROL.md](../../CONTROL.md)); the platform is still mid-development. The feature is verified
> locally (**486 tests green**, `check` clean, both new migrations apply and reverse cleanly).
> **Production promotion and a live-metrics monitoring window are deferred** until there is a
> production target and real traffic.

This is an **additive new app**: nothing existing changes behavior, so there is **no pre-existing
surface to ramp against and nothing to feature-flag off** (an honest deviation from the
internal→%→full template — DESIGN §12). "Off" = restore the slot's "coming soon" line and drop the
URLconf include. Safety comes from the **two-line activation switch** + **two reversible, additive
migrations**, not a kill switch.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate ratings` + `migrate signals` applied through `0003`; `ratings_rating`, `ratings_one_active_per_user_app`, and `signals_imp_user_app_idx` present; `manage.py check` clean. |
| Surface live | `/ratings/apps/<App.id>/rating` resolves; the reviews slot renders inside `app_page.html` for an accepted app; an anonymous page view still renders fully (AC3). |
| Write path correct | a signed-in submit on an accepted app stores exactly one row keyed user×app with a non-null `weight_eligible`/`basis`; a re-submit updates the same row (no duplicate — AC8); an out-of-range/over-length/unknown-app submit is rejected with nothing stored (`rating_rejected`, AC2). |
| Gate recorded = 100% | every stored rating carries a determination; `rating_submitted`/`rating_updated` are tagged `{weight_eligible, basis}` and observed; `rating_gate_unverified` reads 0. |
| Display correct | the slot shows count + distribution + list (AC4), the empty state at 0, all ratings regardless of eligibility (AC7); `rating_display_degraded` reads 0. |
| Stable at target | the above holds with `rating_gate_unverified` = 0 and no sustained `rating_display_degraded`, through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**Two lines + two reversible migrations** ([DESIGN §12](DESIGN.md)):

1. Restore `app_page.html` slot 6 to `<p>Reviews coming soon.</p>` (and drop the
   `{% load ratings_tags %}` line) — the reviews UI vanishes, the page is unchanged otherwise.
2. Remove the `path("ratings/", include("apps.ratings.urls"))` include from `config/urls.py` — the
   rate/remove routes vanish with **zero data migration**.

If the schema must also be undone (design-for-deletion — `ratings` owns its own table; the only
outside footprint is one additive index):

```bash
python manage.py migrate ratings zero    # drops ratings_rating
python manage.py migrate signals 0002    # drops signals_imp_user_app_idx (reverses 0003)
```

The `signals_imp_user_app_idx` index is inert when unused (pure performance), so there is no
correctness reason to reverse it in a real rollback; it is shown for completeness.

**Rehearsed 2026-06-21** on a throwaway PostgreSQL database (`ratings_release_rehearsal`, dropped
afterward): `migrate` applied `ratings/0001` + `signals/0003` → `ratings_rating`,
`ratings_app_created_idx`, `signals_imp_user_app_idx`, and the `ratings_one_active_per_user_app`
unique constraint all present → `manage.py check` clean; then `migrate signals 0002` + `migrate
ratings zero` **unapplied both cleanly** (table + index confirmed gone, `check` still clean) and a
re-`migrate` **re-applied** both (confirmed reversible up→down→up); `makemigrations --check` reports
no drift. The two `ratings:*` routes resolve. **Who can trigger:** any operator with deploy access
(the two-line switch) — the DB step additionally needs DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; the six new constants live in
`apps/core/observability.py`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#5-success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| **Coverage capability = 100%** (H1) | structural — one slot over every D-6-resolved accepted app; the reviews slot renders on every accepted-app page. | None possible (structural). |
| **Gate-determination completeness = 100%** (integrity, AC5) | structural — `weight_eligible`/`eligibility_basis` are `NOT NULL` and stamped on every write; observed via `rating_submitted` + `rating_updated`. | A write that omitted the determination is impossible (NOT NULL + single write path). |
| **Duplicate prevention = 0** (AC8) | structural — `ratings_one_active_per_user_app` unique constraint + `update_or_create`. | None possible (DB constraint). |
| **No-scoring guarantee = 0** (AC6) | structural — no score/weight/rank/average column exists; the summary is count + raw distribution. **No metric can be nonzero.** | None possible (structural). |
| **Gate split** (observability, feeds H3) | `rating_submitted` / `rating_updated` tagged `{weight_eligible, basis}` — share eligible vs not. **Expected ~all *not-eligible* until a `DIGEST` emitter ships (R3)** — the metric makes that visible, not surprising. | Trend, not an alert — a swing toward *eligible* is the signal that a curated surface went live. |
| **Explicit-signal volume & submission rate** | `rating_submitted` + `rating_removed` counts (vision §5.3 expects this sparse). | Trend. |
| **Validation-rejection rate** (AC2) | `rating_rejected` (tagged `reason`) — malformed submissions caught at the boundary. | Trend — a spike means a client/contract problem. |
| **Gate read health** (integrity safety, AC5/§8) | `rating_gate_unverified` — the gate's signals read failed, so the rating stored *fail-closed* (not-eligible + `CURATION_UNVERIFIED`). | **`rating_gate_unverified` nonzero → page** (the one actionable alert — a spike means the signals read is degraded and determinations are unverifiable, though never silently granted weight). |
| **Reviews display health** | `rating_display_degraded` — the reviews slot fell back to its degraded state (fail-soft; the page still rendered). | A sustained rise means the display selector is unhealthy; the page is unaffected. |

## 8. Verification at release (2026-06-21)

- **486 automated tests pass** (417 baseline + 69 new ratings / signals tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model drift.
- Rollout→rollback **rehearsed** on a throwaway PostgreSQL DB (§6): `migrate` applied `ratings/0001`
  + `signals/0003` (table + both indexes + unique constraint confirmed present) → `check` clean →
  `migrate signals 0002` + `migrate ratings zero` reversed both cleanly (confirmed gone) →
  re-`migrate` re-applied both (reversible up→down→up). Throwaway DB dropped after.
- The two `ratings:submit` / `ratings:remove` routes resolve; the six observability constants exist.
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 to tests; the gate fail-closed, write
  atomicity, display fail-soft, no-IDOR, boundary-validation, and no-scoring-field cases are each
  exercised by a dedicated test.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §11/§14](DESIGN.md); none is a release
blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **The gate is ~always *not-eligible* at MVP (R3).** No `DIGEST` emitter exists yet
  (`weekly-digest` / `editorial-curation-tools` unbuilt), so almost every rating records
  *not-eligible*. This is **correct behavior, not a bug** — the value is the recorded substrate
  that becomes weightable the moment a curated surface emits, made visible by the gate-split metric.
- **No public quality number / average (by design, AC6).** The page shows count + raw distribution,
  never a computed average — the gameable number the gate exists to neutralize. The Quality Score is
  the downstream consumer.
- **Eligibility recompute is a named-not-built lever.** Determinations are *re-derivable* (inputs
  retained, corpus append-only) but no `recompute_eligibility(app_id|all)` management path is built —
  no consumer needs it yet. Documented in [DESIGN §5b](DESIGN.md) + the `apps/ratings` README.
- **Deleted-account review text is retained-anonymized, not purged.** On account deletion `user` →
  NULL (SC-10 posture, mirroring signals) — the rating + eligibility survive for H3, unlinked, and
  the review text reads "by a former user". A stronger purge-the-text posture is a one-line
  deletion-hook addition — **noted, not built** (deferred with the integrity/privacy hardening, OQ-3).
- **No anomaly / review-bomb / sockpuppet defense.** Out of scope (the later integrity system, R4/OQ-3).
  This feature ships authenticated-only + one-per-user (a structural volume cap) + the gate (outside
  brigades land *unweighted*). Request rate-limiting is available but unwired (the one-per-user cap
  suffices at MVP).
- **No live-metrics window measured.** Deferred with the local/dev target until a production target
  and real traffic exist (mirrors the five prior closed-out features).

## 10. Stakeholder notification

On the first real (production) promotion: notify downstream feature owners that the curated-rating
gate is **live and recording** — every rating now carries a `weight_eligible` determination per the
global [D-8](../../DECISIONS.md) semantic ("curated = a `DIGEST` impression; an open `APP_PAGE` view
never counts"), which is **binding** on `editorial-curation-tools` (it must *produce* such
impressions), `developer-dashboard` ("reach = curated users"), and the future Quality Score (the
weighting consumer). Hand them the read contract: the eligibility-tagged corpus is theirs to weight;
**no score/weight/average is computed in this layer** (AC6 — that stays downstream). Remind
`weekly-digest` / `editorial-curation-tools` that they are the **first `DIGEST` emitters** — until
one ships, the gate split skews entirely *not-eligible* (R3, expected). No support-facing change at
this release — the local/dev target carries no production traffic.
