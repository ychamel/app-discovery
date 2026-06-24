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

- **OQ-DU-1 (for Stage 2) — reverse-audience read. → RESOLVED (DESIGN §13/§14, DN-DU-DESIGN approved 2026-06-24).**
  developer-updates needs "who currently follows app X" (to scope reach and feed delivery), but
  `apps/subscriptions/selectors.py` only exposes user-scoped reads (`is_following`,
  `followed_apps`). **Resolution:** the AS-3 seam is **pull** — the feed already passes the
  *followed* app_ids into `notices_for_apps`, so notice *delivery* needs **no** reverse read at
  all (this makes M5=0 structural and kills the R3 fan-out). The reverse read is needed only for
  the **audience hint + M2 reach**, met by an additive bounded `subscriptions.selectors.subscriber_count(app_id)`
  (one indexed COUNT) + the additive `subscriptions_app_idx` index (**DU-DESIGN-1/DU-DESIGN-6**).
- **OQ-DU-2 (for Stage 2) — the transparency line (vision Open Q #5). → RESOLVED (DESIGN §8/§14, DN-DU-DESIGN approved 2026-06-24).**
  DU-3 fixes the principle (no score-bearing emit on post; rate-limited). **Resolution
  (verified end-to-end):** posting writes only an `updates_notice` row; `apps/updates` imports
  **no `signals.capture`** (AST-enforced, the discovery/dashboard precedent); the only corpus
  entries are followers' **own** returns via the existing `apps/pages` `APP_PAGE`/`page_reengagement`
  kinds — the developer controls content, never signal (**DU-DESIGN-5**). Must hold through ship
  (the AST test is the structural guarantee).

> **Resolved-direction by the brief (pending DN-20):** the seeded *transparency line* and
> *relationship-to-developer-dashboard* questions are answered in direction — no score-bearing
> emit (DU-3, OQ-DU-2 carries the verification), and a clean boundary (reception/analytics is
> developer-dashboard, explicitly out of scope here).
