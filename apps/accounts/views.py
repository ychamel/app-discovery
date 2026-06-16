"""HTTP surfaces for the accounts feature (DESIGN.md §5 contracts, §9 pages).

Two styles, by audience:
  * **Server-rendered Django views** for the human auth flow (register, sign-in,
    verify landing, sign-out) — DESIGN.md §9.
  * **DRF API views** for the JSON contracts downstream features consume
    (`/me`, `/me/roles/developer`, `/admin/...`) — DESIGN.md §5.

Both authenticate through the one magic-link session; roles gate actions via the
single permission from ``apps.accounts.permissions``.
"""

import logging

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import roles
from apps.accounts.auth_backend import issue_login_link, verify_token
from apps.accounts.forms import EmailForm, RegisterForm
from apps.accounts.models import Account
from apps.accounts.permissions import HasRole
from apps.accounts.serializers import AccountSerializer, DisplayNameSerializer
from apps.accounts.services import (
    UnknownRoleError,
    delete_account,
    grant_role,
    revoke_role,
)
from apps.core import observability
from apps.core.email import EmailSendError
from apps.core.ratelimit import rate_limited

logger = logging.getLogger("apps.accounts.views")

# Django's default backend identifies the session's auth source; we use it as the
# label for our passwordless logins (it loads the Account by pk on later requests).
_SESSION_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _establish_session(request, account: Account) -> None:
    auth_login(request, account, backend=_SESSION_BACKEND)


def _create_account_with_base_role(email: str, display_name: str) -> Account:
    """Create an account and assign the base ``user`` role in one transaction (AC1)."""
    with transaction.atomic():
        account = Account.objects.create_account(email, display_name=display_name)
        grant_role(account, roles.BASE_ROLE)
        return account


# ---------------------------------------------------------------------------
# Registration (#1) — AC1, AC2
# ---------------------------------------------------------------------------
# Rate limiting applies to the POST submission (the decorator no-ops on GET).
@rate_limited
@require_http_methods(["GET", "POST"])
def register(request):
    if request.method == "GET":
        return render(request, "accounts/register.html", {"form": RegisterForm()})

    form = RegisterForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/register.html", {"form": form}, status=400)

    email = form.cleaned_data["email"]
    display_name = form.cleaned_data["display_name"]
    try:
        account = _create_account_with_base_role(email, display_name)
    except IntegrityError:
        # One account per email (AC1). Covers the duplicate-registration race too.
        return render(
            request, "accounts/register.html", {"form": form, "email_taken": True}, status=409
        )

    try:
        issue_login_link(account, "register", base_url=settings.PUBLIC_BASE_URL)
    except EmailSendError:
        # The account exists but stays unconfirmed (never digest-eligible). Surface
        # the failure so the person can resend — never swallow it (AC2).
        logger.error("Registration email send failed for account %s", account.id)
        observability.increment(observability.EMAIL_SEND_FAILURE, purpose="register")
        return render(
            request, "accounts/check_email.html", {"email": email, "send_failed": True}, status=503
        )

    return render(request, "accounts/check_email.html", {"email": email}, status=202)


# ---------------------------------------------------------------------------
# Sign-in (#2) + verify landing (#3) — AC3, AC4
# ---------------------------------------------------------------------------
@require_GET
def signin(request):
    return render(request, "accounts/signin.html", {"form": EmailForm()})


@rate_limited
@require_POST
def login_request(request):
    """Issue a sign-in link, with a generic response to avoid enumeration (§10)."""
    form = EmailForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/signin.html", {"form": form}, status=400)

    email = form.cleaned_data["email"]
    account = Account.objects.filter(email=email).first()
    if account is not None:
        try:
            issue_login_link(account, "login", base_url=settings.PUBLIC_BASE_URL)
        except EmailSendError:
            # Stay generic to avoid revealing the account exists; the failure is
            # logged/counted for ops, and the person can resend.
            logger.error("Sign-in email send failed for account %s", account.id)
            observability.increment(observability.EMAIL_SEND_FAILURE, purpose="login")

    # Identical response whether or not the account exists (DESIGN.md §10).
    return render(
        request, "accounts/check_email.html", {"email": email, "generic": True}, status=202
    )


