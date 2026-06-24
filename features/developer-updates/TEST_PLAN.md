# TEST_PLAN — developer-updates

*Stage 4 artifact (Senior Engineer). The exit proof that every acceptance criterion in the
approved [FEATURE_BRIEF.md](FEATURE_BRIEF.md) maps to a named, passing automated test, built
against the **ratified** [DESIGN.md](DESIGN.md) per [TASKS.md](TASKS.md) (T-01…T-06).*

**Status:** full suite **green — 828 tests** (740 baseline + 88 new), `ruff` clean,
`makemigrations --check` clean, `manage.py check` clean. Never marked done with a failing or
skipped test.

Test modules:
- `apps/updates/tests/test_models.py` — T-01 (the table shape)
- `apps/updates/tests/test_selectors.py` — T-02 (the producer reads)
- `apps/updates/tests/test_seam.py` — T-02 (the AS-3 adapter + the no-import-cycle proof)
- `apps/updates/tests/test_services.py` — T-03 (the write path)
- `apps/updates/tests/test_views.py` — T-05 (the HTTP layer end-to-end)
- `apps/updates/tests/test_imports.py` — T-05 (AC6 structural — no `signals` import)
- `apps/subscriptions/tests/test_notices.py` / `test_views.py` / `test_selectors.py` — the
  repointed seam, the feed fail-soft, and the additive `subscriber_count` (regression on the
  closed app)
- `apps/core/tests/test_config.py` — the five `updates_*` tunables + `validate_all`

---

## Acceptance criteria → tests

### AC1 — owner + role gated (no ownership oracle)
| Given/When/Then | Test(s) |
|---|---|
| Owner posts to an app they own → created & attributed | `test_services.PostNoticeValidationTests.test_valid_update_creates_one_row`; `test_views.PostViewTests.test_valid_update_creates_one_notice_and_prg` |
| Non-owner / unknown id posts → rejected, nothing created, 404 indistinguishable | `test_services.PostNoticeOwnerGateTests.test_posting_to_an_unowned_app_raises_and_writes_nothing` / `.test_posting_to_an_unknown_app_raises`; `test_views.PostViewTests.test_non_owner_post_is_404`; `test_views.ChannelViewGateTests.test_another_devs_app_is_404` / `.test_unknown_app_is_404` |
| Non-developer (lacks role) → 403 on every route | `test_views.ChannelListGateTests.test_non_developer_is_403`; `ChannelViewGateTests.test_non_developer_is_403`; `PostViewTests.test_non_developer_post_is_403` |

### AC2 — post an update (pinned `Notice` contract)
| Given/When/Then | Test(s) |
|---|---|
| Update with title/summary → one `kind="update"` row honoring the shape | `test_services.PostNoticeValidationTests.test_valid_update_creates_one_row`; `test_models.NoticeModelTests.test_persists_all_fields`; `test_views.PostViewTests.test_valid_update_creates_one_notice_and_prg` |
| Boundary validation — unknown kind / blank / over-length / at-cap / stripped | `test_services.PostNoticeValidationTests` (`test_unknown_kind_is_rejected`, `test_blank_title_is_rejected`, `test_blank_summary_is_rejected`, `test_over_length_title_is_rejected_at_the_boundary`, `test_title_exactly_at_the_cap_is_accepted`, `test_over_length_summary_is_rejected`, `test_title_and_summary_are_stripped_before_store`); `test_views.PostViewTests.test_invalid_post_prgs_back_with_message_and_creates_nothing` |

### AC3 — post early-access
| Given/When/Then | Test(s) |
|---|---|
| Early-access note → one `kind="early_access"` row, same contract | `test_services.PostNoticeValidationTests.test_valid_early_access_creates_one_row`; `test_views.PostViewTests.test_valid_early_access_creates_one_notice`; `test_models.NoticeModelTests.test_both_kinds_are_accepted` |

