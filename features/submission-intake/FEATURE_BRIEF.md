# FEATURE_BRIEF — submission-intake

*Stage 1 artifact (Product Analyst). Status: **DRAFTED 2026-06-17 — awaiting approval**;
7 calls flagged under [For confirmation at approval](#for-confirmation-at-approval).
Sources: [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.3 +
§7 Q6, [curated-app-platform-design.md](../../curated-app-platform-design.md) §2.1 / §5.5
/ §6 Dev-facing, global [DECISIONS.md](../../DECISIONS.md) D-1/D-2/D-3/D-4/D-5, and this
feature's [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).*

## Coordinator scope seed (source: breakdown §4.3)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** Developer-facing · Phase 1 (get the catalog in — see breakdown §5)
- **Purpose:** Developer's entry point + the **objective** quality gate (works, not
  malware/spam/dupe, honest metadata).
- **MVP slice:** Submission form (metadata, tags, media, platform targets) + a checklist
  gate. Manual review acceptable at MVP volume.
- **Proves (hypothesis):** H2
- **Depends on:** identity-accounts, interest-taxonomy
- **Vision design ref:** §2.1, §5.5, §6 Dev-facing
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.3

---

## Glossary (no undefined domain terms)

- **App** — the unit a developer submits and the platform catalogues. In the beachhead
  niche (vibecoded webapps, [D-1](../../DECISIONS.md)) an app is a **web application
  reachable at a URL**; its "platform target" reduces to *web* at MVP.
- **Submission** — a developer's act of offering an app to the platform, together with the
  record it creates. A submission has a **lifecycle state** (e.g. pending review →
  accepted / rejected; withdrawn) — the exact states are Stage-2 design; the product-level
  transitions are fixed here.
- **App metadata** — the descriptive information that defines the app to the platform and,
  later, to users: at minimum a name, a description, the app URL, interest tags, and media.
- **Interest tag** — a unit from the shared controlled vocabulary owned by
  [`interest-taxonomy`](../interest-taxonomy/FEATURE_BRIEF.md). Apps are labelled **only**
  with existing tags, referenced by stable identity (`Tag.id`, [D-5](../../DECISIONS.md)).
- **Media** — visual assets describing the app (e.g. screenshots). Exact slots/limits are
  Stage-2 / [`app-pages`](../app-pages/) design.
- **Objective intake gate** — the review that filters a submission against **objective
  floors only** (vision §5.5): the app works, is not malware/spam, is not a duplicate, has
  honest metadata, and meets basic platform policy. It does **not** judge taste, quality,
  or merit — that is the audience's job, downstream.
- **Objective floor** — a pass/fail condition a reviewer can check without taste judgement
  (reachable? honest? duplicate? policy-compliant?). Contrast **merit/taste**, which the
  gate must never adjudicate (§5.5).
- **Platform editor** — an account holding the **admin** role
  ([D-3](../../DECISIONS.md)) authorized to review submissions against the gate. (The
  admin *role + gate* come from `identity-accounts`; richer review *tooling* is
  [`editorial-curation-tools`](../editorial-curation-tools/).)
- **Developer** — an account holding the **developer** role (self-serve,
  [D-3](../../DECISIONS.md)); the only role that may submit and own apps.
- **Honest metadata** — metadata that truthfully describes the actual app (the name,
  description, tags, and media match what the URL actually delivers).
- **Founding catalog** — the 50–150 hand-recruited launch apps (vision §5.4 step 2). Whose
  entry path runs through this feature; recruitment mechanics are an open question (OQ-1).
- **Beachhead niche** — the single launch vertical, **vibecoded webapps**;
  global [D-1](../../DECISIONS.md). It scopes *what an app is* and *the gate's content*,
  not the feature's structure.

---

## Problem statement

The platform's developer-side promise (vision §1, H2) is that an app with **$0 marketing**
can reach a real, matched audience and grow on reception alone. Nothing can be reached,
matched, or measured until it is **in the catalog** — and today there is no way for a
developer to put it there. There is no developer entry point, no record of an app or who
owns it, no way to label an app in the shared interest vocabulary so it *can* be matched,
and no gate to keep spam, broken links, dishonest listings, and duplicates out of the
catalog the whole user-side experience rests on.

The hard part is *what* that gate is allowed to do. The platform's entire premise (§5.5,
§8 one-line test) is that **visibility is earned by the audience, never granted by a
gatekeeper's taste**. So intake must filter **objective floors** — does it work, is it
honest, is it spam/malware, is it a duplicate, does it meet policy — and must refuse to
become a taste filter. Get that boundary wrong in either direction (too permissive →
catalog full of broken/dishonest apps that poison downstream signal; too judgemental →
the platform becomes the app-store gatekeeper it exists to replace) and the premise fails.

