"""Typed, validated access to the application's runtime tunables.

This is the single source of truth for values DESIGN.md (§5, §10) requires to be
configurable rather than hardcoded: the magic-link token lifetime and the
auth-request rate limits.

Resolution precedence for each tunable (most specific wins):

    1. An explicit Django setting  (used by tests via ``override_settings`` and by
       operators who prefer settings)
    2. The corresponding environment variable
    3. The documented default below

A misconfigured value (non-numeric, zero, negative) raises ``ImproperlyConfigured``
**loudly at startup** — see ``CoreConfig.ready`` — never silently at point of use.
"""

import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# --- Documented defaults (one literal per tunable; DESIGN.md §5/§10) ----------
DEFAULT_LOGIN_TOKEN_TTL_SECONDS = 15 * 60  # 15 minutes
DEFAULT_RATE_LIMIT_PER_EMAIL_PER_HOUR = 5
DEFAULT_RATE_LIMIT_PER_IP_PER_HOUR = 20
# Max replaced_by successor hops resolve_tag will follow before declaring a
# cycle/over-long chain (interest-taxonomy DESIGN.md §5a/§10). A handful of merges is
# realistic; anything beyond this is treated as corrupt data, not a longer chain.
DEFAULT_TAXONOMY_RESOLVE_MAX_STEPS = 16
# Per-app screenshot/media bounds (submission-intake DESIGN.md §9, resolves OQ-3). The
# count cap and the per-file byte ceiling are the published contract `app-pages` adopts.
DEFAULT_CATALOG_MEDIA_MAX_COUNT = 8
DEFAULT_CATALOG_MEDIA_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
# Return-to-platform evaluation windows (signal-capture DESIGN.md §9). The single source
# of truth the funnel read path uses to derive returns_3d/returns_14d — so A2's "exact
# tolerance" is a one-line config change and there is no magic 3/14 in logic.
DEFAULT_RETURN_WINDOW_SHORT_DAYS = 3
DEFAULT_RETURN_WINDOW_LONG_DAYS = 14
# Ratings & reviews bounds (ratings-reviews DESIGN.md §10). The rating scale ceiling and the
# review-text length cap are validated at the write boundary; the display limit bounds the
# reviews slot render so it stays O(limit) at 100× data. No magic numbers in logic.
DEFAULT_RATING_SCALE_MAX = 5
DEFAULT_REVIEW_TEXT_MAX_LENGTH = 4000
DEFAULT_REVIEWS_DISPLAY_LIMIT = 20


def _resolve_raw(setting_name: str, env_name: str, default: int) -> object:
    """Return the configured raw value following the documented precedence."""
    if hasattr(settings, setting_name):
        return getattr(settings, setting_name)
    return os.environ.get(env_name, default)


def _positive_int(setting_name: str, env_name: str, default: int) -> int:
    """Coerce a tunable to a positive int, failing loudly on an invalid value."""
    raw = _resolve_raw(setting_name, env_name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ImproperlyConfigured(
            f"{setting_name}/{env_name} must be an integer, got {raw!r}."
        ) from None
    if value <= 0:
        raise ImproperlyConfigured(
            f"{setting_name}/{env_name} must be a positive integer, got {value}."
        )
    return value


def login_token_ttl() -> timedelta:
    """Lifetime of a magic-link login token (DESIGN.md §4/§8)."""
    seconds = _positive_int(
        "LOGIN_TOKEN_TTL_SECONDS",
        "LOGIN_TOKEN_TTL_SECONDS",
        DEFAULT_LOGIN_TOKEN_TTL_SECONDS,
    )
    return timedelta(seconds=seconds)


def rate_limit_per_email_per_hour() -> int:
    """Max auth-request emails accepted per email address per hour (DESIGN.md §10)."""
    return _positive_int(
        "RATE_LIMIT_PER_EMAIL_PER_HOUR",
        "RATE_LIMIT_PER_EMAIL_PER_HOUR",
        DEFAULT_RATE_LIMIT_PER_EMAIL_PER_HOUR,
    )


def rate_limit_per_ip_per_hour() -> int:
    """Max auth requests accepted per client IP per hour (DESIGN.md §10)."""
    return _positive_int(
        "RATE_LIMIT_PER_IP_PER_HOUR",
        "RATE_LIMIT_PER_IP_PER_HOUR",
        DEFAULT_RATE_LIMIT_PER_IP_PER_HOUR,
    )


def taxonomy_resolve_max_steps() -> int:
    """Max successor hops `resolve_tag` follows before bailing on a cycle (DESIGN.md §5a/§10)."""
    return _positive_int(
        "TAXONOMY_RESOLVE_MAX_STEPS",
        "TAXONOMY_RESOLVE_MAX_STEPS",
        DEFAULT_TAXONOMY_RESOLVE_MAX_STEPS,
    )


def catalog_media_max_count() -> int:
    """Max screenshots/images allowed per submitted app (DESIGN.md §9, OQ-3)."""
    return _positive_int(
        "CATALOG_MEDIA_MAX_COUNT",
        "CATALOG_MEDIA_MAX_COUNT",
        DEFAULT_CATALOG_MEDIA_MAX_COUNT,
    )


def catalog_media_max_bytes() -> int:
    """Max byte size accepted for one uploaded app image (DESIGN.md §9, OQ-3)."""
    return _positive_int(
        "CATALOG_MEDIA_MAX_BYTES",
        "CATALOG_MEDIA_MAX_BYTES",
        DEFAULT_CATALOG_MEDIA_MAX_BYTES,
    )


def return_window_short_days() -> int:
    """Short return-to-platform window in days (signal-capture DESIGN.md §9)."""
    return _positive_int(
        "RETURN_WINDOW_SHORT_DAYS",
        "RETURN_WINDOW_SHORT_DAYS",
        DEFAULT_RETURN_WINDOW_SHORT_DAYS,
    )


def return_window_long_days() -> int:
    """Long return-to-platform window in days (signal-capture DESIGN.md §9)."""
    return _positive_int(
        "RETURN_WINDOW_LONG_DAYS",
        "RETURN_WINDOW_LONG_DAYS",
        DEFAULT_RETURN_WINDOW_LONG_DAYS,
    )


def rating_scale_max() -> int:
    """Highest score a rating may carry; the scale is 1..this (ratings-reviews DESIGN.md §10)."""
    return _positive_int(
        "RATING_SCALE_MAX",
        "RATING_SCALE_MAX",
        DEFAULT_RATING_SCALE_MAX,
    )


def review_text_max_length() -> int:
    """Max characters accepted in a review body (ratings-reviews DESIGN.md §10)."""
    return _positive_int(
        "REVIEW_TEXT_MAX_LENGTH",
        "REVIEW_TEXT_MAX_LENGTH",
        DEFAULT_REVIEW_TEXT_MAX_LENGTH,
    )


def reviews_display_limit() -> int:
    """Max reviews rendered in the app-page reviews slot (ratings-reviews DESIGN.md §10/§9)."""
    return _positive_int(
        "REVIEWS_DISPLAY_LIMIT",
        "REVIEWS_DISPLAY_LIMIT",
        DEFAULT_REVIEWS_DISPLAY_LIMIT,
    )


def validate_all() -> None:
    """Evaluate every tunable so misconfiguration surfaces at startup, not at use."""
    login_token_ttl()
    rate_limit_per_email_per_hour()
    rate_limit_per_ip_per_hour()
    taxonomy_resolve_max_steps()
    catalog_media_max_count()
    catalog_media_max_bytes()
    return_window_short_days()
    return_window_long_days()
    rating_scale_max()
    review_text_max_length()
    reviews_display_limit()