### AC4 — producer of the AS-3 feed seam
| Given/When/Then | Test(s) |
|---|---|
| Follower + posted notice → appears newest-first in the feed (seam live) | `test_seam.SeamIntegrationTests.test_returns_render_notices_newest_first_with_id_dropped`; `apps/subscriptions/tests/test_views.FeedViewTests.test_feed_renders_notices_posted_by_the_producer`; `apps/updates/tests/test_views.AudienceScopeAndCorpusTests.test_notice_reaches_a_follower_but_not_a_non_follower` |
| No notices → existing empty state unchanged | `test_seam.SeamIntegrationTests.test_empty_input_and_no_rows_return_empty`; `apps/subscriptions/tests/test_notices.NoticesForAppsTests.test_returns_empty_when_no_notices_exist`; `apps/subscriptions/tests/test_views.FeedViewTests.test_feed_renders_the_notices_empty_state` |
| Adapter maps `PublishedNotice → Notice` (drops `id`) | `test_seam.SeamIntegrationTests.test_returns_render_notices_newest_first_with_id_dropped`; `apps/subscriptions/tests/test_notices.NoticesForAppsTests.test_maps_producer_rows_to_render_notices` |
| Producer read is bounded / 1 query / `limit`-capped | `test_selectors.PublishedNoticesForAppsTests` (`test_one_query_independent_of_notice_count`, `test_capped_at_limit`, `test_newest_first`, `test_scoped_to_requested_apps_only`) |
| Feed fail-soft preserved (producer raise caught by the existing wrapper) | `apps/subscriptions/tests/test_views.FeedViewTests.test_feed_fail_soft_preserved_when_producer_read_raises` |

### AC5 — audience-scoped; buys no reach (M5 = 0 structural)
| Given/When/Then | Test(s) |
|---|---|
| Notice visible **only** to current followers; never to a non-follower | `test_views.AudienceScopeAndCorpusTests.test_notice_reaches_a_follower_but_not_a_non_follower` |
| Posting / viewing injects **no** `Impression` / `EngagementEvent` row | `test_views.AudienceScopeAndCorpusTests.test_posting_and_viewing_inject_no_corpus_rows` |

### AC6 — only genuine returns count; no manufactured signal
| Given/When/Then | Test(s) |
|---|---|
| `apps/updates` imports **nothing** from `signals` (structural) | `test_imports.UpdatesImportsTests.test_no_module_in_the_app_imports_signals` |
| Posting / withdrawing writes no corpus row | `test_views.AudienceScopeAndCorpusTests.test_posting_and_viewing_inject_no_corpus_rows` |

### AC7 — manage / withdraw
| Given/When/Then | Test(s) |
|---|---|
| Owner sees their notices newest-first on the channel | `test_selectors.NoticesForChannelTests` (ordering / own-scope / app-scope / 1 query); `test_views.WithdrawHttpTests.test_channel_lists_notices_newest_first` |
| Withdraw → gone from the channel **and** from a follower's feed, no error | `test_services.WithdrawNoticeTests.test_withdraw_deletes_own_notice_and_returns_true`; `test_views.WithdrawHttpTests.test_withdraw_removes_from_channel_and_prgs`; `test_views.AudienceScopeAndCorpusTests.test_withdrawn_notice_drops_from_follower_feed` |
| Withdraw of a foreign / unknown / wrong-app id → harmless no-op (no leak, no error) | `test_services.WithdrawNoticeTests` (`test_withdraw_unknown_id_is_a_noop_returning_false`, `test_withdraw_another_authors_notice_does_nothing`, `test_withdraw_with_wrong_app_id_does_nothing`); `test_views.WithdrawHttpTests.test_withdraw_unknown_id_is_harmless_noop` |

### AC8 — anti-spam rate limit (config-driven)
| Given/When/Then | Test(s) |
|---|---|
| Over the per-author/per-app window limit → rejected, nothing created | `test_services.PostNoticeRateLimitTests.test_limit_blocks_the_next_post_in_window`; `test_views.RateLimitHttpTests.test_posting_past_the_limit_prgs_back_and_creates_nothing` |
| Per-author **and** per-app scoping; resets outside the window | `test_services.PostNoticeRateLimitTests` (`test_limit_is_per_app`, `test_limit_is_per_author`, `test_a_post_outside_the_window_succeeds`) |
| Config-driven (override changes threshold/window with no code change) | `test_services.PostNoticeRateLimitTests` (class `@override_settings`); `apps/core/tests/test_config.UpdatesTunableTests` (defaults / overrides / non-positive fails loudly) |

