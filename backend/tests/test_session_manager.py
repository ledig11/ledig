from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import time
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.orchestrator.session_manager import SessionManager


class SessionManagerTests(unittest.TestCase):
    def test_expired_sessions_are_cleaned(self) -> None:
        manager = SessionManager(session_ttl_seconds=1, max_sessions=100)
        created = manager.create_session("打开设置")
        self.assertIsNotNone(manager.get_session(created.session_id))
        time.sleep(1.2)
        # Trigger lazy cleanup path.
        manager.create_session("打开记事本")
        self.assertIsNone(manager.get_session(created.session_id))

    def test_overflow_sessions_are_bounded(self) -> None:
        manager = SessionManager(session_ttl_seconds=3600, max_sessions=50)
        oldest_id = manager.create_session("task-oldest").session_id
        for index in range(80):
            manager.create_session(f"task-{index}")
        # Trigger cleanup path and check oldest session dropped.
        fresh = manager.create_session("latest-task")
        self.assertIsNotNone(manager.get_session(fresh.session_id))
        self.assertIsNone(manager.get_session(oldest_id))

    def test_sessions_persist_to_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "session_runtime.db"
            manager = SessionManager(
                session_ttl_seconds=3600,
                max_sessions=100,
                database_path=db_path,
            )
            created = manager.create_session("打开设置")
            manager.upsert_from_next_step(
                session_id=created.session_id,
                task_text="打开设置",
                step_id="step-1",
                action_type="open_settings_app",
                message="请先打开设置",
                last_observation_ref="local://test",
            )

            reloaded = SessionManager(
                session_ttl_seconds=3600,
                max_sessions=100,
                database_path=db_path,
            )
            state = reloaded.get_session(created.session_id)
            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(state.current_step_id, "step-1")
            self.assertEqual(state.last_observation_ref, "local://test")
            self.assertGreaterEqual(len(state.step_history), 1)


if __name__ == "__main__":
    unittest.main()
