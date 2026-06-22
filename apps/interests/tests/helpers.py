"""Shared builders for interests tests — accounts and real taxonomy tags.

Kept in one place so every interests test constructs fixtures identically: a user account
and real taxonomy tags (the only ids the write boundary accepts active, D-5). This feature
validates/resolves against the *real* taxonomy surface (no mocking of
``is_valid_tag``/``resolve_tag``), so the §7 preserve-on-edit seam is exercised against
genuine ``retire_tag`` states.
"""

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role
from apps.taxonomy import services as taxonomy_services
from apps.taxonomy.models import Cluster, Tag


def make_cluster(slug: str, name: str | None = None) -> Cluster:
    return taxonomy_services.add_cluster(slug, name or slug)


def make_tag(slug: str, label: str | None = None, *, cluster: Cluster | None = None) -> Tag:
    clusters = [cluster] if cluster is not None else [make_cluster(f"{slug}-cluster")]
    return taxonomy_services.add_tag(slug, label or slug, clusters=clusters)


def make_account(email: str, *, role: str | None = None) -> Account:
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


def make_user(email: str = "declarer@example.com") -> Account:
    return make_account(email)
