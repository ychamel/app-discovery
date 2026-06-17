"""URL configuration for the taxonomy read API (DESIGN.md §5c).

Mounted under ``taxonomy/`` by the project URLconf, giving the three read endpoints
``/taxonomy/tags``, ``/taxonomy/tags/{id}``, and ``/taxonomy/clusters``.
"""

from django.urls import path

from apps.taxonomy.views import ClusterListView, TagDetailView, TagListView

app_name = "taxonomy"

urlpatterns = [
    path("tags", TagListView.as_view(), name="tag-list"),
    path("tags/<uuid:tag_id>", TagDetailView.as_view(), name="tag-detail"),
    path("clusters", ClusterListView.as_view(), name="cluster-list"),
]
