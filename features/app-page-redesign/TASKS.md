# TASKS.md — app-page-redesign

*Stage 3 (Planner / Tech Lead). Inputs read: the approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md)
and [DESIGN.md](DESIGN.md) (global [D-14](../../DECISIONS.md); APR-DESIGN-1/2). No re-design — every
task traces to a DESIGN section.*

> **Ordering** follows DESIGN §10 (schema/data → core logic → interfaces/API → UI → telemetry →
> docs) with risk front-loaded: the facet registry + additive migration + the write path (clip
> validation, atomic facet writes, the re-review toggle seam) come before any UI. Each task leaves
> the system **working and releasable** — the new fields are additive and degrade to graceful-empty
> (M2), so no intermediate task breaks an existing page.
>
> **Standing guardrails (every task).**
> - **G1 — suite + drift.** Full suite green; `ruff`/`manage.py check` clean; `makemigrations --check`
>   reports **no drift except the one deliberate additive migration in T-02** (AC-9).
> - **G2 — `CatalogApp` byte-stable.** No task changes the shared D-6 `CatalogApp`/`CatalogTag`/
>   `CatalogMedia` shape; discovery/dashboard/widget/subscriptions reads stay untouched (DESIGN §6, AC-9).
> - **G3 — firewall M5=0.** No task adds a `signals` import or emission to satisfy a slot; `apps/updates`
>   imports nothing from `signals` stays AST-true (DESIGN §9.3, AC-6).
> - **G4 — no-JS is the source of truth.** Deep-dive, facet strip, identity grid render and are
>   reachable with JS disabled; HTMX stays optional `hx-boost` (DESIGN §7, AC-4).
> - **G5 — uniformity / no richness-by-identity.** No task adds a tier/payment/identity field to any
>   read-model or template branch; every accepted app gets the same slot set/order (DESIGN §7, AC-7/R2).
> - **G6 — one source of truth.** Facet vocabulary lives only in `facets.py`; the gated-field policy
>   only in `gate.gate_relevant_fields()`/`config`; all writes only through `catalog.services`.
> - **Red-first:** every implementing task starts with a failing test that asserts its DoD, per the
>   Senior Engineer protocol.

---

## T-01 — Facet registry (`catalog/facets.py`, pure declaration)

- **Description.** Create the code-fixed facet vocabulary per DESIGN §4/§5.3/§11a (the `gate.py`
  precedent — declaration only, no DB, no editorial mutation path). Define `FacetCardinality`
  (`SINGLE`/`MULTI`), `FacetValue`, `FacetDef`, and the `FACETS` registry for the four facets
  (`pricing` SINGLE; `maturity` SINGLE; `modality` MULTI; `platform` MULTI) with the exact value keys
  in DESIGN §5.3. Expose the read/validate helpers: `facet_keys()`, `is_valid_facet_value(facet, value)`,
  `cardinality_of(facet)`, and `resolve_facets(rows)` (registry-ordered, drops values not in the current
  registry — the D-5 graceful pattern, DESIGN §5.2/§9.2).
- **Dependencies.** none.
- **Definition of done.** Unit tests: valid `(facet, value)` accepted; off-vocabulary facet **and**
  off-vocabulary value rejected; `cardinality_of` correct per facet; `resolve_facets` returns
  registry order and **silently drops** a value absent from the registry (no error); the module imports
  **no Django model and no DB** (pure declaration — import test). Adding/removing a facet or value is a
  one-file change (DESIGN §4 "one edit site"). G1.
- **Estimated size.** S.
- **Files/areas.** `apps/catalog/facets.py` (new) + its test module.

## T-02 — Additive migration: `App` marketing columns + `AppFacet` table

