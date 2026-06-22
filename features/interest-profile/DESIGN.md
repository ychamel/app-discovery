# DESIGN — interest-profile

*Stage 2 artifact (Software Architect). Status: **pending approval (DN-16)**. Traces to the
approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (DN-15) and to global **[D-3](../../DECISIONS.md)**
(account/role), **[D-5](../../DECISIONS.md)** (tag reference), **[D-4](../../DECISIONS.md)**
(stack). Produced by running the 14-step design protocol
([phase-2-architect.md](../../process/personas/phase-2-architect.md)); the reasoning is folded
into the sections below.*

> **One-line summary.** A new Django app `apps/interests/` owns **one mutable membership
> table** `interests_interest` (one row per user×declared `Tag.id`). The *interest profile is
> the set of a user's rows* — there is **no parent profile row**, so an **empty profile is the
> structural default** (AC6). A single write path set-replaces the user's declared tags
> (validating every id active via D-5 `is_valid_tag`, AC2); a single read surface exposes the
> profile as **resolved, current `Tag.id`s** via D-5 `resolve_tag` (AC7/AC8). The store is pure
> preference state: **no D-7 emit** (IP-5), **CASCADE on the user FK** so account deletion
> removes it with no edit to `accounts` (AC9). It is a **simpler near-twin of
> [`app-subscriptions`](../app-subscriptions/DESIGN.md)** (own mutable table + single
> write/read path + fail-soft inclusion tag + activation include) with one harder seam: the
> picker's set-replace must **preserve a stored reference the active picker can't show**
> (a *no-successor* retired tag) so AC7 holds across edits (§7).

---

## 1. Scope & approach (Step 1–2: SCOPE / REQUIREMENTS)

**Real problem (one sentence):** give a signed-in user a place to declare and maintain which
interest tags they care about, stored as taxonomy-valid `Tag.id`s, exposed through one read
surface a future matcher/digest consumes as the **user side of the Ring-0 match** — without
building the matcher.

**Stakeholders:** the signed-in user (declares/edits), the future `weekly-digest`/matcher (the
one consumer of the read surface), the platform integrity story (M5 reference integrity = 0).

**Lifespan:** **platform** substrate — the durable user side of every future personalization
read. Effort matches: get the store shape, the validation boundary, and the read contract
right now; they are the expensive things to reverse.

**Out of scope (held exactly to the brief):** the matcher/digest/ranking, implicit/behavioral
refinement, cluster-to-cluster ring adjacency, vocabulary editing, follows/collections,
interest intensity/weighting, recommending which tags to pick. This feature emits **no score**
and exposes **only** a resolvable `Tag.id` read surface (the R5 anti-scope-creep line, AC8).

**Functional requirements** (each verifiable, mapped to ACs in §15): declare a set of active
tags (AC1); reject any off-vocabulary/retired/malformed id loudly with no partial write (AC2);
prompt new users non-gatingly (AC3); edit/clear at any time with set-replace semantics (AC4);
a cluster-grouped, active-only, label-bearing picker (AC5); empty profile is a representable
handled state (AC6); stored references survive rename/retire via `resolve_tag`, never silently
dropped (AC7); a single read surface of resolvable `Tag.id`s, no consumer reads storage
directly (AC8); removed on account deletion + user can self-clear (AC9).

**Non-functional (D-2 — no global ceilings; design holds at 100×, CLAUDE.md §5.2):** picker
read and profile read must be **N+1-free** (the taxonomy selectors already prefetch; the
profile read is one indexed query + bulk resolve). Per-user declared sets are small (bounded by
the active vocabulary); reads are per-user and indexed.

**Assumptions ledger** (from the brief; **[v]**=verified against code/ADRs here,
**[w]**=working assumption this design commits to):
- **[v]** D-5 surface exists and is the validate/resolve boundary: `is_valid_tag` (active-only,
  malformed-tolerant), `resolve_tag` (follows `replaced_by`, keeps retired refs, cycle-guarded),
  `list_active_tags`/`list_clusters` (prefetched) — confirmed in `apps/taxonomy/selectors.py`.
- **[v]** `retire_tag(tag, replaced_by=None)` — **successor is optional**
  (`apps/taxonomy/services.py`); therefore a stored interest **can** resolve to a *non-active*
  tag (retired, no successor). This is the seam §7 is built around — not a hypothetical.
- **[v]** `account.delete()` cascades to CASCADE FKs in one transaction
  (`apps/accounts/services.delete_account`); a CASCADE user FK removes the profile with **no
  edit to `accounts`** (exactly the `app-subscriptions` posture, IP-4/AS-4).
- **[v]** New-account registration completes in `accounts.views.verify` and lands the user on
  `accounts:profile` — the natural, already-existing place to surface the non-gating onboarding
  prompt (AC3) without editing auth logic.
