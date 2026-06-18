# RELEASE_NOTES — submission-intake

*Stage 5 artifact (Release Engineer). Status: **released to local / development** — build
re-verified green and rollout→rollback rehearsed on a throwaway database (2026-06-18).*
Sources: verified Stage-4 build, [DESIGN.md §9/§11/§12](DESIGN.md) (rollout + rollback +
the downstream contract), [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (success metrics /
error conditions), [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC9 coverage), global
[D-5](../../DECISIONS.md) (tag-reference contract) and global [D-6](../../DECISIONS.md)
(the catalogued-app cross-feature contract this feature establishes).

---

## 1. What this release is

The platform's **developer entry point and objective intake gate** — the first feature of
Phase 1. It gives any developer with the `developer` role one free, standardized way to
submit a web app (honest metadata + interest tags from the shared vocabulary + screenshots),
runs it through a **fixed set of objective floors** applied by a platform editor (admin
role), and produces an owned, correctly-tagged, **accepted** app that downstream features
consume. It is the on-ramp half of hypothesis H2: an app can *enter* the catalog on equal,
free footing.

It ships as a **new Django app, `apps/catalog/`**, and changes no existing feature's
behavior. It satisfies all nine acceptance criteria AC1–AC9 (mapping in
[TEST_PLAN.md](TEST_PLAN.md)).

## 2. What changed (since "no catalog existed")

- **Data model** — four tables under `apps/catalog/`, all UUID-keyed (D-4 convention):
  - `catalog_app` — one submitted web app: stable `id` (the **cross-feature reference**,
    D-6), individual `owner` (FK → `accounts.Account`), `name`/`description`/`url`,
    `normalized_url` (duplicate signal), a lifecycle `status`
    (`pending`/`accepted`/`rejected`/`withdrawn`) that is the one source of truth for "where
    it is", and `last_submitted_at` (FIFO order + time-to-decision start).
  - `catalog_app_tag` — the app↔tag link, stored as a **soft `tag_id` UUID** under the D-5
    contract (validated with `is_valid_tag` at write, resolved with `resolve_tag` at read;
    no hard FK into `taxonomy`).
  - `catalog_app_media` — one ordered screenshot per row (`image`, `position`, `alt_text`).
  - `catalog_review_decision` — an **append-only** gate-decision log (the audit + metrics
    source): `reviewer`, `outcome`, `failed_criteria`, `note`, `created_at`. The decision
    and the `App.status` flip are written in **one transaction**, so they cannot drift.
- **The objective gate** (`gate.py`) — a **fixed five-floor `Criterion` enum**: `works`,
  `not_spam`, `not_duplicate`, `honest_metadata`, `policy`, plus the reviewer-facing
  `CHECKLIST` wording. There is **no "other"/"quality" value**, so a taste rejection (R1 /
  AC6) is **structurally unrepresentable** — acceptance requires all five floors; rejection
  requires ≥1 named floor.
- **Single write path** (`services.py`) — the only way an app or decision changes:
  `submit_app` / `edit_app` / `add_media` / `remove_media` / `withdraw_app` /
  `resubmit_app` / `accept_app` / `reject_app`. Each is atomic, counted, transition-checked
  against the §7 state machine, and invariant-enforcing: required fields + well-formed
  http(s) URL + ≥1 tag + ≥1 media (AC1, fail loud, no partial row); closed vocabulary (AC4);
  decision atomicity with a row-locked `status == pending` re-check (no double decision);
  re-review on a gate-relevant edit of an accepted app (AC8 — it returns to `pending` and
  leaves the catalog until re-reviewed).
- **Single read path** (`selectors.py`) — owner-scoped views (`get_owned_app`,
  `list_owned_apps` — non-owner is indistinguishable from "not found"), the FIFO
  `list_review_queue` with a duplicate hint, and the **downstream catalogue substrate**
  `list_catalogued_apps` / `get_catalogued_app` which return **accepted apps only**, tags
  resolved via `resolve_tag`, media ordered (the D-6 / AC9 guarantee).
- **Decision notification** (`notifications.py`) — emails the developer the outcome and, on
  rejection, the failing criteria + the editor's note (AC7), via `apps.core.email`. Sent
  **after commit**: a send failure is logged and counted (`email_send_failure`) but **never
  rolls back the decision** (the developer still sees the outcome in "my apps").
- **HTTP surface + pages** — a developer DRF API (endpoints 1–8: submit, my-apps, detail,
  edit, media add/remove, withdraw, resubmit) and an admin review API (9–10: FIFO queue,
  decision), all session-auth and owner-/role-scoped; plus the server-rendered submit form,
  my-apps, app detail/edit, and admin review queue + decision form. Pages and API post to
  the **same** services/selectors (no second source of truth).
- **Admin inspection** — `App` and the append-only `ReviewDecision` registered in Django
  admin for ops cold-start (rich review tooling is `editorial-curation-tools`, out of scope).
- **Shared-surface touches** — 11 new metric constants in `apps/core/observability.py`
  (§7 below); two new tunables in `apps/core/config.py` — `catalog_media_max_count`
  (default 8) and `catalog_media_max_bytes` (default 5 MB); `MEDIA_ROOT`/`MEDIA_URL` in
  `config/settings.py`; app + URL registration; a new **Pillow** dependency for image
  validation. No existing behavior changed.

## 3. Who is affected

- **Developers (developer role)** — can now submit, tag, illustrate, edit, withdraw, and
  resubmit web apps, and see each app's status and (on rejection) the failing objective
  criteria + an actionable note. Taking the `developer` role is self-serve, owned by
  `identity-accounts` (unchanged here).
- **Platform editors (admin role)** — get a FIFO review queue (no priority/fast-lane field
  exists) and a decision form bound to the **fixed five-floor checklist**; every decision is
  an append-only, attributable `ReviewDecision`. Rich curation tooling remains
  `editorial-curation-tools`.
- **Downstream feature teams** (`app-pages`, `editorial-curation-tools`, `signal-capture`,
  `developer-dashboard`) — may now build against the catalogued-app contract. **Action
  required of them** ([D-6](../../DECISIONS.md)): read the catalogue **only** through
  `selectors.list_catalogued_apps` / `get_catalogued_app` (accepted-only); store the app by
  its **`App.id` (UUID)** and nothing else; treat tags as `Tag.id` and resolve with
  `resolve_tag` (never store/compare a label); treat media as the ordered list within the §9
  slots/limits. `app-pages` in particular **must adopt the §9 media limits** before storing
  any app reference.
- **Support / end users** — **no public-facing change** at this release. There is no
  anonymous surface here; public rendering of an accepted app is `app-pages`' job (out of
  scope), which will call `get_catalogued_app`.

