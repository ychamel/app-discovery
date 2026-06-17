# RELEASE_NOTES — interest-taxonomy

*Stage 5 artifact (Release Engineer). Status: **ready to ship** — build re-verified green
and rollout→rollback rehearsed on a throwaway database (2026-06-17).* Sources: verified
Stage-4 build, [DESIGN.md §9/§12](DESIGN.md) (rollout + rollback),
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) (success metrics / error conditions),
[TEST_PLAN.md](TEST_PLAN.md) (AC1–AC8 coverage), global [D-5](../../DECISIONS.md)
(cross-feature tag-reference contract).

---

## 1. What this release is

The platform's **shared controlled vocabulary**: the *one* dictionary of interest **tags**
(grouped into named **clusters**) that both a user's interests and an app's subject matter
will be written in, so every future matching surface can compare the two in one language.
It is a Phase-0 **enabler** with no dependencies and several dependents
(`interest-profile`, `submission-intake`, `editorial-curation-tools`, the matcher).

It ships as a **new Django app, `apps/taxonomy/`**, and modifies no existing feature. It
satisfies all eight acceptance criteria AC1–AC8 (mapping in [TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since "no vocabulary existed")

- **Data model** — `taxonomy_tag` (UUID stable identity, immutable `citext` slug,
  normalized-unique label, `definition`, `active`/`retired` status, optional `replaced_by`
  successor) and `taxonomy_cluster`, joined by a `Tag.clusters` M2M. UUID `id` is the
  **stable cross-feature reference** ([D-5](../../DECISIONS.md)); a rename changes only the
  label, so stored references never break (AC6/AC7).
- **Single write path** (`services.py`, admin-only) — `add_tag` / `rename_tag` /
  `retire_tag` / cluster + membership ops, each atomic, counted, and invariant-checked:
  ≥1 cluster per active tag (AC5), normalized-label/slug de-dup (AC1), non-destructive
  soft-retire with successor validation (AC6). Plus idempotent `update_tag`/`update_cluster`
  sync setters for the seeder (ITX-11).
- **Single read path** (`selectors.py`) — the cross-feature substrate: `list_active_tags`,
  `list_clusters`, `get_tag`, **`is_valid_tag`** (the AC2 closed-set validator consumers
  enforce at their boundary), and **`resolve_tag`** (follows renames + retire/merge
  successors, cycle-guarded — never drops a real reference).
- **JSON read API** (DRF, session-auth, any role) — `GET /taxonomy/tags`,
  `GET /taxonomy/tags/{id}`, `GET /taxonomy/clusters`.
- **Curation surface (cold-start)** — a version-controlled seed file
  `apps/taxonomy/seed/vocabulary.yaml` + idempotent `manage.py seed_taxonomy`, plus the
  `is_staff`-gated Django admin (both route through `services.py`). **No HTTP write API and
  no custom curation UI** at MVP — that is `editorial-curation-tools`.
- **Integrity gate** — `manage.py check_taxonomy` (non-zero exit on any orphan active tag
  or duplicate label).
- **Founding vocabulary** — **11 clusters / 67 tags** for the *vibecoded-webapps* niche
  (size band closes OQ-3; ITX-12).
- **Shared-surface touches** — 5 new metric constants in `apps/core/observability.py`, one
  new tunable `TAXONOMY_RESOLVE_MAX_STEPS` in `apps/core/config.py`, app registration in
  `config/settings.py`/`config/urls.py`, and a new **PyYAML** dependency (ITX-10). No
  existing behavior changed.

## 3. Who is affected

- **End users / developers** — **no direct change** at this release. The vocabulary has no
  end-user screens of its own; the picker (`interest-profile`) and app-tagging UI
  (`submission-intake`) that render *from* it ship later.
- **Platform editors (admin role)** — may now curate the vocabulary two ways: edit
  `seed/vocabulary.yaml` + run `seed_taxonomy`, or use Django admin for ad-hoc changes.
  Both enforce every invariant.
- **Downstream feature teams** — may now build against the tag-reference contract.
  **Action required of them** ([D-5](../../DECISIONS.md)): store the **`Tag.id` (UUID),
  never the label**; validate input with `is_valid_tag(id)` at their write boundary
  (reject off-vocabulary values, don't coin tags); dereference with `resolve_tag(id)` at
  read time. A feature that stores a label string instead **breaks** the safety contract.

## 4. How to use it (operators)

The rollout is the three ordered steps from [DESIGN.md §12](DESIGN.md) — no separate
runbook, no recurring job (nothing in this feature expires):

1. `python manage.py migrate taxonomy` — creates `taxonomy_cluster`, `taxonomy_tag`, and
   the M2M table. **No content.** (Reuses the shared `citext` extension already installed
   by identity-accounts.)
2. `python manage.py seed_taxonomy` — applies `apps/taxonomy/seed/vocabulary.yaml`
   idempotently (upsert-by-slug, whole run in one transaction, no partial apply). Safe to
   re-run; an unchanged file writes nothing.
3. `python manage.py check_taxonomy` — integrity gate; **must exit 0** (zero orphan active
   tags, no duplicate labels) before the vocabulary is considered published.

No new env vars are required. The optional `TAXONOMY_RESOLVE_MAX_STEPS` (default 16) bounds
successor-chain resolution; see [`.env.example`](../../.env.example).

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with
> `identity-accounts` ([R1](../../CONTROL.md)); the platform is still mid-development.
> The feature is verified locally (migration applies, seed → 11/67, `check_taxonomy`
> exit 0, 184 tests green). **Production promotion and a live-metrics monitoring window are
> deferred** until the platform approaches launch and the first consumer
> (`interest-profile`/`submission-intake`) exists to read the vocabulary.

This is an **additive new app with no live downstream consumer yet**, so there is **no
pre-existing behavior to protect and nothing to feature-flag off** (an honest deviation
from the internal→%→full template — there is no surface to ramp against, DESIGN §9).
Safety comes from a **reversible migration** + a **re-runnable seed**, not a kill switch.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate taxonomy` applied; the three tables exist; `/health` → `200`. |
| Vocabulary published | `seed_taxonomy` applied; `check_taxonomy` exits 0 (zero orphans, no dup labels). |
| First consumer integrates | A downstream feature adopts the [D-5](../../DECISIONS.md) contract (stores `Tag.id`, validates with `is_valid_tag`) — at which point the §7 metrics begin to carry real signal. |
| Stable at target | Above holds with `taxonomy_reference_break` = 0 and `taxonomy_integrity_violation` = 0 through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**One action: revert the deploy to the previous release.** If the schema must also be
undone (safe here — no live downstream reference exists yet):

```bash
python manage.py migrate taxonomy zero
```

**Rehearsed 2026-06-17** on a throwaway PostgreSQL database: `migrate` created the three
`taxonomy_*` tables, `seed_taxonomy` loaded **11 clusters / 67 tags**, `check_taxonomy`
exited 0, a re-seed of the unchanged file wrote nothing (idempotent), then
`migrate taxonomy zero` reversed cleanly to **0 `taxonomy_*` tables** while **keeping the
shared `citext` extension** (used by `accounts`). The initial migration is confirmed
reversible. **Who can trigger:** any operator with deploy access and the DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; DB reachability is already
covered by the existing `GET /health`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| Reference-break rate on edit (**core safety, target 0**) | `taxonomy_reference_break` | **Page on any nonzero** — a retire/rename invalidated a reference, or `resolve_tag` hit a cycle/over-long chain. |
| Cluster integrity (zero orphan tags) + non-redundancy | `taxonomy_integrity_violation` (from `check_taxonomy`) | **Alert on any nonzero** — orphan active tag or duplicate label. |
| Vocabulary lifecycle volume (add/rename/retire) | `taxonomy_tag_added`, `taxonomy_tag_renamed`, `taxonomy_tag_retired` | Trend only (not paged) — curation activity. |
| App-coverage / user-coverage / tag-set-size | *editorial, measured against a real catalog* | **Deferred** — no submitted catalog exists pre-`submission-intake` (OQ-4/PL-1). `check_taxonomy` guards size/integrity in the interim. |

**Run `check_taxonomy` after every curation change** (seed run or admin edit); a nonzero
exit is the operational signal that `taxonomy_integrity_violation` would fire.

## 8. Verification at release (2026-06-17)

- **184 automated tests pass** (108 baseline + 76 new taxonomy tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model
  drift (model ↔ migration in sync).
- Rollout→rollback **rehearsed** on a scratch DB (§6): migrate → seed (11/67) →
  `check_taxonomy` exit 0 → idempotent re-seed → `migrate taxonomy zero` reverses to 0
  tables, `citext` retained.
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC8 (AC8 is a design-time guarantee
  verified by schema review — no runtime test until the adjacency table exists).

## 9. Known limitations

- **App-coverage not validated against a real catalog** — the founding 11/67 was authored
  against the niche definition + app archetypes, not submitted apps (none exist before
  `submission-intake`). Re-validate AC4 when that feature lands (**OQ-4 / PL-1**,
  reopenable).
- **No HTTP write API** — curation is `seed_taxonomy` + Django admin only at MVP; a
  `HasRole(ADMIN)`-gated write API arrives with `editorial-curation-tools` (DESIGN §5c).
- **No dedicated audit table** — lifecycle state + timestamps live on the rows, changes are
  counted via observability, and Django admin's `LogEntry` records who-changed-what in the
  admin. A rich append-only audit belongs with `editorial-curation-tools` (DESIGN §13).
- **`resolve_tag` is a per-dereference lookup** — accepted at MVP scale (small table,
  indexed PK); a cached `list_active_tags` projection is the documented growth path
  (DESIGN §9), not built now.
- **No cluster adjacency / ring expansion** — clusters ship first-class so adjacency is a
  later *additive* table over existing clusters (AC8); the relation itself is post-MVP.
- **Single language (English) labels** — localization deferred (FEATURE_BRIEF Constraints).

## 10. Stakeholder notification

On the first real promotion (when a consumer integrates): notify downstream feature owners
that the vocabulary is live and buildable against, and hand them the [D-5](../../DECISIONS.md)
contract — **store `Tag.id`, validate with `is_valid_tag`, dereference with `resolve_tag`;
never store a label string.** Notify editors that curation is via `seed_taxonomy` (edit the
YAML, re-run) or Django admin, and that retiring a tag is non-destructive (it stops being
offered but existing references keep resolving). No support-facing change at this release —
there is no end-user surface yet.