- **Description.** Per DESIGN §5.1/§5.2/§5.4. Add to `App` the four **optional** columns
  `tagline` (`CharField(max_length=300, blank=True, default="")`), `deep_dive`
  (`TextField(blank=True, default="")`), `demo_clip`
  (`FileField(upload_to="app_clips/%Y/%m/", blank=True, null=True)`), `demo_clip_alt`
  (`CharField(max_length=200, blank=True, default="")`). Add the new `AppFacet` model exactly per
  DESIGN §5.2 (`app` FK CASCADE `related_name="app_facets"`, soft `facet`/`value` char fields,
  `UniqueConstraint(app, facet, value)`, an `app` index, `db_table="catalog_app_facet"`). Generate the
  **one** additive migration (4 columns + 1 table + indexes), **no backfill**.
- **Dependencies.** none (model definition is independent; T-01 governs the *values* written, not the
  schema).
- **Definition of done.** Migration applies and **reverses** cleanly (up→down→up); reverse drops the
  columns + table (the documented partial-irreversibility, DESIGN §10). `makemigrations --check`
  reports **only** this migration as drift; existing apps load with empty defaults (no NULL on text
  columns — one empty representation, DESIGN §5.1). **No tier/payment/identity column added** (G5,
  asserted). `AppFacet` CASCADE-deletes with its `App` (test). G1/G2/G5.
- **Estimated size.** S/M.
- **Files/areas.** `apps/catalog/models.py`, `apps/catalog/migrations/` (new), model tests.

## T-03 — Re-review seam (`gate.gate_relevant_fields()`) + config tunables

- **Description.** Per DESIGN §8.1 (APR-DESIGN-2 / D-14b). Replace the `gate.GATE_RELEVANT_FIELDS`
  constant with `gate.gate_relevant_fields() -> frozenset[str]` = `_CORE_GATE_FIELDS`
  (name/description/url/tags/media, always gated) **∪** `config.app_page_gated_fields()`. Add
  `config.app_page_gated_fields()` defaulting to **all four** new field keys
  (`tagline`/`deep_dive`/`facets`/`demo_clip`), env/config-overridable per field. Add the other
  DESIGN §8 config knobs: `config.app_page_deep_dive_max_length()` (default 8000),
  `config.catalog_clip_max_bytes()` (default 10 MB), `config.app_page_devlog_limit()` (default 5).
- **Dependencies.** none.
- **Definition of done.** `gate_relevant_fields()` returns the core ∪ the configured set; overriding
  the config to drop a field removes it from the returned set **without a code change** (test toggles
  config both ways). Default is all-four-on (honesty-first, test). Every existing caller reads the
  function, not the removed constant (grep: no remaining `GATE_RELEVANT_FIELDS` reference). One source
  of truth for the policy (G6). G1.
- **Estimated size.** S.
- **Files/areas.** `apps/catalog/gate.py`, `apps/catalog/config.py` (or the existing config module),
  gate/config tests.

## T-04 — Write path: extend `submit_app`/`edit_app` (facets, marketing copy, clip) + wire the gate

- **Description.** Per DESIGN §8/§8.1. Add **optional** params to `catalog.services`:
  `submit_app(..., tagline="", deep_dive="", facet_values=None, demo_clip=None, demo_clip_alt="")` and
  `edit_app(..., tagline=_UNSET, deep_dive=_UNSET, facet_values=_UNSET, demo_clip=_UNSET,
  demo_clip_alt=_UNSET)` (absent ⇒ unchanged; the existing `_UNSET` sentinel). `facet_values` = an
  iterable of `(facet, value)` pairs, each validated by `facets.is_valid_facet_value` (off-vocabulary
  refused, nothing written — mirrors `_require_valid_tags`), **cardinality enforced** per `FacetDef`
  (refuse a 2nd value for a `SINGLE` facet), **replace-set** semantics (mirror `_set_tags`). Add
  `_validate_clip` (container sniff MP4/WebM + size cap `config.catalog_clip_max_bytes()`) and
  `_store_clip` (generated filename, mirrors `_store_media`); setting a clip **requires**
  `demo_clip_alt` (C5/A4). `deep_dive` stripped + bounded by `config.app_page_deep_dive_max_length()`;
  `tagline` stripped + ≤300. Wire `edit_app` to call `gate.gate_relevant_fields()` (T-03) and record the
  changed field key per new field so the existing `_return_to_review_if_accepted` toggles correctly.
  The required submission floor is **unchanged** (new fields optional).
