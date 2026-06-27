# FEATURE_BRIEF.md — platform-staging

**Status:** **APPROVED** 2026-06-27 (gate **DN-PS-BRIEF** answered in [CONTROL.md](../../CONTROL.md);
PS-1/2/3 resolved — see *Decisions needed to approve* below). **Stage 1 (Product Analyst) artifact.**

**Upstream source:** global [D-11](../../DECISIONS.md) (next bet = staging-validation-before-live),
[STRATEGY.md](../../STRATEGY.md) bet sequence, vision [§5.4 step 3](../../curated-app-platform-design.md),
ratified by the user 2026-06-27 (DN-STRAT-1).

---

## Problem statement

The developer wedge is **code-complete but has never been reachable by anyone**. All 13
shipped features were released to *local/dev only* — nothing has run over HTTPS, on a real
domain, with a real email transport, or on a phone. That means:

- **The thesis is unvalidated.** The bring-your-own-audience bet ([D-10](../../DECISIONS.md))
  rests on the developer's *public face* — the **app page** and the **embeddable widget** —
  looking credible to a real audience. No one has ever seen those surfaces on a device that
  isn't the developer's own laptop in `DEBUG` mode.
- **The deployment path is unexercised.** Production-only concerns are configured but never
  run: `SECRET_KEY` provisioning, `ALLOWED_HOSTS`, HTTPS/HSTS/secure-cookies (all gated on
  `not DEBUG` in [config/settings.py](../../config/settings.py)), a **real email provider**
  (currently the console stub), static-asset serving (no `STATIC_ROOT`/collectstatic is
  configured today), uploaded-media serving, and any monitoring.
- **We cannot responsibly recruit.** Vision §5.4 step 3 puts a validation gate *before* the
  white-glove recruitment of the 50–150 founding developers. Putting real founders onto an
  un-walked, mobile-unchecked UI would risk the wedge's public face on first contact.

**Why now:** every other option on the roadmap (network, `weekly-digest`, editorial,
[D-9](../../DECISIONS.md) monetization) is **density-gated**, and density requires real
adoption, which requires being reachable. Reachability + validation is the only un-gated next
step ([D-11](../../DECISIONS.md)).

## Goal

A reachable, production-configured **staging** deployment of the wedge that has been walked
end-to-end by all three roles on **web and mobile**, with every defect found either fixed or
logged — producing a clear *go / no-go* verdict for live recruitment and an *evidence-based*
verdict on the frontend ([D-11](../../DECISIONS.md)).

## Definitions (no undefined terms downstream)

- **Staging environment** — a deployment of this codebase that is **publicly reachable over
  HTTPS at a stable URL**, configured as production is (`DEBUG=off`, real `SECRET_KEY`/hosts,
  real email transport, persistent PostgreSQL, served static + media), and **separate from any
  developer's local machine**. It is the rehearsal of production, not production itself.
- **The wedge / developer hub** — the already-built surfaces: accounts (passwordless
  magic-link), app submission + the public **app page**, the **updates/changelog** feed, the
  **embeddable widget** + its conversion-attribution funnel, the **developer dashboard**, app
  **subscriptions/follow**, the **interest profile**, and **open search/browse**.
- **The three roles** —
  - **End user / audience member:** arrives from an app page or widget; registers, follows
    apps, sets interests, browses/searches.
  - **Developer:** signs up, submits an app, edits its public page, posts updates, embeds the
    widget, reads their dashboard (reach / engagement / ratings / conversion funnel).
  - **Admin / operator:** runs the platform — reviews and **ACCEPTs** a submission (the
    [D-6](../../DECISIONS.md) ACCEPTED-only gate), confirms email is sending, observes
    logs/monitoring.
- **Full-role walkthrough** — completing each role's primary journeys, in sequence, against
  the live staging URL.
- **Web + mobile** — a desktop browser **and** a phone-sized viewport (real device or emulated
  at standard breakpoints).
- **Responsive / polished** — every wedge template renders usably and without layout breakage
  across desktop and mobile widths; the public app page and widget look credible, not raw.
