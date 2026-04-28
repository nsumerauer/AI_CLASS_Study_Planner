from __future__ import annotations

import json
from datetime import date

from flask import Flask, jsonify, render_template_string, request

from study_planner import Task, build_plan

app = Flask(__name__)

DEFAULT_PAYLOAD = {
    "week_of": "2026-04-20",
    "daily_study_hours": {
        "Monday": 2,
        "Tuesday": 2,
        "Wednesday": 1.5,
        "Thursday": 2,
        "Friday": 1,
        "Saturday": 4,
        "Sunday": 4,
    },
    "tasks": [
        {"name": "Biology lab report", "due": "2026-04-23", "hours_needed": 5},
        {"name": "Statistics problem set", "due": "2026-04-25", "hours_needed": 4},
        {"name": "History reading quiz", "due": "2026-04-27", "hours_needed": 2},
        {"name": "Physics midterm", "due": "2026-05-02", "hours_needed": 12},
    ],
}


@app.get("/")
def home():
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Study Planner</title>
  <style>
    :root { color-scheme: dark; }
    body {
      margin: 0; font-family: Inter, system-ui, Arial, sans-serif;
      background: #0b0f14; color: #e8edf2;
    }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 24px; }
    .card {
      background: #111923; border: 1px solid #233044; border-radius: 12px; padding: 16px;
      box-shadow: 0 6px 24px rgba(0,0,0,.25);
    }
    h1 { margin: 0 0 12px; font-size: 30px; }
    p { margin: 0 0 12px; color: #b8c4d3; }
    .layout { display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; }
    .section-title { margin: 0 0 10px; font-size: 16px; }
    .inputs-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field label { font-size: 13px; color: #9cb0c8; }
    input, select {
      width: 100%; box-sizing: border-box; border-radius: 9px;
      border: 1px solid #2a3a53; background: #0a111a; color: #d4e0ef;
      padding: 9px 10px; font-size: 13px;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; border-bottom: 1px solid #223246; font-size: 13px; }
    th { color: #9cb0c8; text-align: left; }
    .actions { margin: 12px 0 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    button {
      border: 0; border-radius: 10px; background: #25c284; color: #052113; font-weight: 700;
      padding: 10px 14px; cursor: pointer;
    }
    button.secondary { background: #2f425c; color: #d4e0ef; }
    button:hover { filter: brightness(1.08); }
    button:disabled { opacity: .6; cursor: not-allowed; }
    .status { color: #7ee6b7; font-size: 14px; }
    .result-meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 10px; }
    .metric { background: #0a111a; border: 1px solid #223246; border-radius: 10px; padding: 10px; }
    .metric .k { color: #90a4bd; font-size: 12px; margin-bottom: 4px; }
    .metric .v { font-size: 18px; font-weight: 700; }
    .day-block { border: 1px solid #223246; border-radius: 10px; padding: 10px; margin-bottom: 8px; background: #0a111a; }
    .day-title { font-size: 14px; margin-bottom: 6px; color: #9cb0c8; }
    .muted { color: #90a4bd; font-size: 12px; }
    @media (max-width: 980px) {
      .layout { grid-template-columns: 1fr; }
      .inputs-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Study Planner</h1>
    <p>Set your week, available hours, and tasks. Then generate a recommended plan.</p>
    <div class="layout">
      <section class="card">
        <h2 class="section-title">Inputs</h2>
        <div class="field" style="max-width:240px; margin-bottom: 10px;">
          <label for="weekOf">Week Of</label>
          <input id="weekOf" type="date" />
        </div>
        <h3 class="section-title">Daily Study Hours</h3>
        <div class="inputs-grid" id="hoursGrid"></div>
        <h3 class="section-title" style="margin-top:14px;">Tasks</h3>
        <table>
          <thead>
            <tr><th>Task</th><th>Due Date</th><th>Hours</th><th></th></tr>
          </thead>
          <tbody id="taskRows"></tbody>
        </table>
        <div class="actions">
          <button type="button" class="secondary" id="addTask">+ Add Task</button>
          <button type="button" id="run">Generate Plan</button>
          <button type="button" class="secondary" id="reset">Reset Defaults</button>
          <span class="status" id="status">Ready</span>
        </div>
      </div>
      </section>
      <section class="card">
        <h2 class="section-title">Recommended Schedule</h2>
        <div class="result-meta">
          <div class="metric"><div class="k">Week</div><div class="v" id="mWeek">-</div></div>
          <div class="metric"><div class="k">Task Slots</div><div class="v" id="mSlots">0</div></div>
          <div class="metric"><div class="k">Unallocated Hours</div><div class="v" id="mUnalloc">0.0</div></div>
        </div>
        <div id="planOutput" class="muted">Generate a plan to see results.</div>
      </section>
    </div>
  </main>
  <script>
    const starter = {{ starter | safe }};
    const weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
    const weekOf = document.getElementById("weekOf");
    const hoursGrid = document.getElementById("hoursGrid");
    const taskRows = document.getElementById("taskRows");
    const status = document.getElementById("status");
    const runBtn = document.getElementById("run");
    const addTaskBtn = document.getElementById("addTask");
    const resetBtn = document.getElementById("reset");
    const planOutput = document.getElementById("planOutput");

    function renderHours(hours) {
      hoursGrid.innerHTML = "";
      weekdays.forEach((day) => {
        const wrapper = document.createElement("div");
        wrapper.className = "field";
        wrapper.innerHTML = `
          <label for="h-${day}">${day}</label>
          <input id="h-${day}" type="number" min="0" step="0.5" value="${hours?.[day] ?? 0}" />
        `;
        hoursGrid.appendChild(wrapper);
      });
    }

    function makeTaskRow(task = {name: "", due: "", hours_needed: 1}) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><input type="text" placeholder="Task name" value="${task.name ?? ""}" /></td>
        <td><input type="date" value="${task.due ?? ""}" /></td>
        <td><input type="number" min="0.5" step="0.5" value="${task.hours_needed ?? 1}" /></td>
        <td><button type="button" class="secondary removeBtn">Remove</button></td>
      `;
      tr.querySelector(".removeBtn").addEventListener("click", () => tr.remove());
      taskRows.appendChild(tr);
    }

    function loadDefaults() {
      weekOf.value = starter.week_of || "";
      renderHours(starter.daily_study_hours || {});
      taskRows.innerHTML = "";
      (starter.tasks || []).forEach((task) => makeTaskRow(task));
      if (!taskRows.children.length) makeTaskRow();
      status.textContent = "Ready";
      planOutput.innerHTML = '<div class="muted">Generate a plan to see results.</div>';
      document.getElementById("mWeek").textContent = "-";
      document.getElementById("mSlots").textContent = "0";
      document.getElementById("mUnalloc").textContent = "0.0";
    }

    function collectPayload() {
      const daily_study_hours = {};
      weekdays.forEach((day) => {
        const val = Number(document.getElementById(`h-${day}`).value || 0);
        daily_study_hours[day] = Number.isFinite(val) ? val : 0;
      });

      const tasks = Array.from(taskRows.querySelectorAll("tr"))
        .map((tr) => {
          const [nameInput, dueInput, hrsInput] = tr.querySelectorAll("input");
          return {
            name: (nameInput.value || "").trim(),
            due: dueInput.value || null,
            hours_needed: Number(hrsInput.value || 0),
          };
        })
        .filter((t) => t.name && t.hours_needed > 0);

      return {
        week_of: weekOf.value || null,
        daily_study_hours,
        tasks,
      };
    }

    function renderPlan(data) {
      const week = data.week_of || "-";
      const plan = data.plan || {};
      const unallocated = data.unallocated_hours || {};
      const totalUnalloc = Object.values(unallocated).reduce((sum, v) => sum + Number(v || 0), 0);
      const slotCount = Object.values(plan).reduce((sum, dayMap) => sum + Object.keys(dayMap || {}).length, 0);

      document.getElementById("mWeek").textContent = week;
      document.getElementById("mSlots").textContent = String(slotCount);
      document.getElementById("mUnalloc").textContent = totalUnalloc.toFixed(1);

      const daysHtml = weekdays
        .map((day) => {
          const entries = Object.entries(plan[day] || {});
          const tasksHtml = entries.length
            ? entries.map(([task, hours]) => `<div>${task}: <strong>${Number(hours).toFixed(1)}h</strong></div>`).join("")
            : '<div class="muted">(no study)</div>';
          return `<div class="day-block"><div class="day-title">${day}</div>${tasksHtml}</div>`;
        })
        .join("");

      const unallocItems = Object.entries(unallocated)
        .map(([task, hours]) => `<div>${task}: <strong>${Number(hours).toFixed(1)}h</strong></div>`)
        .join("");

      planOutput.innerHTML = `
        ${daysHtml}
        <div class="day-block">
          <div class="day-title">Unallocated Hours</div>
          ${unallocItems || '<div class="muted">All requested hours allocated.</div>'}
        </div>
      `;
    }

    async function runPlan() {
      status.textContent = "Working...";
      runBtn.disabled = true;
      try {
        const payload = collectPayload();
        if (!payload.tasks.length) {
          throw new Error("Add at least one task with hours.");
        }
        const res = await fetch("/api/plan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error("Request failed.");
        renderPlan(data);
        status.textContent = res.ok ? "Done" : "Request failed";
      } catch (err) {
        status.textContent = "Check inputs and try again";
        planOutput.innerHTML = `<div class="muted">${String(err)}</div>`;
      } finally {
        runBtn.disabled = false;
      }
    }

    addTaskBtn.addEventListener("click", () => makeTaskRow());
    resetBtn.addEventListener("click", loadDefaults);
    runBtn.addEventListener("click", runPlan);
    loadDefaults();
  </script>
</body>
</html>
        """,
        starter=json.dumps(DEFAULT_PAYLOAD),
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "healthy"})


@app.post("/api/plan")
def plan():
    payload = request.get_json(silent=True) or {}
    week_of_raw = payload.get("week_of")
    week_of = date.fromisoformat(week_of_raw) if week_of_raw else None
    daily_hours = payload.get("daily_study_hours", {})
    tasks_payload = payload.get("tasks", [])

    tasks = [
        Task(
            name=item["name"],
            hours_needed=float(item["hours_needed"]),
            due=date.fromisoformat(item["due"]) if item.get("due") else None,
        )
        for item in tasks_payload
    ]

    result = build_plan(tasks=tasks, daily_hours=daily_hours, week_of=week_of)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
