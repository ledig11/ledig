# AGENTS.md

## Project mission
Build a Windows-first step-by-step computer operation guidance assistant.
The system observes the current screen and UI tree, then returns only the next best step.

## Principles
- Windows desktop first
- Human-in-the-loop, never full auto control in MVP
- One next step at a time
- UI Automation first, visual fallback second
- Structured outputs only
- Strong logging and replayability
- Mock-friendly architecture
- Safe defaults

## Technical standards
- Frontend: C# .NET 8 WPF
- Backend: Python FastAPI
- Communication: HTTP + WebSocket
- Data: SQLite + JSON fixtures
- Dependency injection required
- DTOs and schemas strongly typed

## Coding style
- Prefer clarity over cleverness
- Keep modules small and replaceable
- Every major service behind an interface
- Avoid hidden global state
- Document TODOs for future realtime/video support

## MVP boundary
Do not implement:
- automatic mouse/keyboard control
- eyewear device drivers
- mobile client
- remote takeover
