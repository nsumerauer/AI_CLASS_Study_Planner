import unittest

from api.index import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "healthy")

    def test_plan_endpoint_success(self):
        payload = {
            "week_of": "2026-04-27",
            "daily_study_hours": {
                "Monday": 2,
                "Tuesday": 2,
                "Wednesday": 1,
                "Thursday": 1,
                "Friday": 0,
                "Saturday": 0,
                "Sunday": 0,
            },
            "tasks": [
                {"name": "Lab", "due": "2026-04-30", "hours_needed": 3, "priority": 1},
                {"name": "Quiz Prep", "due": "2026-05-02", "hours_needed": 2, "priority": 2},
            ],
        }
        response = self.client.post("/api/plan", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("plan", data)
        self.assertIn("metrics", data)
        self.assertIn("allocation_rate", data["metrics"])

    def test_plan_endpoint_handles_empty_tasks(self):
        response = self.client.post("/api/plan", json={"tasks": []})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("plan", data)
        self.assertIn("metrics", data)


if __name__ == "__main__":
    unittest.main()
