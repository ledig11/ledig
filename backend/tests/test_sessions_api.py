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


def build_observation_payload(session_id: str) -> dict:
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
        "screenshot_ref": "local://observation/test",
    }


class SessionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        session_manager.clear_all()
        self._client_ctx = TestClient(app)
        self.client = self._client_ctx.__enter__()

    def tearDown(self) -> None:
        self._client_ctx.__exit__(None, None, None)

    def test_create_and_get_session(self) -> None:
        create_response = self.client.post("/api/sessions", json={"task_text": "打开设置"})
        self.assertEqual(create_response.status_code, 200)
        created = create_response.json()
        self.assertIn("session_id", created)
        self.assertIn("created_at", created)

        session_response = self.client.get(f"/api/sessions/{created['session_id']}")
        self.assertEqual(session_response.status_code, 200)
        session_payload = session_response.json()
        self.assertEqual(session_payload["session_id"], created["session_id"])
        self.assertEqual(session_payload["task_text"], "打开设置")

    def test_next_step_returns_404_for_unknown_session(self) -> None:
        response = self.client.post(
            "/api/sessions/session-not-exists/next-step",
            json={
                "task_text": "打开设置并进入个性化页面",
                "observation": build_observation_payload("session-not-exists"),
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_session_next_step_and_feedback_flow(self) -> None:
        create_response = self.client.post("/api/sessions", json={"task_text": "打开设置并进入个性化页面"})
        session_id = create_response.json()["session_id"]

        next_step_response = self.client.post(
            f"/api/sessions/{session_id}/next-step",
            json={
                "task_text": "打开设置并进入个性化页面",
                "observation": build_observation_payload(session_id),
            },
        )
        self.assertEqual(next_step_response.status_code, 200)
        next_payload = next_step_response.json()
        self.assertEqual(next_payload["session_id"], session_id)
        self.assertTrue(next_payload["step_id"])
        self.assertTrue(next_payload["instruction"])

        feedback_response = self.client.post(
            f"/api/sessions/{session_id}/feedback",
            json={
                "session_id": session_id,
                "step_id": next_payload["step_id"],
                "feedback_type": "incorrect",
                "comment": "用户认为当前建议不正确。",
            },
        )
        self.assertEqual(feedback_response.status_code, 200)
        feedback_payload = feedback_response.json()
        self.assertTrue(feedback_payload["accepted"])
        self.assertEqual(feedback_payload["session_id"], session_id)

        session_response = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual(session_response.status_code, 200)
        session_payload = session_response.json()
        self.assertEqual(session_payload["last_feedback_type"], "incorrect")
        self.assertEqual(session_payload["current_step_id"], next_payload["step_id"])
        self.assertGreaterEqual(len(session_payload["step_history"]), 2)
        self.assertEqual(session_payload["step_history"][-1]["feedback_type"], "incorrect")

    def test_feedback_session_id_mismatch_returns_400(self) -> None:
        create_response = self.client.post("/api/sessions", json={"task_text": "打开设置并进入个性化页面"})
        session_id = create_response.json()["session_id"]

        next_step_response = self.client.post(
            f"/api/sessions/{session_id}/next-step",
            json={
                "task_text": "打开设置并进入个性化页面",
                "observation": build_observation_payload(session_id),
            },
        )
        step_id = next_step_response.json()["step_id"]

        mismatch_response = self.client.post(
            f"/api/sessions/{session_id}/feedback",
            json={
                "session_id": "session-other",
                "step_id": step_id,
                "feedback_type": "reanalyze",
            },
        )
        self.assertEqual(mismatch_response.status_code, 400)

    def test_runtime_stats_endpoint(self) -> None:
        response = self.client.get("/api/sessions/runtime-stats")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("active_session_count", payload)
        self.assertIn("max_sessions", payload)
        self.assertIn("session_ttl_seconds", payload)
        self.assertIn("total_created_count", payload)
        self.assertIn("total_expired_evicted_count", payload)
        self.assertIn("total_capacity_evicted_count", payload)


if __name__ == "__main__":
    unittest.main()
