"""Django admin registration (DESIGN.md §9, §10 cold start).

The built-in admin site is the operator surface for cold-start grants before the
product-facing admin tooling (`editorial-curation-tools`) exists. Audit rows are
read-only here — grants/revokes flow through the role service, not hand edits.
"""

from django.contrib import admin

from apps.accounts.models import Account, LoginToken, RoleGrant


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_active", "is_staff", "email_confirmed_at")
    search_fields = ("email", "display_name")
    ordering = ("email",)


@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ("account", "created_at", "expires_at", "consumed_at")
    readonly_fields = ("token_hash", "created_at")


@admin.register(RoleGrant)
class RoleGrantAdmin(admin.ModelAdmin):
    list_display = ("target_account", "role", "action", "granted_by", "created_at")
    list_filter = ("action", "role")
    # Audit rows are append-only: viewable, never editable from the admin.
    readonly_fields = ("target_account", "role", "action", "granted_by", "created_at")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
