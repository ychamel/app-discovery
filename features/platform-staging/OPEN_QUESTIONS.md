# OPEN_QUESTIONS.md — platform-staging

_All stages: ambiguities, deferrals, escalations._

| ID | Question | Raised by | Stage | Status |
|----|----------|-----------|-------|--------|
| PS-1 | Budget & staging posture: free-tier/low-cost vs. budgeted? staging promoted to prod later, or throwaway? | Product Analyst | 1-define | **RESOLVED 2026-06-27** — free tier to start; **$20–100/mo** when deploying; **prod-bound** (promote staging→prod later, build for durability). Provider/domain stay a Stage-2 call, bounded by this. |
| PS-2 | Real transactional-email provider available (which)? Magic-link auth + M5 are blocked without one. | Product Analyst | 1-define | **RESOLVED 2026-06-27** — **none today**. Architect picks one in budget; deploy ships an **`.md` setup guide**. AC3.1/M5 gate on a real inbox once configured. |
| PS-3 | Who performs & signs off the human-judgment UX walkthrough (AC3.2/AC4.2/AC6) on a real device? | Product Analyst | 1-define | **RESOLVED 2026-06-27** — **the user** performs/signs off; agent supplies a **suggested walkthrough `.md`** (Stage 4). |
