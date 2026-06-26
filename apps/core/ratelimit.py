"""Config-driven fixed-window rate limiting (DESIGN.md §5 #1/#2, §10).

Two limiters share one fixed-window mechanism (the counter + expiry logic in
``_exceeds_limit``, generalized by its window):

  * ``rate_limited`` — the auth-request guard. Counts only *write* requests (form
    submissions), per submitted email and per client IP, in a one-hour window.
  * ``ip_rate_limited_get`` — a per-IP **GET** guard for public reads (the
    embeddable-update-widget render, AC8). It is the sibling of ``rate_limited``:
    the same window mechanism applied to GETs, with a config-driven limit, a
    short window, and **fail-open** on a cache outage (a cache failure must never
    take down a public read — embeddable-update-widget DESIGN §8).

Limits come from ``core.config`` (never hardcoded). Counts live in Django's cache;
the default LocMemCache is per-process — fine for dev and a single worker. **In
production set CACHES to a shared backend (e.g. Redis)** so the limit holds across
workers; this is ops configuration, recorded in the deploy runbook.
"""

from collections.abc import Callable
from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from apps.core import config, observability

_WINDOW_SECONDS = 3600  # one hour, matching the "per hour" limits in DESIGN.md §10


def _client_ip(request: HttpRequest) -> str:
    """Best-effort client IP, honoring a single proxy hop via X-Forwarded-For."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _submitted_email(request: HttpRequest) -> str | None:
    """Normalized email from the request body, or None if absent."""
    data = getattr(request, "data", None)
    if data is None:
        data = getattr(request, "POST", {})
    email = data.get("email") if hasattr(data, "get") else None
    return (email or "").strip().lower() or None


def _exceeds_limit(key: str, limit: int, *, window_seconds: int = _WINDOW_SECONDS) -> bool:
    """Record one hit against ``key`` and report whether it broke the limit.

    ``cache.add`` seeds the counter (and its expiry) only on the first hit, so the
    window is fixed from that first request; ``incr`` then counts within it.
    ``window_seconds`` defaults to the one-hour auth window; the GET limiter passes
    its own (shorter) window — the single parameter that generalizes this internal.
    """
    cache.add(key, 0, timeout=window_seconds)
    try:
        count = cache.incr(key)
    except ValueError:
        # The seed expired between add and incr — start a fresh window.
        cache.set(key, 1, timeout=window_seconds)
        count = 1
    return count > limit


def _too_many_requests() -> HttpResponse:
    return HttpResponse("Too many requests. Please wait and try again.", status=429)


def rate_limited(view):
    """Enforce the per-IP and per-email hourly limits before running ``view``.

    Under the limits this is a no-op pass-through; over either limit it short-
    circuits with `429` and never calls the wrapped view.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        # Only auth *requests* (form submissions) count — not viewing the page.
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return view(request, *args, **kwargs)

        ip = _client_ip(request)
        if _exceeds_limit(f"ratelimit:ip:{ip}", config.rate_limit_per_ip_per_hour()):
            return _too_many_requests()

        email = _submitted_email(request)
        if email and _exceeds_limit(
            f"ratelimit:email:{email}", config.rate_limit_per_email_per_hour()
        ):
            return _too_many_requests()

        return view(request, *args, **kwargs)

    return wrapper


def ip_rate_limited_get(
    limit_fn: Callable[[], int],
    *,
    scope: str,
    window_seconds: int = 60,
    limited_metric: str | None = None,
    degraded_metric: str | None = None,
):
    """Per-IP fixed-window limit on a **GET** view — the public-read sibling of ``rate_limited``.

    ``limit_fn`` is a ``core.config`` callable resolving the per-window limit (never hardcoded);
    ``scope`` namespaces the cache key so this counter never collides with the auth IP limit (or
    another GET limiter). Only GET/HEAD are limited — other methods pass straight through so the
    wrapped view's own method gate (e.g. ``require_GET`` → 405) still applies.

    Outcomes (embeddable-update-widget DESIGN §8):
      * under the limit → the view runs unchanged;
      * over the limit → ``429``, the view is **never called** (no render, no side effect), and
        ``limited_metric`` is counted if given;
      * a cache backend error → **fail open** (the view runs) and ``degraded_metric`` is counted
        — availability of a public read beats strict limiting during a cache outage.

    The metric *names* are injected by the caller (this stays a generic ``core`` helper that
    knows no feature's vocabulary); the widget view passes its ``WIDGET_*`` constants.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request.method not in ("GET", "HEAD"):
                return view(request, *args, **kwargs)

            key = f"ratelimit:{scope}:ip:{_client_ip(request)}"
            try:
                exceeded = _exceeds_limit(key, limit_fn(), window_seconds=window_seconds)
            except Exception:
                # The cache is unavailable — fail open rather than 500 a public read.
                if degraded_metric:
                    observability.increment(degraded_metric)
                return view(request, *args, **kwargs)

            if exceeded:
                if limited_metric:
                    observability.increment(limited_metric)
                return _too_many_requests()

            return view(request, *args, **kwargs)

        return wrapper

    return decorator
