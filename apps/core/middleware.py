"""Request-context middleware (DESIGN.md §10 observability).

Assigns each request a correlation id (honoring an inbound ``X-Request-ID`` if the
proxy set one) and binds the acting account's UUID, so every log line emitted while
handling the request is attributable. Placed after AuthenticationMiddleware so
``request.user`` is resolvable.
"""

import uuid

from apps.core.observability import account_id_var, request_id_var


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request_token = request_id_var.set(request_id)

        user = getattr(request, "user", None)
        account_id = str(user.id) if user is not None and user.is_authenticated else "-"
        account_token = account_id_var.set(account_id)

        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(request_token)
            account_id_var.reset(account_token)
