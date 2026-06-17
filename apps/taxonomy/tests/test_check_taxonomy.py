"""Tests for the check_taxonomy integrity command (T-07, DESIGN.md §6/§10)."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.taxonomy import services
from apps.taxonomy.models import Tag

INCREMENT = "apps.taxonomy.management.commands.check_taxonomy.observability.increment"


class CheckTaxonomyTests(TestCase):
    def setUp(self):
        self.cluster = services.add_cluster("productivity", "Productivity")

    def test_clean_vocabulary_exits_zero_without_violation_counter(self):
        services.add_tag("todo-app", "To-do app", clusters=[self.cluster])
        with patch(INCREMENT) as inc:
            call_command("check_taxonomy", stdout=StringIO())  # no exception => exit 0
        inc.assert_not_called()

    def test_orphan_active_tag_fails_non_zero_and_counts_violation(self):
        Tag.objects.create(slug="orphan", label="Orphan")  # bypass service => manufacture orphan
        with patch(INCREMENT) as inc:
            with self.assertRaises(CommandError):
                call_command("check_taxonomy", stdout=StringIO(), stderr=StringIO())
        inc.assert_called_once()

    def test_empty_cluster_is_warned_not_failed(self):
        # self.cluster has no tags; nothing else exists → a warning, clean exit.
        out = StringIO()
        call_command("check_taxonomy", stdout=out)
        self.assertIn("WARNING", out.getvalue())
        self.assertIn("productivity", out.getvalue())
