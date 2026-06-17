# TEST_PLAN — interest-taxonomy

*Stage 4 artifact (Senior Engineer). Reads: [FEATURE_BRIEF.md](FEATURE_BRIEF.md) (AC1–AC8),
[DESIGN.md](DESIGN.md), [TASKS.md](TASKS.md). Shows every acceptance criterion is exercised
by an automated test (or, for AC8, a design-time guarantee verified by schema review).*

**Suite:** `python manage.py test apps.taxonomy` — **76 tests, all green**; full repo suite
**184 tests green** (108 baseline + 76 new). `ruff check .` clean; `manage.py
makemigrations --check` reports no drift; `manage.py check` clean.

---

## Acceptance-criterion coverage

| AC | What it requires | Automated test(s) |
|----|------------------|-------------------|
| **AC1** Single authoritative, non-redundant set | `test_models.py::TagModelTests::test_labels_differing_only_by_case_cannot_both_exist`, `…_by_whitespace_…`; `test_services.py::AddTagTests::test_duplicate_slug_is_rejected_and_writes_nothing`, `…test_duplicate_normalized_label_is_rejected`; `test_check_taxonomy.py` duplicate path (via `check_integrity`) |
| **AC2** Closed set; off-vocabulary rejected | `test_selectors.py::IsValidTagTests` (active → True; retired/unknown/malformed → False) |
| **AC3** User coverage; clear labels + definitions | `test_founding_vocabulary.py::test_size_band_within_editorial_range` + `…applies_and_passes_integrity`; `test_api.py::TagListEndpointTests::test_lists_active_tags_with_clusters` (label + definition exposed to the picker) |
| **AC4** App coverage; adequate tags | `test_founding_vocabulary.py` (shipped seed applies clean; 11 clusters / 67 tags across the niche archetypes). **Real-catalog coverage deferred** — OQ-4/PL-1 (no catalog pre-`submission-intake`) |
| **AC5** Every active tag in ≥1 cluster; related grouping | `test_services.py::AddTagTests::test_add_tag_requires_at_least_one_cluster`, `ClusterMembershipTests::test_remove_from_last_cluster_orphaning_active_tag_is_rejected`, `UpdateTagTests::test_update_active_tag_to_zero_clusters_is_rejected`, `CheckIntegrityTests`; `test_check_taxonomy.py::test_orphan_active_tag_fails_non_zero_and_counts_violation`; `test_admin.py::TagAdminFormTests::test_form_without_a_cluster_is_invalid` |
| **AC6** Safe rename + defined retire rule | `test_services.py::RenameTagTests` (label only), `RetireTagTests` (soft-retire, kept, successor validation, idempotent); `test_selectors.py::ResolveTagTests` (retired-no-successor → self; retired-with-successor → successor); `test_seed.py::SeedRetireTests::test_tag_dropped_from_file_is_not_deleted`; `test_admin.py::TagAdminRetireActionTests` |
| **AC7** Stable identity across rename | `test_services.py::RenameTagTests::test_rename_changes_label_only_id_and_slug_unchanged`; `test_selectors.py::ResolveTagTests::test_renamed_active_tag_resolves_to_itself_with_new_label`; `test_seed.py::…test_editing_a_label_updates_only_that_label_keeping_id_and_slug` |
| **AC8** Adjacency addable without destructive migration | **Design-time guarantee (verified by schema review, per TASKS note):** clusters are first-class (`taxonomy_cluster` + M2M `Tag.clusters`); adjacency is a *future* additive `taxonomy_cluster_adjacency` table over existing `Cluster` rows — it touches no `Tag`, no membership, no stored reference (DESIGN §4/§7, D-5). No runtime test (nothing to assert until the table exists). |

---

## Edge cases covered

- **Normalized-label dedup:** case-only and whitespace-only label variants both collide
  (DB functional unique index + service pre-check) — `test_models.py`, `test_services.py`.
- **Atomicity / no partial apply:** failed `add_tag` (zero clusters / duplicate) writes
  nothing; malformed/bad-reference seed rolls back the whole run — `test_services.py`,
  `test_seed.py::SeedAbortTests`.
- **`resolve_tag` resolution matrix:** renamed→self, retired-with-successor→successor,
  retired-no-successor→self, multi-hop chain→final, unknown→`None`, and a hand-built
  `replaced_by` **cycle** stops at the config step-limit, logs, counts
  `taxonomy_reference_break`, and returns the last good tag (never loops) — `test_selectors.py`.
- **Retire successor validation:** self, already-retired, and cycle-forming successors are
  rejected; retire is idempotent (keeps original `retired_at`) — `test_services.py`.
- **Orphaning:** removing an active tag's last cluster is refused; a retired tag may be
  orphaned — `test_services.py::ClusterMembershipTests`.
- **Idempotent seed:** re-running an unchanged file writes nothing (no `updated_at` bump);
  editing a label updates only that label; a dropped tag is not deleted — `test_seed.py`.
- **API:** active-only list, retired-reference detail with `replaced_by`, `404` unknown id,
  `403` unauthenticated, no N+1 (prefetch asserted via `assertNumQueries`) — `test_api.py`,
  `test_selectors.py`.
- **Migration:** UUID PKs, citext slug case-insensitivity, status default, `replaced_by`
  `SET_NULL` on successor delete; reversible (`migrate taxonomy zero` drops the three tables,
  keeps the shared `citext` extension) — `test_models.py` + manual verification on dev DB.

## Regression checklist (areas touched)

- `apps/core/observability.py` — added 5 taxonomy metric constants only; existing accounts
  metrics unchanged (full suite green).
- `apps/core/config.py` — added `taxonomy_resolve_max_steps`; `validate_all` extended;
  `apps.core.tests.test_config` green.
- `config/settings.py` (INSTALLED_APPS) + `config/urls.py` (mount `taxonomy/`) — accounts
  routes and health unaffected (full suite green).
- New dependency **PyYAML** (`pyproject.toml`) — used only by `seed_taxonomy`.

## Known deviations (logged)

- **ITX-9** — unauthenticated read = `403` (not the `401` in the original DESIGN §5c) under
  the platform's DRF `SessionAuthentication`; DESIGN §5c updated; matches identity-accounts.
- **ITX-11** — added `update_tag`/`update_cluster` sync setters to the write service to
  realize DESIGN §6's idempotent "update labels/definitions/membership"; DESIGN §5b updated.
- **OQ-4 / PL-1** — AC4 app-coverage against a *real* submitted catalog is deferred (no
  catalog exists pre-`submission-intake`); re-validate when that feature lands.
