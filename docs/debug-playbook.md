# Debug Playbook

## Goal
Provide a minimal repeatable flow to inspect planner behavior and regressions.

## 1) Run Fixture Regression
From repo root:

```bash
python3 backend/scripts/run_scenario_fixture_checks.py
```

Expected output:
- `Scenario fixture checks passed.`

## 2) Inspect Analyze Diagnostics
Useful endpoints:
- `GET /api/debug/analyze-diagnostics`
- `GET /api/debug/analyze-diagnostics?observation_quality=high`
- `GET /api/debug/analyze-diagnostics?planner_source=model&planner_error_code=http_error`

What to check:
- `planner_source` and `planner_error_code`
- `observation_candidate_count`
- `observation_scan_node_count`
- `observation_scan_depth`
- `observation_quality`

## 3) Inspect Diagnostic Timeline
Useful endpoints:
- `GET /api/debug/diagnostic-timeline?session_id=<session_id>`
- `GET /api/debug/diagnostic-timeline?screenshot_ref=<screenshot_ref>`
- `GET /api/debug/diagnostic-timeline?planner_source=mock_fallback&errors_only=true`

What to check:
- whether a diagnostic row can map to observation data (`foreground_window_title`, `screenshot_ref`)
- whether fallback happened after model errors

## 4) Triage Order
1. Confirm fixture script passes.
2. Check diagnostics for model errors and quality signals.
3. Check timeline correlation by `session_id` or `screenshot_ref`.
4. Re-run with narrowed filters (`planner_source`, `observation_quality`, `errors_only`).
