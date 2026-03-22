# QA Checklist

## Scope
This checklist validates the current MVP loop for Windows settings scenario planners and diagnostics.

## A. Fast Regression (Required)
1. From repo root, run:
```bash
python3 backend/scripts/run_scenario_fixture_checks.py
```
Optional (single scenario):
```bash
python3 backend/scripts/run_scenario_fixture_checks.py --scenario personalization
```
Optional (JSON output):
```bash
python3 backend/scripts/run_scenario_fixture_checks.py --json
```
Optional (JUnit XML report):
```bash
python3 backend/scripts/run_scenario_fixture_checks.py --junit-output backend/data/scenario-fixture-report.xml
```
2. Confirm output contains:
- `Scenario fixture checks passed.`

This script validates:
- scenario output alignment with fixture responses (`session_id`, `step_id`, `action_type`, `instruction`, `highlight`)
- recovery flow behavior after `incorrect` feedback
- prompt-builder contract (`step-planner.v2`, task-intent tags, action-constraints section)
- grouped pass/fail summary and mismatch details for failed cases
- unified diff (`expected` vs `actual`) and fixture replacement hint when a case fails

## B. Backend Health (Required)
1. Start backend.
2. Check:
- `GET /health`
- `GET /api/debug/analyze-diagnostics`
- `GET /api/debug/diagnostic-timeline`

3. Validate filters:
- `GET /api/debug/analyze-diagnostics?observation_quality=high`
- `GET /api/debug/analyze-diagnostics?planner_source=model&planner_error_code=http_error`
- `GET /api/debug/diagnostic-timeline?planner_source=mock_fallback&errors_only=true`

## C. Manual UI Loop (Recommended)
1. Open Windows client and trigger `分析下一步`.
2. Confirm overlay rectangle appears and aligns with expected target control.
3. Trigger `这一步不对` then `重新分析`.
4. Confirm recovery step is emitted for supported scenarios.

## D. Regression Exit Criteria
- fixture script passes
- no runtime exceptions in backend logs during analyze/feedback
- diagnostics/timeline queries return expected schema and filter behavior
- one scenario end-to-end manual run succeeds
