"""T-03 — the single read surface ``selectors`` (DESIGN §5.2).

Reads run against the real D-5 ``resolve_tag`` and real ``retire_tag`` states (AC7/AC8).
"""

import uuid

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.interests import selectors
from apps.interests.models import Interest
from apps.interests.tests.helpers import make_tag, make_user
from apps.taxonomy import services as taxonomy_services


class DeclaredTagIdsTests(TestCase):
    def test_returns_a_frozenset_of_resolved_tag_ids(self):
        # AC8: the matcher contract is a frozenset of Tag.ids — never labels/slugs.
        user = make_user()
        a, b = make_tag("calm"), make_tag("focus")
        Interest.objects.create(user=user, tag_id=a.id)
        Interest.objects.create(user=user, tag_id=b.id)
        result = selectors.declared_tag_ids(user)
        self.assertIsInstance(result, frozenset)
        self.assertEqual(result, {a.id, b.id})

    def test_renamed_ref_resolves_to_its_successor(self):
        # AC7: a stored id whose tag was merged into a successor appears AS the successor.
        user = make_user()
        old, successor = make_tag("old"), make_tag("new")
        Interest.objects.create(user=user, tag_id=old.id)
        taxonomy_services.retire_tag(old, replaced_by=successor)
        self.assertEqual(selectors.declared_tag_ids(user), {successor.id})

    def test_no_successor_retired_ref_resolves_to_itself_and_is_kept(self):
        # AC7: a no-successor retired stored id is never silently dropped (M5 = 0).
        user = make_user()
        retired = make_tag("legacy")
        Interest.objects.create(user=user, tag_id=retired.id)
        taxonomy_services.retire_tag(retired, replaced_by=None)
        self.assertEqual(selectors.declared_tag_ids(user), {retired.id})

    def test_two_ids_resolving_to_one_successor_dedupe(self):
        user = make_user()
        old_a, old_b, successor = make_tag("a"), make_tag("b"), make_tag("c")
        Interest.objects.create(user=user, tag_id=old_a.id)
        Interest.objects.create(user=user, tag_id=old_b.id)
        Interest.objects.create(user=user, tag_id=successor.id)
        taxonomy_services.retire_tag(old_a, replaced_by=successor)
        taxonomy_services.retire_tag(old_b, replaced_by=successor)
        self.assertEqual(selectors.declared_tag_ids(user), {successor.id})

    def test_empty_and_anonymous_users(self):
        # AC6: zero rows → empty; anonymous/None → empty.
        empty_user = make_user()
        self.assertEqual(selectors.declared_tag_ids(empty_user), frozenset())
        self.assertEqual(selectors.declared_tag_ids(AnonymousUser()), frozenset())
        self.assertEqual(selectors.declared_tag_ids(None), frozenset())


class DeclaredTagsTests(TestCase):
    def test_returns_resolved_tag_objects_ordered_by_label(self):
        user = make_user()
        zed, alpha = make_tag("zed", "Zed"), make_tag("alpha", "Alpha")
        Interest.objects.create(user=user, tag_id=zed.id)
        Interest.objects.create(user=user, tag_id=alpha.id)
        tags = selectors.declared_tags(user)
        self.assertEqual([t.label for t in tags], ["Alpha", "Zed"])

    def test_anonymous_returns_empty_list(self):
        self.assertEqual(selectors.declared_tags(AnonymousUser()), [])


class HasDeclaredInterestsTests(TestCase):
    def test_true_only_when_a_row_exists(self):
        user = make_user()
        self.assertFalse(selectors.has_declared_interests(user))
        Interest.objects.create(user=user, tag_id=make_tag("calm").id)
        self.assertTrue(selectors.has_declared_interests(user))

    def test_anonymous_is_false(self):
        self.assertFalse(selectors.has_declared_interests(AnonymousUser()))
        self.assertFalse(selectors.has_declared_interests(None))


class CountUnresolvableTests(TestCase):
    def test_zero_for_a_profile_built_through_the_validated_path(self):
        # The invariant: every validated, soft-retired id still resolves → 0.
        user = make_user()
        a, retired = make_tag("calm"), make_tag("legacy")
        Interest.objects.create(user=user, tag_id=a.id)
        Interest.objects.create(user=user, tag_id=retired.id)
        taxonomy_services.retire_tag(retired, replaced_by=None)  # still resolves to itself
        self.assertEqual(selectors.count_unresolvable(), 0)

    def test_detects_a_hand_inserted_bad_id(self):
        # Proves it *detects* an unresolvable id — not that the write path produces one.
        user = make_user()
        Interest.objects.create(user=user, tag_id=uuid.uuid4())  # references nothing
        self.assertEqual(selectors.count_unresolvable(), 1)


class ReadQueryBoundTests(TestCase):
    def test_declared_tag_ids_query_count_is_bounded_by_the_set_size(self):
        # N+1-free over unrelated data: the query count scales with the user's set size, not
        # with how many other tags/users exist (DESIGN §10).
        user = make_user()
        tag_ids = [make_tag(f"tag-{i}").id for i in range(3)]
        for tag_id in tag_ids:
            Interest.objects.create(user=user, tag_id=tag_id)
        # Noise: other users and tags must not change this user's query count.
        other = make_user("other@example.com")
        Interest.objects.create(user=other, tag_id=make_tag("noise").id)

        with CaptureQueriesContext(connection) as ctx:
            selectors.declared_tag_ids(user)
        # One stored-id read + a bounded resolve per id (get_tag + its cluster prefetch).
        self.assertLessEqual(len(ctx.captured_queries), 1 + 2 * len(tag_ids))
