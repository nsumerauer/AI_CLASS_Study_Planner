from datetime import date
import unittest

from study_planner import Task, build_plan


class StudyPlannerTests(unittest.TestCase):
    def test_build_plan_allocates_and_reports_metrics(self):
        tasks = [
            Task(name="Task A", hours_needed=3, due=date(2026, 5, 1)),
            Task(name="Task B", hours_needed=2, due=date(2026, 5, 3)),
        ]
        daily_hours = {
            "Monday": 2,
            "Tuesday": 2,
            "Wednesday": 1,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0,
        }

        result = build_plan(tasks=tasks, daily_hours=daily_hours, week_of=date(2026, 4, 27))

        self.assertEqual(result["week_of"], "2026-04-27")
        self.assertAlmostEqual(result["metrics"]["total_requested_hours"], 5.0)
        self.assertAlmostEqual(result["metrics"]["total_allocated_hours"], 5.0)
        self.assertAlmostEqual(result["metrics"]["allocation_rate"], 1.0)
        self.assertEqual(result["unallocated_hours"], {})

    def test_duplicate_task_names_raise_error(self):
        tasks = [
            Task(name="Duplicate", hours_needed=2),
            Task(name="Duplicate", hours_needed=1),
        ]
        daily_hours = {day: 2 for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

        with self.assertRaises(ValueError):
            build_plan(tasks=tasks, daily_hours=daily_hours, week_of=date(2026, 4, 27))

    def test_negative_daily_hours_raise_error(self):
        tasks = [Task(name="Essay", hours_needed=2)]
        daily_hours = {
            "Monday": -1,
            "Tuesday": 2,
            "Wednesday": 2,
            "Thursday": 2,
            "Friday": 2,
            "Saturday": 2,
            "Sunday": 2,
        }

        with self.assertRaises(ValueError):
            build_plan(tasks=tasks, daily_hours=daily_hours, week_of=date(2026, 4, 27))

    def test_higher_priority_tasks_are_allocated_first(self):
        tasks = [
            Task(name="Reading", hours_needed=2, due=date(2026, 5, 2), priority=1),
            Task(name="Midterm", hours_needed=2, due=date(2026, 5, 2), priority=4),
        ]
        daily_hours = {
            "Monday": 2,
            "Tuesday": 0,
            "Wednesday": 0,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0,
        }

        result = build_plan(tasks=tasks, daily_hours=daily_hours, week_of=date(2026, 4, 27))
        self.assertEqual(result["plan"]["Monday"], {"Midterm": 2.0})
        self.assertEqual(result["unallocated_hours"], {"Reading": 2.0})


if __name__ == "__main__":
    unittest.main()