- **[w] IP-3** No hard min/max declared tags; any "pick a few" nudge is a **config value, not a
  validation floor** (`interest_suggested_minimum()`). A separate **defensive request-size cap**
  (`interest_declaration_max()`) guards against an abusive over-large POST — a safety cap
  (CLAUDE.md §5.4), explicitly *not* a product maximum.
- **[w] IP-5** Declaring/changing interests emits **no D-7 event** — this app does **not** import
  `signals.capture` at all (the cleanest proof of IP-5). An "interest changed" signal, if ever
  wanted, is an additive D-7 decision in a later feature.

---

## 2. Current-state summary (Step 3: CONTEXT)

Relevant existing surfaces this design reuses **as-is** (no change to any of them):

| Surface | What it gives us | Used for |
|---|---|---|
| `taxonomy.selectors.list_clusters()` / `list_active_tags()` | active vocabulary, cluster membership prefetched (no N+1) | the picker render (AC5) |
| `taxonomy.selectors.is_valid_tag(id)` | closed-set validator, active-only, malformed-tolerant | the write boundary (AC2) |
| `taxonomy.selectors.resolve_tag(id)` | follows `replaced_by`; keeps retired refs; cycle-guarded; never rewrites caller's value | the read surface (AC7/AC8) and picker pre-check |
| `accounts` D-3 account + `login_required` + session | the signed-in `user` every row attaches to | authz (AC2/C2) |
| `accounts.services.delete_account` (CASCADE-aware) | one-txn account delete that cascades FKs | profile removal (AC9) |
| `accounts/templates/accounts/profile.html` + `verify`→`profile` landing | the post-registration landing surface | the non-gating onboarding nudge (AC3) |
| `apps/core/config.py`, `apps/core/observability.py` | the house config + metric pattern | tunables + metrics |

**Established house patterns this feature mirrors** (so it reads like the code around it,
CLAUDE.md §5.5): `apps/subscriptions/` and `apps/ratings/` — an own mutable table; a single
`services.py` write path; a single `selectors.py` read path; thin `views.py` (parse → call
service/selector → redirect/render, no ORM/logic); a fail-soft `{% %}` inclusion tag that
degrades and never 500s the host page; an **activation include** in `config/urls.py` whose
removal is the rollback. **Deliberate divergences from the subscriptions twin:** (a) no
`signals.capture` import (IP-5 — no corpus emit); (b) no notices seam (no feed-notice product
here); (c) the write is a **set-replace with preserve-on-edit** (§7), not a single-row
get-or-create.

---

## 3. Proposed architecture (Step 4–5: MODULES / INTERFACES)

New Django app **`apps/interests/`**. Components, each a single responsibility, replaceable and
testable in isolation; dependencies point toward stability (taxonomy/catalog/accounts are
stable upstream; nothing imports `interests`):

```
apps/interests/
  models.py          Interest               — the one owned table (shape only, no logic)
  services.py        set_interests / clear_interests
                                            — the SINGLE write path (validate + reconcile, atomic)
  selectors.py       declared_tag_ids / declared_tags / has_declared_interests
                                            — the SINGLE read surface (resolve at read; AC8)
  errors.py          InterestValidationError — the one loud write-boundary failure (AC2)
  views.py           picker (GET) / save (POST) / clear (POST)
                                            — thin HTTP: parse → service/selector → redirect/render
  urls.py            interests:picker / interests:save / interests:clear
  templatetags/
    interests_tags.py  {% interest_prompt %} — fail-soft onboarding nudge inclusion tag (AC3)
  templates/interests/
    picker.html        the cluster-grouped picker (AC5) + empty/error states
    _prompt_slot.html  the onboarding nudge partial
  admin.py           read-only Interest admin (debugging; never a write path)
```

**Module boundaries / coupling check:**
- `models` holds **shape only** — no business logic (mirrors the subscriptions model docstring).
- `services` is the **only** module that writes `Interest` rows and the **only** caller of
  `is_valid_tag` for this feature's boundary; it owns the reconcile invariant.
