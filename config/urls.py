"""Root URL configuration.

Feature routes are owned by each app and included here. The accounts app
publishes the auth/profile/admin-role surfaces (DESIGN.md §5/§9).
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import health

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("health", health, name="health"),
    path("taxonomy/", include("apps.taxonomy.urls")),
    path("catalog/", include("apps.catalog.urls")),
    # The app-pages activation switch (DESIGN.md §12): removing this include rolls the
    # feature back with zero data migration. /apps/ is free — catalog dev pages live under
    # catalog/apps/.
    path("apps/", include("apps.pages.urls")),
    # The ratings-reviews activation switch (DESIGN.md §12): removing this include rolls the
    # feature back with zero data migration. Own prefix — no collision with the pages /apps/.
    path("ratings/", include("apps.ratings.urls")),
    # The app-subscriptions activation switch (DESIGN.md §15): one half of the rollback (the
    # other is the app_page.html Follow section). Own prefix — no collision with pages /apps/.
    path("subscriptions/", include("apps.subscriptions.urls")),
    # The interest-profile activation switch (DESIGN.md §16): one half of the rollback (the
    # other is the {% interest_prompt %} line in accounts/profile.html). Own prefix.
    path("interests/", include("apps.interests.urls")),
    path("", include("apps.accounts.urls")),
]

# Serve uploaded app screenshots from MEDIA_ROOT in development only; in production a
# web server / object store fronts MEDIA_URL (DESIGN.md §9).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