- **Agent-verifiable vs. human-judgment** — an acceptance criterion is *agent-verifiable* if a
  command/check can confirm it (deploy succeeds, route returns 200, email is dispatched,
  migrations apply). UX-quality criteria (“looks credible on mobile”) require a **human
  sign-off**; the brief marks which is which, and *who* signs off is **PS-3** below.

## User stories

1. **As the platform operator,** I want the built wedge deployed to a reachable,
   production-configured staging environment, so that I can exercise it exactly as a real user
   would — over HTTPS, on a real domain, with real email.
2. **As the platform operator,** I want the deploy to be repeatable (config, secrets,
   migrations, static assets, uploaded media), so that promoting staging → production later is
   a known low-risk step, not a one-off.
3. **As a developer evaluating the platform,** I want to complete the full developer journey on
   staging — sign in, submit an app, edit its public page, post an update, embed the widget,
   and read my dashboard — on both desktop and mobile, so that the public face I will show my
   audience is credible.
4. **As an audience member arriving from a developer's page or widget,** I want to register,
   follow apps, set my interests, and browse/search on both desktop and mobile, so that the
   bring-your-own-audience capture path actually works on a real device.
5. **As the platform admin/operator,** I want to run the operations path — review and ACCEPT a
   submission, confirm email is sending, and see logs/monitoring — so that the platform can be
   *operated*, not just demoed.
6. **As the platform operator,** I want the walkthrough to end in an explicit verdict — (a)
   **go / no-go** for live recruitment and (b) **frontend evidence** (templates sufficient, or
   a specific surface that demonstrably needs more) — so that the [D-11](../../DECISIONS.md)
   recruitment and SPA decisions are made on evidence, not a hunch.

## Acceptance criteria (Given / When / Then)

**S1 — reachable, production-configured deployment**
- **AC1.1** *(agent-verifiable)* **Given** the deployed staging instance, **when** its base URL
  is requested over the public internet, **then** it responds over **HTTPS** with `DEBUG` off
  and serves the home/landing surface (no debug error page, no `ALLOWED_HOSTS` rejection).
- **AC1.2** *(agent-verifiable)* **Given** the staging instance, **when** each primary wedge
  route is requested (home, an app page, search/browse, sign-in, dashboard, the widget embed,
  Django admin), **then** each returns its expected success status with **CSS/JS and uploaded
  media assets loading** (no missing-static / broken-image failures).
- **AC1.3** *(agent-verifiable)* **Given** a fresh database, **when** the deploy runs, **then**
  all migrations apply cleanly to an empty PostgreSQL and the app starts with no manual SQL.

**S2 — repeatable deploy**
- **AC2.1** *(agent-verifiable)* **Given** the deploy procedure, **when** it is run a second
  time from a clean state following only the written steps, **then** it produces an equivalent
  working environment with no undocumented manual fix-ups.
- **AC2.2** *(agent-verifiable)* **Given** the deploy, **when** secrets and environment config
  are inspected, **then** no secret is committed to the repo and every required variable is
  documented (extending [.env.example](../../.env.example)).

**S3 — developer journey (web + mobile)**
- **AC3.1** *(mixed)* **Given** a new developer on staging, **when** they sign in via the
  **magic-link email**, submit an app, edit its public page, post an update, and read their
  dashboard, **then** every step completes end-to-end and the **email actually arrives** via
  the real transport (not the console).
- **AC3.2** *(human-judgment)* **Given** the developer's public app page and the embeddable
  widget, **when** viewed on a **phone-sized viewport**, **then** both render without layout
  breakage and read as credible — sign-off recorded against this criterion.
- **AC3.3** *(agent-verifiable)* **Given** an embedded widget on a third-party page, **when** it
  loads and is clicked through, **then** the conversion-attribution funnel records the
  impression → click → conversion as designed (the firewall stays intact).

**S4 — audience journey (web + mobile)**
- **AC4.1** *(mixed)* **Given** an anonymous visitor arriving from an app page or widget,
  **when** they register, follow an app, set interests, and browse/search, **then** every step
  completes end-to-end on **both desktop and a phone-sized viewport**.
- **AC4.2** *(human-judgment)* **Given** the registration and browse/search surfaces on mobile,
  **when** walked, **then** they are usable without layout breakage — sign-off recorded.

