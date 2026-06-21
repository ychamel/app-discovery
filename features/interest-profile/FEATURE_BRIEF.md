# FEATURE_BRIEF — interest-profile

*Stage 1 artifact (Product Analyst). Status: **APPROVED** (DN-15, 2026-06-21 — approved as
written; **stored unit = tags-only** (AS-1/IP-1 confirmed); **onboarding = optional/non-gating**
(AS-2/IP-2 confirmed)). Traces to [vision §6 User-facing → Interest profile](../../curated-app-platform-design.md),
§2.2 (ring-based matching), §3.1 (the matching input), and proves **H1**
([breakdown §1](../../docs/mvp-component-breakdown.md)).*

---

## Domain terms (defined, not designed)

So the brief contains no undefined terms — these are existing platform contracts, not
new design:

- **Interest tag** — one unit of the shared interest vocabulary owned by
  [interest-taxonomy](../interest-taxonomy/), referenced by its stable UUID `Tag.id`
  under global **[D-5](../../DECISIONS.md)** (validate with `is_valid_tag`, resolve at
  read with `resolve_tag`; **soft-retire**, never hard-deleted).
- **Cluster** — a named grouping of related tags (D-5); a tag belongs to ≥1 cluster.
  Clusters are the day-one anchor for the future ring-based expansion (vision §2.2).
- **Interest profile** — the set of interest tags a signed-in person has **explicitly
  declared they care about**. This feature creates and owns that set; it is *this
  feature's deliverable*.
- **Account / signed-in user** — one account under global **[D-3](../../DECISIONS.md)**;
  the base `user` role every account holds.
- **The matcher / digest** — the (future, not built here) consumer that reads interest
  profiles to decide which curated apps to show which users (vision §2/§3.1). This
  feature is its **input substrate**; building the matcher is out of scope.

---

## Problem statement

**Who:** a signed-in user (every account; D-3 base `user` role), and — indirectly — the
platform's curation engine.

**What problem:** the platform's entire premise is a *personalized* feed of good apps
"matched to their interests" (vision §1). Today there is no way for a user to say **what
they're interested in**. The catalog ([submission-intake](../submission-intake/)) tags
every accepted app with interest tags, and the signal corpus
([signal-capture](../signal-capture/)) records behavior keyed to those tags — but the
**user side of the match is empty**. Without a declared interest profile, the matcher has
no Ring-0 ("users whose interest profile most closely matches the app's tags" — vision
§2.2) to target, so the launch boost and the whole impression economy have nothing to
aim at.

**Why now:** identity ([identity-accounts](../identity-accounts/) ✓) and the vocabulary
([interest-taxonomy](../interest-taxonomy/) ✓) both exist and are released. App pages and
ratings are live. The one missing half of the matching equation is the user's declared
interests — and it gates the Phase-2 user loop and the future `weekly-digest` that **H1**
is measured on. It is the cheapest unblock with the widest downstream payoff.

## Goal

A signed-in user can declare and maintain which interest tags they care about, producing
a durable, taxonomy-valid interest profile that a future matcher/digest can read as the
user side of the Ring-0 match.

## User stories

1. **As a** signed-in user, **I want** to choose the interest tags I care about from the
   platform's vocabulary, **so that** the apps shown to me are matched to what I actually
   like.
2. **As a** newly signed-up user, **I want** to be prompted to pick my interests as part
   of getting started, **so that** my feed is personalized from the beginning instead of
   generic.
3. **As a** signed-in user, **I want** to review and change my interests at any time,
   **so that** my profile stays accurate as my interests change.
4. **As a** user browsing the picker, **I want** the tags grouped into clusters with
   readable names and definitions, **so that** I can find and understand the interests
   worth picking without scanning a flat list.
5. **As a** user who hasn't picked anything (or skipped), **I want** the platform to keep
   working, **so that** an empty profile never blocks me from using the site.
6. **As the** platform (matcher/digest consumer), **I want** each profile expressed as
   resolvable taxonomy `Tag.id`s, **so that** I can match users to app tags without the
   profile breaking when a tag is renamed or retired.

## Acceptance criteria

Each criterion is `Given / When / Then`. "Persisted/valid" means stored against the
account and accepted by the taxonomy's `is_valid_tag` (D-5).

- **AC1 (story 1) — declare interests.**
  *Given* a signed-in user on the interest picker, *when* they select one or more active
  interest tags and save, *then* exactly those tags are persisted to their interest
  profile and shown as selected on their next visit.
- **AC2 (story 1) — closed vocabulary only.**
  *Given* a save request, *when* it contains any value that is not a currently-active
  taxonomy tag (off-vocabulary, retired, or malformed id), *then* the save is rejected
  loudly with a clear message and **no** profile change is persisted (no tag coining —
  D-5).
