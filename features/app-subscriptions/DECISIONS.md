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
