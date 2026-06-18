"""PlatformVisit middleware — the return-to-platform substrate (DESIGN.md §3/§5d/§12).

Turns an **authenticated** request into an idempotent daily visit so the read path can
derive returns_3d/14d (AC4). It does exactly one job — record the visit — and delegates
all write logic to ``capture.record_platform_visit`` (no ORM here).

**Non-blocking, fail-soft-but-counted (§5d).** An anonymous request records nothing. A
capture failure is already counted + logged loudly by ``capture`` (capture_error{kind=
visit}); here we additionally swallow it so a missed visit-day never breaks the user's
page navigation. A single missed day marginally under-counts returns, which the metric
surfaces — unlike the corpus-critical impression path, a retention tick is safe to lose
visibly rather than fail the request.

Registered in ``MIDDLEWARE`` after ``AuthenticationMiddleware`` (so ``request.user`` is
resolved) and ``RequestContextMiddleware`` (so the failure log carries request context).
"""

import logging

from apps.signals import capture

logger = logging.getLogger(__name__)


class PlatformVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._record_visit(request)
        return self.get_response(request)

    def _record_visit(self, request) -> None:
        """Record today's visit for an authenticated user; never break the request (§5d)."""
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return
        try:
            capture.record_platform_visit(user)
        except Exception:
            # capture already counted capture_error{kind=visit} + logged loudly; the visit
            # tick is fail-soft, so navigation continues uninterrupted (§5d).
            logger.debug("platform-visit capture failed; continuing (fail-soft)")