- `selectors` is the **only** read surface; it is the sole place `resolve_tag` is applied to
  stored ids. **No consumer (including this app's own views) reads `Interest` rows directly**
  (AC8) — the picker reads through `selectors`, the matcher reads through `selectors`.
- `views` hold no ORM and no logic; they translate HTTP↔service/selector.
- The inclusion tag depends only on `selectors.has_declared_interests` — one read, fail-soft.

**Cross-cutting concerns placed once:** config in `apps/core/config.py`; metrics in
`apps/core/observability.py`; auth via `accounts` `login_required`; errors as one typed
exception in `errors.py`. Nothing duplicated.

---

## 4. Data design (Step 6: DATA & STATE)

### 4.1 The one owned table — `interests_interest`

```python
class Interest(models.Model):
    """One interest a user has declared — one row per (user, tag_id). Mutable membership:
    created and removed, never versioned. The *interest profile* is the SET of a user's rows;
    there is no parent 'profile' row, so an empty profile is the structural default (AC6)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE = IP-4/AC9: the profile is mutable user preference state, so it is removed when
    # the account is, with no edit to `accounts` (account.delete() cascades this FK). Contrast
    # the D-7 corpus, which anonymizes-not-purges (SC-10) — but no corpus row is written here.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="interests")
    # A SOFT D-5 ref (no DB FK): the declared taxonomy Tag.id. Validated active at the write
    # boundary (is_valid_tag); resolved at read (resolve_tag). Stored by id, never by label/slug.
    tag_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)  # when declared (debug/audit; not load-bearing)

    class Meta:
        db_table = "interests_interest"
        constraints = [
            # AC1/AC4 — one row per user per tag; declaring an already-declared tag is a no-op.
            # CASCADE means no user=NULL rows, so this is a clean composite unique (no NULL
            # collision subtlety). Its index also backs the per-user read (filter(user=...)).
            models.UniqueConstraint(fields=["user", "tag_id"],
                                    name="interests_one_per_user_tag"),
        ]
```

**One source of truth per fact:** the *current* declared set is exactly the user's rows —
nothing else stores it. No score/weight/rank column (R5/AC8 — there is nowhere to put a computed
value; scoring is the consumer's job). No `updated_at`/soft-delete (a declaration exists or it
does not; edits are row add/remove). No parent profile row (so "empty" needs no special marker —
zero rows *is* the empty profile, AC6).

**Lifecycle:** *create* on first declaration of a tag; *delete* on deselect/clear; *no mutate*
(rows are immutable — the set changes by add/remove). *Account deletion* → CASCADE removal (AC9).
*Tag rename/retire* → the row is **untouched**; meaning is recovered at read via `resolve_tag`
(AC7) — the stored id is never rewritten on a taxonomy event (M5 = 0 by construction; the id we
validated as active at write time still exists, since D-5 soft-retires and never hard-deletes).

**Concurrency:** the set-replace runs in one `transaction.atomic()`; the `unique(user, tag_id)`
constraint makes a concurrent double-declare a no-op rather than a duplicate (the reconcile
issues `bulk_create(..., ignore_conflicts=False)` over the *delta only*, so it never collides —
see §7). Two concurrent saves by the same user are serialized by the transaction; last-writer-wins
on the set is the correct semantic for "this is now my set" (AC4). Per-user, so no cross-user
contention.

**Migration:** one additive migration `interests/0001` creating the table + the unique
constraint. No change to any existing table. Reversible (`migrate interests zero` drops it).

**Retention:** lives as long as the account; removed with it. No archival (it is preference
state, not corpus).

---

## 5. Interface contracts (Step 5: INTERFACES — fully specified, no TBD)

### 5.1 Write surface — `apps/interests/services.py`

```python
def set_interests(user, tag_ids: Iterable[UUID]) -> SetResult: ...
def clear_interests(user) -> int: ...
```

**`set_interests(user, tag_ids)`** — the single write path used by the picker save (AC1/AC4/AC2).
- **Input:** the active tag ids the user checked (the picker only offers active tags).
- **Validation (AC2, all-or-nothing, before any write):** every id must pass
  `taxonomy.is_valid_tag(id)`. If **any** id is off-vocabulary, retired, or malformed → raise
  `InterestValidationError` (loud), persist **nothing** (no partial set), count
  `INTEREST_DECLARATION_REJECTED`. Also reject if the submitted count exceeds
  `config.interest_declaration_max()` (defensive cap).
- **Reconcile (atomic):** compute the new stored set per the **preserve-on-edit rule (§7)** =
  `set(tag_ids) ∪ {stored id : resolve_tag(id) is non-active}`; then in one
  `transaction.atomic()` delete `current − new` and `bulk_create` `new − current`. Idempotent:
  saving the same set is a no-op (empty delta). No `signals.capture` call (IP-5).
- **Returns** `SetResult(added: int, removed: int, total: int)` so the view can message the user
  and emit the right metric (first declaration vs. edit vs. cleared).
- **Errors:** `InterestValidationError` (→ view: re-render picker with the message, 400). No
  other expected error; a DB failure propagates loud (the view fail-softs it to a try-again — §9).

**`clear_interests(user)`** — AC9 "clear my profile at will": **delete all** the user's rows
unconditionally (including any preserved non-active refs — an explicit full wipe is the user
saying "none", distinct from a picker save). Returns the deleted count; counts
`INTEREST_PROFILE_CLEARED`. Idempotent (clearing an empty profile deletes 0).

### 5.2 Read surface — `apps/interests/selectors.py` (the AC8 contract — the matcher reads only here)

```python
def declared_tag_ids(user) -> frozenset[UUID]: ...     # the matcher contract (AC8)
def declared_tags(user) -> list[Tag]: ...              # resolved Tag objects for display/picker
def has_declared_interests(user) -> bool: ...          # cheap EXISTS for prompt/empty-state
```

**`declared_tag_ids(user) -> frozenset[UUID]`** — the **single consumer contract** (AC7/AC8).
For each stored row, `resolve_tag(id)` to its **current** meaning and return the **deduplicated**
set of resolved `Tag.id`s. Invariants: never returns a label/slug; never drops a reference that
once existed (a no-successor retired tag resolves to itself and stays in the set — AC7); two
stored ids that resolve to the same successor collapse to one (dedupe). Anonymous/`None` user →
empty set (AC6). **This is what a future matcher reads** — resolved current ids, the same space
catalog app tags resolve into (D-5/D-6), so both sides of the match speak one language.

**`declared_tags(user) -> list[Tag]`** — the same, returning resolved `Tag` objects ordered by
label, for rendering "your interests" and for the picker pre-check. Built on `resolve_tag`,
N+1-bounded by the per-user set size (small).

**`has_declared_interests(user) -> bool`** — one indexed `EXISTS` over the user's rows; drives
the onboarding prompt (show when `False`) and any empty-state branch (AC6). Anonymous → `False`.

**Contract evolution (no-break plan):** the surface is **additive-only** — a future consumer
need (e.g. resolved tags grouped by cluster, or interest intensity per IP/OQ-IP-4) is a *new*
selector over the same store, never a change to these three signatures. The matcher is built
against `declared_tag_ids` with no change here (AC8).

### 5.3 HTTP surface — `apps/interests/views.py` + `urls.py` (mounted at `interests/`)

| Route name | Method · path | Auth | Behavior |
|---|---|---|---|
| `interests:picker` | GET `interests/` | `login_required` | render the cluster-grouped active picker (AC5), pre-checking the user's resolved declared tags; empty + fail-soft-error states (§8/§9) |
| `interests:save` | POST `interests/` (→ `interests/save`) | `login_required` + CSRF | parse checked `tag_id`s → `services.set_interests` → PRG back to `interests:picker` with a success/validation message |
| `interests:clear` | POST `interests/clear` | `login_required` + CSRF | `services.clear_interests` → PRG to `interests:picker` (AC9) |

No interest/profile id ever appears in a URL — a row is addressed by `request.user` + `tag_id`
only, so a user can only ever touch **their own** profile (no IDOR; §11). Anonymous requests are
redirected to sign-in by `login_required` (C2).

### 5.4 Onboarding inclusion tag — `{% interest_prompt %}` (`interests_tags`)

A **fail-soft** inclusion tag (the ratings/subscriptions slot pattern) rendered by one content
line added to `accounts/templates/accounts/profile.html` (the post-registration landing page).
It reads only `selectors.has_declared_interests(request.user)`; when `False` it renders a gentle
"Tell us what you're interested in →" nudge linking to `interests:picker` (encouraged, **never a
blocker** — AC3/AC6); when `True` it renders nothing. **Any** exception → render nothing + count
`INTEREST_PROMPT_DEGRADED` (never 500s the profile page). The single content line in
`profile.html` is the **second half of the activation switch** (§16) — its removal + removing the
`config/urls` include fully rolls the feature back.

> **Why the prompt lives on the profile landing page, not in `verify`'s redirect:** it reuses
> the existing `verify`→`profile` landing with **zero edit to auth logic** — the house pattern is
> a fail-soft inclusion tag in another feature's *template* (ratings/subscriptions did exactly
> this to `app_page.html`), never a behavioral change to another feature's *view*. It satisfies
> AC3 (a new, empty-profile user landing on profile after registration sees the prompt) while
> keeping `interests`' footprint to its own app + one content line.

