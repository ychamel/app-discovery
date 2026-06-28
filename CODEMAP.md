# CODEMAP.md — Shared Code Index

**This is the durable channel for code reuse.** Before writing any shared helper,
type, or service, an agent checks here for one that already exists. After adding or
changing shared code, it records it here. This is the third durable channel alongside
[CONTROL.md](CONTROL.md) (process state) and [DECISIONS.md](DECISIONS.md) (rationale).

## Why this exists

Agents work one task at a time and cannot see what other sessions built. Left alone,
they re-create helpers that already exist — because **you cannot grep for a function
whose name you never thought of.** Surveying the whole codebase every session is also
expensive. A small, curated index solves both: it is cheap to read (one file) and it
surfaces reusable code you didn't know to search for.

## What belongs here

Only the **shared, reusable surface** — code meant to be used across features:

- Utility / helper functions (formatting, parsing, validation, math).
- Shared types, schemas, and constants (the canonical shape of a domain concept).
- Cross-cutting services and clients (data access, caching, auth, logging, config).
- Shared UI components, if any.

**What does NOT belong here:** feature-private code used in exactly one place, generated
code, or test fixtures. If it is not meant to be reused, it stays out of the index — a
bloated map is as useless as none.

## Convention: where shared code lives

Shared code lives under a single, known root (set when the stack is chosen in Stage 2 —
e.g. `shared/`, `lib/`, or `src/utils/`, recorded in [DECISIONS.md](DECISIONS.md)).
This keeps placement consistent so even a targeted search is scoped. The chosen root is
named here once it exists.

> Shared-code root: **`apps/`** — every feature is a Django app under it; cross-cutting
> reusable code lives in `apps/core/`, the canonical account/role surface in
> `apps/accounts/`. Set by `identity-accounts` Stage 2 (global [D-4](DECISIONS.md)).

## Format

One line per item, grouped by area. Keep entries to a signature/name, a one-line
purpose, and a path. Detail lives in the code, not here.

```
<name / signature> — <one-line purpose> — <path>
```

## Index

_Built by `identity-accounts` Stage 4. Entries are added as each shared item ships._

### Configuration (`apps/core/config.py`)
- `login_token_ttl() -> timedelta` — magic-link token lifetime (default 15 min) — `apps/core/config.py`
- `rate_limit_per_email_per_hour() -> int` — auth-request cap per email (default 5) — `apps/core/config.py`
- `rate_limit_per_ip_per_hour() -> int` — auth-request cap per client IP (default 20) — `apps/core/config.py`
- `taxonomy_resolve_max_steps() -> int` — max replaced_by hops `resolve_tag` follows before bailing on a cycle (default 16) — `apps/core/config.py`
- `catalog_media_max_count() -> int` — max screenshots per submitted app (default 8; submission-intake DESIGN §9) — `apps/core/config.py`
- `catalog_media_max_bytes() -> int` — max bytes per uploaded app image (default 5 MB; DESIGN §9) — `apps/core/config.py`
- `validate_all()` — evaluate all tunables at startup (fail loud) — `apps/core/config.py`

### Email (`apps/core/email.py`)
- `EmailSender` (Protocol) / `DefaultEmailSender` — pluggable, fail-loud email send (digest reuses) — `apps/core/email.py`
- `get_email_sender() -> EmailSender` — factory seam for the configured sender — `apps/core/email.py`
- `EmailSendError` — raised when a send cannot be handed to the transport — `apps/core/email.py`

### Rate limiting (`apps/core/ratelimit.py`)
- `rate_limited` (decorator) — enforce per-email + per-IP hourly limits, `429` over cap (no-op on safe methods) — `apps/core/ratelimit.py`
- `ip_rate_limited_get(limit_fn, *, scope, window_seconds=60, limited_metric=None, degraded_metric=None)` (decorator) — per-IP fixed-window limit on a **GET** view (the public-read sibling of `rate_limited`; generalises the shared `_exceeds_limit` by its window): `429` over cap (view not called) + `limited_metric`, **fail-open** on a cache error + `degraded_metric`; non-GET passes through. Metric names are injected (stays feature-agnostic) — `apps/core/ratelimit.py`

### Observability (`apps/core/observability.py`, `apps/core/middleware.py`)
- `increment(metric, **tags)` — emit a counter event (pluggable; logs today) — `apps/core/observability.py`
- metric name constants (`REGISTRATION_COMPLETION`, `SIGNIN_SUCCESS`, `AUTH_ERROR`, `ROLE_GATE_DECISION`, `EMAIL_SEND_FAILURE`, `DELETION_FULFILMENT`, `DEVELOPER_ROLE_ADOPTION`, `ADMIN_ROLE_CHANGE`, `SIGNOUT`) — `apps/core/observability.py`
- taxonomy metric constants (`TAXONOMY_TAG_ADDED`, `TAXONOMY_TAG_RENAMED`, `TAXONOMY_TAG_RETIRED`, `TAXONOMY_REFERENCE_BREAK`, `TAXONOMY_INTEGRITY_VIOLATION`) — `apps/core/observability.py`
- catalog metric constants (`SUBMISSION_STARTED`, `SUBMISSION_COMPLETED`, `SUBMISSION_CREATED`, `APP_WITHDRAWN`, `APP_RESUBMITTED`, `APP_ACCEPTED`, `APP_REJECTED`, `REVIEW_DECISION`, `TAG_OFF_VOCABULARY_REJECTED`, `DUPLICATE_FLAGGED`) — `apps/core/observability.py`
- `check_health() -> dict` — DB + email reachability (backs `/health`, the operator deep probe) — `apps/core/observability.py`
- `_database_ok()` / `_email_ok()` — the two individual reachability probes `check_health` composes; `_database_ok` is reused by the DB-only liveness view — `apps/core/observability.py`
- `RequestContextFilter` + `RequestContextMiddleware` — inject request id + account UUID into logs — `apps/core/observability.py`, `apps/core/middleware.py`

