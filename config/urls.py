"""Root URL configuration.

Feature routes are owned by each app and included here. The accounts app
publishes the auth/profile/admin-role surfaces (DESIGN.md §5/§9).
"""

import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core.views import health, health_live, landing, serve_media

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("health", health, name="health"),
    # DB-only liveness for the platform health check / uptime monitor (DESIGN §4.6).
    path("health/live", health_live, name="health-live"),
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
    # The embeddable-update-widget activation switch (DESIGN.md §13) — the FINAL of the three
    # activation parts (the "apps.widget" INSTALLED_APPS line + the dashboard widget-reach slot
    # are the other two). This single include makes the public widget surface reachable; the
    # documented rollback is `git revert` of the build commit (the dashboard imports
    # widget.selectors, so pulling only this include would not be a clean revert). Own prefix;
    # /widget/ is free — no collision with the pages /apps/ surface.
    path("widget/", include("apps.widget.urls")),
    path("", landing, name="home"),
    path("", include("apps.accounts.urls")),
]

# Serve uploaded app screenshots from MEDIA_ROOT in ALL environments — not just DEBUG.
# Unlike static assets (WhiteNoise serves those, hashed + immutable), media is mutable user
# data living on the persistent disk, so staging (DEBUG=false) must serve it too or uploaded
# screenshots 404 (platform-staging DESIGN §4.3). This is the deliberate, bounded single-node
# trade-off (DESIGN §10): acceptable at staging scale; the documented growth path is
# STORAGES["default"] → an object store (R2 + django-storages), a config-only swap that drops
# this route. Mirrors django.conf.urls.static.static() but without its DEBUG-only guard.
_media_prefix = settings.MEDIA_URL.lstrip("/")
urlpatterns += [
    re_path(rf"^{re.escape(_media_prefix)}(?P<path>.*)$", serve_media, name="media"),
]
