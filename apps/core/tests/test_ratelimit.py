"""Tests for the rate-limit decorator — pass, 429, isolation, reset (T-04)."""

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.ratelimit import rate_limited


@rate_limited
def _ok_view(request):
    return HttpResponse("ok", status=200)


@override_settings(RATE_LIMIT_PER_EMAIL_PER_HOUR=3, RATE_LIMIT_PER_IP_PER_HOUR=100)
class PerEmailLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.factory = RequestFactory()

    def _post(self, email, ip="10.0.0.1"):
        request = self.factory.post("/auth/register", {"email": email}, REMOTE_ADDR=ip)
        return _ok_view(request)

    def test_under_limit_passes(self):
        for _ in range(3):
            self.assertEqual(self._post("a@example.com").status_code, 200)

    def test_over_limit_returns_429(self):
        for _ in range(3):
            self._post("a@example.com")
        self.assertEqual(self._post("a@example.com").status_code, 429)

    def test_limit_is_per_email(self):
        for _ in range(3):
            self._post("a@example.com")
        # A different email (same IP, well under the IP cap) is unaffected.
        self.assertEqual(self._post("b@example.com").status_code, 200)

    def test_email_is_case_insensitive(self):
        for _ in range(3):
            self._post("A@Example.com")
        self.assertEqual(self._post("a@example.com").status_code, 429)

    def test_window_reset_restores_allowance(self):
        for _ in range(3):
            self._post("a@example.com")
        self.assertEqual(self._post("a@example.com").status_code, 429)
        cache.clear()  # simulates the hourly window expiring
        self.assertEqual(self._post("a@example.com").status_code, 200)


@override_settings(RATE_LIMIT_PER_EMAIL_PER_HOUR=100, RATE_LIMIT_PER_IP_PER_HOUR=2)
class PerIpLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.factory = RequestFactory()

    def _post(self, email, ip):
        request = self.factory.post("/auth/register", {"email": email}, REMOTE_ADDR=ip)
        return _ok_view(request)

    def test_over_ip_limit_returns_429_across_distinct_emails(self):
        for i in range(2):
            self.assertEqual(self._post(f"u{i}@x.com", "10.0.0.9").status_code, 200)
        self.assertEqual(self._post("u3@x.com", "10.0.0.9").status_code, 429)

    def test_limit_is_per_ip(self):
        for i in range(2):
            self._post(f"u{i}@x.com", "10.0.0.9")
        self.assertEqual(self._post("z@x.com", "10.0.0.10").status_code, 200)
