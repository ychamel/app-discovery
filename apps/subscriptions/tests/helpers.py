"""Shared builders for subscriptions tests — accounts and accepted catalog apps.

Kept in one place so every subscriptions test constructs fixtures identically: a user
account and a real **accepted** catalog app (the only kind the follow write path accepts,
D-6). Mirrors the ratings test helpers (the near-twin feature).
"""

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role
from apps.catalog import services as catalog_services
from apps.catalog.models import App
from apps.taxonomy import services as taxonomy_services
from apps.taxonomy.models import Tag


def make_tag(slug: str, label: str | None = None) -> Tag:
    cluster = taxonomy_services.add_cluster(f"{slug}-cluster", f"{slug} cluster")
    return taxonomy_services.add_tag(slug, label or slug, clusters=[cluster])


def make_account(email: str, *, role: str | None = None) -> Account:
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


def make_user(email: str = "follower@example.com") -> Account:
    return make_account(email)


def make_accepted_app(owner, *, tag_ids=None, name: str = "Demo App") -> App:
    """Submit and accept an app so it is catalogued (the follow-valid state, D-6)."""
    app = catalog_services.submit_app(
        owner,
        name=name,
        description="A small vibecoded web app.",
        url=f"https://example.com/{name.lower().replace(' ', '-')}",
        tag_ids=list(tag_ids or []),
        media=[_png_upload()],
    )
    catalog_services.accept_app(app, owner)
    return app


def _png_upload():
    """A real, decodable 16x16 PNG (catalog requires ≥1 image)."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(120, 120, 120)).save(buffer, format="PNG")
    return SimpleUploadedFile("shot.png", buffer.getvalue(), content_type="image/png")
