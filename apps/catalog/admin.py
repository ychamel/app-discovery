"""Django-admin registration — the cold-start inspection surface (DESIGN.md §3/§9).

This is the boring, built-in, ``is_staff``-gated surface for *inspecting* apps and gate
decisions before richer tooling (`editorial-curation-tools`) exists. It is **read/inspect**
only here:

  * ``ReviewDecision`` is **append-only** — not addable/changeable/deletable in admin, so
    the audit log can never be edited away (DESIGN.md §4/§9 attributability);
  * ``App`` is registered for inspection; its lifecycle ``status`` is **read-only** in
    admin (status only ever moves through ``apps.catalog.services``, never a raw field edit).

Any genuine state change still goes through the services/pages, not this surface.
"""

from django.contrib import admin

from apps.catalog.models import App, ReviewDecision


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "last_submitted_at")
    list_filter = ("status",)
    search_fields = ("name", "url", "normalized_url")
    # Lifecycle is owned by services.py — never edited as a free-form admin field.
    readonly_fields = ("status", "normalized_url", "last_submitted_at", "created_at", "updated_at")


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(admin.ModelAdmin):
    list_display = ("app", "outcome", "reviewer", "created_at")
    list_filter = ("outcome",)
    readonly_fields = ("app", "reviewer", "outcome", "failed_criteria", "note", "created_at")

    # Append-only: the decision log is the gate audit; it must never be edited or pruned.
    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
