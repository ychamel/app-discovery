"""DRF read shapes for the taxonomy API (DESIGN.md §5c).

Read-only projections of the models. They contain shape only — no business logic —
since the views delegate all read/filter/resolve work to ``apps.taxonomy.selectors``.
"""

from rest_framework import serializers


class ClusterRefSerializer(serializers.Serializer):
    """A cluster as referenced from within a tag (endpoints #1/#2)."""

    id = serializers.UUIDField(read_only=True)
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class TagRefSerializer(serializers.Serializer):
    """A tag as referenced from within a cluster (endpoint #3)."""

    id = serializers.UUIDField(read_only=True)
    label = serializers.CharField(read_only=True)


class TagListSerializer(serializers.Serializer):
    """An active tag in the list view (endpoint #1)."""

    id = serializers.UUIDField(read_only=True)
    slug = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    definition = serializers.CharField(read_only=True)
    clusters = ClusterRefSerializer(many=True, read_only=True)


class TagDetailSerializer(serializers.Serializer):
    """A single tag of any status, exposing lifecycle fields so a consumer can render a
    retired/remapped reference (endpoint #2)."""

    id = serializers.UUIDField(read_only=True)
    slug = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    definition = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    replaced_by = serializers.UUIDField(source="replaced_by_id", read_only=True, allow_null=True)
    clusters = ClusterRefSerializer(many=True, read_only=True)


class ClusterListSerializer(serializers.Serializer):
    """A cluster with its active tags (endpoint #3)."""

    id = serializers.UUIDField(read_only=True)
    slug = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    tags = TagRefSerializer(many=True, read_only=True)
