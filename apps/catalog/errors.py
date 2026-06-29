"""Errors raised by the catalog write service (DESIGN.md §5a/§10).

Each is raised **loudly and never swallowed**: a bad submission/edit/decision surfaces to
the caller (the API view maps it to a status code, §5c) rather than producing a silent bad
write. They subclass ``ValueError`` so a caller can catch the family or each specific case.

Generic per-field problems (a missing required field, a malformed URL) use Django/DRF
``ValidationError`` instead — these classes name the catalog-specific boundary failures.
"""


class CatalogError(ValueError):
    """Base class for all catalog write-service failures."""


class InvalidTagError(CatalogError):
    """A submitted ``tag_id`` is not an active taxonomy tag (off-vocabulary, AC4)."""


class MediaLimitError(CatalogError):
    """An upload is not a valid image/clip, is over size, or breaches a per-app cap (§9)."""


class InvalidFacetError(CatalogError):
    """A submitted ``(facet, value)`` is off-vocabulary, or breaks a facet's cardinality (D-14a)."""


class InvalidTransitionError(CatalogError):
    """A lifecycle change was attempted from a state the §7 state machine forbids (→ 409)."""


class NotOwnerError(CatalogError):
    """An owner-scoped action was attempted on an app the caller does not own."""
