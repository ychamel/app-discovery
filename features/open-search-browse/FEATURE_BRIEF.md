# FEATURE_BRIEF — open-search-browse

*Stage 1 artifact (Product Analyst). Status: **APPROVED** (DN-17, 2026-06-23). The two
bundled scoping calls are resolved: **OQ-OSB-1** — tag/cluster filtering **is in the MVP
slice** (S3/AC3); **OQ-OSB-2** — default neutral order is **browse = newest-accepted-first,
search = keyword relevance** (both non-purchasable, AC5). Advanced to Stage 2 (Design).*

## Coordinator scope seed (source: breakdown §4.2)

> Facts carried over from the component breakdown for traceability. The Product Analyst
> owns the brief below; this block is context, not the brief.

- **Layer / build phase:** User-facing · Phase 2
- **Purpose:** Full catalog findable by anyone (the "open access" half of the integrity
  premise).
- **MVP slice:** Minimal search/listing so direct links and discovery work outside the
  digest.
- **Proves (hypothesis):** enabler / H3
- **Depends on:** app-pages
- **Vision design ref:** §4.1, §6 User-facing
- **Source:** [docs/mvp-component-breakdown.md](../../docs/mvp-component-breakdown.md) §4.2

---

## Domain terms (defined or linked — no undefined terms downstream)

- **Accepted-app catalogue (D-6)** — the set of apps whose `submission-intake` gate
  passed (`status = accepted`). Only these are ever presented. Read through the existing
  D-6 surface (`catalog.list_catalogued_apps` / `get_catalogued_apps`); pending, rejected
  and withdrawn apps are never shown. See [DECISIONS.md](../../DECISIONS.md) D-6.
- **App-page** — the uniform per-app destination built by `app-pages`, addressed by a
  stable `App.id` URL. This feature does not render app detail; it links to the app-page.
- **Interest tag / cluster (D-5)** — the shared vocabulary from `interest-taxonomy`; tags
  carry labels and belong to clusters, with soft-retire resolved at read time
  (`resolve_tag`). The candidate browse/filter axis. See D-5.
- **Open access** — reachable by **anyone, including signed-out visitors**; no login wall
  on browse, search, or following a result link (vision §4.1, §6).
- **Position-neutral ordering** — result order determined only by published, non-purchasable
  signals (e.g. recency, keyword relevance, alphabetical). Never by payment, developer
  subscription tier, or any purchasable placement. The platform's founding premise:
  *money buys tools, never position* (vision §1, §5.6).
- **Curated-rating gate (D-8)** — only a `DIGEST` (organic-curation) impression makes a
  user "curated to" an app and able to affect its Quality Score. A self-driven view —
  including a search or browse result exposure — must **never** confer that eligibility.
  See D-8.

---

## Problem statement

The platform's integrity premise has two halves. The closed half — *who can affect an
app's score* — is already enforced by the curated-rating gate (D-8). The **open half** is
not yet built: today an accepted app is reachable only if it lands in someone's digest or
someone already holds its direct `App.id` link. There is no way for a person — especially
a **signed-out visitor** who is not yet a member — to find an app by name, by keyword, or
by interest, or to browse what the catalogue contains at all.

Without this, the platform cannot honestly claim "anyone can find and access any app"
(vision §4.1), direct links work only if you already have them, and developers have no
non-digest path to being discovered. **Why now:** `app-pages` is released (every accepted
app now has a public destination to link to), so the missing piece is purely the *finding*
surface that points at those pages.

## Goal

*Anyone, signed in or not, can find any accepted app in the catalogue — by browsing it,
searching it by keyword, or filtering it by interest — and reach that app's page, with
result order that is neutral and impossible to buy.*

---

## User stories (6)

- **S1 — Open browse.** As **anyone (including a signed-out visitor)**, I want to browse a
  listing of every accepted app, so that the full catalogue is openly discoverable outside
  the digest.
- **S2 — Keyword search.** As **anyone**, I want to search the catalogue by keyword, so
  that I can find a specific app or apps matching a term without waiting for a digest.
- **S3 — Browse by interest.** As **anyone**, I want to filter/browse the catalogue by an
  interest tag (or cluster), so that I can explore apps in a category I care about.
  *(In MVP scope — resolved DN-17 / OQ-OSB-1.)*
