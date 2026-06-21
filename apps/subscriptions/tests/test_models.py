"""T-02 — structural facts about the ``Subscription`` store (DESIGN §4.1/§4.2).

These assert the *shape* the design mandates, independent of any write logic:

  * **AC5 (structural):** no score/weight/rank column — and no ``updated_at`` /
    ``unfollowed_at`` (one job: the row exists or it does not).
  * **AC1:** a unique constraint on ``(user, app_id)`` — one follow per user per app.
  * **DESIGN §4.2:** the ``user`` FK is **CASCADE** (the AS-5/AC9 contrast with ratings'
    SET_NULL) — and **AC9:** deleting the account removes the follow rows with no edit to
    accounts. The ``subscribe``-event SC-10 anonymize-not-purge half is verified in T-03.
"""

from django.db import models
from django.test import TestCase

from apps.accounts.services import delete_account
from apps.subscriptions.models import Subscription
from apps.subscriptions.tests.helpers import make_accepted_app, make_tag, make_user

# Columns that would mean this layer stores a computed value or a mutable/soft-delete attribute
# the design forbids (AC5 / one-job, DESIGN §4.1).
FORBIDDEN_FIELDS = {
    "score",
    "weight",
    "rank",
    "quality",
    "updated_at",
    "unfollowed_at",
    "is_active",
}


class SubscriptionShapeTests(TestCase):
    def _field_names(self) -> set[str]:
        return {field.name for field in Subscription._meta.get_fields()}

    def test_has_only_the_relationship_columns(self):
        # The store is exactly (id, user, app_id, created_at) — no score/updated_at/soft-delete.
        self.assertEqual(
            self._field_names(), {"id", "user", "app_id", "created_at"}
        )

    def test_has_no_forbidden_columns(self):
        self.assertEqual(self._field_names() & FORBIDDEN_FIELDS, set())

    def test_user_fk_is_cascade_on_deletion(self):
        # The deliberate contrast with ratings' SET_NULL: a follow is removed with its account.
        field = Subscription._meta.get_field("user")
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

    def test_app_id_is_a_soft_ref_not_a_db_fk(self):
        field = Subscription._meta.get_field("app_id")
        self.assertIsInstance(field, models.UUIDField)
        self.assertFalse(field.is_relation)

    def test_unique_constraint_on_user_and_app(self):
        constraint = next(
            c
            for c in Subscription._meta.constraints
            if isinstance(c, models.UniqueConstraint)
            and c.name == "subscriptions_one_per_user_app"
        )
        self.assertEqual(tuple(constraint.fields), ("user", "app_id"))


class AccountDeletionTests(TestCase):
    """AC9 (follow-state half) — account deletion CASCADEs the user's follow rows away."""

    def setUp(self):
        self.user = make_user()
        self.owner = make_user("owner@example.com")
        self.app = make_accepted_app(self.owner, tag_ids=[make_tag("notes").id])

    def test_deleting_the_account_removes_its_follow_rows(self):
        # Create follow rows via the ORM directly (this test isolates the CASCADE; the corpus
        # SC-10 half is in T-03's deletion test).
        user_id = self.user.pk  # account.delete() blanks the in-memory pk — capture it first.
        Subscription.objects.create(user=self.user, app_id=self.app.id)
        other_app = make_accepted_app(
            self.owner, name="Other App", tag_ids=[make_tag("other").id]
        )
        Subscription.objects.create(user=self.user, app_id=other_app.id)
        self.assertEqual(Subscription.objects.filter(user_id=user_id).count(), 2)

        delete_account(self.user)

        self.assertFalse(Subscription.objects.filter(user_id=user_id).exists())

    def test_deleting_one_account_leaves_another_users_follows_intact(self):
        other = make_user("other@example.com")
        Subscription.objects.create(user=self.user, app_id=self.app.id)
        Subscription.objects.create(user=other, app_id=self.app.id)

        delete_account(self.user)

        self.assertEqual(Subscription.objects.filter(user=other).count(), 1)