This is needed **now** because it is the first feature of Phase 1 and the on-ramp for
everything after it: [`app-pages`](../app-pages/) renders what is submitted here,
[`editorial-curation-tools`](../editorial-curation-tools/) curates from the apps accepted
here, [`signal-capture`](../signal-capture/) keys signals to them, and
[`developer-dashboard`](../developer-dashboard/) reports their reception. With no apps in
the catalog, none of those can be built or demonstrated.

## Goal

Give any developer a single, free, standardized way to submit a web app — with honest
metadata, interest tags from the shared vocabulary, and media — and run it through an
**objective** quality gate that filters broken/spam/dishonest/duplicate submissions
without judging taste, producing an owned, correctly-tagged, accepted app that downstream
features can display, curate, and measure.

## User stories (6)

- **US1 — Submit an app.** As a **developer**, I want to submit my web app with its
  metadata, interest tags, media, and URL through one standardized form, so that it can
  enter the catalog and reach an audience without my paying for placement.
  *(traces: breakdown §4.3; vision §2.1)*
- **US2 — Label with the shared vocabulary.** As a **developer / submitter**, I want to tag
  my app using only the platform's controlled interest tags, so that my app is described in
  the same language as user interests and can actually be matched.
  *(traces: vision §2.1 "interest tags"; cross-feature contract [D-5](../../DECISIONS.md))*
- **US3 — Apply the objective gate.** As a **platform editor**, I want to review each
  submission against a fixed checklist of **objective floors** — works, not malware/spam,
  not a duplicate, honest metadata, meets basic policy — so that bad submissions are
  filtered **without** rejecting apps on taste. *(traces: vision §5.5; breakdown §4.3
  "checklist gate")*
- **US4 — Get a decision I can act on.** As a **developer**, I want to learn whether my
  submission was accepted or rejected and, if rejected, *which objective criterion* failed,
  so that I can fix the issue and resubmit. *(traces: vision §5.2 "apps iterate rapidly
  post-launch"; §5.5)*
- **US5 — Own and correct my app.** As a **developer**, I want to own the app(s) I submit
  and correct their metadata or withdraw them, so that the catalog stays accurate and only
  I can change or remove my app. *(traces: ownership keys off the account,
  [D-3](../../DECISIONS.md))*
- **US6 — Hand a clean unit to downstream.** As a **consuming feature** (`app-pages`,
  `editorial-curation-tools`, `signal-capture`, `developer-dashboard`), I want every
  **accepted** app to expose a stable identity and honest, tag-referenced metadata and
  media, so that it can be displayed, curated into digests, and have its signals keyed to
  it — while non-accepted apps are not presented as catalogued. *(traces: cross-feature
  contract; breakdown §5 dependency chain)*

## Acceptance criteria (Given / When / Then)

- **AC1 (US1, submit).** *Given* a signed-in account holding the **developer** role,
  *when* it submits an app providing all required metadata (name, description, app URL,
  ≥1 interest tag, and media), *then* a submission is created, **owned by that account**,
  and enters the review pipeline in a *pending-review* state. *And given* a submission
  missing a required field or supplying a malformed URL, *when* submitted, *then* it is
  refused with a clear per-field message and **no** partial/invalid submission is created
  (fail loud — CLAUDE.md §5.4).
- **AC2 (US1, authorization).** *Given* an account **without** the developer role, *when*
  it attempts to submit an app, *then* the action is refused (submission is developer-gated
  via [D-3](../../DECISIONS.md)). *(Taking the developer role is self-serve and owned by
  `identity-accounts`, not here.)*
- **AC3 (US1/US3, identical free intake — fairness).** *Given* two submissions from
  different developers (e.g. a solo $0-marketing dev and a funded studio), *when* each is
  submitted and reviewed, *then* both pass through the **identical** required fields and the
  **identical** gate, and **no** field, fast-lane, decision, or turnaround is conditioned on
  the developer's payment status, budget, brand, or identity. *(vision §5.6 / §8 — money
  buys tools, never position.)*
