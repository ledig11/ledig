# Runbook

## Goal
Provide one-page operational steps for local validation and troubleshooting.

## 1) Quick Start
From repo root:

```bash
make qa-all
```

This runs:
- Python syntax checks for key backend modules
- fixture regression checks
- golden-path end-to-end API check

## 2) Scenario Regression
Run all scenario fixtures:

```bash
make qa-fixtures
```

Run a single scenario:

```bash
python3 backend/scripts/run_scenario_fixture_checks.py --scenario personalization
```

Machine-readable output:

```bash
python3 backend/scripts/run_scenario_fixture_checks.py --json
```

CI report output:

```bash
python3 backend/scripts/run_scenario_fixture_checks.py --junit-output backend/data/scenario-fixture-report.xml
```

## 3) Golden Path
Run personalization golden path (`analyze -> incorrect -> recover -> confirm`):

```bash
make qa-golden
```

## 4) Debug Endpoints
- `GET /api/debug/analyze-diagnostics`
- `GET /api/debug/diagnostic-timeline`
- `GET /api/debug/session-replay?session_id=<session_id>`

Use filters:
- `observation_quality`
- `planner_source`
- `planner_error_code`
- `errors_only=true` (timeline)

## 5) Troubleshooting
1. If fixture checks fail, inspect script output:
- mismatch list
- `expected vs actual` diff
- suggested fixture replacement JSON

2. If golden path fails:
- check `session-replay` for event ordering and step/action transitions
- check diagnostics for model errors or fallback source

3. If API shape issues appear:
- verify `shared/contracts/analyze-request.schema.json`
- verify backend/client observation DTO fields are aligned
