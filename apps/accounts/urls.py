"""URL routes for the accounts feature (DESIGN.md §5 endpoints, §9 pages).

Mounted at the site root, so ``auth/register`` resolves to ``/auth/register`` etc.
Each route maps obviously to one view; the verify path is derived from
``auth_backend.VERIFY_PATH`` so the emailed link and the route cannot diverge.
"""

from django.urls import path

from apps.accounts import views
from apps.accounts.auth_backend import VERIFY_PATH

app_name = "accounts"

urlpatterns = [
    # Server-rendered auth flow (§9)
    path("auth/register", views.register, name="register"),
    path("auth/signin", views.signin, name="signin"),
    path("auth/login", views.login_request, name="login"),
    path(VERIFY_PATH.lstrip("/"), views.verify, name="verify"),
    path("auth/logout", views.logout, name="logout"),
    path("profile", views.profile, name="profile"),
    # JSON API contracts (§5)
    path("me", views.MeView.as_view(), name="me"),
    path("me/roles/developer", views.DeveloperRoleView.as_view(), name="developer-role"),
    path(
        "admin/accounts/<uuid:account_id>/roles",
        views.AdminAccountRolesView.as_view(),
        name="admin-account-roles",
    ),
    path(
        "admin/accounts/<uuid:account_id>/roles/<str:role>",
        views.AdminAccountRolesView.as_view(),
        name="admin-account-role",
    ),
]