- **AC4 (US2, closed vocabulary + stable reference).** *Given* the controlled vocabulary
  ([`interest-taxonomy`](../interest-taxonomy/)), *when* a developer adds interest tags to a
  submission, *then* only tags that **exist** in the vocabulary are accepted (validated at
  the write boundary; off-vocabulary / free-text values are rejected, never coined as new
  tags), and each accepted tag is stored by its **stable identity** (`Tag.id`), so a later
  tag rename or retire never invalidates the app's labels. *(traces [D-5](../../DECISIONS.md).)*
- **AC5 (US3, objective floors only).** *Given* a submission pending review, *when* an
  editor applies the intake checklist, *then* the submission is **accepted only if it passes
  every objective floor** — (a) the app is reachable/functional, (b) not malware/spam,
  (c) not a duplicate of an already-catalogued app, (d) its metadata is honest, (e) it meets
  basic platform policy — and is rejected otherwise, with the failing criterion recorded.
- **AC6 (US3, no taste gate).** *Given* a submission that an editor personally finds
  low-quality, niche, or unappealing **but** that passes every objective floor in AC5,
  *when* it is reviewed, *then* it is **not** rejected on taste/merit grounds — the gate
  filters floors, not merit (vision §5.5). *(Asserts the §5.5 boundary as a checkable
  product rule; reception decides quality downstream.)*
- **AC7 (US4, actionable decision + resubmit).** *Given* a reviewed submission, *when* a
  decision is reached, *then* the submitting developer is informed of the outcome and, if
  rejected, of **which objective criterion** failed, in actionable terms. *And given* a
  rejected submission, *when* the developer corrects the issue and resubmits, *then* it
  re-enters review — rejection is **not** terminal (vision §5.2).
- **AC8 (US5, ownership + correction + withdrawal).** *Given* a developer who **owns** an
  app, *when* they edit its metadata/tags or withdraw it, *then* the change is saved against
  their app (and re-validated by the gate where the edit affects a gated floor), and a
  withdrawn app stops being presented as catalogued. *And given* an account that does **not**
  own the app, *when* it attempts to edit or withdraw it, *then* the action is refused
  (ownership enforced via the account/role gate, [D-3](../../DECISIONS.md)).
- **AC9 (US6, downstream contract).** *Given* an **accepted** app, *when* a downstream
  feature reads it, *then* the app exposes a stable identity and its honest,
  tag-referenced (`Tag.id`) metadata and media for display, curation, and signal keying.
  *And given* a non-accepted app (pending / rejected / withdrawn), *when* the catalog is
  read, *then* it is **not** presented as a catalogued, curatable app.

## Success metrics

submission-intake is the **on-ramp half of H2**: it proves an app can *enter* the catalog
on equal, free footing — the *reach/reception* half is proven downstream
(`editorial-curation-tools` → `weekly-digest` → `signal-capture` → `developer-dashboard`).
Its metrics therefore measure intake health and gate integrity:

- **Submission completion rate** — developers who start a submission → submit a complete one
  (detects form friction).
- **Time-to-decision** — median time a submission sits *pending → decided*. No hard SLA at
  MVP ([D-2](../../DECISIONS.md)), but it must be **observable** so manual review is shown to
  keep up at founding volume.
- **Gate pass rate** — accepted ÷ reviewed. Watched as a health band: a collapsing pass rate
  is an early signal the gate is creeping from floors into taste (R1 / AC6).
- **Rejection-reason distribution** — share of rejections by objective criterion (works /
  spam / duplicate / dishonest / policy). A "rejected for other/quality" bucket trending up
  flags an AC6 violation.
- **Resubmission success rate** — rejected submissions later corrected and accepted
  (confirms feedback was actionable and rejection is non-terminal — AC7).
- **Tag coverage at submission** — share of submissions where the developer found ≥1 fitting
  tag without help; off-vocabulary attempts = **0** (closed set enforced, AC4). Feeds back to
  `interest-taxonomy`'s coverage metric (its R1).
- **Duplicate / spam catch** — duplicates and spam caught at the gate vs. slipping into the
  catalog (integrity of the floor; AC5).
- **Catalog growth toward the founding target** — count of accepted apps over time, against
  the 50–150 founding-catalog goal (vision §5.4).

## In scope

- **Developer self-serve submission** of a web app: the required metadata (name,
  description, app **URL**), **interest tags** (from the taxonomy), and **media**, plus the
  act of submitting it into a review pipeline.
- **App ownership** keyed to the submitting account ([D-3](../../DECISIONS.md)); one
  developer may own **multiple** apps.
