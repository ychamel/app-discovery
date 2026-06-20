"""URL routes for the app-pages feature (DESIGN.md §5a).

Mounted under ``apps/`` by the project URLconf. All three routes are keyed on the
``App.id`` UUID so the public link is stable across metadata edits (AP-5/AC4).
"""

from django.urls import path

from apps.pages import views

app_name = "pages"

urlpatterns = [
    path("<uuid:app_id>/", views.app_page, name="app-page"),
    path("<uuid:app_id>/try", views.try_redirect, name="try"),
    path("<uuid:app_id>/share", views.share, name="share"),
]
