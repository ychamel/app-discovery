"""Tests for apps.widget.kinds — the closed widget vocabularies (T-01).

``WidgetConversionKind`` is the single source of truth for the conversion ``kind`` column,
the ``record_widget_conversion`` writer, and the conversion selectors. These tests pin its
membership and assert it stays a **separate** vocabulary from ``WidgetEventKind`` (reach and
conversion are distinct facts in distinct tables — DESIGN §6.1), so a future edit to one enum
can never silently bleed members into the other.
"""

from django.test import SimpleTestCase

from apps.widget.kinds import WidgetConversionKind, WidgetEventKind


class WidgetConversionKindTests(SimpleTestCase):
    def test_values_are_exactly_follow_and_account(self):
        self.assertEqual(list(WidgetConversionKind.values), ["follow", "account"])

    def test_is_disjoint_from_the_reach_event_vocabulary(self):
        # Reach kinds and conversion kinds must share no member — they name different facts
        # in different tables, so a string from one is never valid for the other.
        self.assertEqual(
            set(WidgetConversionKind.values) & set(WidgetEventKind.values),
            set(),
        )
