"""URL routes for the developer-updates feature (DESIGN.md §6.5).

Mounted under its own ``updates/`` prefix by the project URLconf, so there is no fall-through
ambiguity with the pages ``apps/`` include. The two mutation routes are keyed on the
``App.id`` UUID (+ a scoped ``notice_id``) + the authenticated user — no unscoped notice id
ever addresses a write, so a developer can only touch their own (no IDOR).
"""

from django.urls import path

from apps.updates import views

app_name = "updates"

urlpatterns = [
    path("", views.my_channels, name="my-channels"),
    path("apps/<uuid:app_id>/", views.channel, name="channel"),
    path("apps/<uuid:app_id>/post", views.post, name="post"),
    path(
        "apps/<uuid:app_id>/notices/<uuid:notice_id>/withdraw",
        views.withdraw,
        name="withdraw",
    ),
]