**S5 — admin / operations path**
- **AC5.1** *(agent-verifiable)* **Given** a PENDING submission, **when** the admin reviews and
  **ACCEPTs** it, **then** it becomes visible on the public catalogue per the D-6 gate.
- **AC5.2** *(agent-verifiable)* **Given** the running instance, **when** an operator looks for
  signal of health, **then** application logs and basic uptime/error monitoring are observable
  (the operator can tell whether the site is up and whether requests are erroring).

**S6 — explicit verdict**
- **AC6.1** *(human-judgment)* **Given** the completed walkthrough, **when** all role journeys
  have been attempted, **then** a written **go / no-go for live recruitment** verdict exists,
  listing every defect found and its disposition (fixed / logged).
- **AC6.2** *(human-judgment)* **Given** the walkthrough evidence, **when** the frontend is
  assessed, **then** a written verdict states either “templates sufficient” or names the
  **specific surface(s)** that demonstrably need more — feeding the D-11 evidence-gated
  SPA decision (a D-4-revisit ADR, not a silent rewrite).

## Success metrics

| Metric | Target |
|--------|--------|
| **M1 — Reachability** | Staging base URL returns 200 over HTTPS, `DEBUG` off (binary: yes). |
| **M2 — Route availability** | 100% of the primary wedge routes (AC1.2 list) return their expected status with assets loading. |
| **M3 — Role-journey completion** | 100% of the three roles' primary journeys completed end-to-end (web). |
| **M4 — Mobile pass** | Every public/wedge surface signed off as usable + unbroken on a phone-sized viewport. |
| **M5 — Email deliverability** | A magic-link email sent on staging actually arrives at a real inbox. |
| **M6 — Deploy reproducibility** | A second clean run from the written steps succeeds with zero undocumented manual steps. |
| **M7 — Defect disposition** | 100% of walkthrough defects either fixed or logged with an owner; zero unresolved blockers in the go/no-go verdict. |

## In scope

- Standing up one reachable, production-configured **staging** environment for the existing
  codebase (hosting, domain/URL, HTTPS, secrets/config, persistent PostgreSQL, served static +
  uploaded media, a **real email transport**, basic monitoring/logging visibility).
- **Polishing** the existing server-rendered Django templates and making them
  **mobile-responsive** ([D-4](../../DECISIONS.md)/[D-11](../../DECISIONS.md)).
- Running the **full-role walkthrough** (user / developer / admin × web + mobile) and **fixing
  the defects it surfaces** in the existing wedge.
- Producing the two written **verdicts** (go/no-go; frontend evidence).
- Documenting the deploy as a repeatable procedure.
- **Two committed `.md` deliverables requested by the user at the gate** (PS-2/PS-3):
  - An **email-provider setup guide** — the Architect (Stage 2) recommends a specific
    transactional-email provider within the PS-1 budget (no provider exists today, PS-2); the
    deploy work writes an `.md` walking through creating the account and wiring credentials.
  - A **suggested full-role walkthrough script** (`.md`) the user follows to perform and sign
    off the human-judgment journeys (AC3.2/AC4.2/AC6) — authored at Stage 4 alongside
    `TEST_PLAN.md`. The user performs the walkthrough themselves (PS-3).

## Out of scope

- **Live recruitment** of founding developers (vision §5.4 step 3) — follows *after* this
  feature's go verdict.
- **A dedicated SPA frontend / framework rewrite** — explicitly deferred + evidence-gated
  ([D-11](../../DECISIONS.md)); this feature only *gathers the evidence* (AC6.2).
- **New product features** — network/`weekly-digest`, editorial-curation, D-9 monetization all
  stay density-gated/backlog. No new user-facing capability is built here beyond deploy + UX
  polish + defect fixes.
- **Native mobile apps** and **off-platform (install) attribution** (vision §7 Q4) — the
  unprototyped hard problem; not on this web-only critical path.
- **Promoting staging to a real production target** — staging is the rehearsal; the live cutover
  is the *next* bet after the go verdict (subject to PS-1 below).

## Constraints & assumptions

