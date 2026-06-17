"""Guards the shipped founding vocabulary (T-09, DESIGN.md §12).

These run against the *real* ``seed/vocabulary.yaml`` so the founding content can't rot
silently: it must apply cleanly, pass the integrity invariants (AC5), apply idempotently,
and stay within the editorial size band recorded in DECISIONS (ITX-12 / OQ-3).
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.taxonomy import services
from apps.taxonomy.models import Cluster, Tag

# Editorial size band for the single beachhead niche (ITX-12 / OQ-3). A guard rail, not a
# target: it catches accidental bloat (synonym creep, R2) or collapse, while leaving room
# to grow. Revisit when a real submitted catalog exists (deferral recorded in OPEN_QUESTIONS).
MIN_TAGS, MAX_TAGS = 40, 90
MIN_CLUSTERS, MAX_CLUSTERS = 6, 16


class FoundingVocabularyTests(TestCase):
    def test_shipped_seed_applies_and_passes_integrity(self):
        call_command("seed_taxonomy", stdout=StringIO())
        report = services.check_integrity()
        self.assertTrue(report.is_clean, f"founding vocabulary is not clean: {report}")
        # Every active tag is in ≥1 cluster (AC5) — i.e. no orphans.
        self.assertEqual(report.orphan_active_tags, [])

    def test_shipped_seed_is_idempotent(self):
        call_command("seed_taxonomy", stdout=StringIO())
        tag_count = Tag.objects.count()
        cluster_count = Cluster.objects.count()
        call_command("seed_taxonomy", stdout=StringIO())  # re-apply
        self.assertEqual(Tag.objects.count(), tag_count)
        self.assertEqual(Cluster.objects.count(), cluster_count)

    def test_size_band_within_editorial_range(self):
        call_command("seed_taxonomy", stdout=StringIO())
        self.assertTrue(MIN_CLUSTERS <= Cluster.objects.count() <= MAX_CLUSTERS)
        self.assertTrue(MIN_TAGS <= Tag.objects.count() <= MAX_TAGS)
