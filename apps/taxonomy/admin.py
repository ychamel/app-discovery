"""Django admin registration — the cold-start curation surface (DESIGN.md §6/§8).

This is the boring, built-in, ``is_staff``-gated surface for ad-hoc edits before
``editorial-curation-tools`` exists (ITX-5) — no custom UI. Every write routes through
``apps.taxonomy.services`` so the admin enforces the *same* invariants as the seed
command and the API: ≥1 cluster per active tag, slug/label de-duplication, and
non-destructive retire. The admin can never reach the ORM behind the service.

To keep that guarantee simple and readable, the editable surface is deliberately small:
  * ``slug`` is editable only on creation (immutable identity, AC7);
  * ``status`` / ``replaced_by`` / ``retired_at`` are read-only — lifecycle is not a
    free-form field edit; retiring is the explicit "Retire selected tags" action, which
    routes through ``retire_tag`` (keep, no successor — the common case). Merging a tag
    into a successor is done via the seed file (`replaced_by:`), where it is validated.
"""

from django import forms
from django.contrib import admin

from apps.taxonomy import services
from apps.taxonomy.models import Cluster, Tag


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        # slug is the immutable natural key — editable only when first created.
        base = list(super().get_readonly_fields(request, obj))
        return base + ["slug"] if obj is not None else base

    def save_model(self, request, obj, form, change):
        if change:
            services.update_cluster(obj, name=obj.name, description=obj.description)
        else:
            services.add_cluster(obj.slug, obj.name, description=obj.description)


class TagAdminForm(forms.ModelForm):
    """Surfaces the ≥1-cluster invariant as a friendly admin validation error (AC5).

    The service is still the enforcer; this just turns the common mistake into a form
    error instead of a server error before the write is attempted.
    """

    class Meta:
        model = Tag
        fields = ("slug", "label", "definition", "clusters")

    def clean(self):
        cleaned = super().clean()
        instance_is_active = self.instance.pk is None or self.instance.is_active
        if instance_is_active and not cleaned.get("clusters"):
            raise forms.ValidationError("An active tag must belong to at least one cluster.")
        return cleaned


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ("label", "slug", "status", "replaced_by")
    list_filter = ("status",)
    search_fields = ("label", "slug")
    readonly_fields = ("status", "replaced_by", "retired_at", "created_at", "updated_at")
    actions = ["retire_selected_tags"]

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        return base + ["slug"] if obj is not None else base

    def save_model(self, request, obj, form, change):
        clusters = list(form.cleaned_data.get("clusters", []))
        if change:
            services.update_tag(
                obj, label=obj.label, clusters=clusters, definition=obj.definition
            )
        else:
            created = services.add_tag(
                obj.slug, obj.label, clusters=clusters, definition=obj.definition
            )
            # Point the admin's in-memory object at the row the service created, so the
            # post-save redirect and LogEntry reference the real tag.
            obj.pk = created.pk

    def save_related(self, request, form, formsets, change):
        # Cluster membership was already set by the service in save_model; skip the
        # default form.save_m2m() so we neither double-write nor bypass the invariant.
        pass

    @admin.action(description="Retire selected tags (kept, no successor)")
    def retire_selected_tags(self, request, queryset):
        for tag in queryset:
            services.retire_tag(tag)
        self.message_user(request, f"Retired {queryset.count()} tag(s).")

    # Deletion would break stored references — retire instead (AC6). Disable it.
    def has_delete_permission(self, request, obj=None):
        return False
