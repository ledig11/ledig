# Architecture

## Client
- Windows WPF application
- Floating step panel
- Transparent overlay
- Screenshot capture
- UI Automation reader
- HTTP request/response + WebSocket realtime event stream

## Backend
- FastAPI
- In-memory session manager (Phase 1)
- Step planner
- Prompt builder
- Recovery planner
- Model gateway
- Realtime event hub (`/api/ws/events`)

### Session Runtime (Phase 1)
- `POST /api/sessions`: create a new guidance session
- `GET /api/sessions/{session_id}`: read current session state and step history
- `POST /api/sessions/{session_id}/next-step`: run planner for one next step under session
- `POST /api/sessions/{session_id}/feedback`: submit `completed | incorrect | reanalyze`
- Existing `POST /api/analyze` and `POST /api/feedback` remain available for compatibility
- Session state is cached in memory and persisted into SQLite (`backend/data/session_runtime.db`)
- Step history now records both next-step outputs and feedback events for replay/debug

## Shared
- DTOs
- JSON schemas
- Step response contracts

## Workflow
1. User speaks a task
2. Client creates a session (or reuses current session)
3. Client captures screenshot
4. Client extracts UI context
5. Backend returns only the next step
6. Client renders overlay and step panel
7. User performs the action
8. System records feedback and continues
