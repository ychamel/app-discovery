"""Loud capture failures (DESIGN.md §5a).

The single write path raises these — it never swallows a failure or writes a partial
row. Each maps to a refused capture at the trust boundary; the surface decides how to
treat the raise (§5d).
"""


class CaptureError(Exception):
    """Base class for a refused capture — never silent (AC11)."""


class UnknownAppError(CaptureError):
    """The app_id is not a real, accepted catalog app (D-6). Nothing is written."""


class ImpressionMismatchError(CaptureError):
    """The supplied impression belongs to a different app or user — cross-app/user forgery (AC3)."""
