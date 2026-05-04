#!/usr/bin/env python3
"""
Weekly Study Planner
--------------------
Generates a personalized weekly study schedule based on:
• Tasks (assignments, exams, projects) with due dates
• Estimated hours needed for each task
• Daily study availability (after work / classes)
• A mixed‑integer optimization algorithm that prioritizes urgent tasks

This version uses a MILP (Mixed Integer Linear Program) instead of a greedy
heuristic. It allocates 0.5‑hour blocks to maximize on‑time completion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from pulp import (
    LpMaximize,
    LpProblem,
    LpStatusOptimal,
    LpVariable,
    PULP_CBC_CMD,
    lpSum,
    value,
)

# Fixed weekday ordering for iteration and schedule construction
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_INDEX = {day: idx for idx, day in enumerate(WEEKDAYS)}


# ------------------------------------------------------------
# Task Model
# ------------------------------------------------------------

@dataclass
class Task:
    """
    Represents a study task with:
        - name
        - total hours required
        - optional due date

    (The greedy version also had a priority field; this MILP version
     encodes urgency through the objective weights instead.)
    """
    name: str
    hours_needed: float
    due: date | None = None


# ------------------------------------------------------------
# Week Utilities
# ------------------------------------------------------------

def start_of_week(any_day: date) -> date:
    """Return the Monday of the week containing 'any_day'."""
    return any_day - timedelta(days=any_day.weekday())


# ------------------------------------------------------------
# Sorting / Urgency Heuristic
# ------------------------------------------------------------

def _task_sort_key(task: Task, week_start: date) -> Tuple[int, float]:
    """
    Sort tasks by:
        1. Earlier due date (urgency)
        2. Larger hours_needed (bigger tasks first)

    This ordering is used only to determine iteration order; the MILP
    optimizer itself determines the final allocation.
    """
    due_offset = 999 if task.due is None else max(0, (task.due - week_start).days)
    return (due_offset, -task.hours_needed)


# ------------------------------------------------------------
# Input Validation / Constraints
# ------------------------------------------------------------

def _normalize_daily_hours(daily_hours: Dict[str, float]) -> Dict[str, float]:
    """
    Ensures daily availability is valid and non-negative.

    Constraint enforced:
        available_hours[d] >= 0
    """
    normalized: Dict[str, float] = {}
    for day_name in WEEKDAYS:
        raw_value = daily_hours.get(day_name, 0.0)
        value = float(raw_value)
        if value < 0:
            raise ValueError(f"Daily study hours cannot be negative for {day_name}.")
        normalized[day_name] = value
    return normalized


def _validate_tasks(tasks: List[Task]) -> None:
    """
    Validates task constraints:
        - name must be non-empty
        - hours_needed > 0
        - no duplicate task names
    """
    seen_names = set()
    for task in tasks:
        if not task.name or not task.name.strip():
            raise ValueError("Task names must be non-empty.")
        if task.hours_needed <= 0:
            raise ValueError(f"Task '{task.name}' must have positive hours_needed.")
        if task.name in seen_names:
            raise ValueError(f"Duplicate task name detected: '{task.name}'.")
        seen_names.add(task.name)


# ------------------------------------------------------------
# Deadline Utility
# ------------------------------------------------------------

def _due_index(task: Task, week_start: date) -> int:
    """
    Convert a task's due date into a weekday index (0–6).
    If no due date is provided, treat it as due at the end of the week.
    """
    if task.due is None:
        return len(WEEKDAYS) - 1
    return min(max((task.due - week_start).days, 0), len(WEEKDAYS) - 1)


# ------------------------------------------------------------
# Objective Evaluation (for reporting)
# ------------------------------------------------------------

def evaluate_objective(plan: Dict[str, Dict[str, float]], tasks: List[Task], week_start: date) -> Dict[str, float]:
    """
    Objective function that scores a complete candidate solution.

    Higher is better. The score rewards on‑time completion most heavily,
    gives smaller credit for total completion, and penalizes late allocation.
    """
    score = 0.0
    on_time_completion = 0.0
    total_completion = 0.0
    late_hours_penalty = 0.0

    for task in tasks:
        total_alloc = 0.0
        on_time_alloc = 0.0
        due_idx = _due_index(task, week_start)

        for day_name, day_plan in plan.items():
            allocated = float(day_plan.get(task.name, 0.0))
            total_alloc += allocated
            if DAY_INDEX[day_name] <= due_idx:
                on_time_alloc += allocated

        on_time_ratio = min(on_time_alloc / task.hours_needed, 1.0)
        completion_ratio = min(total_alloc / task.hours_needed, 1.0)
        late_hours = max(0.0, total_alloc - on_time_alloc)

        on_time_completion += on_time_ratio
        total_completion += completion_ratio
        late_hours_penalty += late_hours

        # Same scoring logic as the greedy version, but applied post‑MILP.
        score += 5.0 * on_time_ratio + 2.0 * completion_ratio - 1.5 * late_hours

    return {
        "objective_score": round(score, 4),
        "on_time_completion": round(on_time_completion, 4),
        "total_completion": round(total_completion, 4),
        "late_hours_penalty": round(late_hours_penalty, 4),
    }


# ------------------------------------------------------------
# MILP Optimization Engine
# ------------------------------------------------------------

def _optimize_plan_milp(ordered_tasks: List[Task], normalized_daily_hours: Dict[str, float], week_start: date) -> Dict[str, Dict[str, float]]:
    """
    Mixed Integer Linear Programming optimizer using 0.5‑hour blocks.

    Decision variable:
        x[t, d] = integer number of half‑hour blocks allocated
                  to task t on day d.

    Constraints enforced:
        1. Daily hour limit:
            sum_t x[t, d] * 0.5 <= available_hours[d]
        2. Task completion:
            sum_d x[t, d] * 0.5 <= hours_needed[t]
        3. Deadline constraint:
            Late allocations are allowed but heavily penalized.
        4. Non-negativity:
            x[t, d] >= 0 (integer)

    Objective:
        Maximize weighted on‑time work, with small credit for late work.
    """
    step_size = 0.5
    problem = LpProblem("study_planner_milp", LpMaximize)

    # Precompute useful structures
    task_names = [task.name for task in ordered_tasks]
    due_by_task = {task.name: _due_index(task, week_start) for task in ordered_tasks}
    blocks_needed = {task.name: int(round(task.hours_needed / step_size)) for task in ordered_tasks}
    day_capacity = {day: int(round(normalized_daily_hours[day] / step_size)) for day in WEEKDAYS}

    # Decision variables: integer half‑hour blocks
    x = {
        (task_name, day): LpVariable(f"x_{task_name}_{day}", lowBound=0, cat="Integer")
        for task_name in task_names
        for day in WEEKDAYS
    }

    # Daily capacity constraints
    for day in WEEKDAYS:
        problem += lpSum(x[(task_name, day)] for task_name in task_names) <= day_capacity[day]

    # Task completion constraints
    for task_name in task_names:
        problem += lpSum(x[(task_name, day)] for day in WEEKDAYS) <= blocks_needed[task_name]

    # Objective: reward on‑time work heavily, late work lightly
    objective_terms = []
    for task_name in task_names:
        due_idx = due_by_task[task_name]
        for day in WEEKDAYS:
            day_idx = DAY_INDEX[day]
            weight = 7.0 if day_idx <= due_idx else 0.5
            objective_terms.append(weight * x[(task_name, day)])

    problem += lpSum(objective_terms)

    # Solve MILP
    solver = PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    if problem.status != LpStatusOptimal:
        raise ValueError("Optimizer failed to find an optimal schedule.")

    # Convert block counts back to hours
    plan: Dict[str, Dict[str, float]] = {day: {} for day in WEEKDAYS}
    for task_name in task_names:
        for day in WEEKDAYS:
            blocks = value(x[(task_name, day)])
            if blocks is None or blocks <= 0:
                continue
            hours = round(float(blocks) * step_size, 2)
            if hours > 0:
                plan[day][task_name] = hours

    return plan


# ------------------------------------------------------------
# Build Weekly Plan
# ------------------------------------------------------------

def build_plan(tasks: Iterable[Task], daily_hours: Dict[str, float], week_of: date | None = None):
    """
    Main entry point for generating a weekly plan.

    Steps:
        1. Determine week start
        2. Validate tasks
        3. Normalize daily availability
        4. Sort tasks by urgency
        5. Run MILP optimizer
        6. Compute summary metrics
    """
    effective_week = week_of or start_of_week(date.today())

    task_list = list(tasks)
    _validate_tasks(task_list)
    normalized_daily_hours = _normalize_daily_hours(daily_hours)

    ordered_tasks = sorted(task_list, key=lambda t: _task_sort_key(t, effective_week))

    plan = _optimize_plan_milp(ordered_tasks, normalized_daily_hours, effective_week)

    # Compute allocated hours per task
    allocated_by_task: Dict[str, float] = {task.name: 0.0 for task in ordered_tasks}
    for day in WEEKDAYS:
        for task_name, hours in plan[day].items():
            allocated_by_task[task_name] += float(hours)

    # Remaining hours
    remaining = {
        task.name: round(task.hours_needed - allocated_by_task.get(task.name, 0.0), 2)
        for task in ordered_tasks
    }

    # Summary metrics
    total_requested_hours = round(sum(task.hours_needed for task in ordered_tasks), 2)
    total_available_hours = round(sum(normalized_daily_hours.values()), 2)
    total_unallocated = round(sum(hours for hours in remaining.values() if hours > 0), 2)
    total_allocated = round(total_requested_hours - total_unallocated, 2)
    allocation_rate = 0.0 if total_requested_hours == 0 else round(total_allocated / total_requested_hours, 4)

    objective_metrics = evaluate_objective(plan, ordered_tasks, effective_week)

    return {
        "week_of": effective_week.isoformat(),
        "plan": plan,
        "unallocated_hours": {name: hours for name, hours in remaining.items() if hours > 0},
        "metrics": {
            "total_requested_hours": total_requested_hours,
            "total_available_hours": total_available_hours,
            "total_allocated_hours": total_allocated,
            "allocation_rate": allocation_rate,
            "objective_score": objective_metrics["objective_score"],
            "on_time_completion": objective_metrics["on_time_completion"],
            "total_completion": objective_metrics["total_completion"],
            "late_hours_penalty": objective_metrics["late_hours_penalty"],
        },
    }


# ------------------------------------------------------------
# Config Loading
# ------------------------------------------------------------

def load_config(config_path: str):
    """Load tasks, availability, and week start from a JSON config file."""
    raw = Path(config_path).read_text(encoding="utf-8")
    payload = json.loads(raw)

    week_of = date.fromisoformat(payload["week_of"]) if payload.get("week_of") else None
    daily_hours = payload.get("daily_study_hours", {})

    tasks = [
        Task(
            name=item["name"],
            hours_needed=float(item["hours_needed"]),
            due=date.fromisoformat(item["due"]) if item.get("due") else None,
        )
        for item in payload.get("tasks", [])
    ]

    return tasks, daily_hours, week_of


# ------------------------------------------------------------
# Output Formatting
# ------------------------------------------------------------

def print_plan(result):
    print("\nWeekly Study Plan\n")
    for day in WEEKDAYS:
        print(f"{day}:")
        day_plan = result["plan"][day]
        if not day_plan:
            print("  (no study)")
        else:
            for task, hrs in day_plan.items():
                print(f"  {task}: {hrs:.1f}h")
        print()

    if result["unallocated_hours"]:
        print("Unallocated hours (increase daily availability to fit all work):")
        for task, hrs in result["unallocated_hours"].items():
            print(f"  {task}: {hrs:.1f}h")


# ------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------

def main():
    tasks, daily_hours, week_of = load_config("example_config.json")
    result = build_plan(tasks, daily_hours, week_of)
    print_plan(result)


if __name__ == "__main__":
    main()
