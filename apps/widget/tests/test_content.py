"""T-04 — the render-contract assembler (DESIGN §5.2/§7/§8).

Covers the populated/empty/degraded/unavailable shapes of ``build_widget_view`` against real
ORM-seeded catalog + ``updates_notice`` rows (no HTTP): newest-first capped notices (AC1), the
truthful empty state (AC2), the live read (AC3), the fail-soft notice-read split, and the
not-available gate. Reuses the ``updates`` test fixtures (one accepted-app builder, no
duplication).
"""

import uuid
from datetime import UTC, datetime
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.updates.models import Notice, NoticeKind
from apps.updates.tests.helpers import make_accepted_app, make_developer, make_tag
from apps.widget import content


def _seed_notice(author, app_id, *, title="Notice", kind=NoticeKind.UPDATE, when=None):
    notice = Notice.objects.create(
        author=author, app_id=app_id, kind=kind, title=title, summary="body"
    )
    if when is not None:
        Notice.objects.filter(pk=notice.pk).update(published_at=when)
    return notice


class BuildWidgetViewTests(TestCase):
    def setUp(self):
        self.developer = make_developer()
        self.app = make_accepted_app(
            self.developer, tag_ids=[make_tag("notes").id], name="Widget Demo"
        )

    def test_returns_notices_newest_first_capped_with_name_and_link(self):
        # Seven notices on a default limit of five → the five newest, newest-first (AC1).
        for day in range(1, 8):
            _seed_notice(
                self.developer,
                self.app.id,
                title=f"Day {day}",
                when=datetime(2026, 6, day, tzinfo=UTC),
            )
        view = content.build_widget_view(self.app.id)
        self.assertIsNotNone(view)
        self.assertEqual(view.app_name, "Widget Demo")
        self.assertEqual(
            view.app_page_path, reverse("pages:app-page", args=[self.app.id])
        )
        self.assertEqual(len(view.notices), 5)
        self.assertEqual(
            [n.title for n in view.notices],
            ["Day 7", "Day 6", "Day 5", "Day 4", "Day 3"],
        )
        self.assertFalse(view.notices_degraded)

    @override_settings(WIDGET_NOTICE_LIMIT=2)
    def test_cap_honors_the_config_limit(self):
        for day in range(1, 5):
            _seed_notice(
                self.developer, self.app.id, when=datetime(2026, 6, day, tzinfo=UTC)
            )
        view = content.build_widget_view(self.app.id)
        self.assertEqual(len(view.notices), 2)

    def test_empty_is_truthful_not_degraded(self):
        view = content.build_widget_view(self.app.id)  # AC2
        self.assertEqual(view.notices, [])
        self.assertFalse(view.notices_degraded)
        self.assertEqual(view.app_name, "Widget Demo")  # name + link still present

    def test_reads_notices_live(self):
        notice = _seed_notice(self.developer, self.app.id, title="Live")
        self.assertEqual(len(content.build_widget_view(self.app.id).notices), 1)  # AC3
        Notice.objects.filter(pk=notice.pk).delete()
        self.assertEqual(content.build_widget_view(self.app.id).notices, [])

    def test_notice_read_failure_degrades_link_only_and_counts(self):
        _seed_notice(self.developer, self.app.id, title="Hidden by the failure")
        with mock.patch(
            "apps.widget.content.updates.published_notices_for_apps",
            side_effect=RuntimeError("updates down"),
        ), mock.patch("apps.widget.content.observability.increment") as inc:
            view = content.build_widget_view(self.app.id)
        self.assertEqual(view.notices, [])
        self.assertTrue(view.notices_degraded)  # not a fabricated "no updates"
        self.assertEqual(view.app_name, "Widget Demo")  # name + link still render
        self.assertEqual(
            view.app_page_path, reverse("pages:app-page", args=[self.app.id])
        )
        inc.assert_called_once_with("widget_notices_degraded")

    def test_unknown_or_unaccepted_app_returns_none(self):
        self.assertIsNone(content.build_widget_view(uuid.uuid4()))  # D-6 gate
