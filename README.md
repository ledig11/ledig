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
- FastAPI backend with legacy APIs (`/api/analyze`, `/api/feedback`) and session APIs (`/api/sessions/*`)
- WPF floating panel plus lightweight highlight overlay
- SQLite logging for analyze, feedback, sessions, and observation traces
- SQLite-backed session runtime persistence (`backend/data/session_runtime.db`) with in-memory cache
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
- A fifth dedicated Windows Settings -> Time & Language scenario is now supported, including incorrect-feedback recovery
- A software installation scenario is now supported (browser download page -> installer wizard guidance)
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
- CI now validates backend QA and Windows client build in GitHub Actions
- WPF client startup now uses dependency injection for service wiring
- WPF startup config now supports API Key as optional so local safe-fallback validation can proceed without external model access
- WPF startup config now supports membership-token/API-Key auth mode plus provider/base-url/model selection for OpenAI-compatible switching
- When auth mode is `member_token`, the client now sends `Authorization: Bearer <token>` to support token-based gateways
- A minimal realtime channel is now available via WebSocket (`/api/ws/events`) with structured analyze/feedback events
- Observation contract now carries visual-fallback metadata (`screenshot_status`, `screenshot_local_path`) in addition to `screenshot_ref`
- Backend API layers now depend on a `LogStore` interface port for easier mock-friendly replacement

## Next
- Extend software-install scenario-state templates to app-specific installers
- Add controlled screenshot-to-model input transport (metadata-only gate is already in place)
- Complete Windows manual smoke run and freeze v1.0.0-rc release checklist

## Windows Test Scripts
Under `scripts/windows/`:
- `start-backend.ps1`: create venv, install deps, and run backend
- `run-backend-qa.ps1`: run backend QA checks (`-Full` includes RC stability)
- `start-client.ps1`: build + run WPF client, auto-prefill startup model config from env vars
- `start-local-test.ps1`: one-command local test flow (backend + QA + client)
- `start-backend-bailian.ps1`: start backend with Bailian/OpenAI-compatible defaults
- `start-client-bailian.ps1`: start client with Bailian presets and model selection
- `start-local-test-bailian.ps1`: one-command Bailian local test flow

API key options:
1. Pass directly in script:
```powershell
.\scripts\windows\start-backend.ps1 -ApiKey "sk-..."
.\scripts\windows\start-client.ps1 -ApiKey "sk-..." -AuthMode api_key
```
2. Or use env var:
```powershell
$env:OPENAI_API_KEY="sk-..."
```
Then run scripts without `-ApiKey`.

### Bailian (OpenAI-compatible) quick start
1) Start backend with Bailian:
```powershell
.\scripts\windows\start-backend-bailian.ps1 -ApiKey "YOUR_KEY" -ModelType "qwen3.5-plus"
```
2) Start client with Bailian preset:
```powershell
.\scripts\windows\start-client-bailian.ps1 -ApiKey "YOUR_KEY" -ModelType "kimi-k2.5"
```
3) Or run full local flow:
```powershell
.\scripts\windows\start-local-test-bailian.ps1 -ApiKey "YOUR_KEY" -ModelType "qwen3.5-plus" -RunRc
```

Notes:
- `BaseUrl` can be the root endpoint `https://coding.dashscope.aliyuncs.com/v1`.
- Backend auto-resolves OpenAI-compatible chat endpoint (`/chat/completions`) when needed.
- In client startup window, you can switch model presets (`qwen3.5-plus`, `kimi-k2.5`) or type custom model names.
