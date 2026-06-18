"""Shared builders for catalog tests (accounts, roles, in-memory image uploads).

Kept in one place so every catalog test constructs the same fixtures the same way: a
developer/admin account, and a small valid PNG as an ``UploadedFile`` for media tests.
"""

import io

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts import roles
from apps.accounts.models import Account
from apps.accounts.services import grant_role


def make_account(email: str, *, role: str | None = None) -> Account:
    """Create an account, optionally granting one role (developer/admin)."""
    account = Account.objects.create_account(email)
    grant_role(account, roles.BASE_ROLE)
    if role is not None:
        grant_role(account, role)
    return account


def make_developer(email: str = "dev@example.com") -> Account:
    return make_account(email, role=roles.DEVELOPER)


def make_admin(email: str = "admin@example.com") -> Account:
    return make_account(email, role=roles.ADMIN)


def make_image_upload(
    name: str = "shot.png",
    *,
    fmt: str = "PNG",
    size: tuple[int, int] = (16, 16),
    content_type: str = "image/png",
) -> SimpleUploadedFile:
    """A real, decodable image as an uploaded file (Pillow-encoded in memory)."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, color=(120, 120, 120)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def make_non_image_upload(
    name: str = "notes.txt", content_type: str = "text/plain"
) -> SimpleUploadedFile:
    """An uploaded file whose bytes are not a decodable image."""
    return SimpleUploadedFile(name, b"this is not an image", content_type=content_type)
