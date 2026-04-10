from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
FIXTURE_DIR = ROOT_DIR / "fixtures" / "minimal"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


MATRIX_CASES = [
    ("analyze-request-settings-bluetooth.json", "next-step-response-settings-bluetooth.json"),
    ("analyze-request-settings-network.json", "next-step-response-settings-network.json"),
    ("analyze-request-settings-display.json", "next-step-response-settings-display.json"),
    ("analyze-request-settings-personalization.json", "next-step-response-settings-personalization.json"),
    ("analyze-request-settings-time-language.json", "next-step-response-settings-time-language.json"),
    ("analyze-request-install-software-download-page.json", "next-step-response-install-software-download-page.json"),
]


def load_json(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def run_iteration(client: TestClient, request_payload: dict, expected_payload: dict) -> None:
    created = client.post("/api/sessions", json={"task_text": request_payload["task_text"]})
    if created.status_code != 200:
        raise AssertionError(f"create session failed: {created.status_code} {created.text}")
    session_id = created.json().get("session_id")
    if not session_id:
        raise AssertionError("create session returned empty session_id")

    payload = json.loads(json.dumps(request_payload))
    payload["observation"]["session_id"] = session_id
    next_step = client.post(f"/api/sessions/{session_id}/next-step", json=payload)
    if next_step.status_code != 200:
        raise AssertionError(f"next-step failed: {next_step.status_code} {next_step.text}")
    actual = next_step.json()

    for key in ("step_id", "action_type", "instruction"):
        if actual.get(key) != expected_payload.get(key):
            raise AssertionError(
                f"{request_payload['task_text']} {key} mismatch: {actual.get(key)!r} != {expected_payload.get(key)!r}"
            )

    feedback = client.post(
        f"/api/sessions/{session_id}/feedback",
        json={
            "session_id": session_id,
            "step_id": actual["step_id"],
            "feedback_type": "reanalyze",
            "comment": "rc stability pass",
        },
    )
    if feedback.status_code != 200:
        raise AssertionError(f"feedback failed: {feedback.status_code} {feedback.text}")
    if not feedback.json().get("accepted", False):
        raise AssertionError("feedback accepted=false")


def run() -> int:
    loops = 3
    with TestClient(app) as client:
        for loop_index in range(loops):
            for request_file, expected_file in MATRIX_CASES:
                run_iteration(
                    client,
                    request_payload=load_json(request_file),
                    expected_payload=load_json(expected_file),
                )

        stats = client.get("/api/sessions/runtime-stats")
        if stats.status_code != 200:
            raise AssertionError(f"runtime-stats failed: {stats.status_code} {stats.text}")
        payload = stats.json()
        if payload.get("total_created_count", 0) < loops * len(MATRIX_CASES):
            raise AssertionError("runtime-stats total_created_count is lower than expected")

    print("RC stability check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

