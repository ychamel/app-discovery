"""URL routes for the app-subscriptions feature (DESIGN.md §6.4).

Mounted under its own ``subscriptions/`` prefix by the project URLconf, so there is no
fall-through ambiguity with the pages ``apps/`` include. Both mutation routes are keyed on
the ``App.id`` UUID + the authenticated user — no subscription id ever appears in a URL
(no IDOR).
"""

from django.urls import path

from apps.subscriptions import views

app_name = "subscriptions"

urlpatterns = [
    path("apps/<uuid:app_id>/follow", views.follow, name="follow"),
    path("apps/<uuid:app_id>/unfollow", views.unfollow, name="unfollow"),
    path("feed", views.feed, name="feed"),
]