- **S4 — Reach the app-page.** As **anyone**, I want each result to link to that app's
  app-page at its stable URL, so that I can see full details and try the app.
- **S5 — Earned, not bought, visibility.** As a **developer**, I want my accepted app to
  appear in open search/browse on equal footing — ordered only by neutral signals — so
  that visibility here is earned, never purchasable.
- **S6 — Honest empty states.** As **anyone**, when nothing matches my query (or the
  catalogue is empty), I want a clear "no results" state, so that I know there is nothing
  to show rather than facing a broken page.

---

## Acceptance criteria (Given / When / Then — every story ≥1)

- **AC1 (S1).** *Given* accepted apps exist in the catalogue, *when* a signed-out visitor
  opens the browse listing, *then* every accepted app appears (paginated), and no
  pending / rejected / withdrawn app is ever shown.
- **AC2 (S2).** *Given* a keyword query, *when* any visitor searches, *then* the results
  contain the accepted apps whose name or description matches the term and exclude
  non-matching and non-accepted apps.
- **AC3 (S3).** *Given* a selected interest tag, *when* a visitor filters by it, *then*
  only accepted apps carrying that tag (resolved per D-5 soft-retire) are shown; a
  retired tag with no active successor offers no stale filter.
- **AC4 (S4).** *Given* a result row for app *X*, *when* the visitor selects it, *then*
  they land on *X*'s app-page at its stable `App.id` URL (the `app-pages` destination).
- **AC5 (S5 — vision invariant).** *Given* two accepted apps in a result set, *when* the
  results are ordered, *then* the order is determined **only** by published neutral
  signals (relevance / recency / alphabetical) and is **not** influenced by any payment,
  developer-subscription tier, or purchasable placement.
- **AC6 (S5 — integrity invariant).** *Given* a visitor views or clicks a search/browse
  result, *when* any signal is recorded for that exposure, *then* it is **not** recorded
  as an organic-curation (`DIGEST`) impression and **never** confers curated-rating
  eligibility or Quality-Score weight (D-8 surface segregation).
- **AC7 (S6).** *Given* a query that matches nothing, or an empty catalogue, *when* the
  page renders, *then* a clear empty-state message is shown with a normal `200` response
  (not a 404 / 500 / blank page).
- **AC8 (S1 — open access).** *Given* a visitor who is **not** signed in, *when* they
  access browse, search, or a result link, *then* access succeeds with no login
  redirect; signing in is never required to discover or reach an app.
- **AC9 (scale).** *Given* the catalogue grows large, *when* a listing or search page
  renders, *then* results are paginated and the database work per page is bounded
  (no per-result N+1) — the assume-growth standard (CLAUDE.md §5.2).

---

## Success metrics

| ID | Metric | Why it matters | MVP expectation |
|----|--------|----------------|-----------------|
| **M1** | **Open-access coverage** — share of accepted apps reachable via browse/search (target **100%**). | The open-access guarantee (§4.1); a gap means an app is unfindable. | 100% by construction. |
| **M2** | **Discovery click-through** — share of search/browse sessions that open ≥1 app-page. | Proves the surface actually drives discovery outside the digest (H3). | Measurable only once exposure logging exists (see OQ-OSB-3); thin until traffic. |
| **M3** | **Zero-result query rate** — share of searches returning nothing. | Search-quality signal; high = vocabulary/coverage mismatch. | Analyst-derived from query logs. |
| **M4** | **Listing/search latency** — p95 render time within budget. | Open surface must stay responsive as the catalogue grows. | Within budget (AC9). |
| **M5** | **Position-neutrality audit = 0** — count of results whose order is influenced by any paid/tier input (**must be 0**). | The money-can't-buy-position invariant (AC5); the one number that, if non-zero, means the premise leaked. | 0 by construction. |
| **M6** | **Catalogue freshness lag** — delay between an app being accepted and appearing in browse. | Consistency with D-6; a long lag undercuts the open guarantee. | ~immediate (reads live D-6). |

---

## In scope

- A **public browse listing** of all accepted apps (D-6), paginated, accessible signed-out.
- **Keyword search** over accepted apps' name and description.
- **Filter/browse by interest tag (or cluster)** via D-5 *(in scope — DN-17 / OQ-OSB-1)*.
- Each result **links to the app-page** at its stable `App.id` URL.
- **Neutral, published, non-purchasable result ordering** (AC5).
- **Empty / zero-result states** (AC7).
- **Surface segregation**: any exposure signal recorded here is non-curated (AC6).

