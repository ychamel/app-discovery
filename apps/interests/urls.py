"""URL routes for the interest-profile feature (DESIGN.md §5.3).

Mounted under its own ``interests/`` prefix by the project URLconf. No interest/profile id
ever appears in a URL — a declaration is addressed by ``request.user`` + ``tag_id`` only, so
a user can only ever touch their own profile (no IDOR, DESIGN §11).
"""

from django.urls import path

from apps.interests import views

app_name = "interests"

urlpatterns = [
    path("", views.picker, name="picker"),
    path("save", views.save, name="save"),
    path("clear", views.clear, name="clear"),
]
