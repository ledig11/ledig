# Windows Step Guide

A Windows-first step-by-step computer operation guidance assistant MVP.

## Goal
Help users complete computer operations step by step, one step at a time.

## MVP Scope
- Windows desktop only
- Screenshot-based guidance
- Floating step panel
- Screen highlight overlay
- Human-in-the-loop assistance

## Current Status
- FastAPI backend with `analyze` and `feedback` APIs
- WPF floating panel plus lightweight highlight overlay
- SQLite logging for analyze, feedback, sessions, and observation traces
- Backend session state tracking for current step and feedback counters
- Semi-real observation fields for foreground window title and primary screen size
- Local observation reference, local screenshot file attempt, and local manifest JSON
- Minimal foreground-window UIA summary captured on the client
- Candidate foreground-window UIA elements captured with bounding rectangles
- Foreground-window UIA candidate capture now uses bounded tree traversal with scoring and stable UI paths
- Model planner entry on the backend with safe fallback to mock planning
- One concrete Windows Settings -> Bluetooth scenario now has dedicated step planning
- The first Settings -> Bluetooth scenario now also uses session-aware recovery after incorrect feedback
- A second dedicated Windows Settings -> Network scenario is now supported for task routing
- The Settings -> Network scenario now also supports session-aware recovery after incorrect feedback
- A third dedicated Windows Settings -> Display scenario is now supported, including incorrect-feedback recovery
- A fourth dedicated Windows Settings -> Personalization scenario is now supported, including incorrect-feedback recovery
- Analyze diagnostics now include observation-quality fields (candidate count, scanned nodes, scan depth, quality level)
- Observation metrics now also use strongly typed request fields (`foreground_window_candidate_count`, `foreground_window_scan_node_count`, `foreground_window_scan_depth`)
- A diagnostic timeline debug view is now available to correlate planner diagnostics with observation records
- A session replay debug endpoint is now available for merged analyze/diagnostic/feedback event timelines
- Analyze diagnostics and timeline endpoints now support quality/source/error-based filtering for replay inspection
- Model-backed planner now enforces safer `action_type` constraints and falls back when model output is unsafe
- Model prompt shaping is now scenario-aware (`step-planner.v2`) with task-intent tags and action constraints
- A fixture-driven regression script now checks core scenario planners in one command
- A QA checklist now documents the required regression/debug verification flow
- A one-page runbook now provides unified local validation and troubleshooting flow
- WPF client startup now uses dependency injection for service wiring
- WPF startup config now supports API Key as optional so local safe-fallback validation can proceed without external model access
- A minimal realtime channel is now available via WebSocket (`/api/ws/events`) with structured analyze/feedback events
- Observation contract now carries visual-fallback metadata (`screenshot_status`, `screenshot_local_path`) in addition to `screenshot_ref`
- Backend API layers now depend on a `LogStore` interface port for easier mock-friendly replacement

## Next
- Extend scenario-state templates to additional high-frequency Windows tasks
- Validate one real Windows task scenario end to end with repeatable fixtures
- Evolve screenshot metadata fallback into model-usable image input in a safe, bounded flow
