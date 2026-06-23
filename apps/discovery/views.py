"""The single thin HTTP view for the open discovery surface (DESIGN.md §6.3).

Mirrors the model-less-consumer house pattern (``apps/pages/``): the view parses the
trust-boundary params, asks taxonomy for the facets + the tag-match set, asks catalog for a
page of results, and renders. It holds **no business logic and no ORM access** beyond calling
the D-5/D-6 read surfaces, and **imports nothing from ``signals``** — a self-driven browse/
search view never confers curated eligibility (AC6, structural).

The failure split (DESIGN §7/§9) is the load-bearing rule:
  * the **core results read** (``search_catalogue``) fails **loud** — a DB error propagates to
    a normal 500, never masked as a fake empty state (which would lie about M1/M3);
  * the **facet sidebar** fails **soft** — on a taxonomy read error the results still render
    and the sidebar shows "filters unavailable".
All visitor input is coerced/clamped here; the response is always 200 for a well-formed
request, including zero results and an empty catalogue (AC7), with no login wall (AC8).
"""

import logging
from uuid import UUID

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.catalog import selectors as catalog
from apps.core import config, observability
from apps.taxonomy import selectors as taxonomy

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def catalogue(request) -> HttpResponse:
    """GET /discover/ — browse/search/filter the accepted catalogue (AllowAny, AC8).

    Browse (no ``q``) is newest-accepted-first; ``q`` searches name+description by relevance;
    ``tag``/``cluster`` filter by interest (``tag`` wins if both arrive). Always 200 for a
    well-formed request; the core read failing is a loud 500 (DESIGN §7).
    """
    query = _parse_query(request)
    page_number = _parse_page(request)
    facets, facets_degraded = _load_facets()
    tag_ids, selected_tag, selected_cluster = _resolve_filter(request, facets)

    try:
        page = catalog.search_catalogue(
            query=query, tag_ids=tag_ids or None, page=page_number
        )
    except Exception:
        # The open surface is down — fail loud (alert), never a fake empty page (DESIGN §9).
        observability.increment(observability.DISCOVERY_LISTING_DEGRADED)
        raise

    _record_usage(query, tag_ids, page)

    context = {
        "page": page,
        "query": query or "",
        "active_tags": [] if facets is None else facets["active_tags"],
        "clusters": [] if facets is None else facets["clusters"],
        "facets_degraded": facets_degraded,
        "selected_tag": selected_tag,
        "selected_cluster": selected_cluster,
    }
    return render(request, "discovery/catalogue.html", context)


def _parse_query(request) -> str | None:
    """Strip and length-clamp ``q``; a blank value means browse mode (None)."""
    raw = (request.GET.get("q") or "").strip()
    if not raw:
        return None
    return raw[: config.discovery_query_max_length()]


def _parse_page(request) -> int:
    """Coerce ``page`` to an int ≥ 1; the primitive clamps an over-large value to the last page."""
    try:
        page = int(request.GET.get("page", "1"))
    except (TypeError, ValueError):
        return 1
    return max(page, 1)


def _load_facets() -> tuple[dict | None, bool]:
    """Load the active-tag/cluster facets, degrading soft on a taxonomy read error (DESIGN §9)."""
    try:
        return {
            "active_tags": taxonomy.list_active_tags(),
            "clusters": taxonomy.list_clusters(),
        }, False
    except Exception:
        logger.warning("discovery facet read failed; rendering without the sidebar")
        observability.increment(observability.DISCOVERY_FACETS_DEGRADED)
        return None, True


def _resolve_filter(
    request, facets: dict | None
) -> tuple[frozenset[UUID], str | None, str | None]:
    """Expand the ``tag``/``cluster`` param into the catalog match set (DESIGN §6.3).

    ``tag`` and ``cluster`` are mutually exclusive — ``tag`` wins. A valid active ``tag`` is
    expanded via ``tag_ids_resolving_to`` (so the filter matches merged predecessors, AC3); an
    unknown/retired/non-UUID ``tag`` is ignored (no stale filter, no error). A ``cluster``
    expands to the union over its active tags. Returns the match set plus the selected
    tag/cluster ids (as strings) for reflecting the active facet back in the sidebar.
    """
    raw_tag = request.GET.get("tag")
    tag_id = _coerce_uuid(raw_tag)
    if tag_id is not None and taxonomy.is_valid_tag(tag_id):
        return taxonomy.tag_ids_resolving_to(tag_id), str(tag_id), None

    raw_cluster = request.GET.get("cluster")
    cluster_id = _coerce_uuid(raw_cluster)
    if cluster_id is not None and facets is not None:
        cluster = _find_cluster(facets["clusters"], cluster_id)
        if cluster is not None:
            tag_ids = _cluster_tag_ids(cluster)
            if tag_ids:
                return tag_ids, None, str(cluster_id)

    return frozenset(), None, None


def _cluster_tag_ids(cluster) -> frozenset[UUID]:
    """The union of ``tag_ids_resolving_to`` over a cluster's active tags (DESIGN §6.3)."""
    expanded: set[UUID] = set()
    for tag in cluster.tags.all():
        expanded |= taxonomy.tag_ids_resolving_to(tag.id)
    return frozenset(expanded)


def _find_cluster(clusters, cluster_id: UUID):
    """Return the cluster with ``cluster_id`` from the already-loaded facets, or None."""
    for cluster in clusters:
        if cluster.id == cluster_id:
            return cluster
    return None


def _coerce_uuid(raw: str | None) -> UUID | None:
    """Coerce a query-param value to a UUID, or None if absent/malformed (never raises)."""
    if not raw:
        return None
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        return None


def _record_usage(query, tag_ids, page) -> None:
    """Emit the per-request discovery counters (DESIGN §11). Never affects the response."""
    if query:
        observability.increment(observability.DISCOVERY_SEARCH_PERFORMED)
    else:
        observability.increment(observability.DISCOVERY_BROWSE_RENDERED)
    if tag_ids:
        observability.increment(observability.DISCOVERY_TAG_FILTERED)
    if page.total == 0:
        observability.increment(observability.DISCOVERY_ZERO_RESULTS)
