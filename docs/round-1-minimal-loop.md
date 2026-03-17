# Round 1 Minimal Loop

This round implements only the smallest mock loop:

1. WPF client sends `task_text` plus a minimal placeholder `observation` to `POST /api/analyze`
2. FastAPI backend returns one fixed mock `NextStepResponse`
3. Client displays the returned `instruction` in the floating panel

Out of scope for this round:
- real screenshot capture
- real UI Automation
- WebSocket
- automatic mouse or keyboard control

Minimal feedback contract placeholder:
- A shared `StepFeedbackRequest` contract is reserved for future actions like `completed`, `incorrect`, and `reanalyze`.
- A minimal backend `POST /api/feedback` endpoint now accepts this contract and returns a fixed success response.

Client-side local feedback mapping:
- The WPF client now maps local actions to `StepFeedbackRequest` placeholders for `completed`, `incorrect`, and `reanalyze`.
- These feedback objects are now submitted to a minimal `POST /api/feedback` endpoint and the latest submission result is displayed in the client.
- The WPF panel also shows tiny read-only debug blocks for the current `session_id`, `step_id`, latest `feedback_type`, and the last observation summary sent with `analyze`.

Minimal SQLite logging:
- Backend initializes a SQLite file at `backend/data/app.db`.
- `POST /api/analyze` writes one summary row containing: timestamp, task text, session id, step id, action type, instruction, minimal observation fields, and highlight rect.
- `POST /api/feedback` writes one summary row containing: timestamp, session id, step id, feedback type, optional comment, accepted flag, and response message.
- This is only a minimal persistence layer for request logging; it is not a full replay system.

Minimal log visibility:
- `GET /api/debug/analyze-logs` returns the most recent analyze log rows in reverse time order.
- `GET /api/debug/feedback-logs` returns the most recent feedback log rows in reverse time order.
- These are fixed small read-only debug endpoints with no pagination, filters, or aggregation.

Minimal session visibility:
- `GET /api/debug/session-summaries` returns recent session summaries derived from existing `analyze_logs` and `feedback_logs`.
- Each summary includes: `session_id`, `last_task_text`, `last_step_id`, `last_action_type`, `last_feedback_type`, and `last_updated_at_utc`.
- This is a tiny read-only session view, not a replay timeline or a general query system.

Minimal observation placeholder:
- Analyze requests now include a tiny `observation` object with placeholder context fields such as `captured_at_utc`, `foreground_window_title`, `screen_width`, `screen_height`, and `screenshot_ref`.
- This is not real screenshot capture, not image upload, and not real UI Automation collection.

## MVP v1 Capabilities
- WPF floating guidance panel with one-step instruction display
- Placeholder highlight preview in-panel plus a separate lightweight overlay window
- Minimal `POST /api/analyze` loop using placeholder observation context
- Minimal `POST /api/feedback` loop for `completed`, `incorrect`, and `reanalyze`
- SQLite request logging for analyze and feedback
- Read-only backend debug endpoints for recent logs and recent session summaries
- Tiny front-end debug visibility for current session, current step, latest feedback type, and latest observation summary

## Not Implemented
- Real screenshot capture or image upload
- Real UI Automation tree collection
- Automatic mouse or keyboard control
- Multi-step planning or recovery flow
- WebSocket updates
- Replay timeline UI or complex querying
- Click-through overlay, multi-monitor support, DPI tuning, or animation polish

## Minimal Demo Flow
1. Start the FastAPI backend.
2. Launch the WPF client.
3. Enter a task such as `打开设置`.
4. Click `分析下一步` and verify that the instruction, highlight text, in-panel preview, overlay window, current context, and observation summary update.
5. Click `这一步不对`, `重新分析`, and `已完成` to verify feedback submission and local status updates.
6. Open backend debug endpoints to verify that analyze logs, feedback logs, and session summaries are being recorded.

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
- `http://127.0.0.1:8000/api/debug/session-summaries`

Windows client:
- Open `windows-client/WindowsStepGuide.Client.csproj` in Visual Studio on Windows and run it.
- Or run `dotnet run` inside `windows-client` if .NET 8 SDK is installed on Windows.
