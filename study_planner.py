#!/usr/bin/env python3
"""
Weekly Study Planner
--------------------
Generates a personalized weekly study schedule based on:
• Tasks (assignments, exams, projects) with due dates  
• Estimated hours needed for each task  
• Daily study availability (after work / classes)  
• A greedy optimization algorithm that prioritizes urgent tasks
"""
  
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

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
        - optional priority weight

    The 'priority' field allows the user to manually weight tasks
    (e.g., exams > homework), which influences the optimization.
    """
    name: str
    hours_needed: float
    due: date | None = None
    priority: float = 1.0


# ------------------------------------------------------------
# Week Utilities
# ------------------------------------------------------------

def start_of_week(any_day: date) -> date:
    """Return the Monday of the week containing 'any_day'."""
    return any_day - timedelta(days=any_day.weekday())


# ------------------------------------------------------------
# Priority / Objective Function
# ------------------------------------------------------------

def _task_sort_key(task: Task, week_start: date) -> Tuple[float, int, float]:
    """
    Defines the *implicit objective function* for the greedy optimizer.

    Tasks are sorted by:
        1. Higher priority weight (user-defined importance)
        2. Earlier due date (urgency)
        3. Larger hours_needed (bigger tasks first)

    This ordering encodes the optimization goal:
        → minimize lateness and maximize timely completion
    """
    due_offset = 999 if task.due is None else max(0, (task.due - week_start).days)
    return (-task.priority, due_offset, -task.hours_needed)


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
        - priority > 0
        - no duplicate task names
    """
    seen_names = set()
    for task in tasks:
        if not task.name or not task.name.strip():
            raise ValueError("Task names must be non-empty.")
        if task.hours_needed <= 0:
            raise ValueError(f"Task '{task.name}' must have positive hours_needed.")
        if task.priority <= 0:
            raise ValueError(f"Task '{task.name}' must have positive priority.")
        if task.name in seen_names:
            raise ValueError(f"Duplicate task name detected: '{task.name}'.")
        seen_names.add(task.name)


<<<<<<< HEAD
# ------------------------------------------------------------
# Greedy Scheduling Algorithm (Optimization Engine)
# ------------------------------------------------------------
=======
def _due_index(task: Task, week_start: date) -> int:
    if task.due is None:
        return len(WEEKDAYS) - 1
    return min(max((task.due - week_start).days, 0), len(WEEKDAYS) - 1)


def evaluate_objective(plan: Dict[str, Dict[str, float]], tasks: List[Task], week_start: date) -> Dict[str, float]:
    """
    Objective function that scores a complete candidate solution.

    Higher is better. The score rewards weighted on-time completion most heavily,
    gives smaller credit for total completion, and penalizes late allocation.
    """
    score = 0.0
    weighted_on_time_completion = 0.0
    weighted_total_completion = 0.0
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

        weighted_on_time_completion += task.priority * on_time_ratio
        weighted_total_completion += task.priority * completion_ratio
        late_hours_penalty += late_hours

        # Strongly prefer on-time completion for high-priority tasks.
        score += task.priority * (5.0 * on_time_ratio + 2.0 * completion_ratio) - 1.5 * late_hours

    return {
        "objective_score": round(score, 4),
        "weighted_on_time_completion": round(weighted_on_time_completion, 4),
        "weighted_total_completion": round(weighted_total_completion, 4),
        "late_hours_penalty": round(late_hours_penalty, 4),
    }

>>>>>>> 094080e9523a2f31b502dd26b631a50e1bd8c3f5

def build_plan(tasks: Iterable[Task], daily_hours: Dict[str, float], week_of: date | None = None):
    """
    Core greedy optimization algorithm.

    Decision variable:
        x[t, d] = hours allocated to task t on day d
        → represented in code as: plan[day_name][task.name]

    Objective (implicit):
        Minimize lateness by allocating hours to:
            - higher priority tasks
            - earlier-due tasks
            - larger tasks
        This is encoded through the sorting key.

    Constraints enforced:
        1. Daily hour limit:
            sum_t x[t, d] <= available_hours[d]
        2. Task completion:
            sum_d x[t, d] = hours_needed[t]
        3. Deadline constraint:
            x[t, d] = 0 if d > due_date[t]
        4. Non-negativity:
            x[t, d] >= 0
    """

    # Determine the week to schedule
    effective_week = week_of or start_of_week(date.today())

    # Validate and prepare tasks
    task_list = list(tasks)
    _validate_tasks(task_list)

    # Normalize daily availability
    normalized_daily_hours = _normalize_daily_hours(daily_hours)

    # Sort tasks according to the optimization objective
    ordered_tasks = sorted(task_list, key=lambda t: _task_sort_key(t, effective_week))

    # Track remaining hours for each task
    remaining = {task.name: float(task.hours_needed) for task in ordered_tasks}

    # Decision variable container: plan[day][task] = hours allocated
    plan: Dict[str, Dict[str, float]] = {day: {} for day in WEEKDAYS}
    remaining_day = {day: float(hours) for day, hours in normalized_daily_hours.items()}
    step_size = 0.5

