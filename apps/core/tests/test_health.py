"""Health endpoint and metric-emission tests (T-17, DESIGN.md §10)."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.core import observability


class HealthEndpointTests(TestCase):
    def test_healthy_when_db_and_email_ok(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["database"])
        self.assertTrue(body["email"])

    def test_degraded_returns_503_when_a_dependency_fails(self):
        with mock.patch("apps.core.observability._email_ok", return_value=False):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertFalse(response.json()["email"])


class LivenessEndpointTests(TestCase):
    """The DB-only liveness probe (platform-staging T-07, DESIGN §4.6)."""

    def test_live_ok_when_db_reachable(self):
        response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_live_down_returns_503_when_db_unreachable(self):
        with mock.patch("apps.core.views._database_ok", return_value=False):
            response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "down"})

    def test_live_never_opens_an_smtp_connection(self):
        """An email outage must not affect liveness (the whole point of the split)."""
        with mock.patch("apps.core.observability._email_ok") as email_probe:
            response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        email_probe.assert_not_called()


class MetricEmissionTests(TestCase):
    def test_increment_emits_named_metric_with_tags(self):
        with self.assertLogs("apps.metrics", level="INFO") as captured:
            observability.increment(observability.ROLE_GATE_DECISION, result="deny")
        output = "\n".join(captured.output)
        self.assertIn("metric=role_gate_decisions", output)
        self.assertIn("result=deny", output)

    def test_increment_never_raises(self):
        # Even with a bad tag value, observability must not break the caller.
        observability.increment("anything", weird=object())
