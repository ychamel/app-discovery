# TEST_PLAN — interest-profile

*Stage 4 artifact (Senior Engineer). Maps every acceptance criterion in
[FEATURE_BRIEF.md](FEATURE_BRIEF.md) to the automated test(s) that verify it, plus the
edge/security/failure coverage and a regression checklist. All tests are real-DB Django
tests run against the **real taxonomy D-5 surface** (no mocking of
`is_valid_tag`/`resolve_tag`); the §7 preserve seam is exercised against genuine
`retire_tag` states.*

Test modules (all under `apps/interests/tests/`):
`test_models.py` · `test_services.py` · `test_selectors.py` · `test_views.py` ·
`test_templatetags.py` · `test_admin.py`; plus the two config tunables in
`apps/core/tests/test_config.py`.

---

## Acceptance criteria → tests

| AC | Verified by |
|----|-------------|
| **AC1** declare interests; persisted + shown selected next visit | `test_services.SetInterestsHappyPathTests.test_first_declaration_persists_exactly_the_submitted_tags`; `test_views.PickerRenderTests.test_signed_in_get_renders_clusters_with_active_tags` + `test_saved_tags_are_pre_checked_on_the_next_get`; `test_views.SaveTests.test_save_persists_and_prg_redirects` |
| **AC2** closed vocabulary; loud reject, no partial write | `test_services.SetInterestsValidationTests` (invalid id / retired id / malformed id / over-size — all reject with the prior set intact + `INTEREST_DECLARATION_REJECTED`); `test_views.SaveTests.test_invalid_id_rerenders_picker_with_400_and_no_change` |
| **AC3** onboarding prompt; encouraged, non-gating | `test_templatetags.InterestPromptTagTests.test_renders_nudge_for_an_empty_profile`; `test_templatetags.ProfilePageNudgeTests.test_empty_profile_user_sees_the_nudge_on_the_profile_page` (the page still serves — non-gating) |
| **AC4** edit anytime; exactly the new set | `test_services.SetInterestsHappyPathTests.test_set_replace_adds_and_removes_on_an_existing_profile`; `test_views.SaveTests.test_edit_reflects_exactly_the_new_set` |
| **AC5** grouped, readable, active-only picker | `test_views.PickerRenderTests.test_signed_in_get_renders_clusters_with_active_tags` + `test_retired_tags_are_never_shown` |
| **AC6** empty profile is a valid handled state | `test_selectors.DeclaredTagIdsTests.test_empty_and_anonymous_users`; `test_selectors.HasDeclaredInterestsTests`; `test_views.PickerRenderTests.test_empty_profile_renders_the_empty_hint_not_an_error` + `test_empty_vocabulary_renders_none_available_copy`; structural (no parent row) `test_models.InterestShapeTests` |
| **AC7** references survive rename/retire (M5 = 0) | `test_selectors.DeclaredTagIdsTests.test_renamed_ref_resolves_to_its_successor` + `test_no_successor_retired_ref_resolves_to_itself_and_is_kept` + `test_two_ids_resolving_to_one_successor_dedupe`; the **edit-time** preserve seam `test_services.PreserveOnEditTests` (no-successor survives a re-save; successor normalization; preserve doesn't block adds) |
| **AC8** readable as resolvable `Tag.id`s via one surface | `test_selectors.DeclaredTagIdsTests.test_returns_a_frozenset_of_resolved_tag_ids`; structural no-score column `test_models.InterestShapeTests.test_has_no_forbidden_columns`; the import-discipline (no consumer reads storage / no corpus emit) `test_services.NoSignalsCaptureImportTests` |
| **AC9** personal mutable state; deletion + self-clear | deletion: `test_models.InterestDeletionTests.test_account_deletion_cascades_interest_rows` (+ other users survive); self-clear: `test_services.ClearInterestsTests`; view: `test_views.ClearViewTests.test_clear_removes_all_rows_and_prg_redirects` |

Every AC maps to ≥1 automated test. **No manual checks required.**

---

## M5 reference-integrity invariant

`test_selectors.CountUnresolvableTests` — `count_unresolvable()` is **0** for any profile
built through the validated write path (even with a no-successor retire), and is proven to
*detect* a deliberately hand-inserted bad id. The live break counter is the taxonomy
`TAXONOMY_REFERENCE_BREAK` (reused).

## Edge / boundary coverage

- **Empty:** empty profile (`declared_tag_ids` empty, picker hint), empty vocabulary
  ("none available", no crash), clearing an empty profile (0 no-op).
- **Idempotency:** re-saving the identical set → empty delta, no row churn, no metric.
- **Boundary:** over-size submit (> `interest_declaration_max()`) rejected.
- **Malformed:** non-UUID id tolerated as invalid (rejected loudly, never crashes).
- **Dedupe:** two stored ids resolving to one successor collapse to a single entry.
- **N+1:** `test_selectors.ReadQueryBoundTests` — query count bounded by the per-user set
  size, independent of unrelated users/tags.

## Security coverage (DESIGN §11)

- **Auth:** anonymous GET/POST → `login_required` redirect with `next=`, no write
  (`test_views.AuthAndMethodTests`).
- **Method gating:** GET on save/clear → 405.
- **CSRF:** POST without a token → 403 (`test_post_without_csrf_is_403`).
- **No IDOR (structural):** no interest id in any URL — rows addressed by `request.user` +
  `tag_id` (enforced by `urls.py`; clear/save act only on `request.user`).
- **XSS:** all tag/cluster text rendered through Django auto-escaping (no `|safe`) — verified
  implicitly by the escaped output in the view tests.
- **Read-only admin:** `test_admin.ReadOnlyAdminTests` — no add/change/delete perms.

## Failure-mode coverage (DESIGN §9)

- **Write loud:** validation reject + atomic rollback leave no partial set (AC2 tests).
- **Picker fail-soft:** `list_clusters` error → degraded page (no 500) + `INTEREST_PICKER_DEGRADED`
  (`test_views.PickerFailSoftTests`).
- **Save DB failure:** surfaces "save, please try again", no partial set
  (`test_views.SaveTests.test_db_write_failure_surfaces_try_again`).
- **Prompt fail-soft:** any read error → renders nothing + `INTEREST_PROMPT_DEGRADED`, the
  profile page still 200s (`test_templatetags` fail-soft tests).

## Regression checklist (areas touched outside the new app)

- `config/settings.py` `INSTALLED_APPS` — `apps.interests` registered (`manage.py check`).
- `config/urls.py` — `interests/` include; existing routes unaffected (full suite green).
- `apps/core/config.py` — two additive tunables + `validate_all` (`apps/core/tests/test_config.py`).
- `apps/core/observability.py` — six additive constants (no behavior change).
- `apps/accounts/templates/accounts/profile.html` — one `{% interest_prompt %}` content line;
  the existing accounts/profile test suite stays green.

## Run

```
python manage.py test apps.interests apps.core.tests.test_config   # the feature + tunables
python manage.py test                                              # full suite (no regressions)
ruff check . ; python manage.py makemigrations --check --dry-run   # lint + no drift
```
