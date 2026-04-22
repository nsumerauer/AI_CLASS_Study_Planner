#!/usr/bin/env python3

from datetime import date, timedelta

# Days of the week in order — used to loop through days of the week
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

class Task:
    """
    Represents a study task.
    (Will add due dates and optimization later.)
    """
    def __init__(self, name, hours_needed):
        self.name = name
        self.hours_needed = hours_needed

def start_of_week(any_day: date) -> date:
    """
    Returns the first day of the week that contains 'any_day' variable.
    Will be useful for date-based scheduling.
    """
    return any_day - timedelta(days=any_day.weekday())

def simple_plan(tasks, daily_hours):
    """
    Simple scheduling algorithm placeholder to show structure.
    No optimization (yet).
    """
    # Create an empty plan: each day maps to a dict of {task_name: hours}
    plan = {d: {} for d in WEEKDAYS}

    # Track how many hours each task still needs
    remaining = {t.name: t.hours_needed for t in tasks}

    # Loop through each day of the week
    for day in WEEKDAYS:
        available = daily_hours.get(day, 0)  # Hours available that day

        # Try to assign hours to tasks in the order they were given
        for task in tasks:
            if remaining[task.name] <= 0:
                continue  # Task already completed

            # Allocate as many hours as possible today
            take = min(available, remaining[task.name])

            if take > 0:
                plan[day][task.name] = take
                remaining[task.name] -= take
                available -= take

            # If no hours left today, move to next day
            if available <= 0:
                break

    return plan

def print_plan(plan):
    """
    Prints out the weekly plan.
    """
    print("\nWeekly Study Plan\n")
    for day in WEEKDAYS:
        print(f"{day}:")
        if not plan[day]:
            print("  (no study)")
        else:
            for task, hrs in plan[day].items():
                print(f"  {task}: {hrs:.1f}h")
        print()

def main():
    # Example hours available each day
    daily_hours = {
        "Monday": 2, "Tuesday": 2, "Wednesday": 2,
        "Thursday": 2, "Friday": 2, "Saturday": 4, "Sunday": 4
    }

    # Example tasks with estimated hours needed
    tasks = [
        Task("Math Homework", 4),
        Task("Chemistry Exam", 6),
        Task("History Essay", 5),
    ]

    # Generate plan and print output
    plan = simple_plan(tasks, daily_hours)
    print_plan(plan)

if __name__ == "__main__":
    main()
