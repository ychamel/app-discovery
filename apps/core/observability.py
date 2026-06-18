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
