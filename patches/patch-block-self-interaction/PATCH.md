# PATCH.md — patch-block-self-interaction

**Source issues (bundled):**
- [`Q-002`](../../issues/Q-002.md) — Should a user be able to submit a review for their own app? → **Answered: Option A — block self-review** (DN-Q002). Severity: **Medium**.
- [`Q-003`](../../issues/Q-003.md) — Should a user be able to follow their own app? → **Answered: Option A — block self-follow** (DN-Q003). Severity: **Low**.

These two are bundled because they are the **same shape**: a single ownership guard
(`viewer owns the app`) that suppresses an interaction control on the public app page and
rejects the corresponding mutation server-side. They touch the same surface (the app page
slots) and the same owner-identity source, so one patch resolves both coherently.

---

## 1. Coordinator triage (2026-06-29) — Source & scope gate

> Written by the Coordinator at routing. The **root-cause design and task list below are
> the Maintenance Planner's to fill** (Stage `P-plan`). This section is the verified
> starting context.

### Owner identity is available without a schema change

The public app page renders `app = catalog.get_catalogued_app(app_id)`, a
[`CatalogApp`](../../apps/catalog/selectors.py#L54) read-model that **already carries
`owner`** ([selectors.py:70](../../apps/catalog/selectors.py#L70), populated from the
existing `App.owner` FK at [selectors.py:108](../../apps/catalog/selectors.py#L108)). So
"is the viewer the app's owner?" is answerable today — **no migration, no new field.**

> Note for the Planner: [`app_page.html`](../../apps/pages/templates/pages/app_page.html)
> carries a comment claiming `CatalogApp` "carries no owner/team/paid field". That comment
> is about page *uniformity* (no app renders a *richer* page than another); it predates /
> is inconsistent with the DTO actually exposing `owner`. Confirm the field is reliably
> populated on the public path before relying on it, and reconcile the comment.

### Self-review (Q-002, Option A)

- Control: the rating form in
  [`_reviews_slot.html`](../../apps/ratings/templates/ratings/_reviews_slot.html#L48-L80),
  rendered via the `{% app_reviews app %}` inclusion tag
  ([`ratings_tags.py`](../../apps/ratings/templatetags/ratings_tags.py)).
- Mutation endpoint: `POST /ratings/apps/<id>/rating` →
  [`ratings.views.submit`](../../apps/ratings/views.py) →
  [`ratings.services.submit_rating`](../../apps/ratings/services.py).

### Self-follow (Q-003, Option A)

- Control: the Follow button in
  [`_follow_slot.html`](../../apps/subscriptions/templates/subscriptions/_follow_slot.html#L12-L17),
  rendered via the `{% app_follow app %}` inclusion tag
  ([`subscriptions_tags.py`](../../apps/subscriptions/templatetags/subscriptions_tags.py)).
- Mutation endpoint: `POST /subscriptions/apps/<id>/follow` →
  [`subscriptions.views.follow`](../../apps/subscriptions/views.py) →
  [`subscriptions.services.follow_app`](../../apps/subscriptions/services.py).

### Scope gate → Patch Track (confirmed)

No migration, **no new or changed public endpoint/route** (the guard is added *behaviour*
on existing endpoints, not a new contract), no global ADR. Hiding the control is
presentation; the robust block is a **server-side owner guard** at the write boundary —
per CLAUDE.md §5.4 the template hide alone is not sufficient (it is bypassable), so both
layers are in scope. **No-Schema Assertion to be confirmed by `makemigrations --check` at
build.**

### Framing for the Planner (not yet designed)

- Decide where the owner guard lives so it is the **single source of truth** for "owner
  cannot self-interact" — service layer is the robust trust boundary; the template hide is
  the cooperating UX layer. Avoid duplicating the ownership rule in two places without one
  canonical helper.
- Decide the rejected-mutation behaviour (e.g. 403 vs. fail-soft message + PRG) consistent
  with each app's existing house pattern (ratings uses PRG + `messages`; subscriptions
  surfaces faults as a message + PRG).
- Decide the suppressed-control UX (hide entirely vs. show a disabled control with a
  notice — Q-002 suggests *"You can't review your own app."*).
- Consider an owner who already has a pre-existing rating/follow from before this patch
  (edge case: should `remove`/`unfollow` still be allowed? likely yes, to let them clean
  up). Record the call in `DECISIONS.md`.

---

## 2. Problem Statement

_pending — Maintenance Planner (P-plan)_

## 3. Proposed Fix / Root-Cause Design

_pending — Maintenance Planner (P-plan)_

## 4. Task List

_pending — Maintenance Planner (P-plan); T-01 must be a red-first regression test._

## 5. No-Schema Assertion

_pending — to be confirmed at build via `makemigrations --check` (no drift)._