---

## Metrics → tests

| Metric | Test(s) |
|---|---|
| M1 `UPDATES_NOTICE_POSTED{kind}` | `test_services.PostNoticeValidationTests.test_post_counts_notice_posted_with_kind` |
| M5 reach beyond followers = 0 (structural) | `test_views.AudienceScopeAndCorpusTests.test_notice_reaches_a_follower_but_not_a_non_follower` |
| M6 `UPDATES_POST_REJECTED{reason=rate_limited}` | `test_services.PostNoticeRateLimitTests.test_rate_limit_counts_post_rejected_rate_limited` |
| `UPDATES_POST_REJECTED{reason=invalid}` | `test_services.PostNoticeValidationTests.test_reject_counts_post_rejected_invalid` |
| `UPDATES_NOTICE_WITHDRAWN` (only on real delete) | `test_services.WithdrawNoticeTests.test_withdraw_counts_notice_withdrawn_only_on_real_delete` |
| `UPDATES_POST_FAILED` (post fail-soft) | `test_views.PostViewTests.test_unexpected_error_fails_soft_with_message_and_counter` |
| `UPDATES_AUDIENCE_DEGRADED` / `UPDATES_CHANNEL_DEGRADED` | `test_views.FailureSplitTests` (`test_audience_hint_degrades_soft`, `test_channel_notices_degrade_soft`) |
| `SUBSCRIPTION_NOTICE_DEGRADED` (feed health, reused) | `apps/subscriptions/tests/test_views.FeedViewTests.test_feed_fail_soft_preserved_when_producer_read_raises` |
| M2 audience reach (analyst-derived from `subscriber_count`) | `apps/subscriptions/tests/test_selectors.SubscriberCountTests` (count correctness, app-scope, unfollow, 1 query) |

---

## The load-bearing design risk (DESIGN §4/§13) → tests

| Risk | Test(s) |
|---|---|
| No import cycle between `subscriptions` and `updates` (the headline self-critique) | `test_seam.ImportCycleAbsenceTests` (`test_importing_both_seam_modules_in_either_order_succeeds`, `test_updates_producer_core_does_not_import_subscriptions`, `test_subscriptions_read_modules_do_not_import_updates`) |
| `updates.views → subscriptions.selectors.subscriber_count` is an **intended** DAG edge (DESIGN §4) — only the producer core (`selectors`/`models`/`services`) must not import back into `subscriptions`. | encoded in `test_updates_producer_core_does_not_import_subscriptions` |

---

## Edge cases covered (DESIGN §9)

- Empty followed set / empty notice set → empty states, no error (`test_selectors`, feed tests).
- Over-length and exactly-at-cap title/summary (`test_services` boundary tests).
- Unknown kind, blank/whitespace title/summary (`test_services`).
- Concurrent-post TOCTOU is an accepted bounded trade-off — no test asserts a lock (by design,
  DESIGN §5.3).
- Withdraw of an already-withdrawn / foreign / wrong-app id → no-op, no leak (`test_services`,
  `test_views`).
- Huge follower / notice counts stay 1 query (`assertNumQueries` in `test_selectors`,
  `SubscriberCountTests`).
- Author account deletion CASCADEs to their notices (`test_models`).

## Regression checklist (areas touched)

- `apps.subscriptions` full suite green — the seam signature + its single call site are
  unchanged (only the body repointed); the additive `subscriptions_app_idx` index is reversible
  (`0002` up→down→up verified).
- `apps.updates/0001_initial` reversible (`migrate updates zero` up→down→up verified).
- `apps.core.config` / `observability` — additive only; `validate_all` covers the new tunables.
- Whole-suite green (828), no migration drift, `ruff` clean.
