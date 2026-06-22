"""T-01 — structural facts about the ``Interest`` store (DESIGN §4.1).

These assert the *shape* the design mandates, independent of any write logic:

  * **AC8 (structural):** no score/weight/rank column — and no ``updated_at`` / soft-delete
    (one job: the declaration exists or it does not).
  * **AC1/AC4:** a unique constraint on ``(user, tag_id)`` — one row per user per tag.
  * **DESIGN §4.1:** the ``user`` FK is **CASCADE** — and **AC9:** deleting the account
    removes the interest rows with no edit to ``accounts``. There is no corpus residue to
    verify (IP-5: no D-7 event is ever written by this feature).
"""

import uuid

from django.db import models
from django.test import TestCase

from apps.accounts.services import delete_account
from apps.interests.models import Interest
from apps.interests.tests.helpers import make_tag, make_user

# Columns that would mean this layer stores a computed value or a mutable/soft-delete
# attribute the design forbids (AC8 / one-job, DESIGN §4.1).
FORBIDDEN_FIELDS = {
    "score",
    "weight",
    "rank",
    "quality",
    "updated_at",
    "retired_at",
    "is_active",
}


class InterestShapeTests(TestCase):
    def _field_names(self) -> set[str]:
        return {field.name for field in Interest._meta.get_fields()}

    def test_has_only_the_membership_columns(self):
        # The store is exactly (id, user, tag_id, created_at) — no score/updated_at/parent.
        self.assertEqual(self._field_names(), {"id", "user", "tag_id", "created_at"})

    def test_has_no_forbidden_columns(self):
        self.assertEqual(self._field_names() & FORBIDDEN_FIELDS, set())

    def test_user_fk_is_cascade_on_deletion(self):
        # IP-4/AC9: the profile is removed with its account (no edit to accounts).
        field = Interest._meta.get_field("user")
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

    def test_tag_id_is_a_soft_ref_not_a_db_fk(self):
        field = Interest._meta.get_field("tag_id")
        self.assertIsInstance(field, models.UUIDField)
        self.assertFalse(field.is_relation)

    def test_unique_constraint_on_user_and_tag(self):
        constraint = next(
            c
            for c in Interest._meta.constraints
            if isinstance(c, models.UniqueConstraint)
        )
        self.assertEqual(tuple(constraint.fields), ("user", "tag_id"))
        self.assertEqual(constraint.name, "interests_one_per_user_tag")


class InterestDeletionTests(TestCase):
    def test_account_deletion_cascades_interest_rows(self):
        # AC9: account.delete() (via accounts.delete_account) removes the user's interest
        # rows by CASCADE — no edit to accounts, no corpus residue (IP-5).
        user = make_user()
        tag_a = make_tag("calm")
        tag_b = make_tag("focus")
        Interest.objects.create(user=user, tag_id=tag_a.id)
        Interest.objects.create(user=user, tag_id=tag_b.id)
        self.assertEqual(Interest.objects.filter(user=user).count(), 2)

        delete_account(user)

        self.assertEqual(Interest.objects.filter(user_id=user.id).count(), 0)

    def test_other_users_rows_survive_a_deletion(self):
        keeper = make_user("keeper@example.com")
        leaver = make_user("leaver@example.com")
        tag = make_tag("calm")
        Interest.objects.create(user=keeper, tag_id=tag.id)
        Interest.objects.create(user=leaver, tag_id=tag.id)

        delete_account(leaver)

        self.assertEqual(Interest.objects.filter(user=keeper).count(), 1)


class InterestConstraintTests(TestCase):
    def test_declaring_the_same_tag_twice_violates_the_unique_constraint(self):
        from django.db import IntegrityError

        user = make_user()
        tag = make_tag("calm")
        Interest.objects.create(user=user, tag_id=tag.id)
        with self.assertRaises(IntegrityError):
            Interest.objects.create(user=user, tag_id=tag.id)

    def test_same_tag_for_two_users_is_allowed(self):
        a = make_user("a@example.com")
        b = make_user("b@example.com")
        tag = make_tag("calm")
        Interest.objects.create(user=a, tag_id=tag.id)
        Interest.objects.create(user=b, tag_id=tag.id)
        self.assertEqual(Interest.objects.filter(tag_id=tag.id).count(), 2)

    def test_a_user_can_declare_unrelated_tags(self):
        user = make_user()
        Interest.objects.create(user=user, tag_id=uuid.uuid4())
        Interest.objects.create(user=user, tag_id=uuid.uuid4())
        self.assertEqual(Interest.objects.filter(user=user).count(), 2)
