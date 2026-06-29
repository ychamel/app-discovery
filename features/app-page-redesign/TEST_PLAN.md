# TEST_PLAN.md — app-page-redesign

*Stage 4 (Senior Engineer). Maps every acceptance criterion (AC-1…AC-9 + the re-review
toggle, [FEATURE_BRIEF.md](FEATURE_BRIEF.md) / [DESIGN.md](DESIGN.md) §12) to its automated
test(s), records the edge cases and the two hard structural invariants, and lists the
regression surface. **Full suite: 1094 tests green** · `ruff` clean · `manage.py check` clean
· `makemigrations --check` reports only the one deliberate additive migration `catalog/0004`.*

> Run the feature's own tests:
> ```
> python manage.py test apps.catalog apps.pages apps.updates apps.core
> ```

---

## Acceptance-criterion coverage

| AC | What it asserts | Test(s) |
|----|-----------------|---------|
| **AC-1** pitch line | tagline renders above the deep-dive **and** as `<meta name="description">`; empty tagline breaks no slot | `pages/tests/test_template.py::PitchTests::test_tagline_renders_and_is_meta_description`, `::test_empty_tagline_breaks_nothing` |
| **AC-2** demo clip | clip renders as the first media peer, `muted`+`loop`+`aria-label`/alt; screenshots still render; no hosted-video/iframe dependency | `pages/tests/test_template.py::DemoClipTests::test_clip_renders_as_muted_aria_labelled_video`, `::test_no_clip_keeps_screenshots` |
| **AC-3** typed facets | facets render as an at-a-glance fact strip; **firewalled** from ranking/discovery (informational only) | `pages/tests/test_template.py::FacetTests::test_facets_render_in_fact_strip` · firewall: `catalog/tests/test_redesign_invariants.py::RankingFirewallInvariantTests` |
| **AC-4** deep dive | the deep dive is a native `<details>` "show more", reachable with **JS disabled** (no `hx`/JS dependency) | `pages/tests/test_template.py::DeepDiveTests::test_deep_dive_is_native_details_no_js`, `::test_no_deep_dive_omits_the_details` |
| **AC-5** developer identity | shows `display_name` + links to **ACCEPTED-only** other apps; no email/PII; pending/rejected excluded | `pages/tests/test_template.py::DeveloperHubTests::*` · `catalog/tests/test_page_content.py::GetAppPageContentTests::test_other_apps_accepted_only_excludes_self_and_leaks_nothing` |
| **AC-6** devlog | devlog renders via `published_notices_for_apps`; **no `signals` import added** (M5=0); fail-soft | `updates/tests/test_devlog_tag.py::*` · `catalog/tests/test_redesign_invariants.py::DevlogFirewallInvariantTests` · `updates/tests/test_imports.py` (walks the new templatetag module) |
| **AC-7** uniformity | two wildly different apps render the **identical always-present slot set/order**; the read-model has no tier/payment/identity field | `pages/tests/test_template.py::StructuralUniformityTests::*` · `catalog/tests/test_redesign_invariants.py::UniformityInvariantTests::*` |
| **AC-8** compelling feel | **human-judgment sign-off** on web + mobile (the PS-3 precedent) | **Out of automated scope** — surfaced by the Release Engineer (Stage 5) for the user, like the `premium-frontend` M7 sign-off |
| **AC-9** no regression | full suite green; `CatalogApp` byte-stable; canonical URL, try-it `app_page` impression, share, follow, reviews still pass; `makemigrations --check` clean except `catalog/0004` | `catalog/tests/test_page_content.py::GetAppPageContentTests::test_catalog_app_contract_unchanged` · `pages/tests/test_views.py::*` (impression/try/share) · the full-suite run + drift check |
| **re-review toggle** | editing each new field on an accepted app returns it to `pending` when gated on, **does not** when toggled off (config-driven, both directions) | `catalog/tests/test_services_marketing.py::EditMarketingFieldsTests::test_marketing_edit_returns_accepted_app_to_pending_by_default`, `::test_marketing_edit_stays_accepted_when_toggled_off`, `::test_partial_toggle_gates_only_configured_field`, `::test_clip_edit_returns_accepted_app_to_pending` · `catalog/tests/test_gate.py::GateRelevantFieldsTests::*` · `core/tests/test_config.py::AppPageGatedFieldsTests::*` |

