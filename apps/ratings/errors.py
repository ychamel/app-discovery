"""Loud failures raised by the ratings write path (DESIGN.md §5a/§8).

Both are raised **before** any write, so a rejected submission never leaves a partial row.
The views map them to HTTP: ``UnknownAppError`` → 404 (AC9), ``RatingValidationError`` →
re-show the page with the error (AC2).
"""


class UnknownAppError(Exception):
    """The target app is not an accepted catalog app (unknown/pending/rejected/withdrawn)."""


class RatingValidationError(Exception):
    """The submitted score or review text violates a boundary rule (range / length)."""
