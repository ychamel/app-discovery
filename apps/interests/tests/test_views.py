"""T-04 — the thin HTTP views picker/save/clear (DESIGN §5.3/§6/§8).

Integration tests through the Django test client against the project URLconf (the
``interests/`` include is live). The write/read logic is unit-tested in T-02/T-03; here we
assert the HTTP contract: auth, CSRF, method gating, PRG, the rendered picker states, and
the fail-soft degraded path.
"""

import uuid
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.core import observability
from apps.interests import selectors
from apps.interests.models import Interest
from apps.interests.tests.helpers import make_tag, make_user


class PickerRenderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_signed_in_get_renders_clusters_with_active_tags(self):
        # AC1/AC5: clusters grouped, active tags labelled.
        tag = make_tag("calm", "Calm")
        response = self.client.get(reverse("interests:picker"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calm")
        self.assertContains(response, str(tag.id))

    def test_saved_tags_are_pre_checked_on_the_next_get(self):
        # AC1: declared tags show as selected on return.
        tag = make_tag("calm", "Calm")
        Interest.objects.create(user=self.user, tag_id=tag.id)
        response = self.client.get(reverse("interests:picker"))
        self.assertContains(response, "checked")

    def test_empty_profile_renders_the_empty_hint_not_an_error(self):
        # AC6: zero declared interests → hint, not an error.
        make_tag("calm")
        response = self.client.get(reverse("interests:picker"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "haven't picked any interests")

    def test_empty_vocabulary_renders_none_available_copy(self):
        # AC6 edge: no active tags at all → "none available", no crash.
        response = self.client.get(reverse("interests:picker"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No interests are available yet")

    def test_retired_tags_are_never_shown(self):
        # AC5: the picker lists only active tags.
        from apps.taxonomy import services as taxonomy_services

        make_tag("calm", "Calm")
        retired = make_tag("legacy", "Legacy")
        taxonomy_services.retire_tag(retired, replaced_by=None)
        response = self.client.get(reverse("interests:picker"))
        self.assertContains(response, "Calm")
        self.assertNotContains(response, "Legacy")


class SaveTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_save_persists_and_prg_redirects(self):
        # AC1: a POST save stores the set and PRG-redirects to the picker.
        a, b = make_tag("calm"), make_tag("focus")
        response = self.client.post(
            reverse("interests:save"), {"tag_id": [str(a.id), str(b.id)]}
        )
        self.assertRedirects(response, reverse("interests:picker"))
        self.assertEqual(selectors.declared_tag_ids(self.user), {a.id, b.id})

    def test_edit_reflects_exactly_the_new_set(self):
        # AC4: add + remove → the next read is exactly the new set.
        a, b, c = make_tag("calm"), make_tag("focus"), make_tag("zen")
        self.client.post(reverse("interests:save"), {"tag_id": [str(a.id), str(b.id)]})
        self.client.post(reverse("interests:save"), {"tag_id": [str(b.id), str(c.id)]})
        self.assertEqual(selectors.declared_tag_ids(self.user), {b.id, c.id})

    def test_invalid_id_rerenders_picker_with_400_and_no_change(self):
        # AC2: an invalid id → 400, the picker re-rendered with the message, nothing persisted.
        a = make_tag("calm")
        self.client.post(reverse("interests:save"), {"tag_id": [str(a.id)]})  # prior state
        response = self.client.post(
            reverse("interests:save"), {"tag_id": [str(a.id), str(uuid.uuid4())]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "valid", status_code=400)
        self.assertEqual(selectors.declared_tag_ids(self.user), {a.id})

    def test_save_to_empty_clears_the_profile(self):
        a = make_tag("calm")
        self.client.post(reverse("interests:save"), {"tag_id": [str(a.id)]})
        self.client.post(reverse("interests:save"), {"tag_id": []})
        self.assertEqual(selectors.declared_tag_ids(self.user), frozenset())

    def test_db_write_failure_surfaces_try_again(self):
        a = make_tag("calm")
        with mock.patch(
            "apps.interests.views.services.set_interests", side_effect=RuntimeError("db down")
        ):
            response = self.client.post(reverse("interests:save"), {"tag_id": [str(a.id)]})
        self.assertContains(response, "save, please try again")


class ClearViewTests(TestCase):
    def test_clear_removes_all_rows_and_prg_redirects(self):
        # AC9: POST clear → all rows gone, PRG to picker.
        user = make_user()
        self.client.force_login(user)
        a, b = make_tag("calm"), make_tag("focus")
        Interest.objects.create(user=user, tag_id=a.id)
        Interest.objects.create(user=user, tag_id=b.id)
        response = self.client.post(reverse("interests:clear"))
        self.assertRedirects(response, reverse("interests:picker"))
        self.assertEqual(Interest.objects.filter(user=user).count(), 0)


class AuthAndMethodTests(TestCase):
    def test_anonymous_get_redirects_to_sign_in_with_next(self):
        response = self.client.get(reverse("interests:picker"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)

    def test_anonymous_post_does_not_write(self):
        user = make_user()
        a = make_tag("calm")
        response = self.client.post(reverse("interests:save"), {"tag_id": [str(a.id)]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Interest.objects.filter(user=user).count(), 0)

    def test_get_on_save_is_405(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("interests:save")).status_code, 405)

    def test_get_on_clear_is_405(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("interests:clear")).status_code, 405)

    def test_post_without_csrf_is_403(self):
        user = make_user()
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        a = make_tag("calm")
        response = csrf_client.post(reverse("interests:save"), {"tag_id": [str(a.id)]})
        self.assertEqual(response.status_code, 403)


class PickerFailSoftTests(TestCase):
    def test_list_clusters_error_renders_degraded_page_not_500(self):
        user = make_user()
        self.client.force_login(user)
        with mock.patch(
            "apps.interests.views.taxonomy.list_clusters", side_effect=RuntimeError("taxonomy down")
        ):
            with mock.patch.object(observability, "increment") as inc:
                response = self.client.get(reverse("interests:picker"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "load interests right now")
        inc.assert_any_call(observability.INTEREST_PICKER_DEGRADED)
