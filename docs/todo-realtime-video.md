# Realtime And Video TODOs

This file tracks follow-up items for future realtime/video support beyond MVP.

## Realtime TODO
- Add heartbeat/ping support and idle-timeout handling for `WS /api/ws/events`.
- Add automatic reconnect strategy on the WPF client with bounded backoff.
- Add event replay cursor (`since_created_at_utc`) so reconnect can catch up.
- Add session-scoped auth token for WebSocket connection safety.

## Video / Visual TODO
- Add optional screenshot upload path (single-frame first) with strict size limits.
- Keep UIA-first routing; use visual fallback only when observation quality is low.
- Add redaction pipeline for sensitive regions before any remote model call.
- Add fixture set that covers weak-UIA + visual-fallback scenarios.
