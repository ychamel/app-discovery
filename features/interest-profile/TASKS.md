# TASKS — interest-profile

*Stage 3 artifact (Planner / Tech Lead). Upstream: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
(DN-15 → approved) and the **ratified** [DESIGN.md](DESIGN.md) (DN-16 → approved; reuses
[D-3](../../DECISIONS.md)/[D-4](../../DECISIONS.md)/[D-5](../../DECISIONS.md) as-is — **no new
global ADR**). Produces an ordered, independently-verifiable task list; full per-AC verification is
written by the Senior Engineer at Stage 4 in `TEST_PLAN.md`. See
[phase-3-planner.md](../../process/personas/phase-3-planner.md).*

> **No re-design.** Every task below traces to a `DESIGN.md` section; nothing here adds a contract
> or decision the design does not already make. The only schema touch is one **additive** migration
> creating `interests_interest` inside the new `apps/interests/` (DESIGN §4). The only touch outside
> the new app is the one sanctioned `{% interest_prompt %}` content line in
> `accounts/templates/accounts/profile.html` (DESIGN §5.4) — the second half of the activation
> switch. This feature is a **simpler near-twin of the closed-out `apps/subscriptions/`** — match
> its conventions (CLAUDE.md §5.5) with the design's two deliberate simplifications (**no
> `signals.capture` import** IP-5; **no parent profile row** → empty is the structural default) and
> the **one harder seam**: the §7 set-replace **preserve-on-edit** reconcile (T-02).

---

## Ordering rationale (sequencing rules → this order)

1. **Schema/data → core logic → interfaces → UI → telemetry → docs.** Spine: the feature's own
   `Interest` store (T-01) → the integrity core, the single write path with the §7 preserve-on-edit
   reconcile + config + write metrics (T-02) → the single read surface the matcher consumes (T-03) →
   the thin HTTP views + picker template + activation include (T-04) → the onboarding inclusion tag +
   the one `profile.html` content line (T-05) → read-only admin + docs (T-06).
2. **Risk first.** The one genuinely load-bearing seam the design front-loads (DESIGN §1/§7/§14) —
   the **set-replace with preserve-on-edit** reconcile that keeps AC4 (set-replace) and AC7 (a
   no-successor-retired ref is never silently dropped, M5 = 0) simultaneously true across edits —
   lands at **T-02** and is unit-tested in isolation against a *real* D-5 no-successor retire state
   before any UI work. The onboarding template edit (the one touch outside the new app) is isolated
   to **T-05**, a content-only one-line insertion with a one-line rollback.
3. **Each task leaves the system working and releasable.** T-01 is a new model + migration with no
   routes. T-02/T-03 add unreached code paths. The picker becomes reachable at T-04 (the
   `config/urls.py` include) but is not yet linked from anywhere; the onboarding nudge appears only
   at T-05. **The activation switch** is the `config/urls.py` include (T-04) **plus** the one
   `{% interest_prompt %}` line in `accounts/profile.html` (T-05) — "off" = remove both (DESIGN §16).

**File-collision note (tasks are sequential — no two edit the same file concurrently):**
- `apps/core/observability.py` is touched by **T-02** (`INTEREST_DECLARED`/`_PROFILE_UPDATED`/
  `_PROFILE_CLEARED`/`_DECLARATION_REJECTED`), **T-04** (`INTEREST_PICKER_DEGRADED`) and **T-05**
  (`INTEREST_PROMPT_DEGRADED`); they run in order, never concurrently. The **M5** counter reuses the
  existing `TAXONOMY_REFERENCE_BREAK` ([observability.py:35](../../apps/core/observability.py)) —
  **not re-added.**
- `apps/core/config.py` is touched once (**T-02**: `interest_suggested_minimum` +
  `interest_declaration_max`, both + their `validate_all` entries).
- `config/settings.py` `INSTALLED_APPS` once (**T-01**); `config/urls.py` once (**T-04**);
  `apps/accounts/templates/accounts/profile.html` once (**T-05** — one content line, no auth-logic
  edit).
- The reused taxonomy D-5 surface (`is_valid_tag`/`resolve_tag`/`list_clusters`/`list_active_tags`)
  and `accounts.delete_account` CASCADE posture are **unchanged** — this feature only *reads*/relies
  on them. This app **never imports `signals.capture`** (IP-5 — asserted in T-02).

