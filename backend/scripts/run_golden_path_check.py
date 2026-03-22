from __future__ import annotations

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


FIXTURE_DIR = BACKEND_DIR.parent / "fixtures" / "minimal"


def load_json(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r}, actual={actual!r}")


def main() -> None:
    analyze_open = load_json("analyze-request-settings-personalization.json")
    analyze_recovery = load_json("analyze-request-settings-personalization-recovery.json")
    analyze_page = load_json("analyze-request-settings-personalization-page.json")

    with TestClient(app) as client:
        # Step 1: first analyze
        resp1 = client.post("/api/analyze", json=analyze_open)
        resp1.raise_for_status()
        step1 = resp1.json()
        session_id = step1["session_id"]
        assert_equal(step1["step_id"], "scenario-open-personalization-settings", "step1.step_id")
        assert_equal(step1["action_type"], "open_personalization_settings", "step1.action_type")

        # Step 2: user reports incorrect
        feedback_payload = {
            "session_id": session_id,
            "step_id": step1["step_id"],
            "feedback_type": "incorrect",
            "comment": "fixture-golden-path",
        }
        feedback_resp = client.post("/api/feedback", json=feedback_payload)
        feedback_resp.raise_for_status()
        feedback_json = feedback_resp.json()
        assert_equal(feedback_json["accepted"], True, "feedback.accepted")
        assert_equal(feedback_json["feedback_type"], "incorrect", "feedback.feedback_type")

        # Step 3: re-analyze should recover
        analyze_recovery["observation"]["session_id"] = session_id
        resp2 = client.post("/api/analyze", json=analyze_recovery)
        resp2.raise_for_status()
        step2 = resp2.json()
        assert_equal(step2["session_id"], session_id, "step2.session_id")
        assert_equal(step2["step_id"], "scenario-recover-personalization-navigation", "step2.step_id")
        assert_equal(step2["action_type"], "recover_personalization_navigation", "step2.action_type")

        # Step 4: when page is reached, planner should confirm in-page
        analyze_page["observation"]["session_id"] = session_id
        resp3 = client.post("/api/analyze", json=analyze_page)
        resp3.raise_for_status()
        step3 = resp3.json()
        assert_equal(step3["session_id"], session_id, "step3.session_id")
        assert_equal(step3["step_id"], "scenario-confirm-personalization-page", "step3.step_id")
        assert_equal(step3["action_type"], "confirm_personalization_page", "step3.action_type")

        # Session state should keep incorrect counter and return to active after analyze.
        states_resp = client.get("/api/debug/session-states", params={"limit": 50})
        states_resp.raise_for_status()
        session_states = states_resp.json()
        matched = next((item for item in session_states if item["session_id"] == session_id), None)
        if matched is None:
            raise AssertionError(f"session_state not found for {session_id}")

        assert_equal(matched["incorrect_feedback_count"] >= 1, True, "session.incorrect_feedback_count>=1")
        assert_equal(matched["session_status"], "active", "session.session_status")
        assert_equal(matched["current_action_type"], "confirm_personalization_page", "session.current_action_type")

    print("Golden path check passed.")


if __name__ == "__main__":
    main()