<<<<<<< HEAD
    # Iterate through each day of the week
    for day_idx, day_name in enumerate(WEEKDAYS):
        available = normalized_daily_hours[day_name]

        # If no hours available today, skip
        if available <= 0:
            continue

        day_date = effective_week + timedelta(days=day_idx)

        # Identify tasks eligible for scheduling today
        eligible_tasks: List[Task] = []
        for task in ordered_tasks:
            if remaining[task.name] <= 0:
                continue
            # Deadline constraint: only schedule tasks not yet overdue
            if task.due is None or task.due >= day_date:
                eligible_tasks.append(task)

        # If no eligible tasks (rare), fall back to any remaining tasks
        if not eligible_tasks:
            eligible_tasks = [task for task in ordered_tasks if remaining[task.name] > 0]

        # Greedy allocation loop
        for task in eligible_tasks:
            if available <= 0:
                break

            # Allocate as much as possible without violating constraints
            take = min(available, remaining[task.name])
            if take <= 0:
                continue

            # Decision variable assignment: x[t, d] = take
            plan[day_name][task.name] = round(plan[day_name].get(task.name, 0.0) + take, 2)

            # Update remaining hours and daily capacity
            remaining[task.name] = round(remaining[task.name] - take, 2)
            available = round(available - take, 2)
=======
    while True:
        if not any(hours > 0 for hours in remaining_day.values()):
            break
        if not any(hours > 0 for hours in remaining.values()):
            break

        base_score = evaluate_objective(plan, ordered_tasks, effective_week)["objective_score"]
        best_move: Tuple[float, str, Task, float] | None = None

        for day_name in WEEKDAYS:
            available = remaining_day[day_name]
            if available <= 0:
                continue
            for task in ordered_tasks:
                if remaining[task.name] <= 0:
                    continue
                take = min(step_size, available, remaining[task.name])
                if take <= 0:
                    continue

                candidate_plan = {d: allocations.copy() for d, allocations in plan.items()}
                candidate_plan[day_name][task.name] = round(candidate_plan[day_name].get(task.name, 0.0) + take, 2)
                candidate_score = evaluate_objective(candidate_plan, ordered_tasks, effective_week)["objective_score"]
                gain = round(candidate_score - base_score, 6)

                if best_move is None or gain > best_move[0]:
                    best_move = (gain, day_name, task, take)

        if best_move is None:
            break
        if best_move[0] <= 0:
            # No move improves the objective further.
            break

        _, best_day, best_task, best_take = best_move
        plan[best_day][best_task.name] = round(plan[best_day].get(best_task.name, 0.0) + best_take, 2)
        remaining[best_task.name] = round(remaining[best_task.name] - best_take, 2)
        remaining_day[best_day] = round(remaining_day[best_day] - best_take, 2)
>>>>>>> 094080e9523a2f31b502dd26b631a50e1bd8c3f5

    # Compute summary metrics
    total_requested_hours = round(sum(task.hours_needed for task in ordered_tasks), 2)
    total_available_hours = round(sum(normalized_daily_hours.values()), 2)
    total_unallocated = round(sum(hours for hours in remaining.values() if hours > 0), 2)
    total_allocated = round(total_requested_hours - total_unallocated, 2)
    allocation_rate = 0.0 if total_requested_hours == 0 else round(total_allocated / total_requested_hours, 4)
    objective_metrics = evaluate_objective(plan, ordered_tasks, effective_week)

    return {
        "week_of": effective_week.isoformat(),
        "plan": plan,
        "unallocated_hours": {name: hours for hours in remaining.items() if hours > 0},
        "metrics": {
            "total_requested_hours": total_requested_hours,
            "total_available_hours": total_available_hours,
            "total_allocated_hours": total_allocated,
            "allocation_rate": allocation_rate,
            "objective_score": objective_metrics["objective_score"],
            "weighted_on_time_completion": objective_metrics["weighted_on_time_completion"],
            "weighted_total_completion": objective_metrics["weighted_total_completion"],
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
            priority=float(item.get("priority", 1.0)),
        )
        for item in payload.get("tasks", [])
    ]

    return tasks, daily_hours, week_of


# ------------------------------------------------------------
# Output Formatting
# ------------------------------------------------------------

def print_plan(result):
    """Pretty-print the weekly plan."""
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
    """Load config, run optimizer, print results."""
    tasks, daily_hours, week_of = load_config("example_config.json")
    result = build_plan(tasks, daily_hours, week_of)
    print_plan(result)


if __name__ == "__main__":
    main()
