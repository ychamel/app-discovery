# DECISIONS — app-pages

*Feature-local decisions (choice + rationale + rejected alternatives). Repo-wide
decisions go in [/DECISIONS.md](../../DECISIONS.md).*

> Stage-1 scoping calls below are **provisional pending brief approval** (CONTROL.md
> DN-9). They reuse the global contracts D-1/D-5/D-6/D-7 as-is — no new global decision
> is proposed by this feature at Stage 1.

### AP-1: Reviews are a slot, not content, at the app-pages MVP
- **Date:** 2026-06-19
- **Stage / feature:** `1-define` / app-pages (Product Analyst)
- **Decision:** The uniform template includes a **reviews section slot rendered as an
  empty state**; app-pages does **not** capture, store, weight, or display ratings/reviews,
  nor implement the curated-rating gate. All review content is owned by `ratings-reviews`.
- **Why:** `ratings-reviews` depends on app-pages and does not exist at app-pages' build
  time, so there is no review source to render; the breakdown §4.2 "reviews block" is
  satisfied at MVP by reserving the slot, keeping the boundary clean (CLAUDE.md §5.4
  one-source-of-truth, §6.4 stay-in-scope). Avoids R4 scope bleed.
- **Alternatives rejected:** (a) Build minimal rating capture in app-pages now — duplicates
  what `ratings-reviews` owns and forecloses the gate design that feature must make. (b)
  Omit the slot entirely — would force a template change (non-uniform churn) when reviews
  land. → tracked as OQ-1; confirmed by DN-9.

### AP-2: Press kit at MVP = the public page itself, no separate press apparatus
- **Date:** 2026-06-19
- **Stage / feature:** `1-define` / app-pages (Product Analyst)
- **Decision:** The "press kit / web home" role (vision §6) is realized **by the public
  page + a stable shareable link + the media already in submission**. No separate
  downloadable press-asset bundle, press-contact field, or embargo control is in the MVP.
- **Why:** The page is already self-contained and shareable (AC4); extra press apparatus is
  speculative scope (CLAUDE.md §5.5 no speculative abstraction) better placed in a later
  dev-facing feature if demand appears. Keeps app-pages a read-only render over the D-6
  catalog.
- **Alternatives rejected:** Build press-asset downloads / press-contact now — adds owned
  content and editing surface app-pages otherwise has none of, for no MVP-validated need.
  → tracked as OQ-3; confirmed by DN-9.