### Core platform views & deployment shell (`apps/core`, platform-staging / D-12)
- `views.health` (`GET /health`) — operator deep probe (DB **+** opens a live SMTP socket); `views.health_live` (`GET /health/live`) — **DB-only** liveness for the orchestrator/uptime monitor (never touches email/cache), the platform-staging health-check target — `apps/core/views.py`
- `views.serve_media` (`/media/<path>`) — serves uploaded media from `settings.MEDIA_ROOT` (read at request time) in **all** environments, not just DEBUG; the deliberate single-node staging trade-off, object-store is the growth path — `apps/core/views.py`, `config/urls.py`
- **`core/base.html`** — the **shared responsive shell every wedge surface inherits** (header nav + auth state, `<main>`, footer, `<meta viewport>`, the single `core/app.css` link, Django `messages` rendered once). Block contract (additive-only): `{% block title %}` (default "App Discovery") / `{% block head %}` / `{% block content %}`. **Extend this — do not add a 7th per-app base.html.** The 6 app bases (`accounts`/`catalog`/`dashboard`/`discovery`/`pages`/`updates`) are thin `{% extends "core/base.html" %}` stubs. The embeddable **widget stays isolated** (self-contained inline `<style>`, no platform stylesheet — AC3.3 firewall) — `apps/core/templates/core/base.html`
- `core/app.css` — the one mobile-first, dependency-free, no-build platform stylesheet (tokens, responsive nav, accessible form/table/card styles, ~600/900 px breakpoints) — `apps/core/static/core/app.css`
- settings deployment helpers: `_cache_settings(redis_url)` (RedisCache from `REDIS_URL`, LocMem fallback → limiter correct across workers) · `_init_sentry(dsn)` (env-gated Sentry, no-op when unset) · `DATABASE_URL` bridge (dj-database-url, discrete `DB_*` fallback) · WhiteNoise manifest static (gated on `not DEBUG`) — `config/settings.py`

### Identity model (`apps/accounts/models.py`)
- `Account` — canonical cross-feature identity (UUID id, citext email, display_name, roles via groups; passwordless) — `apps/accounts/models.py`
- `Account.objects.create_account(email, display_name)` — the one account-creation path (sets unusable password) — `apps/accounts/managers.py`
- `LoginToken` — single-use magic-link credential (hash only) — `apps/accounts/models.py`
- `RoleGrant` — append-only grant/revoke audit row (SET_NULL FKs survive deletion) — `apps/accounts/models.py`

### Roles & authorization (`apps/accounts/`)
- `USER` / `DEVELOPER` / `ADMIN` / `BASE_ROLE` / `SELF_SERVE_ROLES` — role-name constants & policy — `apps/accounts/roles.py`
- `account_roles(account) -> list[str]` — role names an account holds — `apps/accounts/roles.py`
- `account_has_role(user, role) -> bool` — the one fail-closed gate decision — `apps/accounts/permissions.py`
- `HasRole(role)` — DRF permission class factory — `apps/accounts/permissions.py`
- `require_role(role)` — Django view decorator (raises 403 when denied) — `apps/accounts/permissions.py`
- `grant_role` / `revoke_role` — audited role change (writes RoleGrant atomically) — `apps/accounts/services.py`
- `UnknownRoleError` — raised for a role with no group (→ 400) — `apps/accounts/services.py`

### Interest vocabulary — model (`apps/taxonomy/models.py`)
- `Tag` — one vocabulary unit; UUID `id` is the stable cross-feature reference, `slug`/`label`/`status`/`replaced_by`/`clusters` — `apps/taxonomy/models.py`
- `Cluster` — a named grouping of related tags (anchor for future adjacency) — `apps/taxonomy/models.py`
- `CanonicalLabel` — SQL Func for a label's case/whitespace-insensitive duplicate-detection form — `apps/taxonomy/models.py`

### Interest vocabulary — write surface (`apps/taxonomy/services.py`, admin-only single mutate path)
- `add_tag` / `rename_tag` / `retire_tag` — tag lifecycle (≥1 cluster, dedupe, soft-retire + successor) — `apps/taxonomy/services.py`
- `update_tag` — idempotent sync of an existing tag's label/definition/membership (seed path; no-op when unchanged) — `apps/taxonomy/services.py`
- `add_cluster` / `rename_cluster` / `update_cluster` / `assign_to_cluster` / `remove_from_cluster` — cluster + membership writes (refuses to orphan an active tag) — `apps/taxonomy/services.py`
- `check_integrity() -> IntegrityReport` — scan for orphan active tags, empty clusters, duplicate labels — `apps/taxonomy/services.py`
- `DuplicateTagError` / `OrphanTagError` / `RetireSuccessorError` — loud write-service failures — `apps/taxonomy/errors.py`

