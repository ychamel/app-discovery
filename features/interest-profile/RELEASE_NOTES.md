# RELEASE_NOTES — interest-profile

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway PostgreSQL database
(2026-06-22).* Sources: the verified Stage-4 build, [DESIGN.md §9/§12/§16](DESIGN.md)
(failure modes + observability + rollout/rollback), [FEATURE_BRIEF.md §Success metrics](FEATURE_BRIEF.md)
(M1–M6 + acceptance criteria), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9 coverage), and the reused
contracts [D-3](../../DECISIONS.md) (identity / account-deletion cascade), [D-4](../../DECISIONS.md)
(stack), [D-5](../../DECISIONS.md) (`is_valid_tag` write boundary + `resolve_tag` read).
The [app-subscriptions release](../app-subscriptions/RELEASE_NOTES.md) is the precedent this
mirrors — interest-profile is a **simpler near-twin** (own mutable table + single write/read path
+ fail-soft inclusion tag + activation include), **minus** the D-7 emit and the notices seam.

---

## 1. What this release is

The platform's **personalization substrate** — the **user side of the Ring-0 match** (vision
§2.2 / §3.1 / §6). A signed-in user can declare and maintain which [interest-taxonomy](../interest-taxonomy/)
tags they care about, producing a durable, taxonomy-valid interest profile that the future
`weekly-digest`/matcher reads as its Ring-0 input — the half of the matching equation that was
empty until now. It is the cheapest unblock with the widest downstream payoff for proving **H1**.

