"""URL routes for the ratings-reviews feature (DESIGN.md §5e).

Mounted under its own ``ratings/`` prefix by the project URLconf, so there is no
fall-through ambiguity with the pages ``apps/`` include. Both routes are keyed on the
``App.id`` UUID + the authenticated user — no rating id ever appears in a URL (no IDOR).
"""

from django.urls import path

from apps.ratings import views

app_name = "ratings"

urlpatterns = [
    path("apps/<uuid:app_id>/rating", views.submit, name="submit"),
    path("apps/<uuid:app_id>/rating/remove", views.remove, name="remove"),
]
