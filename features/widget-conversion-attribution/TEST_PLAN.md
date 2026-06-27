# TEST_PLAN — widget-conversion-attribution

*Stage 4 (Senior Engineer). Every acceptance criterion (AC1–AC6, [FEATURE_BRIEF.md](FEATURE_BRIEF.md))
maps to ≥1 automated test; edge cases and the regression surface are enumerated. **Status: all
green** — full suite **962 tests**, `ruff` clean, `manage.py check` clean, no migration drift.*

Run: `python manage.py test` (full) or the per-area modules named below.

---

## Acceptance-criterion coverage

### AC1 — a conversion (new follow / new account) that followed a widget click shows on the dashboard
- `apps/widget/tests/test_attribution.py::RecordConversionTests` — the single writer
  `record_widget_conversion` creates/increments the `(app_id, kind, day)` rollup row.
- `apps/subscriptions/tests/test_views.py::FollowAttributionTests::test_new_follow_after_a_widget_click_credits_one_follow`
  — E2E: arm the marker via `GET /widget/<X>/view`, then `POST …/X/follow` → one credited follow.
- `apps/accounts/tests/test_register.py::RegisterAttributionTests::test_new_account_after_a_widget_click_credits_one_account`
  — E2E: arm the marker, then `POST /auth/register` (202) → one credited account.
- `apps/dashboard/tests/test_reception.py::WidgetReachSlotTests::test_screen_b_shows_conversions_distinct_from_reach`
  — the Screen-B slot surfaces `follows`/`accounts` + the derived M2 total.

### AC2 — bounded window; no fabricated links (no marker / expired / wrong app → not credited)
- `apps/widget/tests/test_source.py::AttributeFollowTests` —
  `test_no_marker_is_a_no_source_no_op`, `test_expired_marker_is_not_credited`,
  `test_app_mismatch_is_not_credited`, `test_version_skew_is_a_no_source_no_op`,
  `test_tampered_marker_is_a_no_source_no_op` (each: **not** credited + the matching ops counter).
- `apps/subscriptions/tests/test_views.py::FollowAttributionTests::test_follow_without_a_marker_credits_nothing`.
- `apps/accounts/tests/test_register.py::RegisterAttributionTests` — `…without_a_marker_credits_nothing`,
  `…duplicate_409_credits_nothing`, `…invalid_400_credits_nothing`; `RegisterSendFailureAttributionTests::test_send_failure_503_credits_nothing`.

### AC3 — a distinct funnel stage; reach numbers unchanged
- `apps/dashboard/tests/test_reception.py::WidgetReachSlotTests` —
  `test_screen_b_shows_conversions_distinct_from_reach` (reach integers byte-identical with
  conversions present), `test_screen_b_truthful_zero_conversion_state` (0/0 rendered, not hidden).
- `apps/widget/tests/test_selectors.py::WidgetConversionsTests` / `…ForAppsTests` — windowed
  `SUM…GROUP BY`, zero-fill, `[]→{}`, and **one query** regardless of app count (no N+1).

### AC4 — no PII (no person field in the marker or at rest)
- `apps/widget/tests/test_source.py::SetMarkerTests::test_payload_carries_no_person_field`
  (payload keys are exactly `{v, src, credited}`).
- `apps/widget/tests/test_models.py::WidgetConversionCountModelTests` —
  `test_no_actor_or_pii_or_score_field_exists`, `test_fields_are_exactly_the_designed_set`
  (the table has no user/IP/UA/referrer/device column).

### AC5 — the firewall: `record_subscribe` untouched, no curated-rating eligibility (M5 = 0)
- `apps/widget/tests/test_imports.py` — the AST proof: **no** `apps/widget` module (incl. the new
  `rollup`, `attribution`, `source`) imports `signals`; `test_the_new_attribution_modules_are_actually_walked`
  guards that the new modules are in the swept set.
- `apps/widget/tests/test_attribution.py::FirewallTests::test_recording_a_conversion_writes_no_signals_rows`
  (a credit writes zero corpus rows).
- `apps/subscriptions/tests/test_views.py::FollowAttributionTests::test_credited_follow_leaves_the_corpus_identical_and_uncurated`
  (exactly the one `record_subscribe` event a normal follow writes; `has_impression(CURATED_SURFACES)` stays False).

### AC6 — fail-soft (a marker/attribution failure never breaks a redirect, follow, registration, or reach count)
- `apps/widget/tests/test_views.py::ClickThroughTests::test_marker_failure_is_fail_soft_redirect_and_count_unaffected`
  (302 still fires, click-through reach count intact, `WIDGET_CONVERSION_DEGRADED` counted).
- `apps/subscriptions/tests/test_views.py::FollowAttributionTests::test_attribution_failure_is_fail_soft_follow_still_succeeds`.
- `apps/accounts/tests/test_register.py::RegisterAttributionTests::test_attribution_failure_is_fail_soft_registration_still_202s`.
- `apps/widget/tests/test_attribution.py::RecordConversionTests::test_db_error_propagates_not_swallowed`
  + `test_source.py::…test_writer_db_error_propagates` (the writer raises; the **hook** swallows — the split is explicit).
- `apps/dashboard/tests/test_reception.py::WidgetReachSlotTests::test_screen_b_conversion_read_failure_degrades_whole_slot_together`
  (a conversion-read error degrades the whole widget slot; the rest of the reception renders).

---

## Edge cases covered
- **Marker codec** (`test_source.py`): round-trip; tamper → `BadSignature`; expiry (signed past the
  window) → `EXPIRED`; version skew (`v:2`) → no-source; app mismatch; **per-marker dedup** (a
  re-follow in the same browser is a silent no-op; `account` independently creditable once);
  remaining-window re-issue (`Max-Age ≈ window − age`, not a full reset); cookie attributes
  (`SameSite=Lax`, `Secure` per policy, `HttpOnly`, `Path=/`).
- **Concurrency** (`test_rollup.py`): two first-of-day conversions for the same `(app, kind)` end at
  `count == 2` (create-race retry on the unique constraint).
- **Selectors**: empty (zeros), window-boundary inclusivity, rows outside the window excluded, bulk
  `[]→{}`, one-query-regardless-of-K (no N+1).
- **No false credit**: register 400/409/503 and a re-follow (`created == False`) credit nothing.
- **Last-touch**: a second click for another app overwrites the marker (`test_views.py`, `test_source.py`).

## Regression checklist (areas this feature touched)
- `apps/widget` reach writer/selector/views — existing reach tests stay green after the
  `_increment_daily` extraction (behavior-preserving): `test_attribution.py`, `test_selectors.py`,
  `test_views.py`, `test_models.py`, `test_content.py`, `test_imports.py`.
- `apps/subscriptions/views.follow` — follow + PRG + capture-failure paths unchanged
  (`test_views.py`, `test_services.py`).
- `apps/accounts/views.register` — 202/400/409/503 + rate-limit paths unchanged (`test_register.py`).
- `apps/dashboard` reception — reach slot, my-apps bulk column, loud signals reads, reviews slot
  all unchanged (`test_reception.py` full suite green).
- `apps/core` config/observability — additive tunable + four metrics; `validate_all` covers the new
  tunable (`test_config.py`).

## Gate status
- Full suite: **962 passed**, 0 failed, 0 skipped.
- `ruff check .` clean · `manage.py check` clean · `makemigrations --check` no drift.
- Migration `widget/0002_widgetconversioncount`: **up → down → up** verified clean.
