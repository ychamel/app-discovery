"""Cross-cutting core views — currently the health endpoint (DESIGN.md §10)."""

from django.http import JsonResponse

from apps.core.observability import check_health


def health(request):
    """Report dependency health. 200 when all checks pass, else 503."""
    checks = check_health()
    ok = all(checks.values())
    status_code = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "degraded", **checks}, status=status_code)
