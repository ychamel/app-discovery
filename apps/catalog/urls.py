"""URL routes for the catalog feature (DESIGN.md §5c/§8).

Mounted under ``catalog/`` by the project URLconf. Two surfaces share the mount:
  * the JSON **API** under ``catalog/api/`` (developer endpoints 1–8, review endpoints
    9–10) — kept under its own prefix so it never collides with the human pages;
  * the server-rendered **pages** at ``catalog/`` (submit, my-apps, app detail, review),
    added by T-11/T-12.
"""

from django.urls import path

from apps.catalog import views

app_name = "catalog"

# JSON API — developer surface (T-09, endpoints 1–8).
api_patterns = [
    path("api/apps", views.AppCreateView.as_view(), name="api-app-create"),
    path("api/apps/mine", views.MyAppsView.as_view(), name="api-app-mine"),
    path("api/apps/<uuid:app_id>", views.AppDetailView.as_view(), name="api-app-detail"),
    path("api/apps/<uuid:app_id>/media", views.AppMediaView.as_view(), name="api-app-media"),
    path(
        "api/apps/<uuid:app_id>/media/<uuid:media_id>",
        views.AppMediaItemView.as_view(),
        name="api-app-media-item",
    ),
    path(
        "api/apps/<uuid:app_id>/withdraw",
        views.AppWithdrawView.as_view(),
        name="api-app-withdraw",
    ),
    path(
        "api/apps/<uuid:app_id>/resubmit",
        views.AppResubmitView.as_view(),
        name="api-app-resubmit",
    ),
    # Review surface (T-10, endpoints 9–10).
    path("api/review/queue", views.ReviewQueueView.as_view(), name="api-review-queue"),
    path(
        "api/apps/<uuid:app_id>/decision",
        views.ReviewDecisionView.as_view(),
        name="api-app-decision",
    ),
]

# Server-rendered developer pages (T-11, §8).
page_patterns = [
    path("submit", views.submit_page, name="submit"),
    path("apps", views.my_apps_page, name="my-apps"),
    path("apps/<uuid:app_id>", views.app_detail_page, name="app-detail"),
    # Admin review pages (T-12, §8).
    path("review", views.review_queue_page, name="review"),
    path("review/<uuid:app_id>", views.review_detail_page, name="review-detail"),
]

urlpatterns = [*api_patterns, *page_patterns]
