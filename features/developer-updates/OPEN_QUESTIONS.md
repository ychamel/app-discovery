# OPEN_QUESTIONS — developer-updates

*All stages. Ambiguities, deferrals, escalations. Whoever is active appends here.*

## Seeded at scaffold (from signal-capture OQ-4)

- **Transparency line for developers (vision Open Q #5)** — a dev→user channel plus
  reception data risks becoming a "gaming manual." Where is the line between a useful
  communication tool and one that helps manufacture engagement signal? Must be settled before
  this feature ships, since it emits into the same corpus the Quality Score will trust.
- **Relationship to `developer-dashboard`** — the dashboard *shows* reception (read-only);
  this feature *acts* (post / notify). Keep the boundary clean so they don't merge into one
  over-scoped surface.
- **Early-access scope** — is "early-access" just a kind of update post, or its own gated
  mechanism? (The Stage-1 review considered splitting it into a third feature and chose not
  to — revisit if it grows.) **→ Addressed by DU-1/DN-20.a:** MVP = a notice *kind*
  (announcement); entitlement enforcement out of scope.

## Stage 1 — Product Analyst (2026-06-24)

- **OQ-DU-1 (for Stage 2) — reverse-audience read.** developer-updates needs "who currently
  follows app X" (to scope reach and feed delivery), but `apps/subscriptions/selectors.py`
  only exposes user-scoped reads (`is_following`, `followed_apps`). The model supports it
  (`Subscription.objects.filter(app_id=…)`), so design must add an **additive, bounded**
  (follower-count-independent, mirror the `followed_apps` two-query pattern) audience/feed
  read. **Owner:** Software Architect. Confirmed by reading the selectors + model.
- **OQ-DU-2 (for Stage 2) — the transparency line (vision Open Q #5).** DU-3 fixes the
  principle (no score-bearing emit on post; rate-limited). Design must confirm the concrete
  data flow honors it end-to-end — i.e. nothing in the post → feed → return path writes a
  developer-triggerable signal into the corpus the Quality Score trusts. **Owner:** Software
  Architect; must be settled before ship (seeded OQ).

> **Resolved-direction by the brief (pending DN-20):** the seeded *transparency line* and
> *relationship-to-developer-dashboard* questions are answered in direction — no score-bearing
> emit (DU-3, OQ-DU-2 carries the verification), and a clean boundary (reception/analytics is
> developer-dashboard, explicitly out of scope here).