---

## T-01 — Scaffold `apps/interests` + the `Interest` membership store (CASCADE) + migration

- **Description.** Create the new Django app per DESIGN §3/§4.1: `__init__.py`, `apps.py`
  (`AppConfig`, `name="apps.interests"`), `tests/`. Register `"apps.interests"` in `INSTALLED_APPS`.
  Implement `apps/interests/models.py` exactly to the DESIGN §4.1 contract — **membership-only, no
  parent profile row** (so empty is the structural default, AC6):
  - `Interest` — `id` (UUID pk, default `uuid4`, `editable=False`); `user` FK
    **`on_delete=CASCADE`**, `related_name="interests"` (IP-4/AC9 — the profile is mutable preference
    state, removed when the account is, with **no edit to `accounts`**: `account.delete()` cascades
    this FK, DESIGN §4.1/§6); `tag_id` (`UUIDField`, **soft D-5 ref, no DB FK** — validated active at
    the write boundary, resolved at read; stored by id, never label/slug); `created_at`
    (`auto_now_add`; debug/audit, not load-bearing).
  - **Structural absences (AC8/CLAUDE.md §5.3):** **no** `score`/`weight`/`rank` column (nowhere to
    put a computed value — scoring is the consumer's job, R5/AC8); **no** `updated_at`/soft-delete (a
    declaration exists or it does not; the set changes by row add/remove); **no** parent profile row
    (zero rows *is* the empty profile, AC6).
  - `Meta`: `db_table="interests_interest"`; the **unique constraint** `interests_one_per_user_tag`
    on `(user, tag_id)` (AC1/AC4 — one row per user×tag; declaring an already-declared tag is a
    no-op; CASCADE means no `user=NULL` rows, so this is a clean composite unique whose index also
    backs the per-user read `filter(user=...)`, DESIGN §4.1).
  - **No business logic in the model** — all invariants (validation, the §7 reconcile) are enforced
    by the write path (T-02). The model declares shape only (mirrors the subscriptions model
    docstring).
  - Generate `interests/0001_initial`.
