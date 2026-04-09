from __future__ import annotations

import sys
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.orchestrator.session_manager import session_manager


class LegacyApiSessionSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        session_manager.clear_all()
        self._client_ctx = TestClient(app)
        self.client = self._client_ctx.__enter__()

    def tearDown(self) -> None:
        self._client_ctx.__exit__(None, None, None)

    def test_analyze_then_feedback_syncs_to_session_runtime(self) -> None:
        analyze_response = self.client.post(
            "/api/analyze",
            json={
                "task_text": "打开设置并进入个性化页面",
                "observation": {
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
                    "screenshot_ref": "local://legacy/screenshot",
                },
            },
        )
        self.assertEqual(analyze_response.status_code, 200)
        analyze_payload = analyze_response.json()
        session_id = analyze_payload["session_id"]
        step_id = analyze_payload["step_id"]

        runtime_state = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual(runtime_state.status_code, 200)
        state_payload = runtime_state.json()
        self.assertEqual(state_payload["current_step_id"], step_id)
        self.assertGreaterEqual(len(state_payload["step_history"]), 1)

        feedback_response = self.client.post(
            "/api/feedback",
            json={
                "session_id": session_id,
                "step_id": step_id,
                "feedback_type": "completed",
                "comment": "legacy feedback",
            },
        )
        self.assertEqual(feedback_response.status_code, 200)

        runtime_state_after_feedback = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual(runtime_state_after_feedback.status_code, 200)
        state_after_feedback = runtime_state_after_feedback.json()
        self.assertEqual(state_after_feedback["last_feedback_type"], "completed")


if __name__ == "__main__":
    unittest.main()

