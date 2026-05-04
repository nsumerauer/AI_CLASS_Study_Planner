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
                {"name": "Lab", "due": "2026-04-30", "hours_needed": 3},
                {"name": "Quiz Prep", "due": "2026-05-02", "hours_needed": 2},
            ],
        }
        response = self.client.post("/api/plan", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("plan", data)
        self.assertIn("metrics", data)
        self.assertIn("allocation_rate", data["metrics"])
        self.assertIn("objective_score", data["metrics"])

    def test_plan_endpoint_handles_empty_tasks(self):
        response = self.client.post("/api/plan", json={"tasks": []})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("plan", data)
        self.assertIn("metrics", data)
        self.assertAlmostEqual(data["metrics"]["total_requested_hours"], 0.0)

    def test_plan_endpoint_rejects_invalid_week_of(self):
        payload = {
            "week_of": "not-a-date",
            "daily_study_hours": {"Monday": 1},
            "tasks": [{"name": "A", "hours_needed": 1}],
        }
        response = self.client.post("/api/plan", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_plan_endpoint_rejects_invalid_task_shape(self):
        response = self.client.post("/api/plan", json={"tasks": ["oops"]})
        self.assertEqual(response.status_code, 400)

    def test_plan_endpoint_rejects_planner_validation_errors(self):
        payload = {
            "week_of": "2026-04-27",
            "daily_study_hours": {day: 1 for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
            "tasks": [
                {"name": "Dup", "hours_needed": 1},
                {"name": "Dup", "hours_needed": 1},
            ],
        }
        response = self.client.post("/api/plan", json=payload)
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertIn("Duplicate task name", body.get("error", ""))

    def test_plan_endpoint_rejects_non_object_daily_hours(self):
        payload = {
            "daily_study_hours": [],
            "tasks": [{"name": "Essay", "hours_needed": 2}],
        }
        response = self.client.post("/api/plan", json=payload)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
