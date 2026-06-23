"""Observability surface: metrics, request-scoped log context, health (DESIGN.md §10).

Metrics are emitted through one tiny `increment` seam that currently writes a
structured line to the ``apps.metrics`` logger. Swap that body for StatsD/Prometheus
later — callers and metric names stay identical (design-for-change). Metric names map
1:1 to the brief's success metrics.

Request-scoped context (a request id and the acting account UUID) is carried in
context vars and injected into every log record by ``RequestContextFilter`` — so logs
are correlatable and always identify the actor by UUID, never by raw email.
"""

import logging
from contextvars import ContextVar

from django.core.mail import get_connection
from django.db import connections

# --- Metric names (1:1 with FEATURE_BRIEF success metrics) -------------------
REGISTRATION_COMPLETION = "registration_completion"
SIGNIN_SUCCESS = "signin_success"
AUTH_ERROR = "auth_error"
SIGNOUT = "signout"  # expected logout; unexpected-logout rate is derived from its absence
DEVELOPER_ROLE_ADOPTION = "developer_role_adoption"
ROLE_GATE_DECISION = "role_gate_decisions"
EMAIL_SEND_FAILURE = "email_send_failure"
DELETION_FULFILMENT = "deletion_fulfilment"
ADMIN_ROLE_CHANGE = "admin_role_change"  # alert: any admin grant/revoke

# interest-taxonomy lifecycle + safety metrics (DESIGN.md §9). The two diagnostic
# counters below must stay 0 in a healthy system — alert on any nonzero value.
TAXONOMY_TAG_ADDED = "taxonomy_tag_added"
TAXONOMY_TAG_RENAMED = "taxonomy_tag_renamed"
TAXONOMY_TAG_RETIRED = "taxonomy_tag_retired"
TAXONOMY_REFERENCE_BREAK = "taxonomy_reference_break"  # alert: resolve hit a cycle/over-long chain
TAXONOMY_INTEGRITY_VIOLATION = "taxonomy_integrity_violation"  # alert: orphan/duplicate found

# submission-intake metrics (DESIGN.md §9), 1:1 with the brief's success metrics. The
# off-vocabulary counter must stay 0 in a healthy system — alert on any nonzero value.
SUBMISSION_STARTED = "submission_started"
SUBMISSION_COMPLETED = "submission_completed"
SUBMISSION_CREATED = "submission_created"
APP_WITHDRAWN = "app_withdrawn"
APP_RESUBMITTED = "app_resubmitted"
APP_ACCEPTED = "app_accepted"
APP_REJECTED = "app_rejected"
REVIEW_DECISION = "review_decision"  # tags: outcome, and per failed criterion on reject
TAG_OFF_VOCABULARY_REJECTED = "tag_off_vocabulary_rejected"  # alert: must stay 0 (AC4)
DUPLICATE_FLAGGED = "duplicate_flagged"

# signal-capture metrics (DESIGN.md §9), 1:1 with the brief's success metrics. The
# capture-error counter must stay 0 in a healthy system — alert on any nonzero value.
IMPRESSION_CAPTURED = "impression_captured"
CLICK_THROUGH_CAPTURED = "click_through_captured"
SUBSCRIBE_CAPTURED = "subscribe_captured"
PAGE_REENGAGEMENT_CAPTURED = "page_reengagement_captured"
SHARE_CAPTURED = "share_captured"
PLATFORM_VISIT_CAPTURED = "platform_visit_captured"
OFF_PLATFORM_PROXY_CAPTURED = "off_platform_proxy_captured"  # tagged secondary (AC7)
CAPTURE_ERROR = "capture_error"  # alert: any nonzero — the AC11/R4 loud-loss signal (tags: kind)

# app-pages metrics (DESIGN.md §9). The surface's own fail-soft counter: capture is loud
# *inside* signals (capture_error), silent-but-counted *to the visitor* here (AC7).
APP_PAGE_RENDERED = "app_page_rendered"  # a page was served (tags: app_id) — coverage/view volume
APP_PAGE_NOT_AVAILABLE = "app_page_not_available"  # a non-accepted/unknown id was requested (→404)
# a page emit was caught + dropped (tags: action) — informational, not a hard alert
APP_PAGE_CAPTURE_DEGRADED = "app_page_capture_degraded"

