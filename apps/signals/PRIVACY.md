# Privacy posture — `apps/signals` (behavioral signal capture)

This is the human-readable privacy posture for the behavioral-signal corpus (AC10,
ratified by the brief approval DN-5; design DESIGN.md §10, SC-6/SC-10). It states **what**
is recorded, **why**, **how long**, and **what happens on account deletion**.

## What is recorded

The corpus records **only pseudonymous, in-platform behavioral events keyed to an
`Account.id`**. Every stored row contains only fields on this whitelist:

- the acting **`Account`** (a foreign key — the pseudonymous identity, never raw email),
- the **`App.id`** the event concerns (a catalogued `catalog.App`, D-6 soft reference),
- for an impression, the **frozen capture-time `Tag.id` snapshot** of the app's categories
  *as shown* (D-5 soft references),
- the **`EventKind`** (`click_through` · `subscribe` · `page_reengagement` · `share` ·
  `off_platform_proxy`) and, for an impression, the **`Surface`** (`digest`),
- the **`impression` link** (which shown instance a conversion attributes to),
- the **`is_proxy`** flag (true only for the off-platform secondary signal), and
- **timestamps** (`occurred_at`, `created_at`; and a UTC `visit_date` for a platform visit).

## What is NOT recorded — by schema

The schema has **no column** for any of: IP address, user-agent, device fingerprint,
precise geolocation, referrer, off-platform identifiers, or any free-text. Over-collection
is therefore **unrepresentable** — there is no field to put such data in. This is enforced
structurally (a test asserts these attributes are absent on every model), not by policy.

There is also **no score, weight, rank, or normalized column** anywhere: the corpus is raw
facts. Turning signal into a Quality Score is a downstream consumer's job, never done here.

## Why it is recorded

The single purpose is **backtesting a future Quality Score (hypothesis H3)**: to learn
which apps earn genuine engagement, the platform must have captured the behavioral funnel
*before* the score exists — an uncaptured impression is a permanent hole in the backtest.

Consent is **signup-ToS consent** (no per-event opt-in), justified by the small,
hand-recruited, trusted founding cohort.

## How long it is retained

Retained for the **full MVP with no automatic purge** (brief A3): the backtest needs the
history. There is no scheduled deletion job and nothing expires on its own.

## Account deletion (SC-10)

`accounts.delete_account` hard-deletes the `Account` row. Signal-capture handles the
resulting foreign keys as follows:

- `Impression.user` and `EngagementEvent.user` are **`SET_NULL`** — the behavioral facts
  **survive as anonymized corpus rows** (`user IS NULL`), unlinked from any person. This
  respects the deletion right (the person is unlinked) while keeping the aggregate signal
  the H3 backtest depends on (no-auto-purge).
- `PlatformVisit.user` is **`CASCADE`** — a per-day retention tick is only meaningful while
  joined to a live user's impressions, so an unlinked tick is pure noise and is removed
  with the account.

> **Posture nuance to confirm with data (SC-10).** Whether *anonymize-and-retain* is the
> desired deletion semantics (versus purge-on-deletion) is the one posture call flagged to
> revisit once there is real data and a consumer. The implementation keeps `SET_NULL` so a
> future purge-on-deletion policy would be a **localized** change (one migration + the
> deletion path), not a schema redesign.
