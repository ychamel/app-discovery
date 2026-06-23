"""The single read path for the catalog (DESIGN.md §5b/§9/§11).

Every consumer — the developer's "my apps", the admin review queue, and the **downstream
catalogue** that ``app-pages``/``signal-capture``/``editorial-curation-tools`` read — goes
through these functions. Nothing reads ``catalog_app`` directly past this surface (D-6).

The two cross-feature guarantees live here:

  * **Accepted-only catalogue (AC9/D-6):** ``list_catalogued_apps`` / ``get_catalogued_app``
    return *only* ``accepted`` apps. A pending/rejected/withdrawn app is never presented as
    catalogued.
  * **Tags resolved at read (D-5):** each stored ``tag_id`` is dereferenced through
    ``taxonomy.resolve_tag`` (follows renames/merges, keeps retired refs), so the catalogue
    never shows a stale label and never drops a reference.

Owner reads are owner-scoped: a non-owner's id is indistinguishable from "not found"
(AC8 — no leak, no enumeration).
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from uuid import UUID

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Count, Subquery

from apps.catalog.models import App, AppTag, ReviewDecision
from apps.core import config
from apps.taxonomy import selectors as taxonomy


# --- Read DTOs ---------------------------------------------------------------
@dataclass(frozen=True)
class CatalogTag:
    """A tag on a catalogued app, already resolved to its current meaning (D-5)."""

    id: UUID
    label: str


@dataclass(frozen=True)
class CatalogMedia:
    """One screenshot of a catalogued app, in stable display order."""

    id: UUID
    url: str
    alt_text: str
    position: int


@dataclass(frozen=True)
class CatalogApp:
    """The downstream view of one accepted app — the D-6 cross-feature shape (§11)."""

    id: UUID
    name: str
    description: str
    url: str
    tags: list[CatalogTag]
    media: list[CatalogMedia]


@dataclass(frozen=True)
class ReviewRow:
    """One pending app awaiting review, with the duplicate signal (no priority field, AC3)."""

    app: App
    owner: object
    submitted_at: datetime
    duplicate_hint: int  # number of *other* apps sharing this normalized URL (§6c)


# --- Owner reads (owner-scoped; AC8) -----------------------------------------
def get_owned_app(owner, app_id) -> App | None:
    """Return the caller's app by id, or None if it is not theirs (no leak, AC8)."""
    return (
        App.objects.filter(owner=owner, pk=app_id)
        .prefetch_related("media", "app_tags")
        .first()
    )


def list_owned_apps(owner) -> list[App]:
    """The developer's "my apps" — every app they own, any status, newest first."""
    return list(
        App.objects.filter(owner=owner).prefetch_related("media", "app_tags")
    )


# --- Review queue (FIFO; AC3 — no priority) ----------------------------------
def list_review_queue() -> list[ReviewRow]:
    """Pending apps in strict FIFO order by ``last_submitted_at``, each with a dup hint (§6c).

    The hint counts other apps sharing the same normalized URL — computed in **one** grouped
    query (no N+1). The queue carries no priority/tier field: order is submission time only.
    """
    pending = list(
        App.objects.filter(status=App.Status.PENDING)
        .select_related("owner")
        .order_by("last_submitted_at")
    )
    counts = _url_share_counts([app.normalized_url for app in pending])
    return [
        ReviewRow(
            app=app,
            owner=app.owner,
            submitted_at=app.last_submitted_at,
            duplicate_hint=max(counts.get(app.normalized_url, 1) - 1, 0),
        )
        for app in pending
    ]


def get_app_for_review(app_id) -> App | None:
    """Fetch any app by id for the admin review surface, or None (DESIGN.md §5c #10).

    Unlike ``get_owned_app`` this is **not** owner-scoped — review is admin-gated and acts
    on every developer's app identically (AC3). It is the single read used by the decision
    endpoint so that surface never touches the ORM directly (D-6).
    """
    return App.objects.filter(pk=app_id).select_related("owner").first()


def apps_sharing_url(normalized_url, *, exclude=None) -> list[App]:
    """All apps whose normalized URL matches — the duplicate signal (§6c), never a constraint."""
    queryset = App.objects.filter(normalized_url=normalized_url)
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude)
    return list(queryset)


def _url_share_counts(normalized_urls: list[str]) -> dict[str, int]:
    """Map each normalized URL to how many apps (any status) carry it — one grouped query."""
    rows = (
        App.objects.filter(normalized_url__in=normalized_urls)
        .values_list("normalized_url")
        .annotate(n=Count("id"))
    )
    return {url: n for url, n in rows}


