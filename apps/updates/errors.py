"""Loud failures raised by the updates write path (DESIGN.md §6.2/§7).

All three are raised **before** any write, so a rejected post never leaves a partial row
(mirrors ``apps/ratings/errors.py``). The views map them to HTTP: ``AppNotOwnedError`` → 404
(no ownership oracle, AC1); ``InvalidNoticeError`` / ``RateLimitedError`` → a message + PRG
back, nothing created (AC2/AC3/AC8).
"""


class AppNotOwnedError(Exception):
    """The target app is not one the caller owns (unknown, or another developer's)."""


class InvalidNoticeError(Exception):
    """The notice kind, title, or summary violates a boundary rule (kind / blank / length)."""


class RateLimitedError(Exception):
    """The author has reached the per-app post limit within the configured window (AC8)."""