- **Tagging an app from the controlled vocabulary** — validate against
  [`interest-taxonomy`](../interest-taxonomy/) and store by `Tag.id` ([D-5](../../DECISIONS.md)).
- **The objective intake gate**: a defined checklist of objective floors (works / not
  malware-spam / not duplicate / honest metadata / basic policy), applied by a **platform
  editor** (admin role) — **manual review at MVP volume**, with the failing criterion
  recorded on rejection.
- **Submission lifecycle** at the product level: pending → accepted / rejected →
  correct-and-resubmit; **withdraw**. (Exact states/mechanism are Stage-2 design.)
- **Decision notification** to the developer with an **actionable rejection reason**.
- **Developer editing and withdrawing their own app**, with re-validation where an edit
  touches a gated floor.
- **The accepted-app record** as the stable, honest, tag-referenced unit downstream features
  consume (the cross-feature output contract — AC9).

## Out of scope

- **App pages / public rendering / press kit** — owned by [`app-pages`](../app-pages/). This
  feature *captures and stores* app data; it does **not** render the public app page.
- **Matching, digest assembly, and which users see an app** — owned by
  [`editorial-curation-tools`](../editorial-curation-tools/) and the matcher. Intake does not
  decide an app's audience.
- **Signal capture** — impressions, click-through, installs/opens, returns, retention,
  shares — owned by [`signal-capture`](../signal-capture/). Intake records *what the app is*,
  never *how it is received*.
- **Developer dashboard / reception view** — owned by
  [`developer-dashboard`](../developer-dashboard/).
- **The Quality Score and any taste/merit/quality judgement** (vision §3, §5.5) — the gate is
  objective floors only; quality is decided by the audience downstream.
- **Update & re-boost manager, changelogs, versioning, second-launch boost** (vision §5.2) —
  deferred. Basic owner *metadata correction* (AC8) is in scope; formal versioned updates and
  the re-boost mechanic are not.
- **Automated malware / duplicate / uptime detection at scale** — MVP uses **manual** review
  against a checklist; automation is a deliberate later step (bounded trade-off, [D-2](../../DECISIONS.md)).
- **The interest vocabulary itself** — owned by [`interest-taxonomy`](../interest-taxonomy/);
  this feature consumes it, it does not define or curate tags.
- **The developer-role grant** — taking the developer role is self-serve and owned by
  [`identity-accounts`](../identity-accounts/); this feature *gates on* the role, it does not
  manage it. Likewise the **admin role + gate** come from `identity-accounts`; richer review
  *tooling* is `editorial-curation-tools`.
- **Monetization / paid submission tiers / paid fast-track** (vision §5.6) — all free at MVP;
  **no payment buys entry or a faster decision**, by design (AC3).
- **Native / mobile / desktop app submission and native-install attribution** — **web-only at
  MVP** ([D-1](../../DECISIONS.md)); revisit if the platform expands beyond web.