# --- Open discovery surface (paginated, DB-pushed; open-search-browse §6.1) --
@dataclass(frozen=True)
class CatalogPage:
    """One page of the accepted catalogue, already in final neutral order (DESIGN §6.1)."""

    apps: list[CatalogApp]  # the page; each element is the existing D-6 CatalogApp shape
    total: int  # total accepted apps matching the filter (for "N results" + page count)
    page: int  # 1-based page actually returned (clamped into range)
    page_size: int  # the page size applied
    has_next: bool  # page < ceil(total / page_size)


def search_catalogue(
    *,
    query: str | None = None,
    tag_ids: Collection[UUID] | None = None,
    page: int = 1,
    page_size: int | None = None,
) -> CatalogPage:
    """The open discovery read: a neutrally-ordered page of accepted apps (DESIGN §6.1, AC9).

    The one place that knows how to *query* the catalogue for a page — keyword match, tag-set
    filter, neutral ordering, and pagination, all pushed into the database so the work per
    page is bounded regardless of catalogue size (the existing ``list_catalogued_apps``
    materializes the whole catalogue and cannot scale to a paginated surface).

    Coercion: ``query`` is stripped (blank ⇒ browse mode); ``tag_ids`` is the **already
    expanded** match set (discovery, not catalog, owns merge resolution — clean separation);
    ``page`` is clamped to ``[1, last_page]``; ``page_size`` defaults to
    ``config.discovery_page_size()`` and is clamped to ``[1, config.discovery_page_size_max()]``.

    Filter: always ``status=ACCEPTED`` (pending/rejected/withdrawn are unrepresentable in a
    result, AC1/AC2); ``+`` an FTS match when ``query`` is given; ``+`` carrying a tag in
    ``tag_ids`` when given. Keyword and tag compose (AND).

    Order — the AC5 invariant, only neutral non-purchasable keys: keyword present →
    relevance, then ``accepted_at`` DESC, then ``id``; keyword absent → ``accepted_at`` DESC,
    then ``id``. ``id`` is the stable final tie-break (deterministic pagination). **No
    payment/tier/score/impression term participates** — position-neutrality is structural.

    Returns a valid (possibly empty) page; raises only on a genuine DB failure — never a fake
    empty page that would hide an outage (DESIGN §7/§9).
    """
    keyword = (query or "").strip()
    size = _clamp_page_size(page_size)

    matches = _accepted_matching(keyword, tag_ids)
    total = matches.count()
    last_page = max(1, ceil(total / size)) if total else 1
    current_page = min(max(page, 1), last_page)
    offset = (current_page - 1) * size

    ordered = _apply_neutral_order(matches, keyword)
    page_apps = list(
        ordered.prefetch_related("media", "app_tags")[offset : offset + size]
    )
    resolved = _resolve_tag_labels(page_apps)
    return CatalogPage(
        apps=[_to_catalog_app(app, resolved) for app in page_apps],
        total=total,
        page=current_page,
        page_size=size,
        has_next=current_page < last_page,
    )


def _clamp_page_size(page_size: int | None) -> int:
    """Resolve and clamp the page size to ``[1, discovery_page_size_max()]`` (DESIGN §6.1)."""
    size = config.discovery_page_size() if page_size is None else page_size
    return max(1, min(size, config.discovery_page_size_max()))


def _accepted_matching(keyword: str, tag_ids: Collection[UUID] | None):
    """The accepted-only queryset filtered by keyword (FTS) and/or tag set — no ordering yet.

    The tag filter is expressed as ``id IN (app_tags carrying a wanted tag)`` rather than a
    join, so a multi-tag app is counted once with no ``.distinct()`` (which would otherwise
    collide with ordering by the ``SearchRank`` annotation in Postgres).
    """
    queryset = App.objects.filter(status=App.Status.ACCEPTED)
    if keyword:
        queryset = queryset.filter(
            search_vector=SearchQuery(keyword, search_type="websearch")
        )
    if tag_ids:
        carrier_ids = AppTag.objects.filter(tag_id__in=tag_ids).values("app_id")
        queryset = queryset.filter(id__in=Subquery(carrier_ids))
    return queryset


def _apply_neutral_order(queryset, keyword: str):
    """Order by neutral, non-purchasable keys only — the AC5/M5 position-neutrality invariant.

    Keyword present → keyword relevance, then newest-accepted, then id; keyword absent →
    newest-accepted, then id. ``id`` is the deterministic final tie-break. No paid/tier/
    score/impression input exists here, so position cannot be bought (DESIGN §6.1).
    """
    if keyword:
        ranked = queryset.annotate(
            rank=SearchRank("search_vector", SearchQuery(keyword, search_type="websearch"))
        )
        return ranked.order_by("-rank", "-accepted_at", "id")
    return queryset.order_by("-accepted_at", "id")