## Out of scope

- The **curated feed / weekly digest** and any *personalized* ranking — this is the
  *open, un-personalized* surface; personalization is `weekly-digest`'s job.
- **Quality-Score / reception-weighted ordering** — no ranking-by-popularity here; that
  would couple the open surface to the impression economy and risk a buy-able proxy.
- **Personalization by `interest-profile`** — the open surface is identical for everyone.
- **Collections, saved apps, saved searches, follows** — separate component
  (Collections & follows).
- **Advanced/faceted search** — multi-tag boolean, platform/price facets, sort controls,
  autocomplete/typeahead, fuzzy or semantic search, relevance-tuning ML — beyond the
  minimal slice.
- **Emitting `DIGEST` (curated) impressions** — forbidden here by AC6.
- **Indexing non-accepted apps** (pending/rejected/withdrawn).

---

## Constraints & assumptions

| # | Constraint / assumption | Status |
|---|--------------------------|--------|
| C1 | **Dependency `app-pages`** provides the result destination (stable `App.id` page). | **Verified** — released local/dev. |
| C2 | **D-6 catalog read** (`list_catalogued_apps` / `get_catalogued_apps`, accepted-only, no N+1) is the only catalogue source. | **Verified** — present in `apps/catalog/selectors.py`. |
| C3 | **D-5 taxonomy** (`list_active_tags`, `list_clusters`, `resolve_tag`) supplies filter facets. | **Verified** — present in `apps/taxonomy/selectors.py`. |
| C4 | **Open access** — browse/search/result links must work for anonymous, signed-out visitors (no auth wall). | **Verified** requirement (vision §4.1, §6). |
| C5 | **Surface segregation (D-7/D-8)** — the impression `Surface` enum is `{DIGEST, APP_PAGE}` today; a search/listing exposure is neither, so any signal here needs a **non-curated** surface. *Whether/how to emit is a Stage-2 design call (OQ-OSB-3); the binding rule is AC6.* | **Unverified** (design). |
| C6 | **Stack** — Python / Django + PostgreSQL (D-4). | **Verified.** |
| C7 | **Accessibility** — keyboard-navigable, semantic listing, image alt text carried from D-6 media. | Unverified assumption. |
| C8 | **Privacy** — if any exposure signal is recorded for anonymous visitors, it must carry no PII (signal-capture no-PII rule). | Unverified (tied to C5/OQ-OSB-3). |
| C9 | **Performance / scale** — paginated, bounded queries, works at 100× catalogue (§5.2). | Requirement (AC9). |

---

## Risks (top 5)

| # | Risk | Likelihood / Impact | Mitigation |
|---|------|---------------------|------------|
| **R1** | A search/browse exposure leaks into the **curated-rating gate** (a self-driven view confers eligibility) → breaks §4.1 integrity. | Low / **High** | AC6 — never record search/browse exposure as `DIGEST`; segregate the surface; design reviewed against D-8. |
| **R2** | Result order becomes — or is perceived as — **purchasable / tier-influenced** → violates the founding premise. | Low / **High** | AC5 + M5 audit = 0; neutral published order only; ranking inputs publishable (§5.6). |
| **R3** | Naive search/listing **doesn't scale** (full-table scan, N+1) at 100× catalogue. | Med / Med | AC9 — pagination + bounded queries; Stage 2 picks the index/search approach. |
| **R4** | **Scope creep** into personalized / reception-ranked discovery → a second, accidental digest. | Med / Med | Explicit out-of-scope; neutral ordering only; no Quality-Score read. |
| **R5** | **Soft-retired tags** (D-5) produce stale or empty filters. | Low / Low | Resolve via `resolve_tag`; offer only active tags as facets (AC3). |

---

## Vision alignment

Serves **vision §4.1** ("Anyone can find and access any app" — the open-access half of
the integrity premise) and the founding rule that **money buys tools, never position**
(§1, §5.6), realised through §6 *Open search & browse*. Proves **enabler / H3**.

**Money-buys-position test → PASS.** Ordering is explicitly neutral and non-purchasable
(AC5 / M5), and the integrity segregation (AC6) prevents a visitor from conferring
score-eligibility on an app by viewing it.
