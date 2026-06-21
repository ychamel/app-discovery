"""Loud failures raised by the subscriptions write path (DESIGN.md §5a/§8).

``UnknownAppError`` is raised **before** any write, so a follow of an unknown/non-accepted
app never leaves a row. The view maps it to HTTP 404 (AC1).
"""


class UnknownAppError(Exception):
    """The target app is not an accepted catalog app (unknown/pending/rejected/withdrawn)."""
