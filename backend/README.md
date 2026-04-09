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

Session runtime (Phase 1, in-memory):
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/runtime-stats`
- `POST /api/sessions/{session_id}/next-step`
- `POST /api/sessions/{session_id}/feedback`

Session runtime persistence:
- Session state is cached in memory and persisted to SQLite file: `backend/data/session_runtime.db`
- Session rows survive backend process restart (subject to TTL cleanup rules)

`GET /api/sessions/runtime-stats` fields:
- `active_session_count`
- `max_sessions`
- `session_ttl_seconds`
- `total_created_count`
- `total_expired_evicted_count`
- `total_capacity_evicted_count`

Current analyze logging coverage:
- Core observation fields such as `foreground_window_title`, `screen_width`, `screen_height`, and `screenshot_ref`
- Tiny foreground-window UIA summary fields such as name, control type, class name, automation id, and enabled state
- Candidate UIA elements with bounding rectangles are now logged for planner use
- The backend now supports a model-backed planner entry with safe fallback to the mock planner

Runtime model configuration:
- Request headers: `X-Model-Type`, `X-API-Key` (or `Authorization: Bearer <token>`)
- Optional request headers: `X-Model-Provider`, `X-Model-Base-Url`
- Optional env vars:
  - `WINDOWS_STEP_GUIDE_MODEL_PROVIDER` default: `openai`
  - `WINDOWS_STEP_GUIDE_MODEL_TYPE` default: `gpt-4.1`
  - `OPENAI_API_KEY`
  - `WINDOWS_STEP_GUIDE_MODEL_BASE_URL` default: `https://api.openai.com/v1/responses`
  - `WINDOWS_STEP_GUIDE_MODEL_TIMEOUT_SECONDS` default: `20`

Session runtime configuration (in-memory):
- `WINDOWS_STEP_GUIDE_SESSION_TTL_SECONDS` default: `14400` (4 hours)
- `WINDOWS_STEP_GUIDE_SESSION_MAX_COUNT` default: `500`

Session API error codes:
- `session_not_found` (`404`)
- `session_id_mismatch` (`400`)

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
- Run `python3 backend/scripts/run_session_golden_check.py` for session runtime golden path (`create -> next-step -> feedback -> get session`).

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

Session API examples:

1) Create session

Request:
```json
POST /api/sessions
{
  "task_text": "打开设置并进入个性化页面"
}
```

Response:
```json
{
  "session_id": "session-7ab4f0d3a1cc",
  "created_at": "2026-04-09T06:00:00.000000+00:00"
}
```

2) Next step under session

Request:
```json
POST /api/sessions/session-7ab4f0d3a1cc/next-step
{
  "task_text": "打开设置并进入个性化页面",
  "observation": {
    "session_id": "session-7ab4f0d3a1cc",
    "captured_at_utc": "2026-04-09T06:00:01Z",
    "foreground_window_title": "设置",
    "foreground_window_uia_name": "设置",
    "foreground_window_uia_automation_id": "SystemSettings",
    "foreground_window_uia_class_name": "ApplicationFrameWindow",
    "foreground_window_uia_control_type": "ControlType.Window",
    "foreground_window_uia_is_enabled": true,
    "foreground_window_uia_child_count": 1,
    "foreground_window_uia_child_summary": "ControlType.Button:个性化",
    "foreground_window_actionable_summary": "window_kind=settings",
    "foreground_window_candidate_elements": [],
    "screen_width": 1280,
    "screen_height": 720,
    "screenshot_ref": "local://observation/demo"
  }
}
```

Response:
```json
{
  "session_id": "session-7ab4f0d3a1cc",
  "step_id": "scenario-search-personalization-entry",
  "instruction": "设置窗口已经打开，但当前还没有识别到“个性化”入口。请先在设置窗口中查找“个性化”后再继续分析。",
  "message": "设置窗口已经打开，但当前还没有识别到“个性化”入口。请先在设置窗口中查找“个性化”后再继续分析。",
  "action_type": "search_personalization_entry",
  "requires_user_action": true,
  "confidence": 0.7,
  "highlight": {
    "rect": {
      "x": 640,
      "y": 320,
      "width": 280,
      "height": 120
    }
  },
  "observation_summary": "window_kind=settings"
}
```

3) Feedback under session

Request:
```json
POST /api/sessions/session-7ab4f0d3a1cc/feedback
{
  "session_id": "session-7ab4f0d3a1cc",
  "step_id": "scenario-search-personalization-entry",
  "feedback_type": "reanalyze",
  "comment": "用户手动触发重新分析。"
}
```

Response:
```json
{
  "accepted": true,
  "session_id": "session-7ab4f0d3a1cc",
  "step_id": "scenario-search-personalization-entry",
  "feedback_type": "reanalyze",
  "message": "feedback received"
}
```

Analyze diagnostics filters:
- `GET /api/debug/analyze-diagnostics?observation_quality=high`
- `GET /api/debug/analyze-diagnostics?min_observation_candidate_count=5`
- `GET /api/debug/analyze-diagnostics?planner_source=model&planner_error_code=http_error`
- `GET /api/debug/diagnostic-timeline?session_id=<session_id>`
- `GET /api/debug/diagnostic-timeline?screenshot_ref=<screenshot_ref>&observation_quality=medium`
- `GET /api/debug/diagnostic-timeline?planner_source=mock_fallback&errors_only=true`
- `GET /api/debug/session-replay?session_id=<session_id>`