| # | Item | Verified? |
|---|------|-----------|
| C1 | Config is already 12-factor / env-driven; secrets read from the environment ([config/settings.py](../../config/settings.py)). | **Verified** |
| C2 | HTTPS/HSTS/secure-cookies and `SECRET_KEY`/`ALLOWED_HOSTS` enforcement all activate on `not DEBUG`. | **Verified** |
| C3 | Email transport is pluggable; the current default is the **console stub** — a real provider must be configured for AC3.1/M5. | **Verified** |
| C4 | **No `STATIC_ROOT`/collectstatic and no deploy manifest** exist in the repo today — static/media serving for non-`DEBUG` is a real gap to close (AC1.2). | **Verified** |
| C5 | Database is **PostgreSQL-only** (citext/UUID/FTS depend on it); staging needs a persistent managed/hosted Postgres. | **Verified** |
| C6 | The frontend stays on **server-rendered Django templates**; no SPA is introduced ([D-11](../../DECISIONS.md)). | **Verified** |
| A1 | **Resolved (PS-1):** start on **free tier**; a **$20–100/mo** budget is available when deploying; staging is **promoted to production later** (prod-bound, build for durability — not throwaway). | **Resolved — user** |
| A2 | **Resolved (PS-2):** **no email provider exists yet** — the Architect picks one within budget and the deploy ships an **`.md` setup guide** (see In scope). AC3.1/M5 still gate on a real inbox once configured. | **Resolved — user** |
| A3 | **Resolved (PS-3):** the **user performs the walkthrough** and records sign-offs; the agent supplies a **suggested walkthrough `.md`** (Stage 4). | **Resolved — user** |

## Risks

| Risk | Likelihood / Impact | Mitigation |
|------|---------------------|------------|
| Real email provider not chosen/credentialed → magic-link (passwordless) auth can't be walked end-to-end; **the whole journey is blocked at sign-in**. | High / High | Resolve **PS-2** early; AC3.1/M5 gate on a real inbox. |
| Static/media serving unconfigured for non-`DEBUG` (C4) → broken styling / missing screenshots on staging make the public face look raw. | Med / High | Close the static/media gap as deploy work; AC1.2 verifies assets load. |
| Mobile templates break on small viewports — this is the **load-bearing public surface**. | Med / High | Walk on a real device + standard breakpoints; AC3.2/AC4.2/M4 require fixes. |
| Scope creep into the SPA rewrite under the banner of “polish.” | Med / High | SPA explicitly out of scope; AC6.2 only *gathers evidence* for a separate D-4-revisit. |
| No human available for UX sign-off → AC3.2/AC4.2/AC6 cannot be honestly closed. | Med / Med | Resolve **PS-3**; agent-verifiable ACs proceed regardless, human-judgment ACs block on sign-off. |

## Vision alignment

Serves vision **§5.4 step 3** (validate the wedge in staging before recruiting) and the
[D-10](../../DECISIONS.md) bring-your-own-audience wedge, executes global
[D-11](../../DECISIONS.md), and respects [D-4](../../DECISIONS.md) (templates) and the
*money-buys-tools-never-position* premise (this feature adds no ranking surface).

---

## Decisions needed to approve this brief (gate DN-PS-BRIEF) — **RESOLVED 2026-06-27**

Answered by the user in [CONTROL.md](../../CONTROL.md); brief promoted to APPROVED.

- **PS-1 — Budget & staging posture → RESOLVED.** Start on **free tier**; **$20–100/mo** budget
  available when deploying; staging is **promoted to production later** (prod-bound → deploy work
  targets durability, not disposability). The specific provider/domain remain a **Stage-2
  architecture choice** per D-11/[D-2](../../DECISIONS.md), now bounded by this budget/posture.
- **PS-2 — Email provider → RESOLVED.** **No provider exists today.** The Architect selects a
  transactional-email provider within the PS-1 budget; the deploy work ships an **`.md` setup
  guide** (account creation + credential wiring). Magic-link auth + M5 gate on a real inbox once
  configured (AC3.1/AC4.1).
- **PS-3 — UX walkthrough sign-off owner → RESOLVED.** **The user performs and signs off** the
  human-judgment walkthrough (AC3.2/AC4.2/AC6) on their own device; the agent supplies a
  **suggested walkthrough `.md`** (authored at Stage 4 with `TEST_PLAN.md`) and runs every
  agent-verifiable check.
