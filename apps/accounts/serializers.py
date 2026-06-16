"""DRF serializers for the account API (DESIGN.md §5 #5/#6)."""

from rest_framework import serializers

from apps.accounts import roles


class AccountSerializer(serializers.Serializer):
    """Read shape for `GET /me` — the public view of an account and its roles."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    email_confirmed = serializers.SerializerMethodField()

    def get_roles(self, account) -> list[str]:
        return roles.account_roles(account)

    def get_email_confirmed(self, account) -> bool:
        return account.is_email_confirmed


class DisplayNameSerializer(serializers.Serializer):
    """Write shape for `PATCH /me` — a validated, non-empty display name (AC7)."""

    display_name = serializers.CharField(max_length=80, min_length=1, trim_whitespace=True)
