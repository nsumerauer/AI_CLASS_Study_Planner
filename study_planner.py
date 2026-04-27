#!/usr/bin/env python3
"""
Weekly Study Planner
--------------------
Generates a personalized weekly study schedule based on:
• Tasks (assignments, exams, projects) with due dates  
• Estimated hours needed for each task  
• Daily study availability (after work / classes)  
• A greedy optimization algorithm that prioritizes urgent tasks  

This version supports:
- Interactive terminal input OR JSON config file
- Due date scheduling
- Automatic weekly start calculation
- Tabular output with warnings for under‑allocation
- Only Python standard library (no external dependencies)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


# Days of the week in fixed order — used for iteration and table formatting
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ------------------------------------------------------------
# Date Parsing Utilities
# ------------------------------------------------------------

def parse_date(s: str) -> date:
    """
    Parse a date string in multiple common formats.
    Accepted formats:
        YYYY-MM-DD
        MM/DD/YYYY
        DD/MM/YYYY
    """
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {s!r}. Use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY.")


def week_start_on(d: date, start_on_monday: bool = True) -> date:
    """
    Given any date, return the Monday (or Sunday) of that calendar week.
    Useful for anchoring the weekly schedule.
    """
    if start_on_monday:
        return d - timedelta(days=d.weekday())
    # Sunday-start week
    return d - timedelta(days=(d.weekday() + 1) % 7)


# ------------------------------------------------------------
# Data Models
# ------------------------------------------------------------

@dataclass
class Task:
    """
    Represents a study task such as an assignment, exam, or project.

    Attributes:
        name: Name of the task.
        due: Due date of the task.
        hours_needed: Estimated total hours required to complete it.
    """

    name: str
    due: date
    hours_needed: float = 3.0

    def days_until(self, from_day: date) -> int:
        """Return number of days until due date (0 if due today or overdue)."""
        return max(0, (self.due - from_day).days)


@dataclass
class WeekPlan:
    """
    Represents the final weekly schedule.

    Attributes:
        week_of: Monday of the week being planned.
        daily_capacity: Dict mapping weekday → available hours.
        allocation: Nested dict mapping task → day → hours assigned.
    """

    week_of: date
    daily_capacity: dict[str, float]
    allocation: dict[str, dict[str, float]] = field(default_factory=dict)

    def total_allocated(self, task: str) -> float:
        """Total hours allocated to a given task across the week."""
        return sum(self.allocation.get(task, {}).values())

    def day_total(self, day: str) -> float:
        """Total hours allocated on a given day across all tasks."""
        return sum(t.get(day, 0.0) for t in self.allocation.values())


# ------------------------------------------------------------
# Priority Function
# ------------------------------------------------------------

def _priority_score(task: Task, day: date) -> float:
    """
    Compute a priority score for a task on a given day.

    Higher score = more deserving of time today.

    Logic:
        - Tasks due today get extremely high priority.
        - Otherwise, priority decreases with distance from due date.
        - Larger tasks (more hours_needed) get higher weight.
    """
    d = task.days_until(day)
    if d == 0:
        # Extremely urgent — force heavy allocation
        return task.hours_needed * 1_000.0

    # Softer urgency curve: closer deadlines get higher priority
    return task.hours_needed / (d**1.5 + 0.5)


# ------------------------------------------------------------
# Scheduling Algorithm
# ------------------------------------------------------------

def generate_weekly_plan(
    week_start: date,
    tasks: Iterable[Task],
    daily_hours: dict[str, float],
) -> WeekPlan:
    """
    Core greedy scheduling algorithm.

    For each day:
        1. Determine available hours.
        2. Identify tasks that are still active (not overdue, not completed).
        3. Compute priority scores for each active task.
        4. Allocate small "slices" of time (0.5h max per iteration)
           proportionally to priority scores.
        5. Continue until the day's hours are used or all tasks are satisfied.

    This produces a smooth, human-like distribution of study time.
    """

    tasks = list(tasks)
    remaining = {t.name: float(t.hours_needed) for t in tasks}

    # Initialize allocation table: task → day → hours
    allocation = {t.name: {d: 0.0 for d in WEEKDAYS} for t in tasks}

    # Iterate through each day of the week
    for i, day_name in enumerate(WEEKDAYS):
        day = week_start + timedelta(days=i)
        cap = max(0.0, float(daily_hours.get(day_name, 0.0)))
        left = cap  # Remaining hours for this day

        # Filter tasks that are still relevant
        active = [
            t for t in tasks
            if t.due >= week_start and day <= t.due and remaining[t.name] > 1e-6
        ]

        # Allocate time in small slices for smoother distribution
        while left > 1e-6 and active:
            scores = [(t, _priority_score(t, day)) for t in active]
            total = sum(s for _, s in scores) or 1.0

            # Small step size prevents one task from hogging the day
            step = min(left, 0.5)

            for t, s in scores:
                if left <= 1e-6:
                    break

                # Proportional share of the step
                share = step * (s / total)
                take = min(share, remaining[t.name], left)

                if take <= 1e-9:
                    continue

                allocation[t.name][day_name] += take
                remaining[t.name] -= take
                left -= take

            # Recompute active tasks after each slice
            active = [
                t for t in tasks
                if t.due >= week_start and day <= t.due and remaining[t.name] > 1e-6
            ]

    return WeekPlan(week_of=week_start, daily_capacity=dict(daily_hours), allocation=allocation)


# ------------------------------------------------------------
# Output Formatting
# ------------------------------------------------------------

def print_plan(plan: WeekPlan, tasks: list[Task]) -> None:
    """
    Print the weekly plan in a clean, readable table.
    Includes:
        - Hours per task per day
        - Totals
        - Warnings for under-allocated tasks
    """

    print(f"\nStudy plan for week of {plan.week_of.isoformat()} (Mon–Sun)\n")

    header = f"{'Task':<28}" + "".join(f"{d[:3]:>4}" for d in WEEKDAYS) + f"{'Tot':>6}"
    print(header)
    print("-" * len(header))

    by_name = {t.name: t for t in tasks}

    # Print each task row, sorted by due date then name
    for name in sorted(plan.allocation.keys(), key=lambda n: (by_name[n].due, n)):
        row = plan.allocation[name]
        cells = "".join(
            f"{row[d]:>4.1f}" if row[d] > 0 else f"{'—':>4}"
            for d in WEEKDAYS
        )
        tot = plan.total_allocated(name)
        due = by_name[name].due.isoformat()
        print(f"{name[:26]:<28}{cells}{tot:>6.1f}  (due {due})")

    print("-" * len(header))

    # Daily totals
    cap = "".join(f"{plan.daily_capacity.get(d, 0):>4.1f}" for d in WEEKDAYS)
    used = "".join(f"{plan.day_total(d):>4.1f}" for d in WEEKDAYS)

    print(f"{'Capacity (h)':<28}{cap}{sum(plan.daily_capacity.values()):>6.1f}")
    print(f"{'Allocated (h)':<28}{used}{sum(plan.day_total(d) for d in WEEKDAYS):>6.1f}")

    # Under-allocation warnings
    short = []
    for t in tasks:
        got = plan.total_allocated(t.name)
        if got + 1e-3 < t.hours_needed:
            short.append((t.name, t.hours_needed - got))

    if short:
        print("\nNote: weekly capacity was not enough to cover all estimated hours.")
        for n, gap in sorted(short, key=lambda x: -x[1]):
            print(f"  • {n}: about {gap:.1f} h still unscheduled this week.")


# ------------------------------------------------------------
# Config Loading
# ------------------------------------------------------------

def load_config(path: Path) -> tuple[date, dict[str, float], list[Task]]:
    """
    Load configuration from a JSON file.

    Expected structure:
    {
        "week_of": "2025-04-20",
        "daily_study_hours": { "Monday": 2, ... },
        "tasks": [
            {"name": "Exam", "due": "2025-04-25", "hours_needed": 6}
        ]
    }
    """
    data = json.loads(path.read_text(encoding="utf-8"))

    week_of = parse_date(data["week_of"])
    week_start = week_start_on(week_of)

    daily = data.get("daily_study_hours", {})
    missing = [d for d in WEEKDAYS if d not in daily]
    if missing:
        raise ValueError(f"daily_study_hours missing keys: {missing}")

    tasks = [
        Task(
            name=item["name"],
            due=parse_date(item["due"]),
            hours_needed=float(item.get("hours_needed", 3)),
        )
        for item in data.get("tasks", [])
    ]

    if not tasks:
        raise ValueError("config must include a non-empty 'tasks' list")

    return week_start, daily, tasks


# ------------------------------------------------------------
# Interactive Input Mode
# ------------------------------------------------------------

def interactive_config() -> tuple[date, dict[str, float], list[Task]]:
    """
    Prompt the user for all required scheduling information:
        - Week to plan
        - Daily availability
        - Tasks with due dates and estimated hours
    """

    print("Study planner — enter your week, availability, and tasks.\n")

    raw = input("Week to plan (any date in that week, YYYY-MM-DD) [default: today]: ").strip()
    anchor = parse_date(raw) if raw else date.today()
    week_start = week_start_on(anchor)
    print(f"Using week starting Monday {week_start.isoformat()}.\n")

    print("Study hours available each day (after work / other commitments):")
    daily = {}
    for d in WEEKDAYS:
        s = input(f"  {d} (hours) [0]: ").strip()
        daily[d] = float(s) if s else 0.0

    tasks = []
    print("\nTasks (blank name to finish).")
    while True:
        name = input("Task name (e.g. Calc midterm): ").strip()
        if not name:
            break

        # Keep asking until the user enters a valid date
        while True:
            due_s = input("  Due date (YYYY-MM-DD): ").strip()
            try:
                due = parse_date(due_s)
                break
            except ValueError as e:
                print(f"    Invalid date: {e}. Please try again.")

        h_s = input("  Estimated study hours [3]: ").strip()
        h = float(h_s) if h_s else 3.0

        tasks.append(Task(name=name, due=due, hours_needed=h))

    if not tasks:
        print("No tasks entered.", file=sys.stderr)
        sys.exit(1)

    return week_start, daily, tasks


# ------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------

def main() -> None:
    """
    Entry point for the CLI tool.
    Supports:
        --config <file.json>  → load from JSON
        (no args)             → interactive mode
    """

    parser = argparse.ArgumentParser(
        description="Generate a weekly study plan from due dates and availability."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON file with week_of, daily_study_hours, tasks",
    )
    args = parser.parse_args()

    # Load config or prompt interactively
    if args.config:
        week_start, daily, tasks = load_config(args.config)
    else:
        week_start, daily, tasks = interactive_config()

    # Filter tasks based on due date
    skipped = [t for t in tasks if t.due < week_start]
    active = [t for t in tasks if t.due >= week_start]

    if skipped:
        print("Skipping tasks already due before this week:", file=sys.stderr)
        for t in skipped:
            print(f"  • {t.name} (was due {t.due.isoformat()})", file=sys.stderr)
        print(file=sys.stderr)

    if not active:
        print("No tasks due on or after the start of this week.", file=sys.stderr)
        sys.exit(1)

    # Generate and print the plan
    plan = generate_weekly_plan(week_start, active, daily)
    print_plan(plan, active)


if __name__ == "__main__":
    main()
