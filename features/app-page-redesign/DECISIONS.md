# DECISIONS.md — app-page-redesign

Feature-local decisions. Repo-wide choices go in the global
[../../DECISIONS.md](../../DECISIONS.md). Each entry: the choice, why, and what was rejected.

---

## APR-D-1 — Phased scope: redesign v1 now, heavy bets queued (Coordinator, 2026-06-29)

**Decision.** Scope this feature as a **focused v1 redesign**: restructure the app page and
add the cheapest high-impact slots. The heavier, higher-cost bets are **deferred to separate
future features**, not bundled here.

- **In v1 (this feature):** a restructured page with — a short pitch line / tagline, a
  media carousel (screenshots + an inline looping product-demo clip as a peer to images),
  typed/faceted tags (genre · modality · platform/access · pricing · maturity), a richer
  structured "deep dive" description ("show more"), a developer-identity block ("an app by
  ___" + other apps by the same developer), and surfacing the existing
  [`developer-updates`](../developer-updates/) feed as an on-page devlog.
- **Deferred to future features (see [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) §Deferred bets):**
  full hosted **trailer/video** (storage/transcoding/bandwidth — real infra), **follow the
  developer** (vs. the existing app-follow), and **community Q&A / comments**.

**Why.** The full reimagined page is plausibly 4–6 features' worth of work; landing it as one
mega-feature fights the staged pipeline (CLAUDE.md §2) and §5.5 simplicity discipline. A
focused v1 ships value before the live deploy (APR-D-2) and lets the heavy infra bets be
scoped on their own merits when activated.

**Rejected.** (a) One ambitious v1 covering everything incl. trailer hosting + dev-follow —
too large for one clean Feature-Track pass. (b) Keep brainstorming without scoping — the user
chose to commit.

**User decision:** AskUserQuestion 2026-06-29 → *"Phased: redesign now, heavy bets later."*

---

## APR-D-2 — Sequence this **before** the live staging deploy (Coordinator, 2026-06-29)

**Decision.** Land the app-page redesign **before** the live staging deploy
([DN-PS-DEPLOY](../../CONTROL.md)) and the founding-developer recruitment that follows it.

**Why.** The app page **is** the developer's marketing landing page and the
bring-your-own-audience face of the wedge ([global D-10](../../DECISIONS.md), vision §5.4).
Recruiting founding developers onto a stale listing-style page undersells the wedge; the
deploy should debut the compelling page. This mirrors the precedent set when
[premium-frontend](../premium-frontend/) was sequenced before the deploy for the same reason.

**Implication.** DN-PS-DEPLOY stays parked (reopenable, artifacts ready) until this feature
closes out — exactly as it stayed parked behind `premium-frontend`.

**Rejected.** Deploy first then redesign with real feedback — the user chose to strengthen the
face first; real-feedback iteration remains available post-deploy regardless.

**User decision:** AskUserQuestion 2026-06-29 → *"Redesign first, then deploy."*

---

## APR-DESIGN-1 — Typed facets are code-fixed structured fields, firewalled from ranking (Architect, 2026-06-29)

**Decision.** The new typed facets (**pricing · maturity · modality · platform/access**) are modeled
as **code-fixed structured fields**: a pure declaration in a new `apps/catalog/facets.py` (the
`gate.py` precedent — vocabulary + cardinality in code, no DB, no editorial mutation path) plus a new
`AppFacet` table storing per-app `(facet, value)` rows as **soft, write-validated, read-resolved**
references (the D-5 pattern). Facets are kept **entirely separate from the D-5 taxonomy tag pool** and
never enter `search_catalogue`, the interest matcher, or any score — they are **informational only**
(AC-3). The existing **category/"genre" tags stay as the D-5 taxonomy** already shown in the header
(resolves [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) Q1).

**Why.** A flat tag pool can't enforce typed cardinality ("one pricing value per app") → illegal
states become representable; and reusing `AppTag` would pull facets into the discovery/ranking/match
paths that the tag pool already feeds — breaking AC-3's firewall. Code-fixed structured fields make
illegal states unrepresentable and keep facets ranking-neutral by construction. **Global-relevant** →
promoted to **D-14a** on DESIGN approval (a later feature would be wrong to rank by a facet).

**Rejected.** (a) Extend the D-5 taxonomy (facets as clusters/tags) — couples facets to
ranking/discovery, no cardinality guarantee. (b) A JSON blob column on `App` — not integrity-checkable,
illegal states representable.

**User decision:** AskUserQuestion 2026-06-29 → *"Code-fixed structured fields."*

---

## APR-DESIGN-2 — Re-review policy for public-claim fields is config-togglable (Architect, 2026-06-29)

**Decision.** The new developer-authored public-claim fields (**tagline · deep_dive · facets ·
demo_clip**) **are gate-relevant** — editing them on an *accepted* app returns it to `pending`
re-review, upholding the honest-metadata floor consistently with `description` today. **But** which of
them force re-review is **config-togglable** (default: all on): `gate.GATE_RELEVANT_FIELDS` (the
constant) becomes `gate.gate_relevant_fields()` = an always-gated core (name/description/url/tags/media)
**∪** a config-driven set `config.app_page_gated_fields()` (defaults to all four new fields). Policy is
tunable from observed deployment behaviour **without a code change or migration**.

**Why.** Honesty-first is the right default (vision §4), but re-review churn on marketing iteration may
prove to fight the "make it their hub" goal — and the policy is unvalidated until real usage. A config
toggle is the §5.2 "design for change" answer: keep the integrity guarantee, make the knob cheap to
turn. The user explicitly asked for this togglability. **Global-relevant** → **D-14b** on approval.

**Rejected.** A hardcoded gated set — too rigid for an unvalidated policy. "No re-review" — leaves
post-acceptance public claims unchecked for honesty.

**User decision:** AskUserQuestion 2026-06-29 → *"Yes, but design it to be togglable per-field."*

**Status:** **RATIFIED → global [D-14b](../../DECISIONS.md)** on DESIGN approval (DN-APR-DESIGN, 2026-06-29). APR-DESIGN-1 likewise → **[D-14a](../../DECISIONS.md)**.

---

## APR-BUILD-1 — Stage-4 build deviations from DESIGN (Senior Engineer, 2026-06-30)

Four small, design-aligned implementation calls made during the build (T-01…T-09). None change
scope, schema beyond the one approved additive migration, or any AC; recorded for the reader.

1. **The toggleable-gate-field candidate list lives in `config`, not `gate`.** DESIGN §8.1
   sketched `_TOGGLEABLE_GATE_FIELDS` in `gate.py`. Because `gate` imports `config` (for the
   toggle), keeping the candidate list in `gate` too would invite a `config`↔`gate` cycle. The
   single source is `config.APP_PAGE_TOGGLEABLE_GATE_FIELDS`; `gate.gate_relevant_fields()` =
   `_CORE_GATE_FIELDS | config.app_page_gated_fields()`. The override is one setting/env
   `APP_PAGE_GATED_FIELDS` (a subset, **intersected** with the candidates so config can only
   relax, never widen) — which satisfies DESIGN's "overridable per field" without per-field env
   vars.
2. **Added `config.app_page_other_apps_limit()` (default 6).** DESIGN §8 named "other-apps
   count" as a config limit but T-03 listed only three knobs; added it so the identity-block
   query is principled-bounded (no magic number), consistent with §5.2.
3. **The deep-dive `<details>` lives inside the always-present "About" slot landmark.** To
   reconcile DESIGN §7's "deep-dive slot omitted when empty" with AC-7's "identical slot
   set/order regardless of content", the 9 slot **landmarks** (`data-slot`) are always present
   and the deep-dive `<details>` is content-conditional *within* About. The 10 logical slots of
   §7 are all delivered; the uniformity invariant fingerprints the 9 always-present landmarks.
4. **Clip-edit semantics on `edit_app`.** `demo_clip=_UNSET` leaves the clip unchanged;
   `demo_clip=None` removes it; a file replaces it (alt required). A metadata-only edit via the
   server page never wipes a clip (the view passes `demo_clip` only when a file is uploaded).