## Edge cases (DESIGN §12)

| Edge case | Test |
|-----------|------|
| Empty / legacy app → graceful-empty everywhere | `catalog/tests/test_page_content.py::GetAppPageContentTests::test_legacy_app_degrades_to_empty` · `catalog/tests/test_models.py::AppModelTests::test_marketing_columns_default_to_empty_never_null` |
| Oversized clip rejected loudly | `catalog/tests/test_services_marketing.py::SubmitMarketingFieldsTests::test_oversize_clip_refused` |
| Non-AV clip rejected loudly | `::test_non_av_clip_refused` |
| Clip without alt rejected loudly (C5/A4) | `::test_clip_without_alt_refused` |
| Off-vocabulary facet rejected loudly, nothing written | `::test_off_vocabulary_facet_refused_nothing_written` · `catalog/tests/test_facets.py::FacetRegistryTests`, `::ResolveFacetsTests` |
| `SINGLE`-facet 2nd value rejected | `::test_single_facet_second_value_refused` |
| Facet value removed from registry → dropped at read (D-5) | `catalog/tests/test_page_content.py::GetAppPageContentTests::test_registry_absent_facet_value_dropped_at_read` · `catalog/tests/test_facets.py::ResolveFacetsTests::test_registry_absent_value_silently_dropped` |
| Solo developer → no "other apps" | `pages/tests/test_template.py::DeveloperHubTests::test_no_other_apps_when_solo` · `catalog/tests/test_page_content.py::GetAppPageContentTests::test_legacy_app_degrades_to_empty` |
| Devlog read raising → fail-soft (renders nothing, 200, degrade metric) | `updates/tests/test_devlog_tag.py::AppDevlogTagTests::test_read_error_is_fail_soft_and_counted` |
| `AppFacet` CASCADE-deletes with its app | `catalog/tests/test_models.py::AppFacetModelTests::test_facets_cascade_delete_with_app` |
| Migration up→down→up reverses cleanly | verified at build (`migrate catalog 0004 → 0003 → 0004`, clean) — the documented partial-irreversibility (DESIGN §10) |
| Bounded query count (no N+1) on the page read | `catalog/tests/test_page_content.py::GetAppPageContentTests::test_no_n_plus_one_on_facets_and_media` |

## The two hard structural invariants (DESIGN §12)

Standalone, in `catalog/tests/test_redesign_invariants.py`:

1. **Uniformity** — `UniformityInvariantTests`: `AppPageContent` carries no tier/payment/identity
   field; `CatalogDeveloper` exposes `display_name` only (no PII can leak). The template-side
   "same slots regardless of content" proof is `pages/tests/test_template.py::StructuralUniformityTests`.
2. **Ranking firewall (M5=0)** — `RankingFirewallInvariantTests`: `search_catalogue` /
   `_accepted_matching` never read `app_facets`/`AppFacet`, and the whole `apps.discovery` +
   `apps.interests` packages reference neither. `DevlogFirewallInvariantTests`: the devlog tag
   imports nothing from `signals`.

## Regression surface (areas touched → covered)

- **`catalog` write path** (`submit_app`/`edit_app` extended): `catalog/tests/test_services_write.py`
  (unchanged floor still green) + `test_services_marketing.py` (new optional fields).
- **`catalog` read** (`CatalogApp` reused, new `AppPageContent`): `test_selectors.py` (byte-stable
  contract) + `test_page_content.py`.
- **`catalog` authoring** (form + DRF + serializer): `test_api_developer.py`, `test_pages_developer.py`
  (unchanged), `test_authoring_marketing.py` (new fields round-trip).
- **`catalog` gate** (constant → function): `test_gate.py`.
- **`pages` view + template** (rewritten to `get_app_page_content` + the 10-slot contract):
  `pages/tests/test_views.py`, `test_template.py`.
- **`updates`** (new templatetag): `test_devlog_tag.py`, `test_imports.py`.
- **`core` config + observability** (new tunables + metric): `core/tests/test_config.py`.
- **Cross-feature `CatalogApp` consumers** (discovery / dashboard / widget / subscriptions /
  ratings): full suite green; the two app-page slot-fingerprint tests in `ratings` + `subscriptions`
  updated to the redesigned landmarks.
