"""Cross-cutting core views — the health endpoints + media serving (DESIGN.md §10)."""

from django.conf import settings
from django.http import JsonResponse
from django.views.static import serve as static_serve

from apps.core.observability import _database_ok, check_health


def health(request):
    """Operator deep probe: report dependency health (DB + email). 200 when all pass, else 503.

    This opens a live SMTP connection, so it is NOT safe as an orchestrator liveness target
    (a transient provider blip would loop restarts) — use /health/live for that. See DESIGN §4.6.
    """
    checks = check_health()
    ok = all(checks.values())
    status_code = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "degraded", **checks}, status=status_code)


def health_live(request):
    """Liveness probe for the orchestrator + uptime monitor (platform-staging DESIGN §4.6).

    Depends on **process + DB only** — never on email, cache, or any external transport — so
    a dependency blip cannot mark the service unhealthy and trigger a restart loop.
    """
    ok = _database_ok()
    status_code = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "down"}, status=status_code)


def serve_media(request, path):
    """Serve one uploaded media file from MEDIA_ROOT (platform-staging DESIGN §4.3).

    MEDIA_ROOT is read at request time so it stays the single source of truth (no
    import-time snapshot). Unlike static assets, media is mutable user data on the
    persistent disk and is served in all environments — see config/urls.py for the
    bounded single-node trade-off and the object-store growth path.
    """
    return static_serve(request, path, document_root=settings.MEDIA_ROOT)
