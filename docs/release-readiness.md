# Release Readiness (MVP)

## Goal
Ship a stable Windows Step Guide MVP with session runtime support while keeping one-step guidance and human-in-the-loop safety.

## Scope Freeze
This release includes:
- Sessionized next-step flow (`/api/sessions/*`)
- Legacy compatibility (`/api/analyze`, `/api/feedback`)
- In-memory + SQLite-backed session runtime state
- Structured feedback (`completed | incorrect | reanalyze`)
- Highlight overlay response path

This release explicitly excludes:
- Automatic mouse/keyboard control
- Remote takeover
- Mobile client
- Multi-agent policy/skills orchestration

## Must-Pass Checks
From repo root:

```bash
make qa-all
```

Minimum expected:
- Scenario fixture checks pass
- Session unit tests pass
- Session golden check pass
- Session matrix check pass
- Legacy golden path check pass
- RC stability check pass

## Scenario Acceptance Set
Session matrix should pass all:
1. Settings Bluetooth
2. Settings Network
3. Settings Display
4. Settings Personalization
5. Settings Time & Language
6. Software Installation (download page)

## Manual Smoke Checklist (Windows Client)
1. Launch app and create/continue a session.
2. Click `分析下一步`; verify step text + highlight.
3. Click `这一步不对`; verify feedback accepted and reanalyze can proceed.
4. Click `重新分析`; verify next-step updates under same session.
5. Click `已完成`; verify feedback accepted and session state updates.

## Rollback Trigger
Rollback if any of the following happens in release validation:
- `qa-all` fails
- Session not found recovery fails repeatedly on stable backend
- Legacy endpoints and session endpoints diverge for same observation/task inputs
