"""Loud failures raised by the interests write path (DESIGN.md §5.1/§9).

``InterestValidationError`` is raised **before** any write, so a save containing an
off-vocabulary/retired/malformed id (or an over-large request) never leaves a partial set
(AC2). The view maps it to a re-rendered picker + HTTP 400.
"""


class InterestValidationError(Exception):
    """A submitted interest set failed the closed-vocabulary boundary or the size cap (AC2)."""