# ratings-reviews metrics (DESIGN.md §8.4). The gate-split (RATING_SUBMITTED/_UPDATED tagged
# {weight_eligible, basis}) is the §5 share-eligible metric — expected ~all not-eligible at
# MVP until a DIGEST emitter ships (R3). The two diagnostic counters below should stay 0 in a
# healthy system — alert on any nonzero value.
RATING_SUBMITTED = "rating_submitted"  # tags: weight_eligible, basis — the gate-split metric
RATING_UPDATED = "rating_updated"  # tags: weight_eligible, basis — re-rate of an existing row
RATING_REMOVED = "rating_removed"
RATING_REJECTED = "rating_rejected"  # the AC2 boundary-rejection rate (tags: reason)
RATING_GATE_UNVERIFIED = "rating_gate_unverified"  # alert: the gate (signals) read failed
RATING_DISPLAY_DEGRADED = "rating_display_degraded"  # the reviews slot fell back (fail-soft)

# app-subscriptions metrics (DESIGN.md §9.4). Follow adoption/churn are trends; the one
# actionable alert (M5 capture integrity) is the REUSED signals CAPTURE_ERROR{kind=subscribe}
# — not re-added here. The three *_DEGRADED counters are display fail-soft health.
SUBSCRIPTION_FOLLOWED = "subscription_followed"  # M1 adoption, M2 depth — a new follow created
SUBSCRIPTION_UNFOLLOWED = "subscription_unfollowed"  # M6 unfollow rate — a follow removed
SUBSCRIPTION_FOLLOW_NOOP = "subscription_follow_noop"  # idempotent re-follow of a current follow
SUBSCRIPTION_FEED_DEGRADED = "subscription_feed_degraded"  # the feed read fell back (fail-soft)
SUBSCRIPTION_NOTICE_DEGRADED = "subscription_notice_degraded"  # the notice read fell back
SUBSCRIPTION_CONTROL_DEGRADED = "subscription_control_degraded"  # the follow slot fell back

# interest-profile metrics (DESIGN.md §12). Declaration/edit/clear are adoption trends; the
# one actionable alert is an *unexpected* set_interests write failure (a DB error, not a
# validation reject). REJECTED is expected and NOT alertable. M5 reference integrity reuses
# the taxonomy TAXONOMY_REFERENCE_BREAK counter (emitted by resolve_tag) — not re-added here.
INTEREST_DECLARED = "interest_declared"  # M1 — a save took a profile from 0 → ≥1 tag
INTEREST_PROFILE_UPDATED = "interest_profile_updated"  # M4 — a change to a non-empty profile
INTEREST_PROFILE_CLEARED = "interest_profile_cleared"  # clear_interests, or a save to empty
INTEREST_DECLARATION_REJECTED = "interest_declaration_rejected"  # AC2 reject (expected)
INTEREST_PICKER_DEGRADED = "interest_picker_degraded"  # the picker read fell back (fail-soft)
INTEREST_PROMPT_DEGRADED = "interest_prompt_degraded"  # the onboarding nudge fell back (fail-soft)

# open-search-browse metrics (DESIGN.md §11). Browse/search/tag-filter render counts are
# usage trends; ZERO_RESULTS is M3 (high rate ⇒ revisit search per OQ-OSB-4); FACETS_DEGRADED
# is informational chrome health. The one actionable alert is LISTING_DEGRADED — a core
# results read raised / the open surface 500s. No D-7 signal is emitted (AC6); M2 click-through
# is derived from app-pages' existing APP_PAGE impressions.
DISCOVERY_BROWSE_RENDERED = "discovery_browse_rendered"
DISCOVERY_SEARCH_PERFORMED = "discovery_search_performed"
DISCOVERY_TAG_FILTERED = "discovery_tag_filtered"
DISCOVERY_ZERO_RESULTS = "discovery_zero_results"  # M3 — a query/filter returned total == 0
DISCOVERY_FACETS_DEGRADED = "discovery_facets_degraded"  # the facet sidebar read fell back
DISCOVERY_LISTING_DEGRADED = "discovery_listing_degraded"  # alert: the core results read raised

metrics_logger = logging.getLogger("apps.metrics")


def increment(metric: str, **tags) -> None:
    """Record one occurrence of ``metric`` with optional tags. Never raises."""
    try:
        tag_str = " ".join(f"{key}={value}" for key, value in sorted(tags.items()))
        metrics_logger.info("metric=%s %s", metric, tag_str)
    except Exception:  # observability must never break the request path
        pass


# --- Request-scoped log context ---------------------------------------------
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
account_id_var: ContextVar[str] = ContextVar("account_id", default="-")


class RequestContextFilter(logging.Filter):
    """Inject the current request id and account UUID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.account_id = account_id_var.get()
        return True


# --- Health check ------------------------------------------------------------
def _database_ok() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def _email_ok() -> bool:
    try:
        connection = get_connection()
        connection.open()
        connection.close()
        return True
    except Exception:
        return False


def check_health() -> dict:
    """Report reachability of the dependencies this feature needs (DB + email)."""
    return {"database": _database_ok(), "email": _email_ok()}
