"""Django-admin registration — a **read-only** ``Rating`` inspection surface (DESIGN.md §4).

``services`` is the only writer of ``ratings_rating`` (§5a invariant — the gate determination
is stamped on every write and must not be circumventable). So the admin is registered
read-only: it gives ops an ``is_staff``-gated way to *inspect* ratings and the gate split
during cold-start, but never to add/edit/delete a row. Mirrors the signals read-only admin.
"""

from django.contrib import admin

from apps.ratings.models import Rating


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """An admin registration that can never add, change, or delete its model."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Rating)
class RatingAdmin(ReadOnlyModelAdmin):
    list_display = (
        "id",
        "app_id",
        "user",
        "score",
        "weight_eligible",
        "eligibility_basis",
        "created_at",
    )
    list_filter = ("weight_eligible", "eligibility_basis")
    search_fields = ("app_id",)
    date_hierarchy = "created_at"