- **AC3 (story 2) — onboarding prompt.**
  *Given* a user who has just created an account and has an empty interest profile, *when*
  they proceed through getting-started, *then* they are prompted to pick interests, and
  declaring them is **encouraged but not required** to continue (see AC6).
- **AC4 (story 3) — edit anytime.**
  *Given* a user with an existing interest profile, *when* they add and/or remove tags and
  save, *then* the profile reflects exactly the new set (additions present, removals gone)
  and the change is immediately visible to them.
- **AC5 (story 4) — grouped, readable picker.**
  *Given* the picker, *when* it loads, *then* it presents only currently-**active** tags
  (`list_active_tags`), organized by their clusters with each tag's human-readable label
  (and definition where present) — never raw ids or retired tags.
- **AC6 (story 5) — empty profile is a valid state.**
  *Given* a user with zero declared interests (new, skipped, or removed all), *when* they
  use the platform, *then* nothing errors and no surface assumes a non-empty profile; the
  empty profile is a representable, handled state.
- **AC7 (story 6) — references survive rename/retire.**
  *Given* a profile referencing a tag that is later renamed or soft-retired, *when* the
  profile is read, *then* every stored reference still resolves via `resolve_tag` to the
  tag's current meaning (reference-break-rate = **0**); a retired tag is not silently
  dropped from the stored profile.