# --- Downstream catalogue (ACCEPTED only; AC9/D-6) ---------------------------
def list_catalogued_apps() -> list[CatalogApp]:
    """Every accepted app as its downstream shape: resolved tags + ordered media (AC9/D-6).

    Media and tag links are prefetched and tags are resolved through a single deduped pass,
    so a list read does not N+1 on the number of apps.
    """
    apps = list(
        App.objects.filter(status=App.Status.ACCEPTED).prefetch_related("media", "app_tags")
    )
    resolved = _resolve_tag_labels(apps)
    return [_to_catalog_app(app, resolved) for app in apps]


def get_catalogued_app(app_id) -> CatalogApp | None:
    """Return an accepted app's downstream shape, or None if it is not accepted (AC9/D-6)."""
    app = (
        App.objects.filter(pk=app_id, status=App.Status.ACCEPTED)
        .prefetch_related("media", "app_tags")
        .first()
    )
    if app is None:
        return None
    return _to_catalog_app(app, _resolve_tag_labels([app]))


def get_catalogued_apps(app_ids: list[UUID]) -> list[CatalogApp]:
    """Accepted apps among ``app_ids`` as their D-6 shape — bulk, accepted-only, no N+1.

    The by-ids counterpart to ``get_catalogued_app``, for a consumer (e.g. the followed-apps
    feed) that resolves many ids at once: reading them one-by-one is O(N) queries, and reading
    the whole catalogue is unbounded in catalog size. This is two queries regardless of N (the
    same prefetch + deduped tag resolution as ``list_catalogued_apps``).

    Non-accepted/unknown ids are **silently absent** — same accepted-only guarantee and
    ``CatalogApp`` shape as the single read; the caller orders the result and handles gaps
    (a later withdrawal simply drops out). An empty input returns ``[]``.
    """
    apps = list(
        App.objects.filter(pk__in=app_ids, status=App.Status.ACCEPTED)
        .prefetch_related("media", "app_tags")
    )
    resolved = _resolve_tag_labels(apps)
    return [_to_catalog_app(app, resolved) for app in apps]


def _resolve_tag_labels(apps: list[App]) -> dict[UUID, CatalogTag]:
    """Resolve every stored tag_id across ``apps`` once (deduped) → its current CatalogTag.

    A reference that never existed is dropped; a renamed/merged tag resolves to its current
    meaning; a retired-but-kept tag resolves to itself (D-5 — nothing silently lost).
    """
    tag_ids = {app_tag.tag_id for app in apps for app_tag in app.app_tags.all()}
    resolved: dict[UUID, CatalogTag] = {}
    for tag_id in tag_ids:
        tag = taxonomy.resolve_tag(tag_id)
        if tag is not None:
            resolved[tag_id] = CatalogTag(id=tag.id, label=tag.label)
    return resolved


def _to_catalog_app(app: App, resolved: dict[UUID, CatalogTag]) -> CatalogApp:
    tags = [
        resolved[app_tag.tag_id]
        for app_tag in app.app_tags.all()
        if app_tag.tag_id in resolved
    ]
    media = [
        CatalogMedia(
            id=item.id,
            url=item.image.url,
            alt_text=item.alt_text,
            position=item.position,
        )
        for item in sorted(app.media.all(), key=lambda m: m.position)
    ]
    return CatalogApp(
        id=app.id,
        name=app.name,
        description=app.description,
        url=app.url,
        tags=tags,
        media=media,
    )


# --- Time-to-decision reporting (observable, not an SLA counter; §9/D-2) -----
def time_to_decision(app) -> timedelta | None:
    """Latest decision time minus the app's last submission time, or None if undecided.

    Computed purely from stored timestamps (``ReviewDecision.created_at −
    App.last_submitted_at``) — a reporting value, never a hard SLA (CLAUDE.md §6.2).
    """
    latest = (
        ReviewDecision.objects.filter(app=app).order_by("-created_at").first()
    )
    if latest is None:
        return None
    return latest.created_at - app.last_submitted_at


def decision_latencies() -> list[timedelta]:
    """Time-to-decision for every app that has at least one decision (reporting only)."""
    latencies: list[timedelta] = []
    decided = App.objects.filter(decisions__isnull=False).distinct()
    for app in decided:
        latency = time_to_decision(app)
        if latency is not None:
            latencies.append(latency)
    return latencies