---

## 6. Key flows (Step 6/7 — happy path + the seams)

**Declare (AC1) / Edit (AC4):** GET `interests:picker` → render `list_clusters()` grouped, each
active tag pre-checked iff its id ∈ `{t.id for t in declared_tags(user) if t active}` → user
toggles, POST `interests:save` → `set_interests` validates all-active (AC2) → atomic reconcile
(§7) → PRG back to the picker showing the new set as selected (AC1 "shown as selected on next
visit"; AC4 "additions present, removals gone").

**Onboarding (AC3):** `verify` (registration complete) → `accounts:profile` → the
`{% interest_prompt %}` tag sees an empty profile → renders the nudge → user clicks through to
the picker (or ignores it and keeps using the site — non-gating).

**Empty profile (AC6):** zero rows is the default. `declared_tag_ids` → empty set,
`has_declared_interests` → `False`, the picker renders with nothing checked and a "no interests
yet" hint. No surface assumes non-empty; nothing errors.

**Account deletion (AC9):** `accounts.delete_account` → `account.delete()` → CASCADE removes all
the user's `Interest` rows in the same transaction. **No edit to `accounts`** — the CASCADE FK is
the whole mechanism.

**Matcher read (AC8, future consumer):** the unbuilt `weekly-digest`/matcher calls
`interests.selectors.declared_tag_ids(user)` → a set of resolved current `Tag.id`s → intersects
with a catalogued app's resolved tag set (D-6) for Ring-0. Built against this surface with **no
change here**.

---

## 7. The load-bearing seam — set-replace with preserve-on-edit (AC4 × AC7)

This is the one place the design is more than a CRUD twin, so it gets explicit rigor.

**The tension.** AC4 says a save is a **set-replace** ("the profile reflects *exactly* the new
set"). AC5 says the picker shows **only active** tags. AC7 says a stored reference to a
**renamed/retired** tag is **never silently dropped** (M5 = 0). Because `retire_tag` allows a
**no-successor** retirement (§1 ledger, verified), a user can hold a stored id that `resolve_tag`
maps to a **non-active** tag — which the active-only picker **cannot show or pre-check**. A naive
set-replace ("new set = exactly what was submitted") would **delete that un-showable row on the
next save**, silently dropping it — violating AC7.

**The rule.** On `set_interests(user, submitted_ids)`:
```
preserved = { id for id in current_stored_ids if resolve_tag(id) is not ACTIVE }   # un-showable refs
new_set   = set(submitted_ids) ∪ preserved
delete current_stored_ids − new_set ;  insert new_set − current_stored_ids        # one atomic txn
```
- A **no-successor retired** stored id resolves to itself (non-active) → **preserved** (the user
  never saw it, so they did not deselect it — AC7 holds across edits).
- A **renamed/merged** stored id resolves to its **active successor**, which the picker **shows
  and pre-checks**. If the user keeps it checked, `submitted_ids` carries the *successor* id, so
  `new_set` stores the successor and the old id (which resolves active → not preserved) is
  dropped — a **healthy normalization** toward active ids, with meaning preserved (still resolves
  to the same successor; M5 stays 0). If the user unchecks it, it is an **explicit** removal.
- A genuinely **deselected active** tag → in `current`, not in `submitted`, resolves active →
  not preserved → deleted (AC4 removals gone).

**Why this is correct, not clever:** it is the minimal rule that satisfies AC4 and AC7
simultaneously, derived from a *real* D-5 state (no-successor retire), not speculation. It is
encapsulated in the single write path, named (`_preserved_unshowable_ids`), and unit-tested in
isolation (§12). `clear_interests` deliberately bypasses it (an explicit full wipe is the user
saying "none at all" — AC9).

---

## 8. UX flow (Step — user-facing states)

**Picker (`interests/picker.html`, extends the accounts/pages base):**
- **Loaded:** clusters as `<section>`s (heading = cluster name + definition where present), each
  listing its active tags as labelled checkboxes (label + definition; never raw ids/retired tags
  — AC5), pre-checked for the user's resolved declared tags. A "pick a few" hint when below
  `interest_suggested_minimum()` (IP-3 — copy only, never blocks save). One Save button (POST
  `interests:save`) + a "Clear all" (POST `interests:clear`).
- **Empty profile:** identical picker, nothing checked, a one-line "You haven't picked any
  interests yet" hint (AC6) — not an error.
- **Vocabulary-empty edge:** `list_clusters()` returns nothing → "No interests are available
  yet" copy, no crash (defensive; the seeded taxonomy makes this unlikely).
- **Error (read fail-soft, §9):** if the picker read raises → a degraded "Couldn't load
  interests, try again" page (not a 500) + `INTEREST_PICKER_DEGRADED`.
- **Save outcomes (PRG + Django messages):** success ("Saved your interests"); validation reject
  ("That selection isn't valid — please try again", AC2) re-rendering the picker; write failure
  ("Couldn't save, please try again") with the durable state honest (no partial set).

**Onboarding nudge:** the gentle one-line `{% interest_prompt %}` on the profile page (§5.4) —
encouraged, skippable, disappears once any interest is declared.

All user/tag text rendered through Django auto-escaping (no `|safe`) — XSS-safe (§11).

---

## 9. Failure modes (Step 7: FAILURE — per component, never silent)

| Component | Failure | Detection | Response |
|---|---|---|---|
| `set_interests` validation | off-vocabulary/retired/malformed id (AC2) | `is_valid_tag` returns `False` | raise `InterestValidationError`; **no write**; count `INTEREST_DECLARATION_REJECTED`; view → 400 + message |
| `set_interests` over-size | abusive over-large POST | submitted count > `interest_declaration_max()` | same loud rejection (resource cap, §5.4) |
| `set_interests` reconcile | DB error mid-transaction | exception in `atomic()` | whole save rolls back (no partial set, AC2/AC4); propagates loud → view fail-softs to "try again" (state honest) |
| `taxonomy.is_valid_tag` / `resolve_tag` | taxonomy DB slow/down | exception bubbles | write path: propagates loud (a profile has no meaning without the vocabulary). read path: see picker/matcher rows below |
| `selectors.declared_tag_ids` (matcher read) | resolve error | exception | **propagates loud** to the consumer — the matcher must not silently match on a half-resolved set; the consumer owns its own degradation policy |
| `picker` view read | `list_clusters`/`declared_tags` raises | try/except in view | fail-soft degraded page + `INTEREST_PICKER_DEGRADED` (never 500) |
| `{% interest_prompt %}` tag | any exception | try/except in tag | render nothing + `INTEREST_PROMPT_DEGRADED` (never 500s the profile page) |
| account deletion | CASCADE | n/a | structural — the FK guarantees removal in the delete txn (AC9) |

**Principle:** the **write** fails **loud** where correctness depends on it (validation, the
atomic reconcile) so an invalid or partial set never persists; the **read surfaces a human
touches** (picker, prompt) fail **soft** so a fault never 500s a page; the **matcher read** fails
**loud** to its consumer (it is not a human surface — the consumer decides degradation).

---

## 10. Non-functional handling (Step — perf/scale + config)

**Performance / scale (holds at 100×, D-2/C4):** picker render = `list_clusters()` (prefetched,
no N+1) + one indexed per-user `Interest` read for pre-check. Profile read = one indexed per-user
query + a bounded `resolve_tag` per stored id (sets are small — bounded by the active vocabulary;
the documented 100× growth path, inherited from D-5, is a cached resolved projection). Reconcile
= one transaction, delta-only writes. No cross-user query, no table scan.

**Config tunables (the things likely to change live in config, CLAUDE.md §5.2 — added to
`apps/core/config.py` + `validate_all`):**
- `interest_suggested_minimum() -> int` (default **3**) — the "pick a few" nudge threshold (IP-3;
  **copy only, never a validation floor**).
- `interest_declaration_max() -> int` (default **500**) — defensive per-save request-size cap
  (safety, not a product maximum; comfortably above any realistic active-vocabulary size).

---

## 11. Security model (Step 10: SECURITY)

- **AuthN/AuthZ:** all three routes `login_required` (C2); mutations POST + CSRF. No new identity
  or role — the base D-3 `user`.
- **No IDOR (structural):** no interest/profile id in any URL; a row is addressed by
  `request.user` + `tag_id`, so a user can only read/write their own profile. `declared_*`
  selectors are always scoped to the passed `user`.
- **Closed-vocabulary input (AC2):** every submitted id validated active via `is_valid_tag` at
  the write boundary — no tag coining, no injection of arbitrary ids; malformed ids are tolerated
  as invalid, never crash (the selector is malformed-tolerant).
- **No PII / no secrets:** the store holds `(user_fk, tag_id)` — declared interests, no free text,
  no PII beyond the account link. CASCADE deletion satisfies the deletion right for this
  preference state (AC9); no anonymized residue (unlike the D-7 corpus, none is written here).
- **XSS:** all rendered tag labels/definitions go through Django auto-escaping; no `|safe`.
- **Attributability:** writes are by the authenticated session user; metrics/logs carry the
  request-context account id via the existing `RequestContextMiddleware`.

---

## 12. Observability & tests (Step 11–12: OPERATIONS / TESTS)

**Metrics (added to `apps/core/observability.py`; mapped to brief M1–M6):**
- `INTEREST_DECLARED` — a save that takes a profile from 0 → ≥1 tag (**M1** declaration-rate
  numerator; analyst joins to registration timestamps for "within onboarding").
- `INTEREST_PROFILE_UPDATED` — a save that changes an already-non-empty profile (**M4** edit
  rate).
- `INTEREST_PROFILE_CLEARED` — `clear_interests` (or a save to empty).
- `INTEREST_DECLARATION_REJECTED` — AC2 invalid-id/over-size rejection (expected; **not**
  alertable).
- `INTEREST_PICKER_DEGRADED` / `INTEREST_PROMPT_DEGRADED` — fail-soft read degradations.
- **M5 reference integrity** reuses the taxonomy `TAXONOMY_REFERENCE_BREAK` counter (emitted by
  `resolve_tag` on a cycle); plus an ops selector `count_unresolvable() -> int` (stored ids whose
  `resolve_tag` is `None`) which is **0 by construction** (validated active at write; D-5 never
  hard-deletes) — a cheap invariant check, not a live metric.
- **M2 richness / M3 coverage / M6 match-readiness** are **analyst-derived reads** over the store
  + catalog (not counters) — documented for the Release/Retro stage, not emitted here.

**The one actionable alert:** an **unexpected `set_interests` write failure** (DB error, not a
validation reject) — i.e. a spike in save-path exceptions / `INTEREST_PICKER_DEGRADED`.
Validation rejections and the empty-until-adoption M-metrics are **not** alerts.

**Debugging:** contextual logs (request id + account id via existing middleware); read-only
`Interest` admin for inspection.

**Test plan (each module in isolation; every AC → a concrete check — full table in the Stage-4
`TEST_PLAN.md`):** model (unique constraint, CASCADE-on-delete AC9); `set_interests`
(happy declare AC1, set-replace add/remove AC4, all-or-nothing reject on one bad id AC2,
over-size cap, idempotent same-set, **§7 preserve-on-edit: a no-successor retired stored id
survives a re-save** AC7, successor normalization, no `signals.capture` import IP-5);
`clear_interests` (full wipe incl. preserved); selectors (`declared_tag_ids` resolves + dedupes +
keeps retired AC7/AC8, empty user AC6, anonymous); views (login-required/CSRF, PRG, no-IDOR,
picker fail-soft); inclusion tag (renders when empty, nothing when declared, fail-soft); edge
cases (empty profile, empty vocabulary, malformed id, huge submit).

---

## 13. Tech-stack decision (Step 14 — reuse, **no new global ADR**)

Django + DRF-free server-rendered templates + PostgreSQL under `apps/` — **inherited from
[D-4](../../DECISIONS.md)**; account/role from **[D-3](../../DECISIONS.md)**; tag reference,
validate, resolve from **[D-5](../../DECISIONS.md)**. This feature introduces **no repo-wide
decision** (mirroring `app-subscriptions`/`ratings-reviews`, which also reused the stack +
existing contracts): the store shape, the preserve-on-edit reconcile, the config tunables, and
the no-emit posture are all **feature-local** and **bind no later feature** — so they live in
[features/interest-profile/DECISIONS.md](DECISIONS.md) (IP-DESIGN-1…4), not in the global log.
The **read surface `declared_tag_ids` is the cross-feature contract** the matcher consumes; it is
additive-only by design, but it is published as part of this feature (CODEMAP), not as a new ADR
(it consumes D-5, it does not amend it).

---

## 14. Alternatives considered (Step 9: TRADE-OFFS — ≥2, with sacrifices)

**A. Parent `Profile` row + child `ProfileTag` rows.** Rejected: a parent row makes "empty
profile" a *state to create and check* (does the row exist? is it empty?) instead of the
structural default (zero child rows). It adds a lifecycle (create-on-first-visit) and a second
source of truth, for no benefit — there is no profile-level attribute to store at MVP (onboarding
"seen/skipped" is deliberately not tracked — §17). The membership-only model makes AC6 free.
*Sacrifice of the chosen model:* no place to hang a future profile-level field (e.g. a persisted
"onboarding dismissed" flag) — accepted; it is an additive table/column if ever needed (named,
not built — IP/§17).

**B. Naive set-replace ("new set = exactly submitted").** Rejected: silently drops a
no-successor-retired stored ref on the next save → violates AC7/M5. The §7 preserve rule is the
minimal fix. *Sacrifice:* the reconcile is marginally more than a single `bulk` replace — a few
lines, fully unit-tested, encapsulated in the one write path.

**C. Emit a D-7 `interest_declared` event per change** (treat declaration as a signal). Rejected:
contradicts IP-5/AS-5 — declaration is **preference state, not behavior**; emitting would couple
this app to `signals.capture` and pollute the corpus with non-impression events. *Sacrifice:* no
behavioral trail of *when* interests changed beyond `created_at` + metrics — accepted; an additive
D-7 kind is the named later path if a churn consumer ever needs it.

**D. Store cluster-level interests too** (a profile entry can be a whole cluster). Rejected by
**IP-1/DN-15** — the matcher matches app **tags**; cluster adjacency is the matcher's job over the
D-5 cluster anchor. Clusters are a **picker selection aid** only ("select a cluster" expands to
its member active tags client-/server-side and stores those tag ids). *Sacrifice:* a user who
"means the whole cluster" is stored as its current member tags, not the cluster concept — accepted
(IP-1 rationale: avoids ambiguous, duplicated state the matcher would have to reconcile).

---

## 15. Acceptance-criteria → design-element coverage (exit criterion)

| AC | Design element(s) |
|---|---|
| **AC1** declare | `set_interests` (§5.1) + `Interest` unique row (§4) + picker save (§5.3); pre-checked on return via `declared_tags` |
| **AC2** closed vocabulary | `set_interests` all-or-nothing `is_valid_tag` validation + `InterestValidationError`, no partial write (§5.1/§9) |
| **AC3** onboarding prompt | `{% interest_prompt %}` fail-soft tag on the `verify`→profile landing; encouraged, non-gating (§5.4/§6) |
| **AC4** edit anytime | `set_interests` set-replace reconcile (§7); PRG re-render shows new set (§6/§8) |
| **AC5** grouped readable picker | `picker.html` over `list_clusters()` (active-only, labels+definitions, prefetched) (§8) |
| **AC6** empty profile valid | no parent row — zero rows is the default; `has_declared_interests`/`declared_tag_ids` empty; empty-state UX (§4/§5.2/§8) |
| **AC7** survives rename/retire | stored id never rewritten; `resolve_tag` at read + **§7 preserve-on-edit** for no-successor retire (M5 = 0) |
| **AC8** readable as `Tag.id`s | `declared_tag_ids` single read surface (resolved, deduped); no consumer reads storage (§5.2) |
| **AC9** personal mutable state | CASCADE user FK (account-deletion removal, no `accounts` edit) + `clear_interests` (§4/§5.1/§6) |

Every AC maps to ≥1 design element; every component (§9) has a documented failure behavior; no
"TBD" in any contract (§5). Exit criteria met.

---

## 16. Rollout strategy

**Additive, no schema risk:** one new app, one new table (`interests/0001`), no change to any
existing table. No data migration; no backfill (empty profile is the valid default for every
existing account — AC6).

**Two-part activation switch (the rollback, mirroring subscriptions):**
1. the `config/urls.py` `interests/` include (the routes), and
2. the **one content line** in `accounts/profile.html` rendering `{% interest_prompt %}`.

Removing both fully disables the feature with **zero data migration**; `migrate interests zero`
then drops the table if a full teardown is wanted. **No feature flag** — "off" = don't include
the URLconf + drop the prompt line (the same pattern app-pages/ratings/subscriptions established).

**Backward compatibility:** nothing consumes `interests` yet (the matcher is future), so there is
no consumer to break; the published read surface is additive-only from day one (§5.2/§13).
Migration order: `interests/0001` is independent (no FK to anything but `accounts`, which exists).

---

## 17. Self-critique & simplification pass (Step 13)

- *"Is the §7 preserve rule over-engineering?"* — No: it is the minimal rule that keeps AC7
  ("never silently dropped") true across **edits**, and the triggering state (no-successor retire)
  is a **verified, reachable** D-5 operation, not speculation. Without it a single later edit
  silently breaks a stored ref and M5 ≠ 0. Kept, encapsulated, unit-tested in isolation.
- *"Should onboarding 'skip/dismiss' be persisted so an empty-profile user isn't re-nudged?"* —
  Deliberately **not** built. Tracking dismissal needs a profile-level field → a parent row →
  AC6 stops being structural. The nudge is a gentle one-line link that self-resolves on first
  declaration; nagging an empty-profile user with one quiet line is acceptable at MVP. Persisted
  dismissal is the **named later change** if telemetry shows it annoys (additive column/table).
- *"Two read functions returning ids vs. Tags — duplication?"* — No: `declared_tag_ids` is the
  **consumer contract** (ids, the match space, AC8); `declared_tags` is the **display** read
  (resolved objects, ordered). Different responsibilities, both thin over `resolve_tag`. Kept.
- *"Why no `signals.capture` at all?"* — That **is** the proof of IP-5: the cleanest way to
  guarantee no D-7 emit is to not import the module. The build will assert the import is absent.
- **Simplification removed:** an early sketch had a `Profile` parent row and an `is_onboarded`
  flag — both cut (§14-A, §17 above) because nothing at MVP needs them and they cost AC6's
  structural simplicity. No speculative abstraction remains (CLAUDE.md §5.5).

---

## 18. First version, increments, revisit flags (Step 14: DELIVER)

**Smallest useful first version (this feature):** the app as specified — `Interest` store,
`set_interests`/`clear_interests`, the three selectors, the picker views + template, the
onboarding inclusion tag, the activation include, config + metrics, admin, tests. No increments
deferred *within* this feature (it is already a thin slice).

**Revisit once real usage exists (flagged, not built):**
- **Onboarding gating** — revisit when `weekly-digest` ships and declaration becomes
  load-bearing (IP-2; the brief's R1 mitigation hook).
- **Persisted onboarding dismissal** — if telemetry shows re-nudge friction (§17).
- **Cached resolved projection** — the D-5-inherited 100× growth path if per-read `resolve_tag`
  cost ever matters (§10).
- **Interest intensity** (OQ-IP-4) and an **"interest changed" D-7 signal** (IP-5) — additive,
  named, not built.

---

## 19. Decisions & open questions (pointers)

Feature-local design decisions logged in [DECISIONS.md](DECISIONS.md) as **IP-DESIGN-1…4**
(membership-only no-parent store; preserve-on-edit reconcile; no-D-7-emit posture; onboarding via
fail-soft inclusion tag on the profile landing). Open questions: **OQ-IP-3** (empty-profile
semantics — owned by the future matcher) and **OQ-IP-4** (interest intensity — additive later)
remain open and **out of scope here**, re-affirmed (not blockers). Reuses **D-3/D-4/D-5** as-is —
**no new global ADR**.

**Gate:** raised as **DN-16** in [CONTROL.md](../../CONTROL.md) (approve this DESIGN incl. the §7
preserve-on-edit rule, the onboarding-via-inclusion-tag placement, and the additive read-surface
contract). **No Stage advance until approved.**