### Interest vocabulary — read surface (`apps/taxonomy/selectors.py`, the cross-feature substrate — D-5)
- `list_active_tags()` / `list_clusters()` — active vocabulary with membership prefetched (no N+1) — `apps/taxonomy/selectors.py`
- `get_tag(id) -> Tag | None` — fetch a tag of any status — `apps/taxonomy/selectors.py`
- `is_valid_tag(id) -> bool` — closed-set validator: True only for an active tag (consumers enforce at their write boundary, AC2) — `apps/taxonomy/selectors.py`
- `resolve_tag(id) -> Tag | None` — follow `replaced_by` to current meaning; keeps retired refs, cycle-guarded (AC6/AC7) — `apps/taxonomy/selectors.py`
- `tag_ids_resolving_to(active_id) -> frozenset[UUID]` — **reverse of `resolve_tag`**: an active tag + its transitive merge predecessors (the ids that *mean* it now), for a merge-correct tag filter (open-search-browse AC3); tolerant of a bad id (→ `frozenset()`), bounded by vocabulary size not catalogue — `apps/taxonomy/selectors.py`

### App catalog — model & gate (`apps/catalog/`)
- `App` — one submitted web app; UUID `id` is the stable cross-feature reference (D-6); `owner`/`status`/`normalized_url`/`last_submitted_at` — `apps/catalog/models.py`
- `AppTag` — app↔tag link as a soft `tag_id` UUID (D-5; no DB FK) — `apps/catalog/models.py`
- `AppMedia` — one ordered screenshot (validated image) — `apps/catalog/models.py`
- `ReviewDecision` — append-only gate-decision audit row (outcome + failed_criteria) — `apps/catalog/models.py`
- `Criterion` / `CHECKLIST` / `GATE_RELEVANT_FIELDS` — the fixed five objective floors, no "other" value (AC6) — `apps/catalog/gate.py`
- `normalize_url(raw) -> str` — single rule for "same app" duplicate signal — `apps/catalog/urlnorm.py`

### App catalog — write surface (`apps/catalog/services.py`, the single mutate path)
- `submit_app` / `edit_app` / `add_media` / `remove_media` — content writes with the AC1/AC4/§9 boundary invariants — `apps/catalog/services.py`
- `accept_app` / `reject_app` / `withdraw_app` / `resubmit_app` — lifecycle/decision writes (atomic, row-locked, §7 state machine) — `apps/catalog/services.py`
- `InvalidTagError` / `MediaLimitError` / `InvalidTransitionError` / `NotOwnerError` — loud write-service failures — `apps/catalog/errors.py`

### App catalog — read surface (`apps/catalog/selectors.py`, the cross-feature substrate — D-6)
- `get_owned_app(owner, id)` / `list_owned_apps(owner)` — owner-scoped "my apps", any status (no leak, AC8) — `apps/catalog/selectors.py`
- `list_review_queue() -> list[ReviewRow]` — pending apps FIFO + duplicate hint, no priority field (AC3) — `apps/catalog/selectors.py`
- `apps_sharing_url(normalized_url, *, exclude=None)` — the duplicate signal (§6c) — `apps/catalog/selectors.py`
- `list_catalogued_apps()` / `get_catalogued_app(id) -> CatalogApp | None` — **ACCEPTED only**; resolved tags + ordered media (the D-6 downstream contract, AC9) — `apps/catalog/selectors.py`
- `get_catalogued_apps(ids) -> list[CatalogApp]` — **bulk by-ids**, ACCEPTED only, no N+1; non-accepted/unknown ids silently absent (additive D-6 read, the feed primitive — app-subscriptions DESIGN §4.3) — `apps/catalog/selectors.py`
- `search_catalogue(*, query=None, tag_ids=None, page=1, page_size=None) -> CatalogPage` — **the paginated, DB-pushed open-discovery read** (open-search-browse §6.1): ACCEPTED only; FTS keyword + handed-in tag-set filter (compose AND); **neutral order only** (`SearchRank`/`accepted_at`/`id` — no purchasable key, AC5/M5); constant query count per page at any catalogue size (no N+1, AC9); a valid empty page is never an error, a DB failure is loud — `apps/catalog/selectors.py`
- `CatalogPage` — frozen DTO: `apps: list[CatalogApp]` (the page, in final order) + `total`/`page`/`page_size`/`has_next` — `apps/catalog/selectors.py`
- `services._search_vector_expr() -> SearchVector` — the **single definition** of the catalogue FTS formula (name weight A + description weight B); reused by `submit_app`/`edit_app` maintenance and the backfill migration so the field list lives in one place (open-search-browse §5b/§8) — `apps/catalog/services.py`
- `App.accepted_at` (nullable; newest-first browse-order key, stamped only in `accept_app`) + `App.search_vector` (nullable `SearchVectorField`, maintained only in `submit_app`/`edit_app`); composite index `(status, -accepted_at)` + `search_vector` GIN — additive open-search-browse columns, written only via the catalog write path (no drift) — `apps/catalog/models.py`
- `time_to_decision(app)` / `decision_latencies()` — time-to-decision reporting from stored timestamps (observable, not an SLA) — `apps/catalog/selectors.py`

### Behavioral signals — model & vocabulary (`apps/signals/`, the D-7 event schema)
- `Impression` — one shown instance; UUID `id` is the anchor every conversion attributes to; soft `app_id`, `surface`, `occurred_at` — `apps/signals/models.py`
- `ImpressionTag` — the **frozen** capture-time `Tag.id` snapshot (soft ref, D-5; never re-derived) — `apps/signals/models.py`
- `EngagementEvent` — one downstream act in a single uniform table; `kind` discriminator, optional `impression`, `is_proxy` — `apps/signals/models.py`
- `PlatformVisit` — one per-user-per-UTC-day return tick (the AC4 returns-derivation substrate) — `apps/signals/models.py`
- `EventKind` / `Surface` — the closed, code-fixed event-kind + surface vocabularies (no free-text) — `apps/signals/kinds.py`

