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


# Minimal magic-byte headers the clip sniffer recognises (DESIGN.md §5.1/§9.4): an MP4 carries
# an ``ftyp`` box at offset 4; WebM/Matroska opens with the EBML magic ``1A 45 DF A3``.
_MP4_HEADER = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
_WEBM_HEADER = b"\x1a\x45\xdf\xa3" + b"\x00" * 12


def make_clip_upload(
    name: str = "demo.mp4",
    *,
    container: str = "mp4",
    extra_bytes: int = 0,
    content_type: str = "video/mp4",
) -> SimpleUploadedFile:
    """A demo-clip upload whose magic bytes sniff as the given container (mp4/webm)."""
    header = _WEBM_HEADER if container == "webm" else _MP4_HEADER
    return SimpleUploadedFile(name, header + b"\x00" * extra_bytes, content_type=content_type)