- **AC8 (story 6) — readable by the matcher as `Tag.id`s.**
  *Given* a persisted profile, *when* a consumer reads it, *then* it is exposed as a set
  of resolvable taxonomy `Tag.id`s through a single read surface (no consumer reads the
  profile's storage directly), so the matcher can be built against it without change here.
- **AC9 (privacy) — profile is personal mutable state.**
  *Given* a user deletes their account (D-3), *when* deletion completes, *then* their
  interest profile is removed; *and* a user can clear their own profile at will.

## Success metrics

Measurable signals. Targets are illustrative (D-2 — no global non-functional ceilings);
the analyst names *what* is measured, the Architect/Release set thresholds.

| # | Metric | What it tells us | Why it matters |
|---|--------|------------------|----------------|
| **M1** | **Declaration rate** — % of new accounts that declare ≥1 interest within onboarding. | Adoption of the core action. | If users won't declare interests, the matcher has no input — the headline. |
| M2 | **Profile richness** — median # of tags per non-empty profile. | Whether profiles carry enough signal for Ring-0 matching. | A 1-tag profile barely matches; richness drives match quality. |
| M3 | **Vocabulary coverage** — % of catalog interest tags declared by ≥1 user. | Whether user demand spans the apps we accept. | Tags no user wants = apps with no Ring-0 to launch into (cold-start visibility). |
| M4 | **Edit rate** — % of users who change their profile after first save. | Whether users treat the profile as living. | Confirms story 3 is real, not write-once-and-forget. |
| M5 | **Reference integrity** — count of stored tag references that fail to resolve. | Direct check of AC7. | Must be **0**; any non-zero is a D-5 contract violation. |
| M6 | **Match-readiness (H1 leading indicator)** — % of accepted apps whose tag set intersects ≥1 non-empty profile. | Whether the substrate can actually feed a digest. | This is *why the feature exists*: a profile no app matches produces no curation. |

## In scope

- An interest picker for signed-in users: browse the active vocabulary (grouped by
  cluster), select/deselect interest tags, save.
- Persisting an account's declared interests as taxonomy `Tag.id` references (D-5).
- An onboarding prompt to declare interests for new accounts (encouraged, not gating).
- Editing the profile at any time (add/remove), including clearing it.
- A single read surface exposing a profile as resolvable `Tag.id`s for future consumers.
- Empty-profile handling as a first-class, valid state.
- Removing the profile on account deletion (AC9).

## Out of scope

- **The matcher / digest / ranking itself** — this feature is the *input*; consuming it
  to allocate impressions is `weekly-digest` / the matching engine (vision §6 Internal).
- **Implicit / behavioral interest refinement** — inferring interests from behavior
  (vision §6: "+ implicit refinement from behavior") is explicitly deferred; the MVP slice
  is *explicit* declaration only ([breakdown §4.2](../../docs/mvp-component-breakdown.md)).
- **Cluster-to-cluster adjacency / ring expansion** — owned by the future matcher over the
  D-5 cluster anchor (vision §2.2); not built here.
- **Editing the vocabulary** (creating/renaming/retiring tags or clusters) — owned by
  `interest-taxonomy` / `editorial-curation-tools`; this feature only *reads* it.
- **Following developers/apps & saved collections** — separate Phase-2 features
  (`app-subscriptions` ✓ ships follows); the interest profile is interest tags, not follows.
- **Weighting or scoring interests** (e.g. "love" vs "like" strengths) — flat declared
  set only at MVP; intensity is a named possible later change, not built now (§5.5).
- **Recommending which tags to pick** based on others' behavior — out at MVP.

## Constraints & assumptions

Each marked **[verified]** (confirmed against code/ADRs) or **[unverified]** (a working
assumption needing the Architect's or user's confirmation).

**Constraints**
- **C1 [verified]** Interest references MUST be taxonomy `Tag.id`s under D-5: validate
  with `is_valid_tag` at the write boundary, resolve with `resolve_tag` at read, store the
  id (never the label/slug). The picker MUST source from `list_active_tags` /
  `list_clusters`.
- **C2 [verified]** Profiles attach to the single D-3 account; the action requires a
  signed-in `user` (the base role). No new identity or access method.
- **C3 [verified]** Stack is Django + PostgreSQL, code under `apps/` (D-4); server-rendered
  templates (no SPA) unless the Architect justifies otherwise.
- **C4 [verified]** D-2 — no global performance/scale ceiling is imposed; the design must
  still hold at 100× (CLAUDE.md §5.2). Picker read should not N+1 over tags/clusters
  (the taxonomy selectors already prefetch).

**Assumptions**
- **AS-1 [confirmed — DN-15]** The stored interest unit is the **tag** (`Tag.id`);
  **clusters serve selection/grouping** in the picker (e.g. "select a whole cluster"
  expands to its member tags) but are **not** themselves stored as a profile entry.
  *Rationale:* the matcher matches app **tags** to user tags for Ring-0; cluster-level
  adjacency is the matcher's job over the D-5 cluster anchor.
- **AS-2 [confirmed — DN-15]** Declaring interests is **optional and non-gating** at
  onboarding (prompted, skippable); an empty profile is valid (AC6). *Rationale:* there is
  no digest consumer yet to make declaration load-bearing, and a hard gate would block
  signup for no present payoff. (Revisitable when `weekly-digest` ships.)
- **AS-3 [unverified]** No hard minimum or maximum number of declared tags at MVP; if a
  soft "pick a few" nudge is wanted it is a tunable config value, not a validation floor.
- **AS-4 [verified]** The interest profile is **mutable user state** (edited in place),
  contrasting the append-only signal corpus (D-7). It is therefore **removed** on account
  deletion (AC9) — the same posture `app-subscriptions` took for follow state, *not* the
  D-7/SC-10 anonymize-not-purge rule (which governs already-emitted behavioral events, not
  user-declared preference state).
- **AS-5 [unverified]** Declaring/changing interests does **not** itself emit a D-7
  behavioral event (it is preference state, not an impression/engagement). If a future
  consumer wants "interest changed" as a signal, that is an additive D-7 decision later.

**Dependencies**
- `identity-accounts` ✓ (the account + signed-in `user` role; account-deletion hook).
- `interest-taxonomy` ✓ (D-5 vocabulary read/validate/resolve surface).

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| **R1** | **Cold demand** — users skip the picker, so profiles stay empty and the matcher has no input (M1/M6 low). | Med | High | Onboarding prompt (AC3) + clear value framing; empty profile is handled (AC6) so it's never a blocker; measure M1/M6 and revisit gating if dead. |
| R2 | **Thin profiles** — users pick 1–2 tags, too sparse for good Ring-0 matching (M2 low). | Med | Med | Cluster-grouped picker (AC5) makes related tags easy to add; optional "pick a few" nudge (AS-3). |
| R3 | **Vocabulary mismatch** — user interests don't overlap the catalog's tags (M3/M6 low), so no apps match. | Med | Med | M3/M6 expose the gap; feeds back to `interest-taxonomy` / catalog curation — out of scope to fix here, but made *visible* here. |
| R4 | **Stale references** — a renamed/retired tag breaks a stored profile (violates D-5). | Low | High | Store `Tag.id` + resolve at read (C1/AC7); reference-break-rate (M5) must be 0; picker shows only active tags. |
| R5 | **Scope creep into matching** — pressure to "just rank a bit" while we're here, contaminating the input layer. | Med | Med | Hard out-of-scope line (matcher/scoring excluded); this feature emits no score and exposes only a resolvable `Tag.id` read surface (AC8). |

## Vision alignment

Serves **vision §6 (User-facing → Interest profile)** directly — it *is* the "explicit
tags chosen at signup" half (implicit refinement deferred). It is the **user side of the
Ring-0 match** (§2.2) and the matching input behind the **Quality Score's curated
conversion** (§3.1), making it the substrate the future `weekly-digest` needs to prove
**H1** (a scarce, personalized digest makes users try apps they'd never have found —
[breakdown §1](../../docs/mvp-component-breakdown.md)).

**Money-buys-position check (the prime vision test):** PASS. This is purely user-side
preference declaration; no developer can pay to appear in a user's interests, and the
feature emits no ranking input — it only records what the *user* chose. Nothing here lets
money buy position.
