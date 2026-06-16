"""Config-driven request rate limiting for the auth-request endpoints.

Mitigates email/link bombing and backs the `429` contract (DESIGN.md §5 #1/#2,
§10). Two independent fixed windows are enforced per request: one keyed by the
submitted email address, one by the client IP. Limits come from `core.config`
(never hardcoded); the window is one hour.

Counts live in Django's cache. The default LocMemCache is per-process — fine for
dev and a single worker. **In production set CACHES to a shared backend (e.g.
Redis)** so the limit holds across workers; this is ops configuration, recorded in
the deploy runbook.
"""

from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from apps.core import config

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


def _exceeds_limit(key: str, limit: int) -> bool:
    """Record one hit against ``key`` and report whether it broke the limit.

    ``cache.add`` seeds the counter (and its expiry) only on the first hit, so the
    window is fixed from that first request; ``incr`` then counts within it.
    """
    cache.add(key, 0, timeout=_WINDOW_SECONDS)
    try:
        count = cache.incr(key)
    except ValueError:
        # The seed expired between add and incr — start a fresh window.
        cache.set(key, 1, timeout=_WINDOW_SECONDS)
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
