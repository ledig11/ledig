# Backend

This directory will contain the FastAPI backend for session handling, step planning, and model integration.

Current minimal persistence:
- SQLite database file: `backend/data/app.db`
- Logged requests: `POST /api/analyze`, `POST /api/feedback`
- Realtime events: `WS /api/ws/events` (optional `?session_id=<session_id>` filter)
- Read-only debug endpoints: `GET /api/debug/analyze-logs`, `GET /api/debug/feedback-logs`
- Analyze diagnostics endpoint: `GET /api/debug/analyze-diagnostics`
- Observation trace endpoint: `GET /api/debug/observation-traces`
- Diagnostic timeline endpoint: `GET /api/debug/diagnostic-timeline`
- Session replay endpoint: `GET /api/debug/session-replay?session_id=<session_id>`
- Session summary endpoint: `GET /api/debug/session-summaries`
- Session state endpoint: `GET /api/debug/session-states`

Current analyze logging coverage:
- Core observation fields such as `foreground_window_title`, `screen_width`, `screen_height`, and `screenshot_ref`
- Tiny foreground-window UIA summary fields such as name, control type, class name, automation id, and enabled state
- Candidate UIA elements with bounding rectangles are now logged for planner use
- The backend now supports a model-backed planner entry with safe fallback to the mock planner

Runtime model configuration:
- Request headers: `X-Model-Type`, `X-API-Key`
- Optional env vars:
  - `WINDOWS_STEP_GUIDE_MODEL_PROVIDER` default: `openai`
  - `WINDOWS_STEP_GUIDE_MODEL_TYPE` default: `gpt-4.1`
  - `OPENAI_API_KEY`
  - `WINDOWS_STEP_GUIDE_MODEL_BASE_URL` default: `https://api.openai.com/v1/responses`
  - `WINDOWS_STEP_GUIDE_MODEL_TIMEOUT_SECONDS` default: `20`

Safety behavior:
- If the provider is unsupported, the API key is missing, the model request fails, or the model returns invalid JSON, the backend falls back to `MockStepPlanner`.
- If model output has an empty instruction or an unsafe/unsupported `action_type`, the backend also falls back to safe scenario/mock planning.

Scenario-aware planning:
- Current dedicated settings scenarios: `Bluetooth`, `Network`, `Display`, and `Personalization`.
- The model prompt builder now uses `step-planner.v2` and includes task-intent tags plus explicit action constraints.

Fixture regression check:
- Unified QA command from repo root: `make qa-all`
- Run `python3 backend/scripts/run_scenario_fixture_checks.py` from repo root to verify core scenario planners against minimal fixtures.
- Run `python3 backend/scripts/run_scenario_fixture_checks.py --scenario personalization` to run one scenario group only.
- Run `python3 backend/scripts/run_scenario_fixture_checks.py --json` for machine-readable output (CI-friendly).
- Run `python3 backend/scripts/run_scenario_fixture_checks.py --junit-output <path>` to generate JUnit XML for CI test reports.
- The script performs strict fixture parity checks (session/step/action/instruction/highlight) and prompt-builder contract checks.
- The script prints grouped pass/fail summary per scenario and mismatch details on failure.
- On failure, the script prints `expected vs actual` unified diff plus a suggested fixture replacement snippet.
- See `docs/qa-checklist.md` and `docs/runbook.md` for end-to-end validation order.

Session state behavior:
- `POST /api/analyze` now upserts the current session step, action, instruction, window title, and screenshot reference.
- `POST /api/analyze` also writes a diagnostic record containing planner source, model identity, error code, and raw response excerpt when available.
- Diagnostics now also record prompt/schema version and which candidate UIA element matched the returned highlight when available.
- Analyze diagnostics now also record observation quality fields (`observation_candidate_count`, `observation_scan_node_count`, `observation_scan_depth`, `observation_quality`).
- `POST /api/feedback` now updates `last_feedback_type`, session status, and feedback counters.
- Current statuses are `active`, `completed`, and `needs_review`.
- Session state also records `planner_source`, configured model identity, and the last planner error when the backend falls back to mock planning.

Realtime event payload:
- `event_type` (`analyze` or `feedback`)
- `created_at_utc`, `session_id`, `step_id`
- optional `action_type`, `feedback_type`, `planner_source`, `observation_quality`, `screenshot_ref`, `note`

Analyze diagnostics filters:
- `GET /api/debug/analyze-diagnostics?observation_quality=high`
- `GET /api/debug/analyze-diagnostics?min_observation_candidate_count=5`
- `GET /api/debug/analyze-diagnostics?planner_source=model&planner_error_code=http_error`
- `GET /api/debug/diagnostic-timeline?session_id=<session_id>`
- `GET /api/debug/diagnostic-timeline?screenshot_ref=<screenshot_ref>&observation_quality=medium`
- `GET /api/debug/diagnostic-timeline?planner_source=mock_fallback&errors_only=true`
- `GET /api/debug/session-replay?session_id=<session_id>`