### Behavioral signals — capture write surface (`apps/signals/capture.py`, the single write path — D-7)
- `record_impression(user, app_id, *, surface, occurred_at=None)` — anchor + frozen tag snapshot in one txn (AC1/AC2) — `apps/signals/capture.py`
- `record_click_through(user, app_id, *, impression, occurred_at=None)` — conversion, impression **required** (AC3) — `apps/signals/capture.py`
- `record_subscribe` / `record_page_reengagement` / `record_share(user, app_id, *, impression=None, …)` — engagement acts, impression optional (AC5/AC6) — `apps/signals/capture.py`
- `record_off_platform_proxy(user, app_id, *, impression, …)` — the flagged **secondary** seam, service-set `is_proxy=True` (AC7/§8) — `apps/signals/capture.py`
- `record_platform_visit(user, *, on_date=None)` — idempotent per-user-per-day return substrate (AC4) — `apps/signals/capture.py`
- `UnknownAppError` / `ImpressionMismatchError` — loud capture-boundary failures (never silent, AC11) — `apps/signals/errors.py`
- `PlatformVisitMiddleware` — authenticated request → idempotent daily visit; fail-soft-but-counted (§5d) — `apps/signals/middleware.py`

### Behavioral signals — read surface (`apps/signals/selectors.py`, the single read path — D-7)
- `AppFunnel` — the raw per-app funnel DTO (counts + derived returns; **no score/weight/rank field**, AC9) — `apps/signals/selectors.py`
- `app_funnel(app_id, *, start, end) -> AppFunnel` — per-app raw funnel; returns **derived** at read, no backfill (AC8/SC-9) — `apps/signals/selectors.py`
- `funnel_for_apps(app_ids, *, start, end) -> list[AppFunnel]` — bulk, two grouped queries, no N+1 (AC9) — `apps/signals/selectors.py`
- `category_impressions(tag_id, *, start, end) -> int` — per-category impression baseline from the frozen snapshot (AC2) — `apps/signals/selectors.py`
- `has_impression(user_id, app_id, *, surfaces, as_of=None) -> bool` — factual per-user-per-app existence read (raw, never judged); the ratings curated-gate evidence (additive D-7 read, ratings DESIGN §5d) — `apps/signals/selectors.py`
- `TrendGranularity` (`DAY`/`WEEK`/`MONTH`) — time-bucket grain for `impression_trend`; maps to UTC `Trunc{Day,Week,Month}` (developer-dashboard DESIGN §5.1) — `apps/signals/selectors.py`
- `ImpressionBreakdown` / `ImpressionBucket` — frozen DTOs: per-`Surface` impression counts (every `Surface` value zero-filled) for a window / a time bucket — `apps/signals/selectors.py`
- `impression_breakdown(app_id, *, start, end) -> ImpressionBreakdown` — per-`Surface` reach over a window in ONE grouped query; `total == app_funnel(...).impressions` (invariant); signals stays **neutral** (never judges "curated") (additive D-7 read, developer-dashboard §5.1) — `apps/signals/selectors.py`
- `impression_breakdown_for_apps(app_ids, *, start, end) -> dict[UUID, ImpressionBreakdown]` — bulk per-`Surface` breakdown for K apps in ONE grouped query, no N+1 (AC9) — `apps/signals/selectors.py`
- `impression_trend(app_id, *, start, end, granularity) -> list[ImpressionBucket]` — per-`Surface` impressions bucketed by `granularity`, **sparse** ascending (caller densifies); ONE grouped query, bounded by the window's granularity (AC10/M6) — `apps/signals/selectors.py`

### Behavioral signals — configuration & metrics
- `return_window_short_days()` / `return_window_long_days()` — return-to-platform windows (defaults 3 / 14) — `apps/core/config.py`
- signals metric constants (`IMPRESSION_CAPTURED`, `CLICK_THROUGH_CAPTURED`, `SUBSCRIBE_CAPTURED`, `PAGE_REENGAGEMENT_CAPTURED`, `SHARE_CAPTURED`, `PLATFORM_VISIT_CAPTURED`, `OFF_PLATFORM_PROXY_CAPTURED`, `CAPTURE_ERROR`) — `apps/core/observability.py`
- `Surface.APP_PAGE` — the app-page impression surface (app-pages additive extension, DESIGN §11) — `apps/signals/kinds.py`

### Public app pages (`apps/pages/`, a pure D-6/D-7 consumer — owns no model)
- `emission.record_page_view(request, app_id) -> UUID | None` / `record_try_click(request, app_id, imp)` / `record_share(request, app_id, imp)` — the **surface-side non-blocking** capture wrapper: authenticated-only (AP-4), fail-soft-but-counted (AC7), never raises into the request — `apps/pages/emission.py`
- route names `pages:app-page` / `pages:try` / `pages:share` — the public page, try-it redirect, and share endpoint, keyed on `App.id` (AP-5) — `apps/pages/urls.py`
- app-pages metric constants (`APP_PAGE_RENDERED`, `APP_PAGE_NOT_AVAILABLE`, `APP_PAGE_CAPTURE_DEGRADED`) — `apps/core/observability.py`