- **Dependencies.** none (foundational — the write path T-02 and read path T-03 consume it).
- **Definition of done.**
  - `apps.interests` imports and appears in `INSTALLED_APPS`; `python manage.py check` clean.
  - `makemigrations interests` produces `0001_initial` creating `interests_interest` with the unique
    constraint; `makemigrations --check` clean after commit.
  - A **structural test** asserts: the unique constraint on `(user, tag_id)` is present (AC1); the
    `user` FK `on_delete` is **CASCADE** (DESIGN §4.1); the table has **no**
    score/weight/rank/updated_at column (AC8 / one-job).
  - **AC9 deletion test:** create `Interest` rows for a user via the ORM, call
    `accounts.delete_account(account)` ([accounts/services.py:58](../../apps/accounts/services.py)),
    assert the user's `Interest` rows are **gone** (CASCADE) with no edit to `accounts`. (No corpus
    event is ever written by this feature, so there is no anonymize-not-purge half to verify —
    contrast subscriptions, IP-5.)
  - The migration is reversible: `migrate interests 0001` → `migrate interests zero` →
    `migrate interests 0001` all succeed (DESIGN §16).
  - `ruff` clean; full suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/interests/` (new package: `__init__.py`, `apps.py`, `models.py`,
  `migrations/0001_initial.py`, `tests/__init__.py`, `tests/test_models.py`), `config/settings.py`
  (`INSTALLED_APPS`).

## T-02 — The single write path: `services.py` (`set_interests`/`clear_interests`) + the §7 preserve-on-edit reconcile + `errors.py` + config + write metrics

- **Description.** Implement `apps/interests/services.py` (+ `apps/interests/errors.py`) exactly to
  the DESIGN §5.1/§7 contract — **the only place `Interest` rows are created/deleted, and the only
  caller of `is_valid_tag` for this feature's boundary.** This is the riskiest seam (DESIGN §7/§14 —
  the set-replace **preserve-on-edit** reconcile); build and verify it in isolation before any UI
  work. **This module does NOT import `signals.capture` (IP-5).**
  - `SetResult` — a small `@dataclass(frozen=True)` with `added: int`, `removed: int`, `total: int`
    (so the view can message the user and emit the right metric — first declaration vs. edit vs.
    cleared, DESIGN §5.1).
  - `set_interests(user, tag_ids: Iterable[UUID]) -> SetResult` — the single picker-save write path
    (AC1/AC2/AC4):
    1. **Validation (AC2, all-or-nothing, before any write):** reject if the submitted count exceeds
       `config.interest_declaration_max()` (defensive cap, §5.4); then every id must pass
       `taxonomy.is_valid_tag(id)` — if **any** id is off-vocabulary/retired/malformed → raise
       `InterestValidationError` (loud), persist **nothing** (no partial set), count
       `INTEREST_DECLARATION_REJECTED`.
    2. **Reconcile (§7, atomic):** compute `preserved = {id for id in current_stored_ids if
       resolve_tag(id) is not active}` (the un-showable refs — a no-successor retired stored id the
       active-only picker can't show); `new_set = set(tag_ids) ∪ preserved`; then in **one**
       `transaction.atomic()` delete `current − new_set` and `bulk_create` `new_set − current`
       (delta-only, so the `unique(user, tag_id)` never collides). Encapsulate the preserve rule in a
       named helper (`_preserved_unshowable_ids`) so it is unit-testable in isolation. Idempotent:
       saving the same set is a no-op (empty delta).
    3. Emit the right metric from the delta + prior state: `INTEREST_DECLARED` on 0 → ≥1 (M1);
       `INTEREST_PROFILE_UPDATED` on a change to an already-non-empty profile (M4);
       `INTEREST_PROFILE_CLEARED` on a save to empty.
  - `clear_interests(user) -> int` (AC9) — **delete all** the user's rows unconditionally
    (**including** any preserved non-active refs — an explicit full wipe is the user saying "none",
    distinct from a picker save, so it deliberately **bypasses** the §7 preserve rule, DESIGN
    §5.1/§7). Returns the deleted count; counts `INTEREST_PROFILE_CLEARED`. Idempotent (clearing an
    empty profile deletes 0).
  - `errors.py`: `InterestValidationError` (the one typed loud write-boundary failure, AC2).
  - **Config (DESIGN §10) — added to `apps/core/config.py` with the existing `_positive_int`
    precedence + a `validate_all()` entry each:** `interest_suggested_minimum() -> int` (default
    **3** — the "pick a few" nudge threshold, IP-3, **copy only, never a validation floor**; consumed
    by the picker, T-04) and `interest_declaration_max() -> int` (default **500** — the defensive
    per-save request-size cap, safety not a product maximum).
  - **Metrics (DESIGN §12) — added to `apps/core/observability.py`:** `INTEREST_DECLARED`,
    `INTEREST_PROFILE_UPDATED`, `INTEREST_PROFILE_CLEARED`, `INTEREST_DECLARATION_REJECTED`.
- **Dependencies.** T-01 (`Interest` store).
- **Definition of done.** Tests against the **real taxonomy D-5 surface** (real seeded tags +
  `retire_tag` to create the no-successor state; no mocking of `is_valid_tag`/`resolve_tag`):
  - **AC1** first declaration of active tags → exactly those rows persisted; `set_interests` returns
    `SetResult(added=n, removed=0, total=n)`; `INTEREST_DECLARED` emitted.
  - **AC4 set-replace** add **and** remove on an existing profile → the stored set is **exactly** the
    new set (additions present, removals gone); `INTEREST_PROFILE_UPDATED` emitted.
  - **AC2 all-or-nothing** a save containing **one** off-vocabulary/retired/malformed id → raises
    `InterestValidationError`, **nothing persisted** (the prior set is intact), `INTEREST_DECLARATION_REJECTED`
    counted.
  - **over-size cap** a submit exceeding `interest_declaration_max()` → same loud rejection, no write.
  - **idempotent** saving the identical current set → empty delta, no row churn.
  - **§7 preserve-on-edit (AC7/M5) — the load-bearing test:** a user holds a stored id for a tag that
    is then `retire_tag`'d **with `replaced_by=None`** (verified no-successor state); the active-only
    picker can't show it, so a subsequent `set_interests(other_active_ids)` (not including it)
    **preserves** that retired ref (it survives the re-save — never silently dropped); a separate
    **successor-normalization** case: a stored id whose tag was retired **with** a successor, re-saved
    with the successor checked, normalizes toward the active successor id (old id dropped, meaning
    preserved — still resolves to the same successor; M5 stays 0).
  - **AC9 clear** `clear_interests` deletes **all** rows including a preserved non-active ref; returns
    the count; `INTEREST_PROFILE_CLEARED`; clearing an empty profile → 0.
  - **IP-5 no-emit (structural):** a test asserts `apps.interests.services` does **not** import
    `signals.capture` (the cleanest proof declaration is preference state, not behavior — DESIGN
    §17).
  - `config.interest_suggested_minimum()` / `interest_declaration_max()` return defaults and are
    covered by `validate_all()`.
  - `ruff` clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/interests/services.py` (new), `apps/interests/errors.py` (new),
  `apps/core/config.py` (two tunables + `validate_all`), `apps/core/observability.py` (four
  constants), `apps/interests/tests/test_services.py`.

