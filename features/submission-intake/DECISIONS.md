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
