from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from insight.services import mcp_client
from mcp_server import analytics


class AnalyticsTests(SimpleTestCase):
    """The pure calculations behind the MCP tools."""

    def test_satisfaction(self):
        result = analytics.satisfaction([5, 4, 3, 2])
        self.assertEqual(result["satisfaction_pct"], 50.0)
        self.assertEqual(result["avg_rating"], 3.5)

    def test_nps(self):
        # 2 promoters, 1 passive, 1 detractor -> (2 - 1) / 4 = 25
        result = analytics.nps([10, 9, 7, 3])
        self.assertEqual(result["nps"], 25.0)
        self.assertEqual(result["level"], "Good")

    def test_complaint_topics(self):
        result = analytics.complaint_topics(["Very slow, long queue", "Prices are too expensive", "slow again"])
        self.assertEqual(result["top_complaints"][0]["topic"], "waiting time")
        self.assertEqual(result["top_complaints"][0]["mentions"], 2)

    def test_empty(self):
        self.assertEqual(analytics.satisfaction([])["level"], "No data")


class APIValidationTests(TestCase):
    def test_unknown_branch_returns_400(self):
        response = APIClient().post("/api/analyze/", {"branch_id": 999}, format="json")
        self.assertEqual(response.status_code, 400)


class MCPServerTests(SimpleTestCase):
    """Starts the real MCP server and checks it exposes tools, resources and prompts."""

    def test_capabilities(self):
        caps = mcp_client.get_capabilities()
        self.assertIn("satisfaction_score", [t["name"] for t in caps["tools"]])
        self.assertIn("insight://benchmarks", [r["uri"] for r in caps["resources"]])
        self.assertIn("analysis_report", [p["name"] for p in caps["prompts"]])