### Ratings & reviews (`apps/ratings/`, owns one mutable table `ratings_rating`)
- `Rating` / `EligibilityBasis` — one editable rating per user×app + the recorded curated-gate determination; **no score/weight/rank/average column** (AC6) — `apps/ratings/models.py`
- `gate.determine_eligibility(user, app_id, *, as_of) -> EligibilityDetermination` / `gate.CURATED_SURFACES` — the curated-rating gate; `CURATED_SURFACES` is the single source of the D-8 definition; fails closed + loud — `apps/ratings/gate.py`
- `services.submit_rating` / `services.remove_rating` — the single write path (atomic, boundary-validated, gate stamped every write) — `apps/ratings/services.py`
- `UnknownAppError` / `RatingValidationError` — loud write-boundary failures (→ view 404 / message) — `apps/ratings/errors.py`
- `selectors.reviews_for_app(app_id, *, limit) -> AppReviews` / `selectors.user_rating(user, app_id) -> Rating | None` — the single display read (count + raw distribution, **no average**; all ratings shown) — `apps/ratings/selectors.py`
- route names `ratings:submit` / `ratings:remove` — POST + `login_required`; keyed on user + `App.id` (no rating id → no IDOR) — `apps/ratings/urls.py`
- `{% app_reviews app %}` (`ratings_tags`) — the AP-1 reviews-slot inclusion tag; fail-soft (degrades, never 500s the page) — `apps/ratings/templatetags/ratings_tags.py`
- ratings config tunables `rating_scale_max()` (5) / `review_text_max_length()` (4000) / `reviews_display_limit()` (20) — `apps/core/config.py`
- ratings metric constants (`RATING_SUBMITTED`, `RATING_UPDATED`, `RATING_REMOVED`, `RATING_REJECTED`, `RATING_GATE_UNVERIFIED`, `RATING_DISPLAY_DEGRADED`) — `apps/core/observability.py`

