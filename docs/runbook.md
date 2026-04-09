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
- session runtime unit checks
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

Run session runtime golden path (`create session -> next-step -> feedback -> get session`):

```bash
make qa-session-golden
```

Run 5-scenario session fixture matrix:

```bash
make qa-session-matrix
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

## 6) Session Runtime Checks
Run session API unit tests:

```bash
python3 -m unittest backend.tests.test_sessions_api -v
python3 -m unittest backend.tests.test_session_manager -v
python3 -m unittest backend.tests.test_legacy_api_session_sync -v
```

Session API smoke sequence:
1. `POST /api/sessions`
2. `POST /api/sessions/{session_id}/next-step`
3. `POST /api/sessions/{session_id}/feedback`
4. `GET /api/sessions/{session_id}`
5. `GET /api/sessions/runtime-stats`

If `next-step` returns `404 session not found` after backend restart:
- this is expected for in-memory sessions
- client now recreates a session automatically and retries once
