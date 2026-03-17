# Backend

This directory will contain the FastAPI backend for session handling, step planning, and model integration.

Current minimal persistence:
- SQLite database file: `backend/data/app.db`
- Logged requests: `POST /api/analyze`, `POST /api/feedback`
- Read-only debug endpoints: `GET /api/debug/analyze-logs`, `GET /api/debug/feedback-logs`
- Session summary endpoint: `GET /api/debug/session-summaries`