- **Dependencies.** T-01, T-02, T-03.
- **Definition of done.** Red-first tests: valid facets/marketing/clip persist atomically; off-vocab
  facet, `SINGLE`-facet 2nd value, oversized clip, non-AV clip, and clip-without-alt each raise the
  documented loud error (`InvalidFacetError`/`MediaLimitError`) with **nothing written** (DESIGN §9.2);
  replace-set semantics on `edit_app` (test). Re-review: editing each new field on an ACCEPTED app
  returns it to `pending` **when its toggle is on**, and **does not** when toggled off (config-driven
  test, both directions). Submission floor unchanged (existing submit tests green). All writes on the
  one audited services path (G6). G1.
- **Estimated size.** M.
- **Files/areas.** `apps/catalog/services.py`, `apps/catalog/errors.py` (if a new error type is needed),
  services tests.

## T-05 — Authoring surfaces: server-rendered form + DRF round-trip

- **Description.** Per DESIGN §8 ("both authoring surfaces, no second source of truth"). Extend the
  server-rendered `SubmissionForm` + `submit.html`/`app_detail.html` with the new fields, **facet
  choices fed from `facets.FACETS`** (not hardcoded). Extend the DRF `AppCreateView` /
  `AppDetailView.patch` (`_supplied_edits` learns `tagline`/`deep_dive`/`facet_values`/`demo_clip`/
  `demo_clip_alt`) and the `AppSerializer` + `_form_initial` so the new fields round-trip back for
  editing. Both surfaces call the **same** `catalog.services` functions from T-04.
- **Dependencies.** T-04.
- **Definition of done.** Red-first tests: a server-rendered submit/edit sets and re-displays each new
  field; facet choices in the form match `facets.FACETS` (changing the registry changes the choices —
  no duplicate vocabulary, G6); the DRF create/patch sets each new field and the serializer returns it;
  invalid input surfaces the form/serializer error (loud boundary, DESIGN §9.4). Neither surface
  bypasses owner-scoping. G1.
- **Estimated size.** M.
- **Files/areas.** `apps/catalog/forms.py`, `apps/catalog/views.py`, `apps/catalog/serializers.py`
  (or wherever `AppSerializer` lives), `apps/catalog/templates/catalog/submit.html` +
  `app_detail.html`, form/view tests.

## T-06 — Page-scoped read: `AppPageContent` + `get_app_page_content` + `accepted_apps_by_owner`

- **Description.** Per DESIGN §3/§6. Add to `catalog.selectors` the frozen DTOs `CatalogDeveloper`
  (id + `display_name` only — no new PII), `CatalogFacet` (facet/label/values, registry-ordered via
  `facets.resolve_facets`), and `AppPageContent` (the flat `CatalogApp` base fields **plus** tagline /
  deep_dive / demo_clip_url / demo_clip_alt / facets / developer / other_apps), each degrading to
  empty/None (M2). Implement `get_app_page_content(app_id) -> AppPageContent | None` (accepted-only per
  D-6; builds base fields via the existing private `_to_catalog_app` so `CatalogApp` stays byte-stable;
  bounded queries — `select_related("owner")` + `prefetch_related("media","app_tags","app_facets")` +
  one bounded `accepted_apps_by_owner`; raises only on a genuine DB failure, never a fake-empty page).
  Implement `accepted_apps_by_owner(owner_id, *, exclude, limit) -> list[CatalogApp]` (ACCEPTED-only,
  newest-accepted-first, excludes this app, reuses `_to_catalog_app`).