### App subscriptions (`apps/subscriptions/`, owns one mutable table `subscriptions_subscription`)
- `Subscription` — one current follow per user×app; **no score/updated_at/soft-delete column** (AC5); `user` FK **CASCADE** (the AS-5/AC9 contrast with ratings' SET_NULL) — `apps/subscriptions/models.py`
- `services.follow_app(user, app_id) -> bool` / `services.unfollow_app(user, app_id) -> bool` — the single write path; the **only** module importing `signals.capture`; follow row + its one `subscribe` emit in **one `transaction.atomic()`** (M5 1:1 by construction); unfollow is hard-delete, no corpus event (OQ-3) — `apps/subscriptions/services.py`
- `UnknownAppError` — loud write-boundary failure (→ view 404) — `apps/subscriptions/errors.py`
- `selectors.is_following(user, app_id) -> bool` / `selectors.followed_apps(user, *, limit) -> list[CatalogApp]` — the single read path (bulk D-6 resolve, accepted-only, no N+1) — `apps/subscriptions/selectors.py`
- `notices.Notice` (frozen DTO) / `notices.notices_for_apps(ids) -> list[Notice]` — the **empty-until-producer** feed-notice seam (AS-3=A); returns `[]` today, **the one place to repoint** when `developer-updates` ships — `apps/subscriptions/notices.py`
- route names `subscriptions:follow` / `subscriptions:unfollow` / `subscriptions:feed` — POST mutations + GET feed; `login_required`; keyed on user + `App.id` (no subscription id → no IDOR) — `apps/subscriptions/urls.py`
- `{% app_follow app %}` (`subscriptions_tags`) — the Follow-slot inclusion tag; fail-soft (degrades, never 500s the page) — `apps/subscriptions/templatetags/subscriptions_tags.py`
- subscriptions config tunable `followed_feed_page_size()` (100) — the feed cap — `apps/core/config.py`
- subscriptions metric constants (`SUBSCRIPTION_FOLLOWED`, `SUBSCRIPTION_UNFOLLOWED`, `SUBSCRIPTION_FOLLOW_NOOP`, `SUBSCRIPTION_FEED_DEGRADED`, `SUBSCRIPTION_NOTICE_DEGRADED`, `SUBSCRIPTION_CONTROL_DEGRADED`); the M5 alert reuses signals `CAPTURE_ERROR{kind=subscribe}` — `apps/core/observability.py`

### Interest profile (`apps/interests/`, owns one mutable table `interests_interest`)
- `Interest` — one declared tag per user×tag; **no score/updated_at/soft-delete column** (AC8); **no parent profile row** (empty = structural default, AC6); `user` FK **CASCADE** (AC9, no `accounts` edit) — `apps/interests/models.py`
- `selectors.declared_tag_ids(user) -> frozenset[UUID]` — **the future-matcher read contract** (AC8): resolved current `Tag.id`s, deduped; a no-successor retired ref resolves to itself and stays (AC7) — `apps/interests/selectors.py`
- `selectors.declared_tags(user) -> list[Tag]` (resolved, label-ordered, display) / `selectors.has_declared_interests(user) -> bool` (drives the nudge) / `selectors.count_unresolvable() -> int` (M5 ops invariant, 0 by construction; reuses taxonomy `TAXONOMY_REFERENCE_BREAK`) — `apps/interests/selectors.py`
- `services.set_interests(user, tag_ids) -> SetResult` / `services.clear_interests(user) -> int` — the single write path; all-or-nothing `is_valid_tag` validation (AC2) + the §7 set-replace **preserve-on-edit** reconcile (AC4 × AC7); **does NOT import `signals.capture`** (IP-5, no D-7 emit) — `apps/interests/services.py`
- `InterestValidationError` — loud write-boundary failure (→ view re-render + 400) — `apps/interests/errors.py`
- route names `interests:picker` / `interests:save` / `interests:clear` — GET picker + POST mutations; `login_required`; keyed on `request.user` + `tag_id` (no interest id → no IDOR) — `apps/interests/urls.py`
- `{% interest_prompt %}` (`interests_tags`) — the onboarding-nudge inclusion tag on `accounts/profile.html`; fail-soft, non-gating (AC3) — `apps/interests/templatetags/interests_tags.py`
- interests config tunables `interest_suggested_minimum()` (3, copy-only nudge) / `interest_declaration_max()` (500, defensive cap) — `apps/core/config.py`
- interests metric constants (`INTEREST_DECLARED`, `INTEREST_PROFILE_UPDATED`, `INTEREST_PROFILE_CLEARED`, `INTEREST_DECLARATION_REJECTED`, `INTEREST_PICKER_DEGRADED`, `INTEREST_PROMPT_DEGRADED`); the M5 alert reuses taxonomy `TAXONOMY_REFERENCE_BREAK` — `apps/core/observability.py`

### Open discovery surface (`apps/discovery/`, a pure D-5/D-6 read consumer — owns no model)
- route name `discovery:browse` (`/discover/`) — GET, **AllowAny (no `login_required`, AC8)**: browse (newest-accepted-first) / keyword search / single-axis tag|cluster filter over the accepted catalogue, rendered via `catalogue.html`; **imports nothing from `signals`** (AC6 structural — a self-driven view never confers curated eligibility) — `apps/discovery/urls.py`, `apps/discovery/views.py`
- failure split: the core `search_catalogue` read fails **loud** (→ 500 + `DISCOVERY_LISTING_DEGRADED`, never a fake empty state); the facet sidebar fails **soft** (results render + `DISCOVERY_FACETS_DEGRADED`); invalid/retired/unknown `tag`/`cluster` is ignored, not an error (AC3) — `apps/discovery/views.py`
- discovery config tunables `discovery_page_size()` (24) / `discovery_page_size_max()` (100) / `discovery_query_max_length()` (200) — `apps/core/config.py`
- discovery metric constants (`DISCOVERY_BROWSE_RENDERED`, `DISCOVERY_SEARCH_PERFORMED`, `DISCOVERY_TAG_FILTERED`, `DISCOVERY_ZERO_RESULTS` = M3, `DISCOVERY_FACETS_DEGRADED`, `DISCOVERY_LISTING_DEGRADED` = the one alert); **no D-7 emit** (M2 click-through derived from app-pages' `APP_PAGE` impressions) — `apps/core/observability.py`

### Developer dashboard (`apps/dashboard/`, a pure D-3/D-6/D-7/D-8 read consumer — owns no model)
- route names `dashboard:my-apps` (`/dashboard/`) + `dashboard:app` (`/dashboard/apps/<uuid>/`) — GET-only, `login_required` + `require_role(developer)`; a read-only owner-scoped view of an accepted app's reception; **imports nothing from `signals.capture`** (AC8 structural — viewing emits no D-7 impression, AST-enforced in `tests/test_imports.py`) — `apps/dashboard/urls.py`, `apps/dashboard/views.py`
- `reception.build_my_apps_summaries(owner, *, window) -> list[ReceptionSummary]` / `reception.build_app_reception(owner, app_id, *, window) -> AppReception | None` — the composition layer: bounded my-apps list (no N+1, AC9) + the per-app reach/funnel/reviews assembly; owner-scope ⇒ `None` (→404); curated-first via `ratings.gate.CURATED_SURFACES`; trend densified onto a continuous axis — `apps/dashboard/reception.py`
- failure split: the core reception (signals) read **fails loud** (→500 + `DASHBOARD_RECEPTION_DEGRADED`, the one alert, never a fake-empty page); the reviews slot **fails soft** (`DASHBOARD_REVIEWS_DEGRADED`, stays 200) — `apps/dashboard/views.py`, `apps/dashboard/reception.py`
- **additive off-platform widget slot (embeddable-update-widget AC9 + widget-conversion-attribution AC3):** `reception.WidgetReachView` (now reach **+ the conversion funnel stage**: `follows`/`accounts`/`conversions_total` + the derived M2 rate) + `ReceptionSummary.widget_impressions` (Screen A stays reach-only) / `AppReception.widget_reach`, read via `widget.selectors` (`widget_reach` **and** `widget_conversions` together on Screen B + one bulk `widget_reach_for_apps` on Screen A, no N+1); the whole slot **fails soft together** (`available=False` / column→0 + `DASHBOARD_WIDGET_DEGRADED`) — the cross-app edge `dashboard → widget`; labeled off-platform, distinct from the per-`Surface` breakdown — `apps/dashboard/reception.py`
- `windows.REPORTING_WINDOWS` (the fixed 8: 1w/2w/1m/3m/6m/1y/3y/all + per-window `TrendGranularity`) + `windows.resolve_window(key, *, now) -> ResolvedWindow` (fail-safe: unknown/blank → `DEFAULT_WINDOW_KEY`, never raises, AC7) — a **code-fixed table, no `config` entry** — `apps/dashboard/windows.py`
- `charts.build_sparkline(buckets) -> SparklineSvg | None` — pure inline-SVG polyline geometry (total + curated line), stdlib only, no app imports, no JS; `None` for an empty/all-zero window — `apps/dashboard/charts.py`
- dashboard metric constants (`DASHBOARD_MY_APPS_VIEWED`, `DASHBOARD_RECEPTION_VIEWED`, `DASHBOARD_ACCESS_DENIED`, `DASHBOARD_RECEPTION_DEGRADED` = the one alert, `DASHBOARD_REVIEWS_DEGRADED`, `DASHBOARD_NONEMPTY_RECEPTION` = M3) — `apps/core/observability.py`

### Developer updates (`apps/updates/`, the single **AS-3 producer** — owns the `updates_notice` table)
- route names `updates:my-channels` (`/updates/`) + `updates:channel` (`/updates/apps/<uuid>/`) + `updates:post` (POST) + `updates:withdraw` (POST `…/notices/<uuid>/withdraw`) — all `login_required` + `require_role(developer)` (D-3); mutations POST+CSRF, addressed by `request.user`+`app_id`(+scoped `notice_id`) ⇒ no IDOR; non-owner id ⇒ 404 indistinguishable (D-6); **imports nothing from `signals`** (AC6 structural — posting is inert to the corpus, AST-enforced in `tests/test_imports.py`) — `apps/updates/urls.py`, `apps/updates/views.py`, `apps/updates/tests/test_imports.py`
- `updates.selectors.published_notices_for_apps(app_ids, *, limit) -> list[PublishedNotice]` (the AS-3 producer feed read — 1 query, `limit`-bounded, follower-count-independent, R3) + `notices_for_channel(owner, app_id) -> list[PublishedNotice]` (the AC7 owner manage list); returns the frozen `PublishedNotice` DTO (`PublishedNotice.from_model` is the single model→DTO map), never ORM rows — `apps/updates/selectors.py`
- `updates.services.post_notice(author, app_id, *, kind, title, summary) -> PublishedNotice` / `withdraw_notice(author, app_id, notice_id) -> bool` — the **only** writer of `updates_notice`: owner-gate (`AppNotOwnedError`→404), boundary validation (`InvalidNoticeError`), durable table-derived rate limit (`RateLimitedError`, AC8); withdraw = scoped idempotent hard delete — `apps/updates/services.py`, `apps/updates/errors.py`
- `updates.models.Notice` / table `updates_notice` (soft D-6 `app_id` ref, `author` FK CASCADE, `kind`∈{update,early_access}, `title`/`summary`/`published_at`; **no** score/`updated_at`/`withdrawn_at`; index `updates_app_published_idx` on `(app_id, published_at)`) — `apps/updates/models.py`
- **AS-3 seam repoint (the single adapter, DU-DESIGN-2):** `subscriptions.notices.notices_for_apps(app_ids)` now delegates to `updates.selectors` and maps `PublishedNotice → Notice` (drops `id`); the render `Notice` DTO + its one call site (`subscriptions.views._notices_fail_soft`) are unchanged; feed health reuses `SUBSCRIPTION_NOTICE_DEGRADED`. The two-package dependency stays a DAG with no import cycle (proven in `apps/updates/tests/test_seam.py`) — `apps/subscriptions/notices.py`
- **additive reverse-audience read on the closed `apps/subscriptions/`:** `subscriptions.selectors.subscriber_count(app_id) -> int` (1 indexed COUNT — backs the post-form audience hint + M2) + the additive `subscriptions_app_idx` index on `subscriptions_subscription(app_id)` (`0002`; no new column, no behaviour change) — `apps/subscriptions/selectors.py`, `apps/subscriptions/models.py`
- updates config tunables `updates_feed_notice_limit()` (50) / `updates_max_posts_per_window()` (5) / `updates_post_window_hours()` (24) / `updates_title_max_length()` (120) / `updates_summary_max_length()` (4000) — `apps/core/config.py`
- updates metric constants (`UPDATES_NOTICE_POSTED{kind}` = M1, `UPDATES_NOTICE_WITHDRAWN`, `UPDATES_POST_REJECTED{reason}` = M6 trend, `UPDATES_POST_FAILED` = the one alert, `UPDATES_CHANNEL_DEGRADED`, `UPDATES_AUDIENCE_DEGRADED`); feed health reuses `SUBSCRIPTION_NOTICE_DEGRADED`; M5 (reach beyond followers = 0) is structural, no counter — `apps/core/observability.py`

### Embeddable update widget (`apps/widget/`, owns the `widget_reach_count` table)
- route names `widget:render` (`GET /widget/<uuid>/`) + `widget:view` (`GET /widget/<uuid>/view`) — **AllowAny** anonymous public reads (AC5); render is per-IP rate-limited (AC8) + `@xframe_options_exempt` + `Cache-Control` and counts one impression fail-soft; `/view` counts one click-through fail-soft then 302s to `reverse("pages:app-page", [app_id])` (server-derived, no open redirect, F4); unknown/non-accepted id → neutral `unavailable.html`; **imports nothing from `apps.signals`** (AC6 firewall = structural by absence, AST-enforced in `tests/test_imports.py`) — `apps/widget/urls.py`, `apps/widget/views.py`, `apps/widget/tests/test_imports.py`
- `widget.rollup._increment_daily(model, app_id, kind)` — the **one** concurrency-correct daily-rollup increment, **shared by both** the reach writer and the conversion writer (atomic per-day `F("count")+1` + unique-constraint create-race retry via a nested savepoint, EUW-IMPL-1); parameterized by the rollup model class; imports no `signals` — `apps/widget/rollup.py`
- `widget.attribution.record_widget_impression(app_id)` / `record_widget_click_through(app_id)` — the **single writer** of `widget_reach_count`; `record_widget_conversion(app_id, kind)` — the **single writer** of `widget_conversion_count` (the credited *source* app; `kind`∈`WidgetConversionKind`). All three delegate to `rollup._increment_daily`; trust a caller-validated `app_id` (the view / the signed marker's `src`), raise on DB error (caller wraps fail-soft) — `apps/widget/attribution.py`
- `widget.source` — the **only** module that knows the `widget_src` cookie format (widget-conversion-attribution DESIGN §3/§5.1): `set_marker(response, source_app_id)` arms a first-party signed source-only cookie on the click 302; `attribute_follow(request, response, *, followed_app_id)` / `attribute_account(request, response)` decode it, enforce the window + per-marker `credited`-set dedup (R4), and call `record_widget_conversion` on a credit (re-issuing the cookie with the remaining window). Payload = `{v, src, credited}` (no person field — AC4); a missing/tampered/expired/wrong-app marker is a no-op + `WIDGET_CONVERSION_{NO_SOURCE,EXPIRED}`; a DB error propagates (caller fail-soft); imports no `signals` — `apps/widget/source.py`
- `widget.selectors.widget_reach(app_id, *, start, end) -> WidgetReach` / `widget_reach_for_apps(…) -> dict[UUID, WidgetReach]` (frozen `WidgetReach{impressions, click_throughs}`) **and** `widget_conversions(app_id, *, start, end) -> WidgetConversion` / `widget_conversions_for_apps(…) -> dict[UUID, WidgetConversion]` (frozen `WidgetConversion{follows, accounts}`) — the **single readers**; each one grouped `SUM…GROUP BY` over the window's UTC-day range, zero-filled, no N+1; both rates (click-through, M2 conversion) are derived at display, not stored — `apps/widget/selectors.py`
- `widget.content.build_widget_view(app_id) -> WidgetView | None` — the pure render assembler (`WidgetView{app_name, app_page_path, notices, notices_degraded}` + `WidgetNotice`); reads `updates.selectors.published_notices_for_apps` (capped at `widget_notice_limit()`, newest-first, fail-soft → `notices_degraded`) + `catalog.get_catalogued_app` (D-6 gate → `None`) + `reverse("pages:app-page")` — `apps/widget/content.py`
- `widget.models.WidgetReachCount` / table `widget_reach_count` (`kind`∈{impression,click_through}; unique `widget_reach_count_unique` + index `widget_reach_app_kind_date_idx`) and `widget.models.WidgetConversionCount` / table `widget_conversion_count` (the credited *source* `app_id`; `kind`∈{follow,account}; unique `widget_conversion_count_unique` + index `widget_conv_app_kind_date_idx`) — both: soft D-6 `app_id` ref, `count_date`/`count`, **no** `user`/IP/referrer/score column (AC4/AC6 structural). `widget.kinds.WidgetEventKind` + `WidgetConversionKind` (disjoint vocabularies) — `apps/widget/models.py`, `apps/widget/kinds.py`
- widget config tunables `widget_notice_limit()` (5) / `widget_render_rate_limit_per_ip_per_minute()` (60) / `widget_cache_max_age_seconds()` (60) / `widget_attribution_window_days()` (30 — the last-touch attribution window, WCA-2) — `apps/core/config.py`
- widget metric constants (`WIDGET_RENDERED` = M4, `WIDGET_EMPTY`, `WIDGET_CLICK_THROUGH` = M2, `WIDGET_NOT_AVAILABLE`, `WIDGET_RATE_LIMITED` = AC8, `WIDGET_NOTICES_DEGRADED`, `WIDGET_RENDER_DEGRADED`, `WIDGET_COUNT_DEGRADED` = the one reach alert, `WIDGET_LIMITER_DEGRADED`, `DASHBOARD_WIDGET_DEGRADED`) + conversion metrics (`WIDGET_CONVERSION_ATTRIBUTED` = M1 tagged `kind`, `WIDGET_CONVERSION_NO_SOURCE` / `_EXPIRED` = M3 coverage, `WIDGET_CONVERSION_DEGRADED` = the one conversion alert/M6); M4/M5 (firewall=0, PII fields=0) are structural, no counter — `apps/core/observability.py`
- **conversion hooks** (the only `→ widget` edges besides dashboard): `subscriptions.views.follow` credits a follow conversion fail-soft on a genuinely **new** follow (`created=True`); `accounts.views.register` credits an account conversion fail-soft on the **202** new-account path only — each a one-line `widget.source` call wrapped in a `_attribute_*` try/except (`WIDGET_CONVERSION_DEGRADED`); the conversion's own `record_subscribe` corpus event + the created account are untouched (AC5/AC6) — `apps/subscriptions/views.py`, `apps/accounts/views.py`

<!-- Example of the shape this takes once code exists:

### Utilities
- `formatRelativeDate(date) -> string` — "3d ago" style relative time — `shared/date.ts`
- `slugify(text) -> string` — URL-safe slug from arbitrary text — `shared/text.ts`

### Domain types
- `QualityScore` — canonical quality-score shape — `shared/ranking/types.ts`

### Services
- `fetchCatalog(niche) -> Catalog` — cached catalog read — `shared/catalog/service.ts`
-->

## Maintenance rules

- **The Engineer (Stage 4) keeps this current** — it is part of definition-of-done.
  Adding or changing shared code without updating this index is an incomplete task.
- **A stale index is worse than none.** Keep it to the shared surface only, so it stays
  small enough to trust.
- **The Retrospective Analyst (Stage 6) reconciles it against reality** at feature close,
  removing entries for deleted code and adding any shared helper that slipped through.
- When this file grows beyond comfortable reading, **partition it by area** (one map per
  top-level package) and keep this file as the index of indexes — mirroring how
  `features/` scales by folder.
