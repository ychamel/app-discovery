"""URL routes for the open discovery surface (DESIGN.md §6.3).

Mounted under ``discover/`` by the project URLconf — that single include is the entire
activation switch (and removing it is the entire rollback, DESIGN §11/§16).
"""

from django.urls import path

from apps.discovery import views

app_name = "discovery"

urlpatterns = [
    path("", views.catalogue, name="browse"),
]
