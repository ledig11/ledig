# Backend

This directory will contain the FastAPI backend for session handling, step planning, and model integration.

Current minimal persistence:
- SQLite database file: `backend/data/app.db`
- Logged requests: `POST /api/analyze`, `POST /api/feedback`
- Read-only debug endpoints: `GET /api/debug/analyze-logs`, `GET /api/debug/feedback-logs`
- Analyze diagnostics endpoint: `GET /api/debug/analyze-diagnostics`
- Observation trace endpoint: `GET /api/debug/observation-traces`
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

Session state behavior:
- `POST /api/analyze` now upserts the current session step, action, instruction, window title, and screenshot reference.
- `POST /api/analyze` also writes a diagnostic record containing planner source, model identity, error code, and raw response excerpt when available.
- Diagnostics now also record prompt/schema version and which candidate UIA element matched the returned highlight when available.
- `POST /api/feedback` now updates `last_feedback_type`, session status, and feedback counters.
- Current statuses are `active`, `completed`, and `needs_review`.
- Session state also records `planner_source`, configured model identity, and the last planner error when the backend falls back to mock planning.
