# apps/interests — interest profile (declared interest tags)

A signed-in user's **declared interest tags** as a mutable membership set — the *user side of
the Ring-0 match* a future `weekly-digest`/matcher consumes (the Phase-2 personalization
substrate, H1). A user picks active taxonomy tags they care about; the profile is editable and
clearable at any time.

This app **computes no score** and **emits no D-7 event** — it does **not** import
`signals.capture` (IP-5). Declaring an interest is *preference state*, not behavior; turning
declared interests into a ranking is the future matcher's job. The matcher reads exactly one
surface: `selectors.declared_tag_ids(user) -> frozenset[UUID]` (resolved current `Tag.id`s, the
AC8 contract). See [DESIGN.md](../../features/interest-profile/DESIGN.md).

It owns **one mutable table**, `interests_interest` — one row per `(user, tag_id)`, created and
removed but never versioned. There is **no parent profile row**: the profile *is* the set of a
user's rows, so an **empty profile is the structural default** (AC6 — zero rows needs no marker).
The `user` FK **CASCADE**s — a declaration is live preference state, removed with the account
(AC9) with **no edit to `accounts`**. Unlike subscriptions there is no corpus residue (no event
is ever written).

## Routes (mounted under `interests/`)

| Name | Method | Auth | Behavior |
|------|--------|------|----------|
| `interests:picker` (`interests/`) | GET | `login_required` | The cluster-grouped, active-only, label-bearing picker (AC5), pre-checking the user's resolved declared tags (AC1). Empty profile → a gentle hint (AC6); empty vocabulary → "none available", no crash; read error → a fail-soft degraded page (never a 500). |
| `interests:save` (`interests/save`) | POST + CSRF | `login_required` | Set the declared set → PRG to the picker with a success message. An invalid id → re-render with the message + **400**, no partial write (AC2); a DB failure → a try-again message, the save rolled back. |
| `interests:clear` (`interests/clear`) | POST + CSRF | `login_required` | Remove **all** the caller's interests, then PRG (AC9). |

No interest/profile id ever appears in a URL: a declaration is addressed by `request.user` +
`tag_id`, so a user can only ever touch their own profile (no IDOR).

## The single write path + the §7 preserve-on-edit reconcile ([services.py](services.py))

`set_interests` / `clear_interests` is the **only** place `Interest` rows change, and the only
caller of `is_valid_tag` for this feature's write boundary. `set_interests`:

- **Validates all-or-nothing (AC2):** every submitted id must be an active tag (and the count
  must be within `interest_declaration_max()`), or nothing is written — a `InterestValidationError`
  is raised and `interest_declaration_rejected` counted.
- **Reconciles as a set-replace with preserve-on-edit (§7):** the stored set becomes the
  submitted set **plus** any stored id the active-only picker can't show — a *no-successor*
  retired tag that `resolve_tag` maps to a non-active tag (`retire_tag` allows `replaced_by=None`).
  The user never saw it, so they did not deselect it; preserving it keeps AC7/M5 = 0 across
  edits. A renamed/merged id resolves to its *active* successor (shown + pre-checked), so it
  **normalizes** toward the successor on re-save. The delta-only writes run in one
  `transaction.atomic()`.

`clear_interests` deliberately **bypasses** the preserve rule (including any preserved
non-active ref): an explicit full wipe is the user saying "none at all" (AC9).

## Single read surface ([selectors.py](selectors.py))

The **only** read surface and the only place `resolve_tag` is applied to stored ids — no
consumer (including this app's own views) reads `Interest` rows directly (AC8):

- `declared_tag_ids(user) -> frozenset[UUID]` — **the matcher contract:** resolved current
  `Tag.id`s, deduped. A no-successor retired ref resolves to itself and stays (AC7); two ids
  resolving to one successor collapse. Anonymous/`None` → empty (AC6).
- `declared_tags(user) -> list[Tag]` — the same, as resolved `Tag` objects ordered by label
  (display + the picker pre-check).
- `has_declared_interests(user) -> bool` — one indexed `EXISTS` (drives the onboarding nudge).
- `count_unresolvable() -> int` — the M5 ops invariant (stored ids whose `resolve_tag` is
  `None`; **0 by construction**). The live reference-break counter is the taxonomy
  `taxonomy_reference_break` (reused, not re-added).

## The onboarding nudge ([templatetags/interests_tags.py](templatetags/interests_tags.py))

`{% interest_prompt %}` is the only coupling to another feature's template: one content line on
`accounts/profile.html` (the post-registration landing). It shows a gentle, **non-gating** link
to the picker when the user has declared nothing, and self-resolves once any interest exists
(AC3). **Fail-soft:** any error renders nothing + `interest_prompt_degraded` and never 500s the
profile page.

## Observability ([apps/core/observability.py](../../apps/core/observability.py))

`interest_declared` (M1), `interest_profile_updated` (M4), `interest_profile_cleared`,
`interest_declaration_rejected` (expected — **not** alertable), and the two display fail-soft
counters `interest_picker_degraded` / `interest_prompt_degraded`. The **one actionable alert**
is an *unexpected* `set_interests` write failure (a DB error, not a validation reject). M5
integrity reuses the taxonomy `taxonomy_reference_break`.

## Config tunables ([apps/core/config.py](../../apps/core/config.py))

`interest_suggested_minimum()` (3) — the "pick a few" picker nudge threshold (copy only,
**never a validation floor**). `interest_declaration_max()` (500) — a defensive per-save
request-size cap (safety, not a product maximum).

## Rollback / operations

Additive, **no feature flag**. Two-part rollback (the activation switch):

1. Remove the `{% interest_prompt %}` line + the `{% load interests_tags %}` from
   `apps/accounts/templates/accounts/profile.html` (one content-line revert).
2. Remove the `path("interests/", include("apps.interests.urls"))` include from
   [config/urls.py](../../config/urls.py).

With the feature off the profile page renders exactly as before. If a full teardown is needed
the migration is reversible: `migrate interests zero` drops `interests_interest` — zero impact
on other apps (design-for-deletion; interests owns its own table and only *reads* the taxonomy
D-5 surface, which it never changes).
