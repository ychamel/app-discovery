"""Django-admin registration — read-only corpus inspection for ops cold-start (DESIGN.md §3/§5c/§9).

The corpus is **append-only**: ``capture`` is the only writer, and that guarantee must not
be circumventable through the admin. So all four models are registered **read-only** — no
add/change/delete permission on any of them. This gives ops an ``is_staff``-gated way to
*inspect* the corpus (and confirm capture is flowing) during cold-start, while inspection +
the ``capture_error`` metric make loss/tampering observable (§10 attributability). Rich
analytics is a future consumer's job, not this surface.
"""

from django.contrib import admin

from apps.signals.models import (
    EngagementEvent,
    Impression,
    ImpressionTag,
    PlatformVisit,
)


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """An admin registration that can never add, change, or delete its model (append-only)."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Impression)
class ImpressionAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "app_id", "user", "surface", "occurred_at")
    list_filter = ("surface",)
    search_fields = ("app_id",)
    date_hierarchy = "occurred_at"


@admin.register(ImpressionTag)
class ImpressionTagAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "impression", "tag_id")
    search_fields = ("tag_id",)


@admin.register(EngagementEvent)
class EngagementEventAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "kind", "app_id", "user", "is_proxy", "occurred_at")
    list_filter = ("kind", "is_proxy")
    search_fields = ("app_id",)
    date_hierarchy = "occurred_at"


@admin.register(PlatformVisit)
class PlatformVisitAdmin(ReadOnlyModelAdmin):
    list_display = ("id", "user", "visit_date")
    date_hierarchy = "visit_date"