It ships as a **new Django app, `apps/interests/`**, owning **one mutable table**
`interests_interest` (one row per `user × Tag.id`). The *interest profile is the set of a user's
rows* — there is **no parent profile row**, so an **empty profile is the structural default**
(AC6). Declaration is **pure preference state, not behavior**: this app **emits no
[D-7](../../DECISIONS.md) event and does not import `signals.capture` at all** (IP-5 — asserted by
a no-import test). It computes nothing — no score, weight, or rank anywhere (R5/AC8); it only
records what the *user* chose and exposes it through one read surface. It changes no existing
feature's behavior and satisfies all nine acceptance criteria AC1–AC9 (mapping in
[TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since there was no way for a user to say what they're interested in)

- **New app `apps/interests/`, owning one mutable table `interests_interest`**
  ([DESIGN §4](DESIGN.md)) — one row per `(user, tag_id)`, created on declaration and
  **hard-deleted** on deselect/clear (the store is *exactly the current declared set* — one source
  of truth). Columns: `id` (UUID pk), `user` (FK), `tag_id` (a **soft D-5 ref**, no DB FK —
  validated active at the write boundary, resolved at read), `created_at`. **There is no
  `score`/`weight`/`rank` column** — AC8's "no scoring in this layer" is *structural*, not a
  convention. **No `updated_at`, no soft-delete** — a declaration exists or it does not; the set
  changes by row add/remove. **No parent profile row** — zero rows *is* the empty profile, so AC6
  needs no special marker or create-on-first-visit lifecycle. The `(user, tag_id)` **unique
  constraint** `interests_one_per_user_tag` makes "declaring an already-declared tag is a no-op"
  structural (AC1/AC4); its index also backs the per-user read. Migration **`interests/0001_initial`**.
- **`user` FK is `on_delete=CASCADE`** ([DESIGN §4.1](DESIGN.md), IP-4/AC9) — the profile is
  *mutable user preference state*, so `account.delete()`
  ([accounts/services.py](../../apps/accounts/services.py)) removes the user's interest rows
  automatically **with no edit to `accounts`** (the deletion boundary is owned by the FK, exactly
  the `app-subscriptions` posture). Unlike the D-7 corpus there is **no anonymized residue** —
  none is written here. This also satisfies the user's right to clear their own profile
  (`clear_interests`).
- **The single write path + the §7 preserve-on-edit reconcile** ([DESIGN §5.1/§7](DESIGN.md)) —
  `services.set_interests` / `clear_interests` are the **only** place `Interest` rows are mutated
  and the **only** caller of `is_valid_tag` for this feature's boundary. `set_interests`
  **validates every submitted id active via D-5 `is_valid_tag` all-or-nothing before any write**:
  one off-vocabulary / retired / malformed id → `InterestValidationError`, **nothing persisted**
  (no partial set), `INTEREST_DECLARATION_REJECTED` counted (AC2); an over-large POST is rejected
  by the defensive `interest_declaration_max()` cap. It then set-replaces the declared set in **one
  `transaction.atomic()`** — but the new set is `submitted ∪ {stored id : resolve_tag(id) is
  non-active}`, so a stored ref to a **no-successor retired tag** (a real D-5 state — `retire_tag`
  allows `replaced_by=None`) that the active-only picker **can't show** is **preserved across the
  edit, never silently dropped** (the load-bearing seam — AC4 × AC7, M5 = 0). A renamed/merged tag
  normalizes toward its active successor; a genuinely deselected active tag is removed. The
  reconcile is delta-only (`bulk_create` over `new − current`, delete `current − new`) so a
  concurrent double-declare is a no-op, not a collision. Saving the same set is idempotent.
  `clear_interests` deliberately bypasses preserve — an explicit full wipe is the user saying
  "none at all" (AC9).
- **The single read surface — the matcher contract** ([DESIGN §5.2](DESIGN.md)) —
  `selectors.declared_tag_ids(user) -> frozenset[UUID]` is the **one consumer contract** (AC8): for
  each stored row it applies D-5 `resolve_tag` to the tag's **current** meaning and returns the
  **deduplicated** set of resolved `Tag.id`s (a no-successor retired ref resolves to itself and
  stays in the set — AC7; two ids resolving to the same successor collapse to one; anonymous →
  empty). This is the **same id space catalog app tags resolve into (D-5/D-6)**, so both sides of
  the future match speak one language. `declared_tags(user)` returns the resolved `Tag` objects
  ordered by label for display/picker pre-check; `has_declared_interests(user)` is one indexed
  `EXISTS` driving the prompt and empty-state. **No consumer — including this app's own views —
  reads `Interest` rows directly** (AC8); the surface is **additive-only** by design (a future
  matcher is built against `declared_tag_ids` with no change here).
- **Thin `login_required` HTTP views** ([DESIGN §5.3](DESIGN.md)) — `GET /interests/`
  (`interests:picker`, the cluster-grouped active picker pre-checking the user's resolved declared
  tags), `POST /interests/save` (`interests:save`, PRG back to the picker with a success/validation
  message), `POST /interests/clear` (`interests:clear`, AC9). **No interest/profile id appears in
  any URL** — a row is addressed by `request.user` + `tag_id`, so a user can only ever touch
  **their own** profile (**no IDOR, structural**). Anonymous requests → redirect to sign-in
  (`login_required`, C2); CSRF on every form. The picker read is wrapped **fail-soft**: any fault
  renders a degraded "couldn't load, try again" page (+ `INTEREST_PICKER_DEGRADED`) and **never
  500s**. The **write** fails **loud** where correctness depends on it (validation, the atomic
  reconcile) so an invalid or partial set never persists.
- **The cluster-grouped picker** ([DESIGN §8](DESIGN.md), AC5) — `picker.html` renders
  `taxonomy.list_clusters()` (prefetched, N+1-free) as `<section>`s, each listing its **active**
  tags as labelled checkboxes (label + definition; **never raw ids or retired tags**), pre-checked
  for the user's resolved declared set. Handles the empty-profile, empty-vocabulary, and
  fail-soft-error states without crashing. A "pick a few" hint below `interest_suggested_minimum()`
  is **copy only — never a validation floor** (IP-3).
- **The onboarding nudge — a fail-soft inclusion tag** ([DESIGN §5.4](DESIGN.md), AC3) —
  `{% interest_prompt %}` (`interests_tags`) reads only `selectors.has_declared_interests`; on an
  empty profile it renders a gentle "Tell us what you're interested in →" link to the picker, and
  **nothing** once any interest is declared. It is **encouraged, never a blocker** (non-gating —
  AC3/AC6) and **fail-soft**: any exception renders nothing (+ `INTEREST_PROMPT_DEGRADED`) and
  **never 500s the profile page**. It lives as **one content line** in
  `accounts/templates/accounts/profile.html` (the existing post-registration landing), reusing the
  `verify`→`profile` redirect **with zero edit to auth logic** — the house pattern (a fail-soft
  inclusion tag in another feature's *template*, never a behavioral change to its *view*).
- **Read-only admin** ([DESIGN §5/§12](DESIGN.md)) — `Interest` visibility for operability; the
  admin offers **no** add/change/delete path (writes go only through `services`, so the reconcile
  invariant can never be bypassed).
- **Shared-surface touches** — two config tunables (`interest_suggested_minimum()` default 3,
  `interest_declaration_max()` default 500, both validated by the existing `validate_all()`) and
  six metric constants (§7 below) added to `apps/core`; `apps.interests` added to `INSTALLED_APPS`;
  the `path("interests/", include("apps.interests.urls"))` **activation switch** added to
  `config/urls.py`; one **content-only** edit to `accounts/profile.html` (the
  `{% interest_prompt %}` line + a `{% load interests_tags %}` line). `apps/accounts`,
  `apps/taxonomy` reused **as-is** (no edit to either). **No new `.env` key.** No existing behavior
  changed — the `accounts` suite stays green after the one profile.html content line.

## 3. Who is affected

- **Signed-in users** — can now declare an interest profile from `/interests/`: browse the active
  vocabulary grouped by cluster, select/deselect tags, save, edit at any time, and clear it. The
  picker action requires sign-in.
- **Newly-registered users** — landing on the profile page after `verify` see a gentle, skippable
  prompt to pick interests (AC3). An empty profile is fully valid (AC6) — the prompt never blocks
  using the site, and disappears once any interest is declared.
- **The platform / the future matcher** — there is now a **user side of the Ring-0 match** to
  target. The future `weekly-digest`/matcher reads `interests.selectors.declared_tag_ids(user)` — a
  set of resolved current `Tag.id`s — and intersects it with a catalogued app's resolved tag set
  (D-6). Built against this surface with **no change here** (AC8).
- **Analysts / the future Quality Score** — M2 (richness), M3 (vocabulary coverage), and M6
  (match-readiness, the H1 leading indicator) are **analyst-derived reads** over the interest store
  joined to the catalog — **not computed here** (no scoring in this layer). M1 (declaration rate)
  is derived by joining `interest_declared` to registration timestamps.
- **`weekly-digest` / the matcher (Phase 2+, unbuilt)** — inherits `declared_tag_ids` as its
  Ring-0 contract. Onboarding gating (IP-2) is **revisitable** when a digest consumer makes
  declaration load-bearing.
- **Support** — no support-facing change at this release (local/dev target).

## 4. How to use it (operators)

The rollout is the ordered, additive steps from [DESIGN §16](DESIGN.md) — no new env var, no
feature flag, no recurring job:

1. `python manage.py migrate interests` — applies `interests/0001_initial` (creates
   `interests_interest`). No data migration, no backfill — an **empty profile is the valid default
   for every existing account** (AC6).
2. `python manage.py check` — must report no issues before the surface is considered live.
3. Deploy the build (which includes `apps.interests` in `INSTALLED_APPS`, the
   `{% interest_prompt %}` line in `accounts/profile.html`, and the
   `path("interests/", include("apps.interests.urls"))` activation switch in `config/urls.py`). The
   picker, the save/clear routes, and the onboarding nudge go live on deploy.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with `identity-accounts`,
> `interest-taxonomy`, `submission-intake`, `signal-capture`, `app-pages`, `ratings-reviews`, and
> `app-subscriptions` ([CONTROL.md](../../CONTROL.md)); the platform is still mid-development. The
> feature is verified locally (**616 tests green**, `check` clean, `interests/0001` applies and
> reverses cleanly). **Production promotion and a live-metrics monitoring window are deferred**
> until there is a production target and real traffic.

This is an **additive new app**: nothing existing changes behavior, so there is **no pre-existing
surface to ramp against and nothing to feature-flag off** (an honest deviation from the
internal→%→full template — DESIGN §16). Safety comes from the **two-part activation switch** + the
**one reversible, additive migration**, not a kill switch. **"Off" = remove the `config/urls`
include + the `accounts/profile.html` `{% interest_prompt %}` line** (zero data migration; the
table can be dropped separately by reversing `0001`). Backward-compatible: with the feature off,
the profile page renders exactly as today.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate interests` applied through `0001`; `interests_interest`, the `interests_one_per_user_tag` unique constraint, the per-user index, and the CASCADE `user` FK to `accounts_account` present; `manage.py check` clean. |
| Surface live | the three `interests:*` routes resolve; the picker renders the cluster-grouped active vocabulary for a signed-in user; the `{% interest_prompt %}` nudge renders on the profile page for an empty-profile user and an anonymous profile view still renders fully. |
| Write path correct | a save of active tags stores exactly that set keyed `user × tag_id` and shows it pre-checked on return (AC1/AC4); one bad id rejects the **whole** save with nothing persisted (`InterestValidationError`, AC2); a re-save of the same set is a no-op; **a no-successor retired stored ref survives a re-save** (the §7 preserve seam — AC7); the app imports no `signals.capture` (IP-5). |
| Read contract correct | `declared_tag_ids` returns resolved, deduped current `Tag.id`s; a renamed tag resolves to its successor and a no-successor retired ref stays in the set (AC7/AC8); `count_unresolvable()` reads **0** (M5). |
| Display correct | empty-profile and empty-vocabulary states render without error (AC6); `interest_picker_degraded` / `interest_prompt_degraded` read 0. |
| Stable at target | the above holds with no sustained `interest_picker_degraded` / unexpected `set_interests` write-failure spikes through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**Two surface touches + one reversible migration** ([DESIGN §16](DESIGN.md)):

1. Remove the `{% interest_prompt %}` line (and the `{% load interests_tags %}` line) from
   `accounts/templates/accounts/profile.html` — the onboarding nudge vanishes, the profile page is
   unchanged otherwise.
2. Remove the `path("interests/", include("apps.interests.urls"))` include from `config/urls.py` —
   the picker/save/clear routes vanish with **zero data migration**.

If the schema must also be undone (design-for-deletion — `interests` owns its own table and has
**no outside footprint** beyond the two surface touches and the soft `tag_id` D-5 ref):

```bash
python manage.py migrate interests zero    # drops interests_interest
```

Because the feature emits no D-7 corpus events, there is **nothing in another app's store to
unwind** — the rollback is fully contained to `interests`' own table plus the two surface lines.

**Rehearsed 2026-06-22** on a throwaway PostgreSQL database (`interests_release_rehearsal`, dropped
afterward): `migrate` applied `interests/0001_initial` → `interests_interest`, the
`interests_one_per_user_tag` unique constraint, the per-user `user_id` index, and the CASCADE
`user` FK to `accounts_account` all confirmed present → `manage.py check` clean; then `migrate
interests zero` **unapplied cleanly** (table confirmed gone) and a re-`migrate` **re-applied** it
(confirmed reversible **up→down→up**); `makemigrations --check` reports no drift. The three
`interests:*` routes resolve (`/interests/`, `/interests/save`, `/interests/clear`). **Who can
trigger:** any operator with deploy access (the two surface touches) — the DB step additionally
needs DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; the six new constants live in
`apps/core/observability.py`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| **M1 declaration rate (the headline)** | `interest_declared` — a save that took a profile from 0 → ≥1 tag. Analyst joins to registration timestamps for "within onboarding". | Trend, not an alert (the adoption baseline this feature establishes). |
| **M4 edit rate** | `interest_profile_updated` — a save that changed an already-non-empty profile; `interest_profile_cleared` — a clear (or a save to empty). | Trend — confirms the profile is treated as living, not write-once. |
| **AC2 rejection health** | `interest_declaration_rejected` — an invalid-id / over-size save rejected loudly with nothing persisted. | **Expected, not alertable** — this is correct fail-loud behavior. |
| **M5 reference integrity (AC7)** | the taxonomy `taxonomy_reference_break` counter (emitted by `resolve_tag` on a cycle) + the ops selector `count_unresolvable()` (stored ids whose `resolve_tag` is `None`), which is **0 by construction** (validated active at write; D-5 never hard-deletes). | A non-zero `count_unresolvable()` is a **D-5 contract violation** — investigate (must be 0). |
| **M2 richness / M3 vocabulary coverage / M6 match-readiness** | **Derived by analysts** from the interest store joined to the catalog (not counters) — documented here, not emitted. Expected **thin** until adoption grows and `weekly-digest` exists — visible, not hidden. | None in this layer (analyst-derived). |
| **Read display health** | `interest_picker_degraded` / `interest_prompt_degraded` — a fail-soft read fell back to its degraded/empty state (the page still rendered). | A sustained rise means a read dependency (taxonomy selectors / `has_declared_interests`) is unhealthy; the page is unaffected. |

**The one actionable alert:** an **unexpected `set_interests` write failure** — a DB error in the
atomic reconcile, **not** a validation reject — i.e. a spike in save-path exceptions or
`interest_picker_degraded`. Validation rejections (`interest_declaration_rejected`) and the
empty-until-adoption M-metrics (M2/M3/M6) are **not** alerts.

## 8. Verification at release (2026-06-22)

- **616 automated tests pass** (552 baseline + 64 new interests tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model drift.
- Rollout→rollback **rehearsed** on a throwaway PostgreSQL DB (§6): `migrate` applied
  `interests/0001_initial` (table + `interests_one_per_user_tag` unique constraint + per-user index
  + CASCADE `user` FK to `accounts_account` confirmed present) → `check` clean → `migrate interests
  zero` reversed it cleanly (table confirmed gone) → re-`migrate` re-applied it (reversible
  up→down→up) → no drift. Throwaway DB dropped after.
- The three `interests:picker` / `:save` / `:clear` routes resolve; the six observability constants
  and the two config tunables (`interest_suggested_minimum`/`interest_declaration_max`) exist; both
  halves of the activation switch (the `config/urls` include + the `accounts/profile.html`
  `{% interest_prompt %}` line) are present.
- Tested against the **real taxonomy D-5 surface** (no `is_valid_tag`/`resolve_tag` mocking); the §7
  preserve seam is exercised against genuine `retire_tag(replaced_by=None)` and
  `retire_tag(replaced_by=successor)` states. The IP-5 no-`signals.capture`-import is AST-asserted.
  [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 to tests; the §7 preserve-on-edit, the
  all-or-nothing validation, the no-IDOR boundary, the picker/prompt fail-soft, the no-scoring
  structural guarantee, the resolve+dedupe read, and the AC9 CASCADE-deletion case are each
  exercised by a dedicated test.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §14/§17/§18](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **No consumer reads the profile yet (the matcher is future).** `declared_tag_ids` is published
  and stable, but until `weekly-digest`/the matcher ships, nothing reads it. This is **correct** —
  the substrate is the value; building it right now (the store shape, the validation boundary, the
  resolved read contract) is the expensive-to-reverse part.
- **Onboarding is non-gating and dismissal is not persisted (IP-2 / DESIGN §17).** An empty-profile
  user sees the one-line nudge on every profile visit until they declare an interest. Persisting a
  "dismissed" flag would need a parent profile row → AC6 stops being structural. Named, not built —
  revisit if telemetry shows re-nudge friction, or when a digest consumer makes declaration
  load-bearing (revisit onboarding gating, IP-2).
- **Declaration emits no behavioral signal (IP-5).** Declaring/changing interests writes **no D-7
  event** — declaration is preference state, not behavior, and the app does not import
  `signals.capture`. There is no behavioral trail of *when* interests changed beyond `created_at` +
  the M1/M4 metrics. An additive "interest changed" D-7 kind is the named later path if a churn
  consumer ever needs it.
- **Flat declared set — no interest intensity / weighting (OQ-IP-4, out of scope).** A profile is a
  flat set of tags; "love" vs "like" strengths are a named additive later change (a new selector
  over the same store), not built now.
- **Clusters are a picker selection aid, not a stored unit (IP-1 / DN-15).** A user who "means the
  whole cluster" is stored as its current member tag ids; cluster-to-cluster adjacency is the
  matcher's job over the D-5 cluster anchor.
- **Per-read `resolve_tag` is not cached.** The profile read is one indexed query + a bounded
  `resolve_tag` per stored id (sets are small). A cached resolved projection is the D-5-inherited
  100× growth path — named, not built.
- **No live-metrics window measured.** Deferred with the local/dev target until a production target
  and real traffic exist (mirrors the seven prior closed-out features).

## 10. Stakeholder notification

On the first real (production) promotion: notify downstream feature owners that the **user side of
the Ring-0 match is live** — signed-in users can now declare a taxonomy-valid interest profile,
read through the single `interests.selectors.declared_tag_ids(user) -> frozenset[UUID]` contract
(resolved current `Tag.id`s, the same id space catalog app tags resolve into). Hand `weekly-digest`
/ the matcher its inheritance: build against `declared_tag_ids` with **no change here** (AC8);
onboarding gating (IP-2) is revisitable once declaration becomes load-bearing. Remind analysts /
the future Quality Score that **M2 (richness), M3 (vocabulary coverage), and M6 (match-readiness)
are theirs to derive** from the interest store joined to the catalog — **nothing is scored in this
layer** (AC8). No support-facing change at this release — the local/dev target carries no
production traffic.