- **Dependencies.** T-01 (facet resolve), T-02 (columns/table).
- **Definition of done.** Selector tests against seeded rows: full content returned for an accepted app;
  `None` for non-accepted/unknown (D-6); empty/legacy app yields empty strings / `None` clip / `[]`
  facets / `[]` other_apps (graceful, M2); facets in registry order with a registry-absent value dropped
  (T-01 behaviour); `other_apps` excludes pending/rejected/withdrawn and the app itself (AC-5; no leak,
  DESIGN §9.4); **bounded query count, no N+1** (`assertNumQueries`-style, DESIGN §9.1). `CatalogApp`
  byte-stable — discovery/dashboard/widget tests still green (G2). G1.
- **Estimated size.** M.
- **Files/areas.** `apps/catalog/selectors.py`, selector tests.

## T-07 — Devlog inclusion tag `{% app_devlog app %}` (fail-soft) + degrade metric

- **Description.** Per DESIGN §4/§6/§9.3/§9.5. Add `apps/updates/templatetags/updates_tags.py` with an
  `{% app_devlog app %}` inclusion tag (mirrors `ratings_tags`/`subscriptions_tags`) that reads
  `updates.published_notices_for_apps([app.id], limit=config.app_page_devlog_limit())` (newest-first)
  and renders a small devlog slot template with its own empty/degraded state. **Fail-soft:** on any
  error it renders nothing and increments a new `APP_PAGE_DEVLOG_DEGRADED` metric constant — never 500s.
  Adds **no** `signals` import/emission (M5=0 structural, AC-6/G3).
- **Dependencies.** T-03 (the devlog-limit config knob).
- **Definition of done.** Red-first tests: published notices render as a devlog; no notices → graceful
  empty state; the underlying read raising → tag renders nothing + the page stays 200 + the degrade
  metric fires (fail-soft); **AST/import assertion** that the new tag module adds no `signals` import
  and the `apps/updates` no-`signals` invariant still holds (G3/M3). G1.
- **Estimated size.** S.
- **Files/areas.** `apps/updates/templatetags/updates_tags.py` (new) + a small slot template,
  `apps/updates` metric constants, templatetag tests.

## T-08 — Template rewrite to the uniform 10-slot contract + design-system CSS + view wiring

- **Description.** Per DESIGN §3/§7 + the [D-13](../../DECISIONS.md) build-free design system. Point
  `pages/views.app_page` at `get_app_page_content` (T-06). Rewrite
  `apps/pages/templates/pages/app_page.html` to the **fixed ordered 10 slots** in DESIGN §7 — Hero
  (name + tagline + fact strip of tags + facets) · Media gallery (demo clip first as
  `<video autoplay muted loop playsinline>` + `aria-label`/alt, then screenshots) · Try-it · About ·
  **Deep dive via native `<details><summary>`** (no-JS, G4/AC-4) · Developer hub (display_name + other
  apps grid) · `{% app_devlog %}` · Follow · Share · Reviews — each with its DESIGN §7 empty-state
  behaviour (M2). Add the new component classes (`fact-strip`, `facet`, `media--clip`, `devlog`,
  `dev-hub`, `other-apps-grid`) to the **one** `core/app.css` (no new build step, no per-type
  templates — DESIGN §7). Honor `prefers-reduced-motion` via the existing design-system motion guard.
  Emit `tagline` as `<meta name="description">` (AC-1). Existing slots (try-it `app_page` impression,
  share, follow, reviews) and the canonical edit-stable URL **unchanged** (AC-9).
- **Dependencies.** T-06, T-07.
- **Definition of done.** Render tests: tagline renders above the deep-dive **and** as the
  meta-description; empty tagline → no broken slot (AC-1). Demo clip renders as first media peer with
  `muted` + `aria-label`/alt; screenshots still render; no hosted-video dependency (AC-2). Facets render
  as a fact strip (AC-3). Deep dive present and reachable **with JS disabled** (`<details>` markup
  assertion, no `hx`/JS dependency — AC-4/G4). Identity block shows `display_name` + links to other
  **ACCEPTED** apps only, no email/PII (AC-5). Devlog slot renders via the T-07 tag (AC-6). Try-it
  `app_page` D-7 impression, share, follow, reviews still pass; canonical URL stable (AC-9). No
  tier/payment/identity branch in the template (G5). G1.
