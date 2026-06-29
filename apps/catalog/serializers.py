"""DRF read shapes for the catalog API (DESIGN.md §5c).

Read-only projections of an ``App`` and its decisions. They contain shape only — the views
delegate all write/validate work to ``apps.catalog.services`` and all status/resolution
work to ``apps.catalog.selectors``/``apps.taxonomy``. Tags are resolved at read (D-5) and a
rejected app's latest decision carries the failing-floor labels + note so the developer
sees actionable feedback (AC7).
"""

from rest_framework import serializers

from apps.catalog.gate import Criterion
from apps.taxonomy import selectors as taxonomy


class MediaSerializer(serializers.Serializer):
    """One screenshot, in display order."""

    id = serializers.UUIDField(read_only=True)
    url = serializers.SerializerMethodField()
    alt_text = serializers.CharField(read_only=True)
    position = serializers.IntegerField(read_only=True)

    def get_url(self, media) -> str:
        return media.image.url


class TagRefSerializer(serializers.Serializer):
    """A tag reference, resolved to its current id + label (D-5)."""

    id = serializers.UUIDField(read_only=True)
    label = serializers.CharField(read_only=True)


class LatestDecisionSerializer(serializers.Serializer):
    """The most recent gate decision on an app (None until first reviewed)."""

    outcome = serializers.CharField(read_only=True)
    failed_criteria = serializers.SerializerMethodField()
    note = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_failed_criteria(self, decision) -> list[str]:
        return [Criterion(value).label for value in decision.failed_criteria]


class ReviewQueueRowSerializer(serializers.Serializer):
    """One pending app in the admin review queue (endpoint 9). No priority field (AC3)."""

    app = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    submitted_at = serializers.DateTimeField(read_only=True)
    duplicate_hint = serializers.IntegerField(read_only=True)

    def get_app(self, row) -> dict:
        return {"id": str(row.app.id), "name": row.app.name, "url": row.app.url}

    def get_owner(self, row) -> dict:
        return {"id": str(row.owner.id), "email": row.owner.email}


class DecisionResultSerializer(serializers.Serializer):
    """The result of a review decision (endpoint 10)."""

    id = serializers.UUIDField(read_only=True)
    outcome = serializers.CharField(read_only=True)
    failed_criteria = serializers.SerializerMethodField()
    note = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def get_failed_criteria(self, decision) -> list[str]:
        return [Criterion(value).label for value in decision.failed_criteria]


class AppSerializer(serializers.Serializer):
    """The developer's view of one of their apps, any status (endpoints 2/3/etc.)."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    last_submitted_at = serializers.DateTimeField(read_only=True)
    tags = serializers.SerializerMethodField()
    media = MediaSerializer(many=True, read_only=True)
    latest_decision = serializers.SerializerMethodField()
    # Marketing fields round-trip back for editing (app-page-redesign DESIGN.md §8). Facets
    # are returned as plain ``(facet, value)`` pairs (the registry resolves labels at display).
    tagline = serializers.CharField(read_only=True)
    deep_dive = serializers.CharField(read_only=True)
    demo_clip_url = serializers.SerializerMethodField()
    demo_clip_alt = serializers.CharField(read_only=True)
    facets = serializers.SerializerMethodField()

    def get_tags(self, app) -> list[dict]:
        resolved = []
        for app_tag in app.app_tags.all():
            tag = taxonomy.resolve_tag(app_tag.tag_id)
            if tag is not None:
                resolved.append({"id": tag.id, "label": tag.label})
        return TagRefSerializer(resolved, many=True).data

    def get_demo_clip_url(self, app) -> str | None:
        return app.demo_clip.url if app.demo_clip else None

    def get_facets(self, app) -> list[dict]:
        return [
            {"facet": facet.facet, "value": facet.value}
            for facet in app.app_facets.all()
        ]

    def get_latest_decision(self, app) -> dict | None:
        decision = app.decisions.order_by("-created_at").first()
        if decision is None:
            return None
        return LatestDecisionSerializer(decision).data
