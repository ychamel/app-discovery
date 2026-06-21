# apps/ratings — ratings & reviews

One **editable rating (+ optional review) per user per app**, plus the **curated-rating
gate**: every rating records whether its author was *organically curated* to that app (a
`Surface.DIGEST` impression), so a bought or farmed rating can never silently count. The
feature fills the empty `app-pages` reviews slot (AP-1).

This app **computes no score** (RR-1). It captures ratings and *records* eligibility; turning
the eligibility-tagged corpus into a quality number is a downstream consumer's job (the future
Quality Score). See [DESIGN.md](../../features/ratings-reviews/DESIGN.md).

It owns **one mutable table**, `ratings_rating` — the deliberate contrast with the append-only
D-7 signals corpus: a rating is the user's current, editable opinion, not an immutable
behavioral fact.

## Routes (mounted under `ratings/`)

| Name | Method | Auth | Behavior |
|------|--------|------|----------|
| `ratings:submit` (`ratings/apps/<uuid:app_id>/rating`) | POST + CSRF | `login_required` | Create/update the caller's rating, then PRG-redirect to `pages:app-page`. Invalid input → message + redirect back (AC2); unknown/non-accepted app → 404 (AC9). |
| `ratings:remove` (`ratings/apps/<uuid:app_id>/rating/remove`) | POST + CSRF | `login_required` | Hard-delete the caller's rating, then redirect to the page (AC8). |

No rating id ever appears in a URL: a rating is addressed by `request.user` + `app_id`, so a
user can only ever touch their own (no IDOR).

## The gate ([gate.py](gate.py))

`CURATED_SURFACES = frozenset({Surface.DIGEST})` is the **single place** the platform's §4.1
rule lives (global **[D-8](../../DECISIONS.md)**): an impression on one of these surfaces is
organic curation; an open `APP_PAGE` view is not. `determine_eligibility` reads the *evidence*
through the neutral D-7 selector `signals.selectors.has_impression` (signals never judges what
its rows mean) and **fails closed + loud** — on a read error the rating is recorded
`weight_eligible=False, basis=CURATION_UNVERIFIED` with a `rating_gate_unverified` metric,
never silently granted weight and never blocked. Changing what counts as curation is one line
in `CURATED_SURFACES`.

At MVP, ~all ratings record *not-eligible* until a `DIGEST` emitter ships — expected (R3),
made visible by the gate-split metric. The determination is **re-derivable** (inputs retained,
the signals corpus append-only): a `recompute_eligibility` management path is the named growth
lever, **not built** (no consumer needs it yet).

## Single write / single read

- **Write:** [services.py](services.py) (`submit_rating` / `remove_rating`) is the only place
  `Rating` rows change. It validates the app (D-6) and input at the boundary, stamps the gate
  determination, and writes everything in one atomic `update_or_create` so `weight_eligible`
  and `eligibility_basis` can never drift.
- **Read:** [selectors.py](selectors.py) (`reviews_for_app` / `user_rating`) is the only
  display surface. The summary is a **count + raw score distribution — never an average** (AC6;
  the gameable number the gate neutralizes). All ratings show regardless of eligibility (AC7);
  the gate flag is internal substrate, not a public badge.

## Observability ([apps/core/observability.py](../../apps/core/observability.py))

`rating_submitted` / `rating_updated` (tagged `{weight_eligible, basis}` — the gate-split
metric), `rating_removed`, `rating_rejected{reason}` (AC2), `rating_gate_unverified` (**the one
actionable alert** — the signals read is degraded), `rating_display_degraded` (the slot fell
back fail-soft).

## Config tunables ([apps/core/config.py](../../apps/core/config.py))

`rating_scale_max()` (5), `review_text_max_length()` (4000), `reviews_display_limit()` (20).

## Rollback / operations

Additive, **no feature flag**. Two-line rollback:

1. Restore slot 6 of `apps/pages/templates/pages/app_page.html` to `<p>Reviews coming soon.</p>`
   (and drop the `{% load ratings_tags %}` line).
2. Remove the `path("ratings/", include("apps.ratings.urls"))` include from
   [config/urls.py](../../config/urls.py).

If a full teardown is needed, the migrations are reversible: `migrate ratings zero` drops
`ratings_rating`, and `migrate signals 0002` drops the additive `signals_imp_user_app_idx`
index — zero impact on other apps (design-for-deletion; ratings owns its own table, the only
outside touch is one reversible index).
