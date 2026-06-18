# DECISIONS — submission-intake

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

## A-SI (2026-06-17) — Brief approved

`FEATURE_BRIEF.md` approved by the user ("proceed"). The 7 calls flagged under *For
confirmation at approval* are confirmed (mirroring `interest-taxonomy`'s A4) and recorded
below as SI-1…SI-7. Stage advanced to `2-design`.

- **SI-1 — "An app" = a web app reachable at a URL.** "Platform target" reduces to *web*
  at MVP. *Rationale:* beachhead niche is vibecoded webapps ([D-1](../../DECISIONS.md)).
  *Rejected:* native/mobile/desktop intake — deferred, web-only at MVP (Out of scope).
- **SI-2 — The gate is human-applied (admin role) against a checklist.** Manual review;
  no automated malware/uptime/duplicate detection at MVP. *Rationale:* bounded MVP volume
  of 50–150 founding apps (breakdown §4.3, [D-2](../../DECISIONS.md)). *Rejected:* building
  detection automation now — named later step, not built (Out of scope).
- **SI-3 — Rejection is non-terminal.** Developers may correct and resubmit (AC7).
  *Rationale:* apps iterate rapidly post-launch (vision §5.2).
- **SI-4 — Apps are owned by an individual developer account.** No team/org ownership at
  MVP. *Rationale:* mirrors `identity-accounts`' individual-account scope. *Rejected:*
  team/org-owned apps — deferred (Out of scope).
- **SI-5 — Founding-catalog recruitment is an offline editorial process.** The submission
  form serves the resulting self-submission; no separate in-product recruitment surface
  (closes OQ-1; R6). *Rationale:* breakdown §7 Q6 "likely offline". *Reopens scope* if an
  in-product invite/recruitment surface is later wanted.
- **SI-6 — Owner metadata *correction* is in scope; formal versioned updates + re-boost
  are deferred.** *Rationale:* §5.2 boundary — basic accuracy correction (AC8) yes, the
  update/re-boost manager no (Out of scope).
- **SI-7 — Media at MVP = screenshots/images;** exact slots/limits/formats align with
  [`app-pages`](../app-pages/) in Stage 2 ([unverified] → confirmed as the MVP shape; the
  Architect coordinates exact limits, OQ-3). *Rationale:* brief Constraints.

## Stage-4 build deviations (Senior Engineer, 2026-06-18)

Small implementation choices made while building `apps/catalog`; none change the DESIGN
contracts (DESIGN §5 surfaces, §11/§12 D-6, the gate, the lifecycle).

- **SI-8 — JSON API is mounted under `catalog/api/…`, pages under `catalog/…`.** DESIGN §5c
  lists API paths (`/apps`, `/apps/{id}`) and §8 lists page paths (`/apps`, `/apps/{id}`)
  that would *collide* on `GET /apps/{id}` (JSON vs HTML). Resolved by giving the API its own
  `api/` prefix. *Rationale:* the design paths are resource-relative; a prefix is an
  implementation detail that keeps both surfaces over the same services (no second source of
  truth). *Rejected:* content-negotiation on one path (more surprising; harder to test).
- **SI-9 — `Pillow` added to `pyproject.toml`** for boundary image validation, exactly as
  DESIGN §1/§9/§12 anticipated (mirrors how `interest-taxonomy` added `PyYAML`). Not a new
  stack decision.
- **SI-10 — `duplicate_flagged` is emitted inside `submit_app`** via a `normalized_url`
  existence check (the write path reading for its own metric); the consumer-facing duplicate
  *hint* remains `selectors.apps_sharing_url` (T-07). Keeps the "same app" rule in
  `urlnorm.normalize_url` as the single source of truth.
- **SI-11 — `urlnorm.normalize_url` collapses only the four cosmetic classes DESIGN §6c
  fixes** (scheme case, host case, default port, trailing slash) and deliberately does **not**
  collapse `www.` — `www.example.com` and `example.com` can serve different apps, and review
  is manual (SI-2), so over-merging is the worse error. Documented in the module.
