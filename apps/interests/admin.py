"""Django-admin registration — a **read-only** ``Interest`` inspection surface (DESIGN.md §3).

``services`` is the only writer of ``interests_interest`` (the §5.1 invariant — the
all-or-nothing validation and the §7 preserve-on-edit reconcile must not be circumventable).
So the admin is registered read-only: it gives ops an ``is_staff``-gated way to *inspect*
declared-interest rows during cold-start, but never to add/edit/delete one. Mirrors the
signals/ratings/subscriptions read-only admin.
"""

from django.contrib import admin

from apps.interests.models import Interest


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """An admin registration that can never add, change, or delete its model."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Interest)
class InterestAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "user", "tag_id", "created_at")
    search_fields = ("tag_id",)
    date_hierarchy = "created_at"
