"""Shared builders for signals tests (accounts + a catalogued app).

Kept in one place so every signals test constructs the same fixtures the same way: a
user account, and a real **accepted** catalog app (the only kind capture will accept,
D-6) with a known tag set so the frozen capture-time snapshot can be asserted.
"""

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role
from apps.catalog import services as catalog_services
from apps.catalog.models import App
from apps.taxonomy import services as taxonomy_services
from apps.taxonomy.models import Tag


def make_tag(slug: str, label: str | None = None) -> Tag:
    """Create one active taxonomy tag in its own cluster (the minimum valid tag)."""
    cluster = taxonomy_services.add_cluster(f"{slug}-cluster", f"{slug} cluster")
    return taxonomy_services.add_tag(slug, label or slug, clusters=[cluster])


def make_account(email: str, *, role: str | None = None) -> Account:
    """Create an account, optionally granting one role."""
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


def make_user(email: str = "viewer@example.com") -> Account:
    return make_account(email)


def make_admin(email: str = "admin@example.com") -> Account:
    return make_account(email, role=roles.ADMIN)


def make_accepted_app(owner, *, tag_ids, name: str = "Demo App") -> App:
    """Submit and accept an app so it is catalogued (the capture-valid state, D-6)."""
    app = catalog_services.submit_app(
        owner,
        name=name,
        description="A small vibecoded web app.",
        url=f"https://example.com/{name.lower().replace(' ', '-')}",
        tag_ids=tag_ids,
        media=[_png_upload()],
    )
    catalog_services.accept_app(app, owner)
    return app


def _png_upload():
    """A real, decodable 16x16 PNG as an uploaded file (catalog requires ≥1 image)."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color=(120, 120, 120)).save(buffer, format="PNG")
    return SimpleUploadedFile("shot.png", buffer.getvalue(), content_type="image/png")
