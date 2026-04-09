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


CASES = [
    ("analyze-request-settings-bluetooth.json", "next-step-response-settings-bluetooth.json"),
    ("analyze-request-settings-network.json", "next-step-response-settings-network.json"),
    ("analyze-request-settings-display.json", "next-step-response-settings-display.json"),
    ("analyze-request-settings-personalization.json", "next-step-response-settings-personalization.json"),
    ("analyze-request-settings-time-language.json", "next-step-response-settings-time-language.json"),
]


def load_json(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def compare_response(expected: dict, actual: dict) -> list[str]:
    mismatches: list[str] = []
    for key in ("step_id", "action_type", "instruction"):
        if actual.get(key) != expected.get(key):
            mismatches.append(f"{key} mismatch: {actual.get(key)!r} != {expected.get(key)!r}")

    expected_rect = (((expected.get("highlight") or {}).get("rect")) or {})
    actual_rect = (((actual.get("highlight") or {}).get("rect")) or {})
    expected_tuple = (
        expected_rect.get("x"),
        expected_rect.get("y"),
        expected_rect.get("width"),
        expected_rect.get("height"),
    )
    actual_tuple = (
        actual_rect.get("x"),
        actual_rect.get("y"),
        actual_rect.get("width"),
        actual_rect.get("height"),
    )
    if expected_tuple != actual_tuple:
        mismatches.append(f"highlight.rect mismatch: {actual_tuple} != {expected_tuple}")
    return mismatches


def run() -> int:
    failures: list[str] = []
    with TestClient(app) as client:
        for request_file, expected_file in CASES:
            request_payload = load_json(request_file)
            expected_payload = load_json(expected_file)

            created = client.post("/api/sessions", json={"task_text": request_payload["task_text"]})
            if created.status_code != 200:
                failures.append(f"{request_file}: create session failed {created.status_code}")
                continue
            session_id = created.json().get("session_id")
            if not session_id:
                failures.append(f"{request_file}: session_id missing")
                continue

            request_payload["observation"]["session_id"] = session_id
            response = client.post(f"/api/sessions/{session_id}/next-step", json=request_payload)
            if response.status_code != 200:
                failures.append(f"{request_file}: next-step failed {response.status_code}")
                continue
            actual_payload = response.json()
            mismatches = compare_response(expected_payload, actual_payload)
            for mismatch in mismatches:
                failures.append(f"{request_file}: {mismatch}")

    if failures:
        print("Session fixture matrix check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Session fixture matrix check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

