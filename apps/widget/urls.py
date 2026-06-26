"""URL routes for the embeddable-update-widget feature (DESIGN §5.2).

Mounted under ``widget/`` by the project URLconf — that include is the feature's activation
switch (DESIGN §13). Both routes are keyed on the ``App.id`` UUID (the stable public id) and are
GET-only, AllowAny, public-content reads.
"""

from django.urls import path

from apps.widget import views

app_name = "widget"

urlpatterns = [
    path("<uuid:app_id>/", views.widget_render, name="render"),
    path("<uuid:app_id>/view", views.widget_view_redirect, name="view"),
]
