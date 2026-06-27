# OPEN_QUESTIONS.md — platform-staging

_All stages: ambiguities, deferrals, escalations._

| ID | Question | Raised by | Stage | Status |
|----|----------|-----------|-------|--------|
| PS-1 | Budget & staging posture: free-tier/low-cost vs. budgeted? staging promoted to prod later, or throwaway? | Product Analyst | 1-define | **RESOLVED 2026-06-27** — free tier to start; **$20–100/mo** when deploying; **prod-bound** (promote staging→prod later, build for durability). Provider/domain stay a Stage-2 call, bounded by this. |
| PS-2 | Real transactional-email provider available (which)? Magic-link auth + M5 are blocked without one. | Product Analyst | 1-define | **RESOLVED 2026-06-27** — **none today**. Architect picks one in budget; deploy ships an **`.md` setup guide**. AC3.1/M5 gate on a real inbox once configured. |
| PS-3 | Who performs & signs off the human-judgment UX walkthrough (AC3.2/AC4.2/AC6) on a real device? | Product Analyst | 1-define | **RESOLVED 2026-06-27** — **the user** performs/signs off; agent supplies a **suggested walkthrough `.md`** (Stage 4). |
| DN-PS-DESIGN | Ratify the Stage-2 architecture: (1) host = **Render** (free now, ~$14–25/mo durable, PS-1); (2) email = **Resend** vs Postmark (PS-2); (3) consolidate the 6 `base.html` into **one shared responsive shell** vs in-place polish. Standard items PS-DESIGN-2/3/5/6/8 proceed on approval. | Software Architect | 2-design | **RESOLVED 2026-06-27** — user confirmed inline: **(1) Render**, **(2) Resend**, **(3) Consolidate**; standard items proceeded on that approval. PS-DESIGN-1…8 → RATIFIED; recorded as global **[D-12](../../DECISIONS.md)**; Stage → 3-plan. |
