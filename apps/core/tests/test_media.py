"""Media-serving route tests (platform-staging T-02, DESIGN §4.3).

Uploaded screenshots live on a persistent disk and must be served even when
DEBUG is false (staging runs DEBUG=false), unlike the DEBUG-only convenience
route that shipped before this feature.
"""

import tempfile
from pathlib import Path

from django.test import TestCase, override_settings


class MediaServingTests(TestCase):
    def _write_media_file(self, media_root: str, name: str, contents: bytes) -> None:
        (Path(media_root) / name).write_bytes(contents)

    def test_media_served_when_debug_false(self):
        """A file under MEDIA_ROOT is served (200) with DEBUG off — not a 404."""
        with tempfile.TemporaryDirectory() as media_root:
            self._write_media_file(media_root, "shot.png", b"fake-image-bytes")
            with override_settings(DEBUG=False, MEDIA_ROOT=media_root):
                response = self.client.get("/media/shot.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"fake-image-bytes")

    def test_media_served_when_debug_true(self):
        """The DEBUG convenience behaviour is preserved (same route, both states)."""
        with tempfile.TemporaryDirectory() as media_root:
            self._write_media_file(media_root, "shot.png", b"fake-image-bytes")
            with override_settings(DEBUG=True, MEDIA_ROOT=media_root):
                response = self.client.get("/media/shot.png")
        self.assertEqual(response.status_code, 200)

    def test_missing_media_file_is_404_not_a_server_error(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(DEBUG=False, MEDIA_ROOT=media_root):
                response = self.client.get("/media/does-not-exist.png")
        self.assertEqual(response.status_code, 404)
