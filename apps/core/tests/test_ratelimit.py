"""Tests for the rate-limit decorators — pass, 429, isolation, reset, fail-open (T-04, T-03)."""

from unittest import mock

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core import config
from apps.core.ratelimit import ip_rate_limited_get, rate_limited


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


def _build_get_view(limit_fn, **kwargs):
    """A GET view wrapped by the per-IP limiter that records whether its body ran."""
    calls = {"n": 0}

    @ip_rate_limited_get(limit_fn, scope="test_widget", **kwargs)
    def view(request):
        calls["n"] += 1
        return HttpResponse("ok", status=200)

    return view, calls


class IpRateLimitedGetTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.factory = RequestFactory()

    def _get(self, view, ip="10.0.0.1"):
        return view(self.factory.get("/widget/x/", REMOTE_ADDR=ip))

    def test_under_limit_passes_through(self):
        view, calls = _build_get_view(lambda: 3)
        for _ in range(3):
            self.assertEqual(self._get(view).status_code, 200)
        self.assertEqual(calls["n"], 3)

    def test_over_limit_returns_429_and_does_not_call_the_view(self):
        view, calls = _build_get_view(
            lambda: 2, limited_metric="widget_rate_limited"
        )
        for _ in range(2):
            self.assertEqual(self._get(view).status_code, 200)
        with mock.patch("apps.core.ratelimit.observability.increment") as inc:
            response = self._get(view)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(calls["n"], 2)  # the 3rd request never ran the body
        inc.assert_called_once_with("widget_rate_limited")

    def test_limit_is_per_ip(self):
        view, _ = _build_get_view(lambda: 1)
        self.assertEqual(self._get(view, ip="10.0.0.1").status_code, 200)
        self.assertEqual(self._get(view, ip="10.0.0.1").status_code, 429)
        # A different IP has its own fresh allowance.
        self.assertEqual(self._get(view, ip="10.0.0.2").status_code, 200)

    def test_window_reset_restores_allowance(self):
        view, _ = _build_get_view(lambda: 1)
        self._get(view)
        self.assertEqual(self._get(view).status_code, 429)
        cache.clear()  # simulates the window expiring
        self.assertEqual(self._get(view).status_code, 200)

    @override_settings(WIDGET_RENDER_RATE_LIMIT_PER_IP_PER_MINUTE=2)
    def test_limit_is_config_driven(self):
        view, _ = _build_get_view(config.widget_render_rate_limit_per_ip_per_minute)
        for _ in range(2):
            self.assertEqual(self._get(view).status_code, 200)
        self.assertEqual(self._get(view).status_code, 429)

    def test_cache_error_fails_open_and_counts_degraded(self):
        view, calls = _build_get_view(lambda: 1, degraded_metric="widget_limiter_degraded")
        with mock.patch(
            "apps.core.ratelimit.cache.add", side_effect=RuntimeError("cache down")
        ), mock.patch("apps.core.ratelimit.observability.increment") as inc:
            response = self._get(view)
        self.assertEqual(response.status_code, 200)  # served despite the cache outage
        self.assertEqual(calls["n"], 1)  # the body ran (fail-open)
        inc.assert_called_once_with("widget_limiter_degraded")

    def test_non_get_passes_through_unlimited(self):
        view, calls = _build_get_view(lambda: 1)
        # POST is not a read — the limiter ignores it so the view's own method gate applies.
        for _ in range(5):
            response = view(self.factory.post("/widget/x/", REMOTE_ADDR="10.0.0.1"))
            self.assertEqual(response.status_code, 200)
        self.assertEqual(calls["n"], 5)
