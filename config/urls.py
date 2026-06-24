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
    # The open-search-browse activation switch (DESIGN.md §11/§16): this single include is the
    # entire activation — and removing it is the entire rollback (zero data migration). Own
    # prefix; no collision with the pages /apps/ surface.
    path("discover/", include("apps.discovery.urls")),
    # The developer-dashboard activation switch (DESIGN.md §12): this single include (plus the
    # "apps.dashboard" INSTALLED_APPS line) is the entire activation — and removing them is the
    # entire rollback, zero data migration (the app owns no schema). Own prefix; no collision.
    path("dashboard/", include("apps.dashboard.urls")),
    # The developer-updates activation switch (DESIGN.md §12) — the FINAL of the three
    # activation parts (the "apps.updates" INSTALLED_APPS line + the subscriptions.notices seam
    # repoint are the other two). Rollback is the honest three-part revert: this include +
    # the seam revert to `return []` + the INSTALLED_APPS line. Own prefix; no collision.
    path("updates/", include("apps.updates.urls")),
    path("", include("apps.accounts.urls")),
]

# Serve uploaded app screenshots from MEDIA_ROOT in development only; in production a
# web server / object store fronts MEDIA_URL (DESIGN.md §9).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
