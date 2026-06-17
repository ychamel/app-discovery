"""Root URL configuration.

Feature routes are owned by each app and included here. The accounts app
publishes the auth/profile/admin-role surfaces (DESIGN.md §5/§9).
"""

from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("health", health, name="health"),
    path("taxonomy/", include("apps.taxonomy.urls")),
    path("", include("apps.accounts.urls")),
]
