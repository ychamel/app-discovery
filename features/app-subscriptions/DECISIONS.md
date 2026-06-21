# DECISIONS — app-subscriptions

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## Confirmation calls flagged by the Product Analyst (Stage 1, 2026-06-21)

> Defensible MVP-scoped calls made while drafting [FEATURE_BRIEF.md](FEATURE_BRIEF.md), so
> the brief is complete and reviewable. Each is the brief's working assumption; **approving
> the brief (DN-13) confirms them, or the user adjusts.** AS-3 and AS-5 are the two that need
> an explicit call (a scope fork and a privacy posture) — surfaced, not silently assumed
> (CLAUDE.md §6.5).
>
> **RESOLVED 2026-06-21 (DN-13):** brief approved as written; **AS-3 = option A** (ship the
> forward-compatible, empty-until-producer notice surface now); **AS-5 confirmed** (deletion
> removes follow state, emitted `subscribe` events follow SC-10). AS-1/AS-2/AS-4 carry as the
> brief's working assumptions into Stage 2 (AS-4's unfollow-corpus question is OQ-3).

- **AS-1 — `subscribe` reuses the existing D-7 kind (no new global decision).** D-7 already
  reserves `EngagementEvent.kind = subscribe`; a follow emits through `signals.capture.*`
  with no schema change. *(Brief AC5, AS-1; verified against [/DECISIONS.md](../../DECISIONS.md) D-7.)*
- **AS-2 — Follow originates from the `app-pages` surface.** The follow control lives on the
  app page (reusing the established slot/inclusion-tag pattern `ratings-reviews` used for the
  AP-1 reviews slot). *(Brief AS-2; verified — `apps/pages` closed out.)*
- **AS-3 ✓ (RESOLVED DN-13 = option A) — notice *generation* is out; the notice *surface*
  ships now.** Update/early-access content is produced by `developer-updates` (Phase 3, not
  built), so generation is unambiguously out of scope. **DN-13 chose option A:** MVP ships a
  **forward-compatible, empty-until-producer notice surface** in the feed now (mirrors the
  honest-MVP pattern of D-8, where `ratings-reviews` shipped a gate that is ~always
  not-eligible until a `DIGEST` emitter exists); the surface is ready for `developer-updates`
  with no rework. *Rejected:* option B (defer the surface entirely — weaker return pull, R1);
  and, outright, building any notice *authoring* here (that is `developer-updates`, CLAUDE.md
  §6.4 single responsibility). Fixes AC8 as in scope. *(Brief AS-3, AC8, R1; DN-13.)*
- **AS-4 — Follow state is this feature's own mutable store; the corpus event is append-only
  D-7.** One current relationship per user×app (editable: follow/unfollow), distinct from the
  append-only `subscribe` event — mirrors `ratings-reviews`' mutable `ratings_rating` vs. the
  D-7 corpus. Whether *unfollow* needs its own corpus representation (D-7 has no `unfollow`
  kind) is left to Stage 2 (OQ-3). *(Brief AS-4.)*
- **AS-5 ✓ (PRIVACY — CONFIRMED DN-13) — account deletion removes follow state; emitted
  events follow SC-10.** Deleting an account removes its live follow relationships (not
  corpus), while already-emitted `subscribe` events are anonymized-not-purged per the
  existing **SC-10** rule — no new corpus-deletion behavior invented here. *(Brief AC9, AS-5;
  CLAUDE.md §6.5; DN-13.)*

> No new **global** decision is proposed at Stage 1 — the feature reuses D-3 (identity),
> D-6 (catalogued app), and D-7 (event schema incl. the `subscribe` kind) as-is. The
> Architect (Stage 2) will weigh whether anything (e.g. unfollow's corpus representation,
> AS-4/OQ-3) warrants one.

## Design decisions (Stage 2, Software Architect, 2026-06-21 — [DESIGN.md](DESIGN.md))

> Feature-local. **No new global ADR** — the design reuses D-3/D-6/D-7 as-is. Pending user
> approval of the design (DN-14).

