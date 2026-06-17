"""Read-only JSON API for the interest vocabulary (DESIGN.md §5c).

Each view is a thin projection of ``apps.taxonomy.selectors`` — it serializes what the
selector returns and contains no ORM access or business logic of its own. Reads require
an authenticated session (the project-wide DRF default ``IsAuthenticated``) but no
special role: any signed-in user may read the vocabulary to pick interests. There are
no write endpoints at MVP (curation = seed command + Django admin, §6).
"""

from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.taxonomy import selectors
from apps.taxonomy.serializers import (
    ClusterListSerializer,
    TagDetailSerializer,
    TagListSerializer,
)


class TagListView(APIView):
    """GET /taxonomy/tags — all active tags with their clusters (endpoint #1)."""

    def get(self, request):
        tags = selectors.list_active_tags()
        return Response(TagListSerializer(tags, many=True).data)


class TagDetailView(APIView):
    """GET /taxonomy/tags/{id} — one tag of any status; 404 if unknown (endpoint #2)."""

    def get(self, request, tag_id):
        tag = selectors.get_tag(tag_id)
        if tag is None:
            raise NotFound("No tag with that id.")
        return Response(TagDetailSerializer(tag).data)


class ClusterListView(APIView):
    """GET /taxonomy/clusters — all clusters, each with its active tags (endpoint #3)."""

    def get(self, request):
        clusters = selectors.list_clusters()
        return Response(ClusterListSerializer(clusters, many=True).data)
