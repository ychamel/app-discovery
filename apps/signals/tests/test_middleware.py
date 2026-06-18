"""T-06 — PlatformVisitMiddleware: idempotent, anonymous-safe, fail-soft-but-counted (§5d)."""

from datetime import date
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.signals.middleware import PlatformVisitMiddleware
from apps.signals.models import PlatformVisit
from apps.signals.tests.helpers import make_user


class PlatformVisitMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = make_user()
        self.sentinel = HttpResponse("ok")
        self.middleware = PlatformVisitMiddleware(lambda request: self.sentinel)

    def _get(self, user):
        request = self.factory.get("/")
        request.user = user
        return self.middleware(request)

    def test_authenticated_request_records_one_visit(self):
        response = self._get(self.user)
        self.assertIs(response, self.sentinel)
        self.assertEqual(PlatformVisit.objects.filter(user=self.user).count(), 1)

    def test_repeated_requests_same_day_are_idempotent(self):
        self._get(self.user)
        self._get(self.user)
        self.assertEqual(PlatformVisit.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            PlatformVisit.objects.get(user=self.user).visit_date, date.today()
        )

    def test_anonymous_request_records_nothing(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = self.middleware(request)
        self.assertIs(response, self.sentinel)
        self.assertEqual(PlatformVisit.objects.count(), 0)

    def test_capture_failure_is_fail_soft_but_counted(self):
        """A real failure deep in capture is counted (capture_error{kind=visit}) yet the
        response is still returned — navigation is never broken (§5d)."""
        with mock.patch.object(
            PlatformVisit.objects, "get_or_create", side_effect=RuntimeError("db down")
        ):
            with self.assertLogs("apps.metrics", level="INFO") as logs:
                response = self._get(self.user)

        self.assertIs(response, self.sentinel)  # unbroken navigation
        self.assertTrue(
            any("capture_error" in line and "kind=visit" in line for line in logs.output)
        )
