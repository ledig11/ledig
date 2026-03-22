# Round 1 Minimal Loop

This round implements only the smallest mock loop:

1. WPF client sends `task_text` plus a minimal placeholder `observation` to `POST /api/analyze`
2. FastAPI backend returns one lightweight observation-aware mock `NextStepResponse`
3. Client displays the returned `instruction` in the floating panel

Out of scope for this round:
- full UI Automation tree collection
- WebSocket
- automatic mouse or keyboard control

Minimal feedback contract placeholder:
- A shared `StepFeedbackRequest` contract is reserved for future actions like `completed`, `incorrect`, and `reanalyze`.
- A minimal backend `POST /api/feedback` endpoint now accepts this contract and returns a fixed success response.

Client-side local feedback mapping:
- The WPF client now requires a startup modal for manual entry of `model_type` and `API Key` before the main window opens.
- The WPF client now maps local actions to `StepFeedbackRequest` placeholders for `completed`, `incorrect`, and `reanalyze`.
- These feedback objects are now submitted to a minimal `POST /api/feedback` endpoint and the latest submission result is displayed in the client.
- The WPF panel also shows tiny read-only debug blocks for the current `session_id`, `step_id`, latest `feedback_type`, and the last observation summary sent with `analyze`.
- The WPF panel now also keeps a tiny local read-only list of the most recent observations for manual verification and future replay-oriented debugging.
- The WPF client now also writes one tiny local observation manifest JSON per observation attempt and tries to save one local primary-screen screenshot file for the same observation.
- The WPF panel now also shows the latest local observation asset status, including screenshot capture result and local manifest path.
- The WPF client now also captures a tiny foreground-window UI Automation snapshot and shows it in a local debug block.

Minimal SQLite logging:
- Backend initializes a SQLite file at `backend/data/app.db`.
- `POST /api/analyze` writes one summary row containing: timestamp, task text, session id, step id, action type, instruction, minimal observation fields, and highlight rect.
- `POST /api/feedback` writes one summary row containing: timestamp, session id, step id, feedback type, optional comment, accepted flag, and response message.
- This is only a minimal persistence layer for request logging; it is not a full replay system.

Minimal observation-aware planning:
- The backend planner is still mock-based, but it now lightly inspects `task_text`, `foreground_window_title`, and a tiny foreground-window UIA summary.
- If the foreground window title looks related to the task, the response asks the user to continue in the current window.
- Otherwise, the response asks the user to switch to a more relevant window first, and it can also use the foreground window's UIA control type plus a tiny window-kind heuristic as fallback hints.
- This is still not real UI Automation reasoning or screenshot understanding.

Minimal log visibility:
- `GET /api/debug/analyze-logs` returns the most recent analyze log rows in reverse time order.
- `GET /api/debug/feedback-logs` returns the most recent feedback log rows in reverse time order.
- `GET /api/debug/observation-traces` returns the most recent observation-oriented trace rows in reverse time order for lightweight replay/debug inspection.
- `GET /api/debug/observation-traces` also supports tiny exact-match filters for `session_id` and `screenshot_ref`, plus a small `limit` override.
- These are still fixed small read-only debug endpoints with no pagination, fuzzy search, or replay reconstruction.

Minimal session visibility:
- `GET /api/debug/session-summaries` returns recent session summaries derived from existing `analyze_logs` and `feedback_logs`.
- Each summary includes: `session_id`, `last_task_text`, `last_step_id`, `last_action_type`, `last_feedback_type`, and `last_updated_at_utc`.
- This is a tiny read-only session view, not a replay timeline or a general query system.

Minimal observation status:
- Analyze requests now include a tiny `observation` object with `captured_at_utc`, `foreground_window_title`, `screen_width`, `screen_height`, and `screenshot_ref`.
- Analyze requests now also include a tiny foreground-window UIA summary: `foreground_window_uia_name`, `foreground_window_uia_automation_id`, `foreground_window_uia_class_name`, `foreground_window_uia_control_type`, and `foreground_window_uia_is_enabled`.
- Analyze requests now also include a tiny foreground-window direct-child summary: `foreground_window_uia_child_count` and `foreground_window_uia_child_summary`.
- Analyze requests now also include `foreground_window_actionable_summary`, a small derived summary intended for lightweight planner use.
- `foreground_window_title` is now a semi-real value read from the current foreground window title when available, with a minimal safe fallback if reading fails.
- `screen_width` and `screen_height` are now semi-real values read from the current primary screen size when available, with a minimal safe fallback if reading fails.
- `screenshot_ref` is now a local pseudo-real observation reference generated once per observation, so the same analyze request can carry a stable local identifier for logging and future replay mapping.
- The client also keeps the most recent observations in a small local-only debug list, including `captured_at_utc`, `foreground_window_title`, screen size, and `screenshot_ref`.
- The client also writes a local manifest record for each observation under the user's local app data folder and tries to attach one local primary-screen screenshot path to it.
- The client also captures a minimal foreground-window UI Automation snapshot including name, control type, class name, automation id, and enabled state.
- The client also captures a tiny direct-child UIA summary from the foreground window, capped to a few immediate children for low risk.
- The client also derives one tiny `foreground_window_actionable_summary` from title, control type, and direct-child hints.
- The backend analyze logs and observation trace endpoint now also retain the tiny foreground-window UIA summary fields.
- Screenshot capture is local-only, single-shot, primary-screen only, with silent fallback if capture fails.
- This round still does not include screenshot upload, multi-monitor capture, DPI-accurate tuning, or full UI Automation tree collection.

