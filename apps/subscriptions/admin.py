"""Django-admin registration — a **read-only** ``Subscription`` inspection surface (DESIGN.md §5).

``services`` is the only writer of ``subscriptions_subscription`` (§5a invariant — the follow
write and its atomic ``subscribe`` emit must not be circumventable). So the admin is
registered read-only: it gives ops an ``is_staff``-gated way to *inspect* follow state during
cold-start, but never to add/edit/delete a row. Mirrors the signals/ratings read-only admin.
"""

from django.contrib import admin

from apps.subscriptions.models import Subscription


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """An admin registration that can never add, change, or delete its model."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Subscription)
class SubscriptionAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "app_id", "user", "created_at")
    search_fields = ("app_id",)
    date_hierarchy = "created_at"
