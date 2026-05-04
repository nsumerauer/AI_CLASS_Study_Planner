# ROBOTS.md

This document defines the **repository structure**, **runtime entry points**, and **constraints** for humans and AI agents assisting with the Study Planner Project.

## Product summary

- **What it is:** A Flask web app plus scheduling core that builds a weekly study plan from tasks, due dates, priorities, and per-day hour budgets.
- **Optimization lens:** Allocation uses a documented objective (`evaluate_objective` in `study_planner.py`) and iterative greedy improvement over discrete time steps (default 0.5 h).
- **Deployments:** Packaged for **Vercel** serverless (`vercel.json`); UI and API ship from `api/index.py`.

## Directory tree (authoritative)

```text
.
├── api/
│   └── index.py          # Flask app: GET /, GET /api/health, POST /api/plan; embedded HTML/CSS/JS UI
├── tests/
│   ├── test_study_planner.py   # Planner unit tests (tasks, metrics, objective ordering)
│   └── test_api.py             # Flask test_client contract tests
├── study_planner.py      # Task model, validation, build_plan(), evaluate_objective(), CLI helpers
├── requirements.txt      # Production/runtime deps (Flask)
├── vercel.json           # Rewrite all routes to api/index.py for hosting
├── example_config.json   # Sample JSON input for local CLI-style experiments
├── README.md             # Human-facing install, API, testing, deployment, acknowledgments
└── ROBOTS.md             # This file — structural map for AI tools and contributors
```

## Module responsibilities

| Module | Must not |
|--------|----------|
| `study_planner.py` | Import Flask or HTTP concerns. Keep pure scheduling + validation. |
| `api/index.py` | Contain core allocation algorithms — delegate to `build_plan`. |

## Agent contribution rules

1. Preserve scope: **study planning** only—no unrelated features without explicit owner request.
2. Prefer **deterministic** behavior; document any randomness (currently none).
3. **Backward compatibility:** Do not break JSON field names or health response without README + ROBOTS updates.
4. **Tests:** Any change to `build_plan`, objective weights, or API validation must include or update tests under `tests/`.
5. **Dependencies:** Minimize additions; justify new packages in README.
6. **Security:** Do not commit secrets. Do not weaken input validation on `/api/plan`.

## Verification commands (required before merge-ready handoff)

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
```

CI mirrors these commands (`.github/workflows/ci.yml`).

## Contribution Workflow for AI Agents

1. Read this file before generating code.
2. Follow the current architecture.
3. Propose new modules when adding major features.
4. Ensure all new code is documented and testable.
5. Maintain separation between:
   - scheduling logic
   - optimization logic
   - user interface

## Related documentation

- Human setup and API examples: `README.md`
- Dependency pins: `requirements.txt`
