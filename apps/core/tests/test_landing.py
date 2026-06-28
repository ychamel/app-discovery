"""Tests for the static landing page view (T-04, DESIGN.md §5.2)."""

from django.test import TestCase
from django.urls import reverse


class LandingPageTests(TestCase):
    def test_landing_page_returns_200(self):
        """GET / -> 200, is not a redirect."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_contains_required_links_and_text(self):
        """Landing page contains value-prop text and core entry point links."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

        # Verify value-prop text/headline
        self.assertContains(response, "Discover the Best Indie Web Apps")
        self.assertContains(response, "curated catalog")

        # Verify entry-point links
        self.assertContains(response, reverse("discovery:browse"))
        self.assertContains(response, reverse("accounts:register"))
        self.assertContains(response, reverse("accounts:signin"))

    def test_landing_page_emits_metric(self):
        """Landing page logs a landing_rendered metric on access."""
        with self.assertLogs("apps.metrics", level="INFO") as captured:
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        output = "\n".join(captured.output)
        self.assertIn("metric=landing_rendered", output)

    def test_landing_page_issues_no_database_queries(self):
        """Landing page should render without querying the database."""
        with self.assertNumQueries(0):
            response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_post_not_allowed(self):
        """POST / -> 405 Method Not Allowed."""
        response = self.client.post(reverse("home"))
        self.assertEqual(response.status_code, 405)