## 4. How to use it (operators)

The rollout is the ordered steps from [DESIGN.md §12](DESIGN.md) — no separate runbook, and
**no recurring job** (nothing in this feature expires):

1. Ensure the **Pillow** dependency is installed (`pip install -e .` / your env's sync) and
   set `MEDIA_ROOT` (an absolute path to a writable, **non-executable** volume; defaults to
   `./media` when unset). Optionally tune `CATALOG_MEDIA_MAX_COUNT` (default 8) and
   `CATALOG_MEDIA_MAX_BYTES` (default 5 MB) — see [`.env.example`](../../.env.example).
2. `python manage.py migrate catalog` — creates the four `catalog_*` tables. **No content.**
   (Reuses the shared `citext` extension already installed by `identity-accounts`.)
3. `python manage.py check` — must report no issues before the surface is considered live.
4. The **founding catalog** enters through the **same** developer form — recruitment is
   offline (SI-5); there is no separate in-product recruitment surface.

No new env vars are *required* (all have defaults). `MEDIA_ROOT` should be set explicitly in
any shared/production environment.

## 5. Rollout strategy

> **Current deployment target: local / development only** — consistent with
> `identity-accounts` and `interest-taxonomy` ([R1](../../CONTROL.md)); the platform is still
> mid-development. The feature is verified locally (migration applies, four tables created,
> `check` clean, 315 tests green). **Production promotion and a live-metrics monitoring
> window are deferred** until the platform approaches launch and the first consumer
> (`app-pages` / `editorial-curation-tools`) exists to read the catalogue.

This is an **additive new app with no live downstream consumer yet**, so there is **no
pre-existing behavior to protect and nothing to feature-flag off** (an honest deviation from
the internal→%→full template — there is no surface to ramp against, DESIGN §9). Safety comes
from a **reversible migration** + removable media files, not a kill switch.

Promotion is gate-based, not percentage-based:

| Gate | Criterion to advance |
|------|----------------------|
| Schema live | `migrate catalog` applied; the four `catalog_*` tables exist; `/health` → `200`. |
| Surface live | A developer can submit (201, `pending`) and an admin can decide (accept/reject) end-to-end; `manage.py check` clean. |
| First catalogued app | At least one app reaches `accepted` and is returned by `list_catalogued_apps`. |
| First consumer integrates | A downstream feature adopts the [D-6](../../DECISIONS.md) contract (reads via the catalogue selectors, stores `App.id`) — at which point the §7 metrics carry real signal. |
| Stable at target | Above holds with `tag_off_vocabulary_rejected` = 0 and no decision `email_send_failure` backlog through the monitoring window; no Sev-1/Sev-2. |

## 6. Rollback (rehearsed)

**One action: revert the deploy to the previous release.** If the schema must also be undone
(safe here — no live downstream reference exists yet):

```bash
python manage.py migrate catalog zero    # drops the four catalog_* tables
# optional: clear uploaded screenshots
rm -rf "$MEDIA_ROOT"/app_media
```

**Rehearsed 2026-06-18** on a throwaway PostgreSQL database (`catalog_release_rehearsal`,
dropped afterward): `migrate` created the four `catalog_*` tables (`catalog_app`,
`catalog_app_tag`, `catalog_app_media`, `catalog_review_decision`) with the shared `citext`
extension present; `manage.py check` clean; then `migrate catalog zero` reversed cleanly to
**0 `catalog_*` tables** while **keeping the shared `citext` extension** (used by `accounts`
and `taxonomy`); a re-`migrate catalog` re-applied cleanly (the migration is confirmed
reversible). **Who can trigger:** any operator with deploy access and the DB credentials.

## 7. Monitoring & alerts (tied to brief success metrics)

Metrics are emitted via `apps.core.observability.increment`; DB reachability is already
covered by the existing `GET /health`. Mapping to the brief's
[success metrics](FEATURE_BRIEF.md#success-metrics):

| Brief metric | Signal | Alert |
|--------------|--------|-------|
| Submission completion rate | `submission_started` / `submission_completed` / `submission_created` | Trend only — a falling ratio signals form friction. |
| Time-to-decision | `review_decision.created_at − app.last_submitted_at` (computed from stored timestamps, not a counter) | Trend only — no hard SLA (D-2); must stay **observable** so manual review is shown to keep up at founding volume. |
| Gate pass rate (accepted ÷ reviewed) | `app_accepted` / `app_rejected` (+ `review_decision` outcome tag) | **Alert on a collapsing pass rate** — early signal the gate is creeping from floors into taste (R1 / AC6). |
| Rejection-reason distribution | `review_decision` per-`criterion` tag on reject | **Alert on a skew** toward any single floor, or any inability to map a rejection to one of the five floors (the AC6 drift signal). |
| Resubmission success rate | `app_resubmitted` then `app_accepted` | Trend only — confirms feedback was actionable and rejection is non-terminal (AC7). |
| Tag coverage / off-vocabulary (**core safety, target 0**) | `tag_off_vocabulary_rejected` | **Page on any nonzero** — the closed-set boundary (AC4) leaked. Must read 0. |
| Duplicate / spam catch | `duplicate_flagged` + `review_decision` (`not_duplicate`/`not_spam` criteria) | Trend only — integrity of the manual floor (AC5). |
| Catalog growth toward founding target | count of `accepted` apps (via `list_catalogued_apps`) | Trend toward the 50–150 founding goal (vision §5.4). |
| Decision notification delivery | `email_send_failure` | **Alert on any nonzero for a decision** — the developer may not have been notified, though the decision stands (§5d). |

## 8. Verification at release (2026-06-18)

- **315 automated tests pass** (184 baseline + 131 new catalog tests).
- `ruff check .` clean; `manage.py check` clean; `makemigrations --check` reports no model
  drift (model ↔ migration in sync).
- Rollout→rollback **rehearsed** on a scratch DB (§6): `migrate` → four `catalog_*` tables +
  shared `citext` present → `check` clean → `migrate catalog zero` reverses to 0 catalog
  tables (`citext` retained) → re-`migrate catalog` re-applies (reversible).
- [TEST_PLAN.md](TEST_PLAN.md) maps 100% of AC1–AC9 to tests.

## 9. Known limitations

*(All are deliberate, bounded MVP trade-offs from [DESIGN.md §13](DESIGN.md); none is a
release blocker. The data-dependent ones are reopenable when their triggering feature lands.)*

- **Manual review only** — no automated malware / duplicate / uptime detection at MVP; the
  five floors are human-applied against a checklist at founding volume (50–150 apps). The
  queue gains pagination + a cached catalogue projection at 100× — the documented growth
  path, not built now (R2 / DESIGN §9).
- **Duplicate detection is a manual signal, not a constraint** — `normalized_url` powers a
  "N other apps share this URL" hint; it is **not** a DB unique constraint and **not** an
  auto-reject. A partial-unique index on accepted URLs is a named, deferred hardening
  (DESIGN §13), revisited with real duplicate volume.
- **Re-review on any gate-relevant edit of an accepted app** — a typo fix returns the app to
  `pending` and it leaves the catalogue until re-reviewed (the safe default; honest/works
  floors can break on an edit). The "stay-live + async re-review" / two-state published-vs-
  pending-update model is the deferred versioned-updates machinery (SI-6), reopenable.
- **Owner-account-deletion `CASCADE`** removes a developer's apps. Safe at MVP (no downstream
  consumer keys to them yet); flagged to revisit (withdraw-instead-of-delete or `SET_NULL`)
  when `signal-capture` keys signals to apps.
- **No first-class per-attempt submission history** — one `App` row + the append-only
  `ReviewDecision` log; a `SubmissionVersion` table arrives with versioned updates (SI-6),
  not speculated now.
- **Local file storage** for screenshots (Django storage API under `MEDIA_ROOT`); swap to an
  object store by changing the storage backend (no caller change) — premature at founding
  volume.
- **No live-metrics window measured** — deferred with the local/dev target until a consumer
  exists (mirrors `identity-accounts` / `interest-taxonomy`).

## 10. Stakeholder notification

On the first real promotion (when a consumer integrates): notify downstream feature owners
that the catalogue is live and buildable against, and hand them the
[D-6](../../DECISIONS.md) contract — **read via `list_catalogued_apps` / `get_catalogued_app`
(accepted-only); store `App.id`, never anything else; resolve tags with `resolve_tag`, never
store a label; media is the ordered list within the §9 slots/limits.** `app-pages` must adopt
the §9 media slots/limits before storing any app reference. Notify editors that review is via
the admin review queue against the fixed five-floor checklist, that every decision is an
append-only attributable record, and that a rejection is non-terminal (the developer can
correct and resubmit). No support-facing change at this release — there is no end-user
surface yet.