- **Team / organization-owned apps** — MVP apps are owned by an **individual** account
  (mirrors `identity-accounts`' individual-account scope).
- **Founding-catalog recruitment as a product surface** — likely an **offline** editorial
  process (OQ-1); the submission form serves the resulting self-submission.

## Constraints & assumptions

*(Each marked **[verified]** = grounded in a recorded decision/source, or **[unverified]** =
a proposal this brief makes that the user/Architect should confirm.)*

- **Platform = web.** "An app" is a web app reachable at a **URL**; the "platform target" of
  breakdown §4.3 reduces to *web* at MVP. **[verified — D-1]**
- **Stack** is Django / DRF / PostgreSQL with the shared `apps/` root, server-rendered
  templates, magic-link/session auth, and `Group`-based roles. **[verified — D-4]**
- **Submitter authorization:** only accounts holding the **developer** role may submit/own
  apps; **gate review requires the admin role**. **[verified — D-3]**
- **Tag contract:** app interest tags must be **valid taxonomy tags**, stored by `Tag.id`,
  validated with `is_valid_tag` at the write boundary and resolved with `resolve_tag` at
  read. **[verified — D-5]**
- **Review is manual at MVP volume** (50–150 founding apps); turnaround has **no hard SLA**
  but must be **observable**. **[verified — breakdown §4.3 / §5.4 + D-2]**
- **The gate is objective floors only, never taste** (§5.5), and **no paid path** to or
  fast-track through acceptance exists (§5.6). **[verified — vision §5.5 / §5.6]**
- **Decision notification** reuses the shared email capability (`apps/core/email.py`, D-4);
  this feature consumes it, it does not build email infrastructure. **[verified — D-4]**
- **Media at MVP = screenshots/images;** exact slots/limits/formats align with `app-pages`
  in Stage 2. **[unverified — proposal]**
- **The floors are objective *enough* to be checklist-driven** (determinism for review,
  CLAUDE.md §6.2) but **human-applied** at MVP; the precise checklist wording is finalized in
  Stage 2/3. **[unverified — checklist content TBD in design]**
- **No behavioral data** is collected here — only app metadata + ownership + lifecycle state;
  behavioral-signal capture and its privacy/retention posture are `signal-capture`'s.
  **[verified — boundary]**

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Gate creeps from objective floors into taste** — editors reject apps they dislike, turning the platform into the gatekeeper it exists to replace (violates §5.5 / the premise). | Med | High | AC6 makes taste-rejection a product-rule violation; rejections must cite a specific objective criterion (AC5); rejection-reason distribution + gate-pass-rate metrics surface drift. |
| R2 | **Manual review doesn't scale / becomes a bottleneck** — slow turnaround discourages developers. | Med (low at founding volume) | Med | Manual review is a **bounded** MVP choice for 50–150 apps (D-2 / §5.2); time-to-decision is tracked; automation is a named later step, not built now. |
| R3 | **Broken or dishonest apps slip the gate** — catalog/users lose trust, downstream signal is polluted. | Med | High | "Works" + "honest metadata" are explicit floors checked before acceptance (AC5); downstream consumes **only accepted** apps (AC9); edits to gated floors trigger re-validation (AC8). |
| R4 | **Off-vocabulary or mis-tagging** — apps mismatched to audiences, undermining H2's "reaches a *matched* audience". | Med | Med | Tags validated against the taxonomy and stored by `Tag.id` (AC4, D-5); tag-coverage metric feeds taxonomy's coverage work; editor can correct tags at review. |
| R5 | **Spam / duplicate flood** — open developer self-serve (like open signup in `identity-accounts`) invites junk submissions. | Med | Med | Spam + duplicate are explicit gate floors (AC5); manual review catches them at MVP volume; integrity automation deliberately deferred (breakdown §3). |
| R6 | **Founding-catalog entry-path ambiguity** — unclear whether founding apps are self-submitted or editor-entered → duplicate tooling or a stalled catalog. | Low–Med | Med | OQ-1 flagged for confirmation; proposed default = developers **self-submit**, editors recruit **offline** (breakdown §7 Q6 "likely offline"). |

## Vision alignment

Serves vision **§2.1** (submission & intake — step 1 of an app's lifecycle), **§5.5**
(the *objective* quality gate that filters floors, not merit — "curate the matching, not
the merit"), and **§6 Dev-facing** (the submission & intake pipeline). It upholds **§5.6 /
the one-line test (§8)**: intake is identical and free for every developer — no budget,
brand, or payment buys entry or a faster decision (AC3) — so *money buys tools, never
position* holds at the on-ramp, and "an unknown solo dev with $0 marketing" enters on
exactly the footing of a funded studio. This is the **entry half of H2**: an app can get
into the catalog and be correctly described so it *can* reach a matched audience; the
reception half is proven by the features that consume what this one produces.

---

## For confirmation at approval

The brief makes these calls from the source material; flag any you'd decide differently
(they are otherwise treated as confirmed on approval, mirroring `interest-taxonomy`'s A4):

1. **"An app" = a web app reachable at a URL**; "platform target" reduces to *web* at MVP.
   *(from [D-1](../../DECISIONS.md); Glossary, Constraints)*
2. **The gate is applied by a human editor (admin role) against a checklist** — manual
   review, no automated malware/uptime/duplicate detection at MVP. *(breakdown §4.3; AC5)*
3. **Rejection is non-terminal** — developers may correct and resubmit. *(§5.2; AC7)*
4. **Apps are owned by an individual developer account** — no team/org ownership at MVP.
   *(mirrors `identity-accounts`; Out of scope)*
5. **Founding-catalog recruitment is an offline editorial process**; the submission form
   serves the resulting self-submission, rather than a separate recruitment product surface.
   *(breakdown §7 Q6; OQ-1 — Out of scope, R6)*
6. **Owner metadata *correction* is in scope; formal versioned updates + re-boost are
   deferred.** *(§5.2 boundary; In/Out of scope, AC8)*
7. **Media at MVP = screenshots/images**, with exact slots/limits aligned to `app-pages` in
   Stage 2. *(Constraints — [unverified])*