- **Estimated size.** M.
- **Files/areas.** `apps/pages/views.py`, `apps/pages/templates/pages/app_page.html`,
  `apps/core/static/core/app.css`, page render tests.

## T-09 — TEST_PLAN.md (AC map + hard invariants) + CODEMAP + final verification

- **Description.** Per DESIGN §12/§14/§15. Write `TEST_PLAN.md` mapping **AC-1…AC-9 + the re-review
  toggle** to named tests (DESIGN §12 table), plus the edge cases (empty/legacy app, oversized/non-AV
  clip rejected, off-vocab facet rejected, `SINGLE` 2nd value rejected, registry-removed facet value
  dropped at read, solo developer no "other apps", devlog read raising fail-soft). Add the **two hard
  structural invariants** as standalone tests: **(i) uniformity** — two apps with wildly different
  content render the **identical slot set/order**; the read-model carries no tier/payment/identity field
  (AC-7/G5); **(ii) firewall** — `AppFacet` is read by **no** ranking/discovery path (import/usage
  assertion) and the devlog slot adds **no** `signals` emission (AC-3/AC-6/M5=0/G3). Record the CODEMAP
  additions named in DESIGN §14 (`catalog/facets.py`, `AppFacet`, `get_app_page_content`/
  `AppPageContent`/`CatalogFacet`/`CatalogDeveloper`/`accepted_apps_by_owner`, `gate.gate_relevant_fields()`,
  `{% app_devlog %}`, the new config/metric constants).
- **Dependencies.** T-01…T-08.
- **Definition of done.** Every AC-1…AC-9 + the toggle maps to ≥1 passing named test in `TEST_PLAN.md`;
  the two hard-invariant tests pass; full suite green; `ruff`/`check` clean; `makemigrations --check`
  shows **only** the T-02 migration; CODEMAP updated for every new shared symbol (G6). AC-8 (compelling
  feel) is **explicitly out of automated scope** — flagged in the plan as the human-judgment sign-off
  the Release Engineer surfaces (the premium-frontend PS-3 precedent). G1–G6 all asserted.
- **Estimated size.** M.
- **Files/areas.** `features/app-page-redesign/TEST_PLAN.md`, `CODEMAP.md`, plus any cross-cutting
  invariant test module.

---

## Coverage map (every DESIGN element → ≥1 task)

| DESIGN element | Task(s) |
|---|---|
| Facet registry `catalog/facets.py` (§4/§5.3) | T-01 |
| `App` columns + `AppFacet` table + migration (§5.1/§5.2/§5.4) | T-02 |
| Re-review seam `gate_relevant_fields()` + config knobs (§8.1) | T-03 |
| Write path `submit_app`/`edit_app` + clip helpers + facet/cardinality validation (§8) | T-04 |
| Authoring: server form + DRF + serializer round-trip (§8) | T-05 |
| `AppPageContent`/`CatalogFacet`/`CatalogDeveloper`/`get_app_page_content`/`accepted_apps_by_owner` (§3/§6) | T-06 |
| `{% app_devlog %}` inclusion tag + `APP_PAGE_DEVLOG_DEGRADED` (§4/§6/§9.3/§9.5) | T-07 |
| Uniform 10-slot template + design-system CSS + view wiring + no-JS deep-dive + meta-description (§3/§7) | T-08 |
| Failure modes / firewall / security (§9) | T-04, T-06, T-07, T-08, T-09 |
| Tests/AC map + hard invariants + CODEMAP + ADR follow-through (§12/§14/§15) | T-09 |

**Exit-criteria check.** Every DESIGN element appears in ≥1 task ✔ · every task has a concrete
definition of done ✔ · no `L` tasks (all S/M) ✔ · risk front-loaded (registry + migration + write path
before any UI) ✔ · each task leaves the system working and releasable ✔.
