# RELEASE_NOTES — developer-updates

*Stage 5 artifact (Release Engineer). Status: **RELEASED to local/dev** 2026-06-24.
Production promotion + the live-metrics window defer until a prod target/traffic exists (as
the prior ten features).*

Traces to [DESIGN §12 Rollout](DESIGN.md) · [FEATURE_BRIEF.md](FEATURE_BRIEF.md) success
metrics M1–M6 · [TEST_PLAN.md](TEST_PLAN.md) (AC1–AC8).

---

## 1. What changed

The platform now has a **developer→follower communication tool**. An app owner can post
**update** and **early-access** notices about apps they own; those notices surface
newest-first in the **existing followed-apps feed** of every user who already follows the
app — and **nowhere else**. `developer-updates` is the **single producer** that fills the
AS-3 notice seam (`subscriptions.notices.notices_for_apps`), which until now returned an
empty list. The owner can list and withdraw their notices, and posting is rate-limited per
author/per app.

The integrity line (brief R1, vision Open Q #5) is the headline property: a notice reaches
**only an audience the developer already earned** (current followers) and writes **no
score-bearing signal** into the corpus. Posting buys no reach and no ranking — **M5 = 0 is
structural**, not merely measured.

**Shipped components:**

- **NEW app `apps/updates/`** owning **one table** `updates_notice`
  (`updates/0001_initial`; author FK `CASCADE`; `updates_app_published_idx`; **no**
  `score`/`updated_at`/`withdrawn_at` columns — withdraw is a hard delete, one source of
  truth):
  - [`selectors.py`](../../apps/updates/selectors.py) — the producer reads: the
    `PublishedNotice` DTO + `published_notices_for_apps(app_ids, limit)` (**1 query**,
    `limit`-bounded, newest-first) + `notices_for_channel` (the owner's own notices).
  - [`services.py`](../../apps/updates/services.py) — the **only** writer: `post_notice`
    (owner gate AC1 + kind/length validation AC2/AC3 + the durable table-derived rate
    limit AC8) and `withdraw_notice` (scoped, idempotent hard delete AC7). Imports **no**
    `signals.capture`.
  - Four role+owner-gated views + auto-escaped server-rendered templates (no JS, no
    `|safe`) — [`urls.py`](../../apps/updates/urls.py) under the `updates/` prefix.
  - Six `UPDATES_*` observability counters in
    [`apps/core/observability.py`](../../apps/core/observability.py); five `updates_*`
    config tunables in [`apps/core/config.py`](../../apps/core/config.py).

- **The AS-3 seam repoint** in
  [`apps/subscriptions/notices.py`](../../apps/subscriptions/notices.py): `notices_for_apps`
  now delegates to the producer and maps each `PublishedNotice` → the
  `subscriptions`-owned render `Notice` (the single adapter, **DU-DESIGN-2**). The render
  `Notice` shape and its one call site (`subscriptions.views._notices_fail_soft`) are
  **unchanged** — the feed template renders `Notice`s exactly as before, and the feed's
  fail-soft contract is preserved (a producer fault → "No news yet" +
  `SUBSCRIPTION_NOTICE_DEGRADED`, never a 500).

- **TWO additive, neutral changes on the closed `apps/subscriptions/`**: the reverse-audience
  read `subscriptions.selectors.subscriber_count` (the audience hint + M2) backed by a new
  `subscriptions_app_idx` index (`subscriptions/0002`). No new column, no behaviour change.

**Verified before ship:** **828 tests** green (+88 over the 740 baseline), `ruff check`
clean, `python manage.py check` no issues, `makemigrations --check` → no drift; both new
migrations reversible (backward SQL verified — `DROP TABLE updates_notice CASCADE` /
`DROP INDEX subscriptions_app_idx`).

## 2. Who is affected

- **Developers** (the `developer` role) with ≥1 **accepted** app — the new authoring
  audience; they gain a free way to talk to followers (vision §5.6/§6/§8).
- **Followers** — users who already follow an app now see its update/early-access notices in
  their existing feed. They opted in by following; no notice ever reaches a non-follower.
- **No one else, and no regression.** The seam repoint is body-only (signature + call site +
  `Notice` shape unchanged); the two `subscriptions` additions are inert until called.
  Signed-out / non-developer users get **403** on the routes; an owner posting/withdrawing
  on an app they don't own (or an unknown id) gets **404** (no ownership oracle, AC1).

## 3. How to use it

A developer (logged in, `developer` role) opens **`/updates/`** to see their accepted apps,
**`/updates/apps/<app-id>/`** to see/post notices for one app (title + summary, kind =
update or early-access), and withdraws a notice from that same channel. Posting is capped at
`updates_max_posts_per_window` (default 5) per app per `updates_post_window_hours` (default
24). A posted notice appears immediately, newest-first, in the followed-apps feed of every
current follower; withdrawing removes it from both the channel and followers' feeds.

## 4. Operator rollout

- **Stack:** reuse **D-4** (Python/Django + PostgreSQL, server-rendered templates) — no new
  global ADR; the app lives at `apps/updates/`.
- **Activation switch = three parts + two additive migrations, all in place** (DESIGN §12):
  1. `"apps.updates"` in `INSTALLED_APPS`
     ([`config/settings.py`](../../config/settings.py)).
  2. `path("updates/", include("apps.updates.urls"))` in
     [`config/urls.py`](../../config/urls.py).
  3. The **seam repoint** in
     [`apps/subscriptions/notices.py`](../../apps/subscriptions/notices.py) (delegate +
     adapter, replacing `return []`).
  - Migrations: `updates/0001_initial` (the table) + `subscriptions/0002` (the additive
    index). Both additive and reversible; existing data untouched. Deploy migrations before
    the seam repoint goes live (the producer read needs the table).
- **No feature flag, no data backfill.** The feature is dark until the seam is repointed:
  with the table present but the seam still `return []`, nothing surfaces. The seam repoint
  is the effective on-switch.
- **Promotion table:**

  | Stage | Target | Promotion criterion |
  |-------|--------|---------------------|
  | local/dev | **done (2026-06-24)** | 828 tests green; routes resolve; both migrations reversible; rollback rehearsed |
  | internal | _deferred_ | no error spike; `UPDATES_POST_FAILED` ≈ 0 and `SUBSCRIPTION_NOTICE_DEGRADED` flat for the soak window |
  | prod (% → full) | _deferred_ | M5 reach-beyond-followers = 0 (structural, asserted); `UPDATES_POST_FAILED` / `SUBSCRIPTION_NOTICE_DEGRADED` below threshold for the soak window; M6 rate-limit trend sane — **deferred: no prod target/traffic** |

## 5. Rollback (rehearsed)

This is the **first feature that repoints a *closed* app's seam**, so rollback is **not** a
single include-removal. The rehearsal (below) found the honest revert is broader than the
"three parts" of the activation surface — it also touches the seam's module-level imports and
the `subscriptions` test files the build rewrote. **The clean, atomic operational rollback is
therefore `git revert` of the build commit** (`eb5b05d` developer-updates/development), which
performs every part below in one reversible step. The manual equivalent, if reverting by
hand:

1. **Seam** — revert
   [`apps/subscriptions/notices.py`](../../apps/subscriptions/notices.py) `notices_for_apps`
   to the empty body (`return []`) **and remove its module-level
   `from apps.updates import selectors` / `from apps.core import config` imports and the
   `_to_notice` helper** — otherwise importing `subscriptions.notices` fails once
   `apps.updates` leaves `INSTALLED_APPS` (rehearsal finding #1).
2. **Route** — remove the `path("updates/", …)` include from `config/urls.py`.
3. **App** — remove `"apps.updates"` from `INSTALLED_APPS`.
4. **Closed-app tests** — restore the three `apps/subscriptions/tests/` files the build
   rewrote to assert producer-coupled behaviour (`test_notices.py`, `test_views.py`,
   `test_selectors.py`) to their pre-feature, empty-seam versions; otherwise the
   `subscriptions` suite goes red against the reverted seam (rehearsal finding #2). A
   `git revert` does this automatically.
5. **Data (optional)** — `updates_notice` + the `subscriptions_app_idx` index may stay inert
   or be migrated down: `python manage.py migrate updates zero` and
   `python manage.py migrate subscriptions 0001`.

→ The followed-apps feed instantly returns to its **empty-until-producer** state; the follow
graph, catalogue, and corpus are untouched.

**Who can trigger it:** any operator with repo/deploy access (`git revert` of the build
commit + redeploy; the optional DB step needs no data coordination — the table holds only
notice content).

**Rehearsal (2026-06-24, performed this session — up → down → up):**
- **Up:** full suite **828 green**; `/updates/…` routes resolve; both migrations' backward
  SQL generates cleanly (`DROP TABLE updates_notice CASCADE`, `DROP INDEX
  subscriptions_app_idx`).
- **Down:** applied all five parts above. `python manage.py check` clean; the
  rollback-critical suites — `apps.subscriptions` + `apps.catalog` + `apps.signals` —
  **306 green** (the 5 producer-coupled tests retire with the feature); the seam returns
  `[]` (feed empty state restored).
- **Up:** restored from HEAD; `git status` **clean**; full suite **828 green** again.

## 6. Monitoring — metrics → signals → alert

Six counters in [`apps/core/observability.py`](../../apps/core/observability.py):

| Counter | Feeds | Notes |
|---------|-------|-------|
| `UPDATES_NOTICE_POSTED{kind}` | **M1** adoption | a notice was created (tagged update / early_access) |
| `UPDATES_NOTICE_WITHDRAWN` | channel health | only on a real delete (not on a no-op withdraw) |
| `UPDATES_POST_REJECTED{reason}` | **M6** spam control | `reason=rate_limited` (the M6 trend) / `reason=invalid` (validation) — **expected, not an alert** |
| `UPDATES_POST_FAILED` | **the actionable write alert** | the create raised → fail-soft to the user (PRG + message, durable state = not posted); a rising rate is the one write-path Sev signal |
| `UPDATES_CHANNEL_DEGRADED` | health (fail-soft) | the channel's own-notices read fell back → the dev can still post |
| `UPDATES_AUDIENCE_DEGRADED` | health (fail-soft) | the audience-size hint fell back → posting never blocked |

- **The feed-producer health signal is the existing `SUBSCRIPTION_NOTICE_DEGRADED`** (not
  re-added): if the producer read raises, the existing feed wrapper catches it → "No news
  yet" + that counter. The feed **never errors** (AC4/AC7).
- **The two actionable signals are `UPDATES_POST_FAILED` (write) and
  `SUBSCRIPTION_NOTICE_DEGRADED` (feed).** Everything else is fail-soft or expected-trend.
- **M5** (reach beyond followers) target = **0**, enforced **structurally** (the pull model:
  notices are keyed by `app_id` and the feed only pulls a user's *followed* ids → a
  non-follower is unreachable). No "must-stay-0" alert is needed because no code path can
  reach a non-follower; it is an asserted test invariant
  ([TEST_PLAN.md](TEST_PLAN.md) AC5/M5), not a runtime gauge.
- **M2** (median followers reached) is analyst-derived from
  `subscriptions.selectors.subscriber_count` × posting apps — no dedicated counter.
- **M3/M4** (return rate / engagement lift) are **consumed, not produced** here: they come
  from the existing `signal-capture` return kinds (`APP_PAGE` / `page_reengagement`) emitted
  by the *follower's own* click-through, never by posting (AC6 — `apps/updates` imports no
  `signals.capture`, AST-enforced).

## 7. Known limitations

- **No live metrics yet** — local/dev only, no prod traffic; M1–M6 are instrumented but the
  measurement window opens when a prod/consumer target exists (the prior-feature pattern).
- **In-platform feed only** — no email / push / external delivery (out of scope; a later
  feature). A follower sees a notice only when they next open the feed.
- **No edit, no drafts, no scheduling** — withdraw + repost is the honest MVP; all named
  future seams (DESIGN §14).
- **No per-user read/unread state** — the feed shows current notices for followed apps; it
  does not track which a given user has seen (the pull model's accepted trade-off, DESIGN §10).
- **Early-access is the *announcement* only** — no entitlement/access-control gating of a
  pre-release build (out of scope).
- **A benign rate-limit TOCTOU** — concurrent posts at the window boundary may both land; the
  limit is a spam guardrail, not a correctness invariant (DESIGN §5.3, accepted).

---

*Reuses **D-3** (role gate), **D-4** (stack), **D-6** (owner-scoping), **D-7** (corpus —
consumed, not extended), and the **AS-3** producer contract — no new global ADR. Feature-local
decisions DU-DESIGN-1…6 (**BUILT**) in [DECISIONS.md](DECISIONS.md).*
