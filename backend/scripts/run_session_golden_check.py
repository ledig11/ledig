from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def build_observation(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "captured_at_utc": "2026-04-09T00:00:00Z",
        "foreground_window_title": "设置",
        "foreground_window_uia_name": "设置",
        "foreground_window_uia_automation_id": "SystemSettings",
        "foreground_window_uia_class_name": "ApplicationFrameWindow",
        "foreground_window_uia_control_type": "ControlType.Window",
        "foreground_window_uia_is_enabled": True,
        "foreground_window_uia_child_count": 1,
        "foreground_window_uia_child_summary": "ControlType.Button:个性化",
        "foreground_window_actionable_summary": "window_kind=settings",
        "foreground_window_candidate_elements": [],
        "screen_width": 1280,
        "screen_height": 720,
        "screenshot_ref": "local://observation/session-golden",
    }


def run() -> int:
    with TestClient(app) as client:
        create = client.post("/api/sessions", json={"task_text": "打开设置并进入个性化页面"})
        if create.status_code != 200:
            print(f"create session failed: {create.status_code} {create.text}")
            return 1
        session_id = create.json().get("session_id")
        if not session_id:
            print("create session failed: missing session_id")
            return 1

        next_step = client.post(
            f"/api/sessions/{session_id}/next-step",
            json={
                "task_text": "打开设置并进入个性化页面",
                "observation": build_observation(session_id),
            },
        )
        if next_step.status_code != 200:
            print(f"next-step failed: {next_step.status_code} {next_step.text}")
            return 1
        next_payload = next_step.json()
        step_id = next_payload.get("step_id")
        if not step_id:
            print("next-step failed: missing step_id")
            return 1

        feedback = client.post(
            f"/api/sessions/{session_id}/feedback",
            json={
                "session_id": session_id,
                "step_id": step_id,
                "feedback_type": "incorrect",
                "comment": "golden check: user marks step incorrect",
            },
        )
        if feedback.status_code != 200:
            print(f"feedback failed: {feedback.status_code} {feedback.text}")
            return 1
        feedback_payload = feedback.json()
        if not feedback_payload.get("accepted", False):
            print("feedback failed: accepted is false")
            return 1

        state = client.get(f"/api/sessions/{session_id}")
        if state.status_code != 200:
            print(f"get session failed: {state.status_code} {state.text}")
            return 1
        state_payload = state.json()
        if state_payload.get("last_feedback_type") != "incorrect":
            print("get session failed: last_feedback_type mismatch")
            return 1
        if state_payload.get("current_step_id") != step_id:
            print("get session failed: current_step_id mismatch")
            return 1
        if len(state_payload.get("step_history", [])) < 1:
            print("get session failed: step_history is empty")
            return 1

    print("Session golden check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

