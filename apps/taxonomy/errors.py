"""Errors raised by the taxonomy write service (DESIGN.md §5b/§10).

Each is raised loudly and never swallowed: a curation mistake surfaces to the editor
(admin or seed command) rather than producing a silent bad write. They subclass
``ValueError`` so callers can catch the family or each specific case.
"""


class TaxonomyError(ValueError):
    """Base class for all write-service validation failures."""


class DuplicateTagError(TaxonomyError):
    """A tag with the same slug or normalized label already exists (AC1 / R2)."""


class OrphanTagError(TaxonomyError):
    """A write would leave an active tag in zero clusters (AC5)."""


class RetireSuccessorError(TaxonomyError):
    """A retire successor is missing, retired, the tag itself, or would form a cycle (OQ-2)."""