## MVP v1 Capabilities
- WPF floating guidance panel with one-step instruction display
- Manual startup gate for model type and API key entry before app interaction
- Placeholder highlight preview in-panel plus a separate lightweight overlay window
- Minimal `POST /api/analyze` loop using partial real observation context
- Lightweight observation-aware mock planning based on current foreground window title
- Lightweight window-kind heuristic based on foreground title plus minimal UIA summary
- One local pseudo-real `screenshot_ref` generated per observation for log correlation
- One local read-only recent observation list in the WPF client for trace-style inspection
- One local observation manifest JSON written per observation
- One local primary-screen screenshot file attempt per observation, referenced from the manifest when capture succeeds
- One minimal foreground-window UI Automation snapshot captured per observation for local debugging
- One tiny foreground-window UIA summary included in observation requests and backend trace logs
- One tiny direct-child UIA summary included for low-risk window content hints
- One tiny actionable summary included for lightweight planner decisions
- One backend read-only observation trace endpoint backed by existing analyze logs
- One front-end debug block for the latest local observation asset status and paths
- Minimal `POST /api/feedback` loop for `completed`, `incorrect`, and `reanalyze`
- SQLite request logging for analyze and feedback
- Read-only backend debug endpoints for recent logs and recent session summaries
- Tiny front-end debug visibility for current session, current step, latest feedback type, and latest observation summary

## Not Implemented
- Screenshot upload or remote storage
- Real model invocation or secure credential storage
- Real UI Automation tree collection
- Child control-level UI Automation traversal or action targeting
- Automatic mouse or keyboard control
- Multi-step planning or recovery flow
- WebSocket updates
- Replay timeline UI or complex querying
- Backend-backed observation replay storage
- Observation trace pagination, fuzzy search, or full replay reconstruction
- Click-through overlay, multi-monitor support, DPI tuning, or animation polish

## Minimal Demo Flow
1. Start the FastAPI backend.
2. Launch the WPF client.
3. Enter a task such as `打开设置`.
4. Click `分析下一步` and verify that the instruction, highlight text, in-panel preview, overlay window, current context, and observation summary update.
5. Confirm that `Observation Summary` shows the current foreground window title when available and the current primary screen size instead of fixed placeholder dimensions.
6. Confirm that `Observation Summary` now shows a per-request local `screenshot_ref` such as `local://observation/...` instead of a fixed placeholder value.
7. Confirm that `Recent Observations` shows the newest observation first and keeps only a small recent local list.
8. Click `这一步不对`, `重新分析`, and `已完成` to verify feedback submission and local status updates.
9. Open backend debug endpoints to verify that analyze logs, feedback logs, observation traces, and session summaries are being recorded.
10. Call `GET /api/debug/observation-traces?session_id=...` or `GET /api/debug/observation-traces?screenshot_ref=...` to verify exact trace lookup for recent observations.
11. Inspect the local app data observation manifest folder and confirm that each analyze attempt produces a small JSON manifest keyed by the observation reference.
12. Confirm that successful observations also create a local PNG file under the screenshot folder and that the manifest's `ScreenshotLocalPath` points to it.
13. Confirm that the WPF `Observation Assets` block and `Recent Observations` list show screenshot capture status and local file path information.
14. Confirm that the WPF `Foreground Window UIA` block and the manifest JSON include foreground-window UIA fields such as control type, class name, and automation id.

## Run / Demo
Backend:
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Useful backend URLs:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/debug/analyze-logs`
- `http://127.0.0.1:8000/api/debug/feedback-logs`
- `http://127.0.0.1:8000/api/debug/observation-traces`
- `http://127.0.0.1:8000/api/debug/observation-traces?session_id=<session_id>`
- `http://127.0.0.1:8000/api/debug/observation-traces?screenshot_ref=<screenshot_ref>`
- `http://127.0.0.1:8000/api/debug/session-summaries`

Windows client:
- Open `windows-client/WindowsStepGuide.Client.csproj` in Visual Studio on Windows and run it.
- Or run `dotnet run` inside `windows-client` if .NET 8 SDK is installed on Windows.
