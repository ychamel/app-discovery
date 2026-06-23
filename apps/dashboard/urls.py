"""URL routes for the developer-dashboard (DESIGN.md §5.3).

Mounted under ``dashboard/`` by the project URLconf — that single include (plus the
``INSTALLED_APPS`` line) is the entire activation switch, and removing it is the entire
rollback with zero data migration (DESIGN §8/§12).
"""

from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.my_apps, name="my-apps"),
    path("apps/<uuid:app_id>/", views.app_reception, name="app"),
]