@require_GET
def verify(request):
    """Consume a magic-link token: create a session on success, else 410 (AC3)."""
    raw_token = request.GET.get("token", "")
    account = verify_token(raw_token) if raw_token else None
    if account is None:
        observability.increment(observability.AUTH_ERROR, reason="invalid_token")
        return render(request, "accounts/verify.html", {}, status=410)

    if account.email_confirmed_at is None:
        account.email_confirmed_at = timezone.now()
        account.save(update_fields=["email_confirmed_at"])
        # First successful verify completes registration (metric at confirm).
        observability.increment(observability.REGISTRATION_COMPLETION)

    _establish_session(request, account)
    observability.increment(observability.SIGNIN_SUCCESS)
    return redirect("accounts:profile")


# ---------------------------------------------------------------------------
# Sign-out (#4) — AC5
# ---------------------------------------------------------------------------
@require_POST
def logout(request):
    auth_logout(request)  # flushes the session entirely
    observability.increment(observability.SIGNOUT)  # expected logout (vs. unexpected)
    return HttpResponse(status=204)


# ---------------------------------------------------------------------------
# Profile page (server-rendered) — AC7 view; controls post to the API endpoints
# ---------------------------------------------------------------------------
@login_required
@require_GET
def profile(request):
    return render(
        request,
        "accounts/profile.html",
        {"account": request.user, "roles": roles.account_roles(request.user)},
    )


# ---------------------------------------------------------------------------
# /me — view (#5), edit (#6), delete (#7) — AC7, AC8
# ---------------------------------------------------------------------------
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data)

    def patch(self, request):
        serializer = DisplayNameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 on invalid/empty
        request.user.display_name = serializer.validated_data["display_name"]
        request.user.save(update_fields=["display_name"])
        return Response(AccountSerializer(request.user).data)

    def delete(self, request):
        if request.data.get("confirm") is not True:
            return Response(
                {"detail": "Deletion must be confirmed with {\"confirm\": true}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        delete_account(request.user)
        auth_logout(request)
        observability.increment(observability.DELETION_FULFILMENT)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Self-serve developer role (#8) — AC6
# ---------------------------------------------------------------------------
class DeveloperRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # The ONLY self-serve role is developer (DL-2); the target is always self.
        grant_role(request.user, roles.DEVELOPER)
        observability.increment(observability.DEVELOPER_ROLE_ADOPTION)
        return Response(AccountSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Admin grant/revoke (#9, #10) — AC9
# ---------------------------------------------------------------------------
class AdminAccountRolesView(APIView):
    permission_classes = [IsAuthenticated, HasRole(roles.ADMIN)]

    def post(self, request, account_id):
        target = get_object_or_404(Account, pk=account_id)
        role = request.data.get("role")
        try:
            grant_role(target, role, granted_by=request.user)
        except UnknownRoleError:
            return Response(
                {"detail": f"Unknown role: {role!r}."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Alert-worthy: any admin grant/revoke is recorded as a metric event.
        observability.increment(observability.ADMIN_ROLE_CHANGE, action="grant", role=role)
        return Response(AccountSerializer(target).data)

    def delete(self, request, account_id, role):
        target = get_object_or_404(Account, pk=account_id)
        try:
            revoke_role(target, role, granted_by=request.user)
        except UnknownRoleError:
            return Response(
                {"detail": f"Unknown role: {role!r}."}, status=status.HTTP_400_BAD_REQUEST
            )
        observability.increment(observability.ADMIN_ROLE_CHANGE, action="revoke", role=role)
        return Response(status=status.HTTP_204_NO_CONTENT)
