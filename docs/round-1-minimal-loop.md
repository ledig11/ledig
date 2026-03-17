# Round 1 Minimal Loop

This round implements only the smallest mock loop:

1. WPF client sends `task_text` to `POST /api/analyze`
2. FastAPI backend returns one fixed mock `NextStepResponse`
3. Client displays the returned `instruction` in the floating panel

Out of scope for this round:
- real screenshot capture
- real UI Automation
- WebSocket
- database
- automatic mouse or keyboard control