- **AS-DESIGN-1 — `Subscription` is this feature's own mutable store; deletion CASCADEs (the
  deliberate contrast with ratings' SET_NULL).** One `subscriptions_subscription` row per
  user×app, `created`/hard-deleted, never versioned (AS-4). The `user` FK is **CASCADE**, so
  account deletion removes follow state automatically with **no edit to `accounts.delete_account`**
  (AC9). *Why CASCADE, not SET_NULL:* a follow is live relationship state with no standalone
  analytic value once the person is gone — the behavioral residue already lives in the retained
  `subscribe` corpus event (SC-10 anonymize-not-purge, unchanged). A rating, by contrast, *is*
  eligibility-tagged corpus and must survive unlinked. *Rejected:* deriving follow state from the
  append-only corpus (no table) — reconstructing mutable current-state from an event log is the
  complexity AS-4 avoids and forces OQ-3's global change. *(DESIGN §4.)*
- **AS-DESIGN-2 — the follow write and its one `subscribe` emit are ONE atomic transaction.**
  `services.follow_app` calls `signals.capture.record_subscribe` (the single D-7 write path)
  *inside* the same `transaction.atomic()` as the `get_or_create`, and only when a new row was
  created. So M5 (subscribe events == follows) is **1:1 by construction**, not merely measured:
  a committed follow ⟺ a committed event; a capture failure rolls back the follow too (no orphan
  state) and is surfaced + counted via `CAPTURE_ERROR{kind=subscribe}` (AC5/AC7). Calling capture
  (not bypassing it) honors D-7's single-write-path rule; nesting its `atomic()` as a savepoint
  and rolling back an *uncommitted* event is not an append-only violation. *(DESIGN §6.1/§14.)*
- **OQ-3 → RESOLVED: unfollow needs NO D-7 corpus kind (at MVP).** D-7 has no `unfollow` kind;
  we do not add one. The mutable store already holds current state; unfollow is an *absence*,
  which D-7 models by read-time derivation (like "did-not-return"), not a stored row; M6
  (unfollow rate) is read from the `SUBSCRIPTION_UNFOLLOWED` metric; no consumer needs
  unfollow-as-corpus yet (building it = speculative abstraction, §5.5). Stays additively
  reversible — a future churn consumer can add the `EventKind` without touching this feature.
  *Rejected:* OQ-3 = yes (add the kind now). *(DESIGN §8; resolves [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-3.)*
- **OQ-4 → RESOLVED: the follow control is a fail-soft `{% app_follow app %}` inclusion tag in a
  new app-page Follow slot (after the header).** Mirrors `ratings`' AP-1 slot pattern: a new
  `<section aria-label="Follow">` immediately after `<header>`, rendering viewer-state (anonymous
  → "Sign in to follow"; signed-in → Follow/Unfollow). Viewer-state-driven, so app-page
  uniformity holds; fail-soft so a subscriptions fault never 500s the page; one-section rollback;
  independent of the ratings slot (no collision). *Rejected:* editing an existing slot's content
  (no natural home); a header-inline control (clutters identity). *(DESIGN §5f; resolves
  [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) OQ-4.)*
- **AS-DESIGN-3 — additive D-6 read `catalog.get_catalogued_apps(ids)` (no N+1 feed).** The feed
  resolves N followed `app_id`s in one bulk, accepted-only query (vs O(N) `get_catalogued_app`
  calls or an unbounded whole-catalog read). This is an **additive D-6 read-surface extension**
  (same `CatalogApp` shape, accepted-only guarantee preserved), exactly the "one-line selector
  over the same base queryset" D-6 anticipates — **not a new global ADR**. Mirrors
  `signals.funnel_for_apps` (bulk) beside `app_funnel` (single). *(DESIGN §4.3.)*
- **AS-DESIGN-4 — the notice surface is a single empty-until-producer seam (AS-3 = option A).**
  `notices.notices_for_apps(app_ids) -> list[Notice]` returns `[]` today (no producer); the
  feed renders notices if any, else "No news yet" (AC8). The `Notice` DTO pins the render
  contract `developer-updates` (Phase 3) will honor. No producer/registry/provider machinery is
  built — one repointable function (the honest-MVP pattern of D-8's gate). *(DESIGN §5d/§6.3.)*