## T-03 — The single read surface: `selectors.py` (`declared_tag_ids`/`declared_tags`/`has_declared_interests`) + the M5 ops selector

- **Description.** Implement `apps/interests/selectors.py` exactly to the DESIGN §5.2 contract — the
  **only** read surface and the **only** place `resolve_tag` is applied to stored ids; **no consumer
  (including this app's own views) reads `Interest` rows directly** (AC8). No write, no scoring.
  - `declared_tag_ids(user) -> frozenset[UUID]` — the **single matcher contract** (AC7/AC8): for each
    stored row `resolve_tag(id)` to its **current** meaning, return the **deduplicated** set of
    resolved `Tag.id`s. Invariants: never returns a label/slug; a no-successor retired tag resolves
    to itself and **stays** in the set (AC7); two stored ids resolving to the same successor collapse
    to one (dedupe); anonymous/`None` user → empty `frozenset` (AC6). This is the future matcher's
    read — resolved current ids in the same space catalog app tags resolve into (D-5/D-6).
  - `declared_tags(user) -> list[Tag]` — the same, returning resolved `Tag` objects **ordered by
    label**, for rendering "your interests" and the picker pre-check; bounded by the per-user set
    size (small).
  - `has_declared_interests(user) -> bool` — one indexed `EXISTS` over the user's rows; drives the
    onboarding prompt (show when `False`) and the empty-state branch (AC6); anonymous → `False`.
  - `count_unresolvable() -> int` — the **M5** ops invariant selector (DESIGN §12): count stored ids
    whose `resolve_tag` is `None`. **0 by construction** (validated active at write; D-5 soft-retires,
    never hard-deletes) — a cheap invariant check, not a live metric. (The live M5 break counter is
    the taxonomy `TAXONOMY_REFERENCE_BREAK`, emitted by `resolve_tag` itself — **reused, not
    re-added.**)
- **Dependencies.** T-01 (`Interest` store). (Independent of T-02 — reads only; both precede T-04.)
- **Definition of done.** Tests over fixtures (real D-5 resolve, real `retire_tag` states):
  - **AC8** `declared_tag_ids` returns a `frozenset` of resolved current `Tag.id`s; never a
    label/slug.
  - **AC7** a stored id whose tag was renamed/merged resolves to its **successor** in the set; a
    **no-successor retired** stored id resolves to **itself** and is **kept** (not dropped); two ids
    resolving to one successor **dedupe** to a single entry.
  - **AC6** a user with zero rows → `declared_tag_ids` empty, `has_declared_interests` `False`;
    anonymous/`None` → empty / `False`.
  - `declared_tags` returns resolved `Tag` objects **ordered by label**.
  - `count_unresolvable()` returns **0** for a profile built only through the validated write path
    (the invariant), and is exercised to return >0 only via a deliberately hand-inserted bad id
    (proving it detects, not that the path produces one).
  - **no N+1:** `declared_tags`/`declared_tag_ids` resolve a per-user set in a **bounded** query
    count for the set size (`assertNumQueries`, DESIGN §10).
  - `ruff` clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/interests/selectors.py` (new),
  `apps/interests/tests/test_selectors.py`.

## T-04 — Thin HTTP views (`picker`/`save`/`clear`) + `urls.py` + picker template + activation include

- **Description.** Implement `apps/interests/views.py` + `apps/interests/urls.py` +
  `apps/interests/templates/interests/picker.html` exactly to the DESIGN §5.3/§6/§8 contract, then
  add `path("interests/", include("apps.interests.urls"))` to `config/urls.py` — the **first half of
  the activation switch** (DESIGN §16). Views hold **no business logic and no ORM access** (parse →
  call service/selector → redirect/render — the pages/ratings/subscriptions house pattern):
  - `interests:picker` → GET `interests/` (`login_required`): render the **cluster-grouped active**
    picker from `taxonomy.list_clusters()` (prefetched, no N+1 — AC5), each active tag a labelled
    checkbox (label + definition; never raw ids/retired tags) **pre-checked** iff its id is in the
    user's resolved declared tags (`selectors.declared_tags`). Empty-profile → nothing checked + a
    "You haven't picked any interests yet" hint (AC6, not an error). Empty-vocabulary edge →
    "No interests are available yet" copy, no crash. A "pick a few" hint when below
    `config.interest_suggested_minimum()` (IP-3 — copy only, never blocks save). **The picker read is
    fail-soft (DESIGN §9):** a `list_clusters`/`declared_tags` error → a degraded "Couldn't load
    interests, try again" page (not a 500) + `INTEREST_PICKER_DEGRADED`.
  - `interests:save` → POST `interests/` (→ `interests/save`) (`login_required` + CSRF): parse the
    checked `tag_id`s → `services.set_interests` → **PRG redirect** back to `interests:picker` with a
    Django success message ("Saved your interests"). `InterestValidationError` → re-render the picker
    with the validation message + **400** (AC2, durable state honest — no partial set). A DB write
    failure → "Couldn't save, please try again" (the save rolled back, no partial set).
  - `interests:clear` → POST `interests/clear` (`login_required` + CSRF): `services.clear_interests`
    → PRG to `interests:picker` (AC9).
  - **No interest/profile id in any URL** — a row is addressed by `request.user` + `tag_id` only, so
    a user can only ever touch **their own** profile (no IDOR, DESIGN §11). Anonymous → `login_required`
    redirect to sign-in with `next=` (C2). All tag label/definition text rendered through Django
    auto-escaping (no `|safe`).
  - Add `INTEREST_PICKER_DEGRADED` to `apps/core/observability.py` (DESIGN §12).
- **Dependencies.** T-02 (`set_interests`/`clear_interests` + the config tunables), T-03
  (`declared_tags` for pre-check / `has_declared_interests`).
- **Definition of done.** Integration tests (Django test client, project URLconf with the include):
  - **AC1** signed-in GET `interests:picker` renders clusters with active tags grouped + labelled;
    after a save the saved tags are **pre-checked on the next GET** (shown as selected).
  - **AC5** the picker lists **only active** tags, grouped by cluster, with labels (+ definitions
    where present); never raw ids or retired tags.
  - **AC4** POST save with an add+remove → PRG redirect; the next GET reflects exactly the new set.
  - **AC2** POST save containing an invalid id → re-renders the picker with the validation message +
    **400**; no profile change persisted.
  - **AC6** a user with zero interests → the picker renders with nothing checked + the empty hint, **no
    error**; empty-vocabulary fixture → the "none available" copy, no crash.
  - **AC9** POST `interests:clear` → all rows removed + PRG redirect.
  - **auth/CSRF:** anonymous GET/POST → `login_required` redirect with `next=`, **no write**; GET on
    save/clear → 405; POST without CSRF → 403.
  - **fail-soft:** with `list_clusters` (or `declared_tags`) patched to raise → the picker renders a
    degraded page (no 500) + `INTEREST_PICKER_DEGRADED`.
  - `manage.py check` clean; `ruff`/template lint clean; suite green.
- **Estimated size.** M.
- **Files/areas touched.** `apps/interests/views.py` (new), `apps/interests/urls.py` (new),
  `apps/interests/templates/interests/picker.html` (new), `config/urls.py` (the include),
  `apps/core/observability.py` (one constant), `apps/interests/tests/test_views.py`.

## T-05 — The onboarding nudge: the `interest_prompt` inclusion tag + partial + the one `accounts/profile.html` line

- **Description.** Implement the onboarding nudge exactly to the DESIGN §5.4 contract (AC3) — the one
  touch **outside** the new app, isolated here and **content-only** (no auth-logic edit):
  - `apps/interests/templatetags/interests_tags.py` —
    `@register.inclusion_tag("interests/_prompt_slot.html", takes_context=True) def
    interest_prompt(context)`: reads **only** `selectors.has_declared_interests(request.user)` and
    returns `{request, show: not has}`. **Fail-soft (DESIGN §5.4/§9):** **any** exception → render
    nothing + count `INTEREST_PROMPT_DEGRADED`, **never raises into the page render** (preserves the
    profile page — never 500s it).
  - `apps/interests/templates/interests/_prompt_slot.html` — when `show` is true, a gentle one-line
    "Tell us what you're interested in →" nudge **linking to `interests:picker`** (encouraged,
    **never a blocker** — AC3/AC6); when false, renders nothing.
  - The **one sanctioned edit** to `apps/accounts/templates/accounts/profile.html` (DESIGN §5.4):
    add `{% load interests_tags %}` near the top and one `{% interest_prompt %}` content line in the
    profile body. This reuses the existing `verify`→`profile` landing
    ([accounts/views.py:152](../../apps/accounts/views.py)) so a newly-registered, empty-profile user
    sees the nudge with **zero edit to auth logic** (the ratings/subscriptions slot pattern). This
    line is the **second half of the activation switch** (DESIGN §16) — its removal + removing the
    `config/urls` include fully rolls the feature back.
  - Add `INTEREST_PROMPT_DEGRADED` to `apps/core/observability.py` (DESIGN §12).
- **Dependencies.** T-03 (`has_declared_interests`), T-04 (the `interests:picker` route name the
  nudge links to).
- **Definition of done.** Render tests (the tag in isolation + the `accounts:profile` page via the
  test client, with `apps.interests.urls` included):
  - **AC3** a signed-in user with an **empty** profile loads `accounts:profile` → the nudge renders,
    linking to `interests:picker`; declaring interests is **not required** to use the page
    (non-gating).
  - **AC3/AC6** a user **with** ≥1 declared interest → the nudge renders **nothing** (self-resolves).
  - **fail-soft:** with `has_declared_interests` patched to raise → the tag renders **nothing**,
    `INTEREST_PROMPT_DEGRADED` incremented, and **the profile page still renders** (no 500).
  - the existing `accounts/profile.html` content is otherwise unchanged (the prior profile-page tests
    stay green).
  - `ruff`/template lint clean; suite green.
- **Estimated size.** S.
- **Files/areas touched.** `apps/interests/templatetags/__init__.py` + `interests_tags.py` (new),
  `apps/interests/templates/interests/_prompt_slot.html` (new),
  `apps/accounts/templates/accounts/profile.html` (the `{% load %}` + one nudge line),
  `apps/core/observability.py` (one constant), `apps/interests/tests/test_templatetags.py`.

## T-06 — Read-only admin, README, CODEMAP, DECISIONS finalize, rollback note

- **Description.** Close-out: a thin read surface + docs + index — no behavioural change to the
  feature paths (DESIGN §3 admin / §16).
  - `apps/interests/admin.py` — a **read-only** `Interest` admin (list `user`, `tag_id`,
    `created_at`; no add/edit — writes go only through `services`, DESIGN §3 invariant). Mirrors the
    signals/ratings/subscriptions read-only admin pattern.
  - `apps/interests/README.md` — the app's single responsibility (declared interest tags as a mutable
    membership set, **no scoring, no D-7 emit**), the three routes, "owns one mutable table
    `interests_interest` (**CASCADE** on account delete), no parent profile row", the §7 set-replace
    **preserve-on-edit** reconcile, the `declared_tag_ids` matcher contract (AC8), and the
    **rollback** (remove the `config/urls` `interests/` include + the `accounts/profile.html`
    `{% interest_prompt %}` line; if needed `migrate interests zero`).
  - [CODEMAP.md](../../CODEMAP.md) — record the new shared touch-points: `interests.selectors.declared_tag_ids`
    (**the future-matcher read contract**, AC8) + `declared_tags`/`has_declared_interests`,
    `interests.services.set_interests`/`clear_interests` (the single write path), the
    `interests:*` route names, the `{% interest_prompt %}` tag, the two new config tunables
    (`interest_suggested_minimum`/`interest_declaration_max`), and the new observability constants.
  - [features/interest-profile/DECISIONS.md](DECISIONS.md) — mark **IP-DESIGN-1…4** as **built**.
    Note the named-not-built revisit flags (onboarding gating; persisted onboarding dismissal; cached
    resolved projection; interest intensity OQ-IP-4; an "interest changed" D-7 signal) per DESIGN
    §18.
  - The Stage-4 `TEST_PLAN.md` (per-AC Given/When/Then → test) is the Senior Engineer's exit
    artifact, produced alongside the build, not in this task.
- **Dependencies.** T-01…T-05.
- **Definition of done.** `apps/interests/admin.py` registers a read-only `Interest` admin (a test or
  `check` confirms no add/change perms); `README.md` matches the shipped routes/store/rollback;
  `CODEMAP.md` lists every new shared surface above; `DECISIONS.md` marks IP-DESIGN-1…4 built;
  `makemigrations --check` clean; **full suite green, `ruff` clean, no drift** (the close-out sweep).
- **Estimated size.** S.
- **Files/areas touched.** `apps/interests/admin.py` (new), `apps/interests/README.md` (new),
  [CODEMAP.md](../../CODEMAP.md), `features/interest-profile/DECISIONS.md`,
  `apps/interests/tests/test_admin.py` (optional read-only assertion).

---

## Design-element coverage (exit criterion: every design element in ≥1 task)

| DESIGN element | Task(s) |
|----------------|---------|
| §4.1 `Interest` membership store + unique constraint; structural no-score/no-updated_at/no-parent-row (AC6/AC8) | **T-01** |
| §4.1/§6 lifecycle + **CASCADE** on account delete (IP-4/AC9), no `accounts` edit | **T-01** (shape + deletion) + **T-02** (create/delete) |
| §5.1 single write path `set_interests` + `SetResult` + all-or-nothing `is_valid_tag` validation (AC2) | **T-02** |
| §5.1/§7 the set-replace **preserve-on-edit** reconcile (`_preserved_unshowable_ids`, AC4 × AC7, M5=0) | **T-02** |
| §5.1 `clear_interests` (full wipe incl. preserved, bypasses §7 — AC9) + `errors.InterestValidationError` | **T-02** |
| IP-5 no `signals.capture` import (preference state, not behavior) | **T-02** (import-absence assertion) |
| §5.2 single read surface `declared_tag_ids`/`declared_tags`/`has_declared_interests` (resolved, deduped, AC6/AC7/AC8) | **T-03** |
| §12 M5 ops invariant `count_unresolvable` (0 by construction) + reuse of `TAXONOMY_REFERENCE_BREAK` | **T-03** |
| §5.3/§6/§8 thin views (`picker`/`save`/`clear`) + `urls` + `config/urls` include; cluster-grouped active picker; empty/empty-vocab/error states; no-IDOR | **T-04** |
| §5.4 the `{% interest_prompt %}` fail-soft inclusion tag + partial + the one `accounts/profile.html` line (AC3) | **T-05** |
| §10 config tunables `interest_suggested_minimum` / `interest_declaration_max` | **T-02** (added) + **T-04** (suggested-minimum consumed) |
| §11 security (login_required, own-data-only/no IDOR, closed-vocab boundary, CSRF, autoescape) | **T-02** (boundary) + **T-04** (auth/CSRF/no id) + **T-05** (autoescape) |
| §9 failure modes (loud write/atomic rollback · fail-soft picker/prompt · loud matcher read) | **T-02** + **T-03** + **T-04** + **T-05** |
| §12 observability constants (`DECLARED`/`PROFILE_UPDATED`/`PROFILE_CLEARED`/`DECLARATION_REJECTED`/`PICKER_DEGRADED`/`PROMPT_DEGRADED`) | **T-02** + **T-04** + **T-05** |
| §3 read-only admin surface | **T-06** |
| §16 rollout/rollback (additive, no flag, two-part switch, design-for-deletion) + CODEMAP/docs + IP-DESIGN-1…4 built | **T-06** |
| §15 per-AC verification → `TEST_PLAN.md` | Stage 4 (Senior Engineer) |

**AC roll-up:** AC1 → T-01+T-02+T-03+T-04; AC2 → T-02+T-04; AC3 → T-05; AC4 → T-02+T-04; AC5 → T-04;
AC6 → T-01 (no parent row)+T-03+T-04+T-05; AC7 → T-02 (§7 preserve)+T-03 (resolve at read); AC8 → T-03
(single read surface)+T-01 (no score column); AC9 → T-01 (CASCADE)+T-02 (`clear_interests`)+T-04
(clear view). All nine acceptance criteria are covered; **no `L` tasks** (all S/M); every task has a
checkable definition of done and declared files.
