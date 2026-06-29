"""The code-fixed typed-facet vocabulary (DESIGN.md §4/§5.3 — the ``gate.py`` precedent).

Typed facets ("pricing", "maturity", "modality", "platform") are **structured fields**,
not free text and **not** taxonomy tags: they describe an app at a glance on its page and
are deliberately **firewalled from ranking/discovery** (D-14a). Like the intake ``gate``,
the vocabulary is product-fixed, so it lives in **code** — type-safe, no migration to read
it, no editorial mutation path. Changing the vocabulary is a one-file edit here.

This module holds **no Django model and no DB access** — pure declaration (one job). The
write path (``catalog.services``) validates a written ``(facet, value)`` against it at the
boundary; the read path (``catalog.selectors``) resolves stored ``AppFacet`` rows through
it at display, **silently dropping** a value no longer in the registry (the D-5 graceful
pattern — a vocabulary change never errors an existing page).
"""

from dataclasses import dataclass
from enum import Enum


class FacetCardinality(Enum):
    """How many values one app may carry for a facet (enforced in the write service)."""

    SINGLE = "single"  # at most one value (e.g. an app has one pricing model)
    MULTI = "multi"  # zero or more values (e.g. an app can be web *and* mobile)


@dataclass(frozen=True)
class FacetValue:
    """One selectable value within a facet, with its display label."""

    key: str  # the stored, code-fixed value key (e.g. "free")
    label: str  # the human label rendered on the page (e.g. "Free")


@dataclass(frozen=True)
class FacetDef:
    """One facet: its key, display label, cardinality, and ordered value vocabulary."""

    key: str  # the stored, code-fixed facet key (e.g. "pricing")
    label: str  # the human label rendered as the fact-strip group (e.g. "Pricing")
    cardinality: FacetCardinality
    values: tuple[FacetValue, ...]  # the closed value set, in display order

    def value(self, key: str) -> FacetValue | None:
        """The ``FacetValue`` for ``key`` within this facet, or None if not in the set."""
        for value in self.values:
            if value.key == key:
                return value
        return None


@dataclass(frozen=True)
class ResolvedFacet:
    """A facet with its app's set values resolved to display order (read side).

    Returned by :func:`resolve_facets`; the page read (``catalog.selectors``) maps it onto
    its ``CatalogFacet`` DTO. Only carries values that are still in the current registry.
    """

    facet: str  # the registry key (e.g. "pricing")
    label: str  # the facet's display label (e.g. "Pricing")
    values: list[FacetValue]  # the app's values for this facet, in registry order


def _def(key: str, label: str, cardinality: FacetCardinality, values: dict[str, str]) -> FacetDef:
    """Build a ``FacetDef`` from a {value_key: value_label} mapping (declaration helper)."""
    return FacetDef(
        key=key,
        label=label,
        cardinality=cardinality,
        values=tuple(FacetValue(key=k, label=v) for k, v in values.items()),
    )


# The closed facet vocabulary (DESIGN.md §5.3) — the ONE edit site. Insertion order is the
# display order of the fact strip; value insertion order is the display order within a facet.
FACETS: dict[str, FacetDef] = {
    "pricing": _def(
        "pricing",
        "Pricing",
        FacetCardinality.SINGLE,
        {
            "free": "Free",
            "freemium": "Freemium",
            "paid": "Paid",
            "subscription": "Subscription",
        },
    ),
    "maturity": _def(
        "maturity",
        "Maturity",
        FacetCardinality.SINGLE,
        {
            "concept": "Concept",
            "alpha": "Alpha",
            "beta": "Beta",
            "early_access": "Early access",
            "live": "Live",
        },
    ),
    "modality": _def(
        "modality",
        "Modality",
        FacetCardinality.MULTI,
        {
            "single_player": "Single-player",
            "multiplayer": "Multiplayer",
            "collaborative": "Collaborative",
            "online": "Online",
            "offline": "Offline",
            "realtime": "Realtime",
            "async": "Asynchronous",
        },
    ),
    "platform": _def(
        "platform",
        "Platform",
        FacetCardinality.MULTI,
        {
            "web": "Web",
            "pwa": "PWA",
            "desktop": "Desktop",
            "mobile": "Mobile",
        },
    ),
}


def facet_keys() -> list[str]:
    """The facet keys, in registry (display) order."""
    return list(FACETS.keys())


def is_valid_facet_value(facet: str, value: str) -> bool:
    """True iff ``facet`` is a registry facet and ``value`` is one of its value keys.

    The single closed-set validator consumers enforce at their write boundary — an
    off-vocabulary facet or value is refused, never coined (mirrors ``is_valid_tag``).
    """
    facet_def = FACETS.get(facet)
    return facet_def is not None and facet_def.value(value) is not None


def cardinality_of(facet: str) -> FacetCardinality:
    """The cardinality of ``facet``; raises ``KeyError`` for an unknown facet (fail loud).

    Callers validate the facet first (``is_valid_facet_value``), so an unknown key here is a
    programming error, surfaced loudly rather than silently defaulted.
    """
    return FACETS[facet].cardinality


def resolve_facets(rows) -> list[ResolvedFacet]:
    """Group stored facet rows into registry-ordered ``ResolvedFacet``s for display.

    ``rows`` is any iterable of objects exposing ``.facet`` and ``.value`` strings (the
    ``AppFacet`` rows). Facets and values are emitted in **registry order**, regardless of
    storage order; a row whose facet or value is **not in the current registry is silently
    dropped** (the D-5 graceful pattern — a vocabulary change never errors a page). A facet
    with no surviving value is omitted, so the caller renders only set facets.
    """
    selected: dict[str, set[str]] = {}
    for row in rows:
        if is_valid_facet_value(row.facet, row.value):
            selected.setdefault(row.facet, set()).add(row.value)

    resolved: list[ResolvedFacet] = []
    for facet_key, facet_def in FACETS.items():
        chosen = selected.get(facet_key)
        if not chosen:
            continue
        values = [value for value in facet_def.values if value.key in chosen]
        resolved.append(
            ResolvedFacet(facet=facet_key, label=facet_def.label, values=values)
        )
    return resolved
