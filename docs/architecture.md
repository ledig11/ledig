# Architecture

## Client
- Windows WPF application
- Floating step panel
- Transparent overlay
- Screenshot capture
- UI Automation reader
- HTTP/WebSocket communication

## Backend
- FastAPI
- Session manager
- Step planner
- Prompt builder
- Recovery planner
- Model gateway

## Shared
- DTOs
- JSON schemas
- Step response contracts

## Workflow
1. User speaks a task
2. Client captures screenshot
3. Client extracts UI context
4. Backend returns only the next step
5. Client renders overlay and step panel
6. User performs the action
7. System checks feedback and continues
