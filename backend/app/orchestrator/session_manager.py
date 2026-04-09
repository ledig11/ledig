from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from datetime import timedelta
from threading import Lock
from typing import Optional

from app.models.session import SessionState, SessionStepHistoryItem


class SessionManager:
    def __init__(
        self,
        *,
        session_ttl_seconds: int = 60 * 60 * 4,
        max_sessions: int = 500,
        database_path: Optional[Path] = None,
    ) -> None:
        self._lock = Lock()
        self._sessions: dict[str, SessionState] = {}
        self._last_touched_utc: dict[str, datetime] = {}
        self._session_ttl = timedelta(seconds=max(1, session_ttl_seconds))
        self._max_sessions = max(50, max_sessions)
        self._database_path = database_path or (Path(__file__).resolve().parents[2] / "data" / "session_runtime.db")
        self._total_created_count = 0
        self._total_expired_evicted_count = 0
        self._total_capacity_evicted_count = 0
        self._initialize_db()
        self._load_from_db()

    def create_session(self, task_text: Optional[str] = None) -> SessionState:
        created_at = datetime.now(timezone.utc).isoformat()
        session_id = f"session-{uuid.uuid4().hex[:12]}"
        state = SessionState(
            session_id=session_id,
            created_at=created_at,
            task_text=task_text.strip() if task_text else None,
        )
        with self._lock:
            self._cleanup_locked()
            self._sessions[session_id] = state
            self._touch_locked(session_id)
            self._total_created_count += 1
            self._persist_session_locked(state)
            self._persist_counters_locked()
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            self._cleanup_locked()
            state = self._sessions.get(session_id)
            if state is None:
                return None
            self._touch_locked(session_id)
            return state.model_copy(deep=True)

    def upsert_from_next_step(
        self,
        *,
        session_id: str,
        task_text: str,
        step_id: str,
        action_type: str,
        message: str,
        last_observation_ref: Optional[str],
    ) -> SessionState:
        with self._lock:
            self._cleanup_locked()
            state = self._sessions.get(session_id)
            if state is None:
                state = SessionState(
                    session_id=session_id,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                self._sessions[session_id] = state

            state.task_text = task_text
            state.current_step_id = step_id
            state.last_observation_ref = last_observation_ref
            state.step_history.append(
                SessionStepHistoryItem(
                    created_at=datetime.now(timezone.utc).isoformat(),
                    step_id=step_id,
                    action_type=action_type,
                    message=message,
                )
            )
            self._touch_locked(session_id)
            self._persist_session_locked(state)
            return state.model_copy(deep=True)

    def apply_feedback(
        self,
        *,
        session_id: str,
        step_id: str,
        feedback_type: str,
        comment: Optional[str],
    ) -> Optional[SessionState]:
        with self._lock:
            self._cleanup_locked()
            state = self._sessions.get(session_id)
            if state is None:
                return None

            state.last_feedback_type = feedback_type
            for index in range(len(state.step_history) - 1, -1, -1):
                item = state.step_history[index]
                if item.step_id == step_id:
                    item.feedback_type = feedback_type
                    break
            feedback_message = comment if comment else f"feedback:{feedback_type}"
            feedback_action_type = "feedback_comment" if comment else "feedback"
            state.step_history.append(
                SessionStepHistoryItem(
                    created_at=datetime.now(timezone.utc).isoformat(),
                    step_id=step_id,
                    action_type=feedback_action_type,
                    message=feedback_message,
                    feedback_type=feedback_type,
                )
            )
            self._touch_locked(session_id)
            self._persist_session_locked(state)
            return state.model_copy(deep=True)

    def _touch_locked(self, session_id: str) -> None:
        self._last_touched_utc[session_id] = datetime.now(timezone.utc)

    def _cleanup_locked(self) -> None:
        now = datetime.now(timezone.utc)
        expired_ids = [
            session_id
            for session_id, touched_at in self._last_touched_utc.items()
            if now - touched_at > self._session_ttl
        ]
        for session_id in expired_ids:
            self._sessions.pop(session_id, None)
            self._last_touched_utc.pop(session_id, None)
            self._delete_session_locked(session_id)
        self._total_expired_evicted_count += len(expired_ids)

        # Keep bounded memory under bursty traffic.
        if len(self._sessions) <= self._max_sessions:
            return

        sorted_ids = sorted(
            self._last_touched_utc.items(),
            key=lambda item: item[1],
        )
        overflow_count = len(self._sessions) - self._max_sessions
        for session_id, _ in sorted_ids[:overflow_count]:
            self._sessions.pop(session_id, None)
            self._last_touched_utc.pop(session_id, None)
            self._delete_session_locked(session_id)
        self._total_capacity_evicted_count += max(0, overflow_count)
        if expired_ids or overflow_count > 0:
            self._persist_counters_locked()

    def get_runtime_stats(self) -> dict[str, int]:
        with self._lock:
            self._cleanup_locked()
            return {
                "active_session_count": len(self._sessions),
                "max_sessions": self._max_sessions,
                "session_ttl_seconds": int(self._session_ttl.total_seconds()),
                "total_created_count": self._total_created_count,
                "total_expired_evicted_count": self._total_expired_evicted_count,
                "total_capacity_evicted_count": self._total_capacity_evicted_count,
            }

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._last_touched_utc.clear()
            self._total_created_count = 0
            self._total_expired_evicted_count = 0
            self._total_capacity_evicted_count = 0
            with self._connect() as connection:
                connection.execute("DELETE FROM runtime_sessions")
                connection.execute("DELETE FROM runtime_stats")
                connection.commit()

    def _initialize_db(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    task_text TEXT,
                    last_observation_ref TEXT,
                    current_step_id TEXT,
                    last_feedback_type TEXT,
                    step_history_json TEXT NOT NULL DEFAULT '[]',
                    last_touched_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_stats (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    total_created_count INTEGER NOT NULL DEFAULT 0,
                    total_expired_evicted_count INTEGER NOT NULL DEFAULT 0,
                    total_capacity_evicted_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO runtime_stats (
                    singleton_id,
                    total_created_count,
                    total_expired_evicted_count,
                    total_capacity_evicted_count
                ) VALUES (1, 0, 0, 0)
                """
            )
            connection.commit()

    def _load_from_db(self) -> None:
        with self._lock:
            with self._connect() as connection:
                session_rows = connection.execute(
                    """
                    SELECT
                        session_id,
                        created_at,
                        task_text,
                        last_observation_ref,
                        current_step_id,
                        last_feedback_type,
                        step_history_json,
                        last_touched_utc
                    FROM runtime_sessions
                    """
                ).fetchall()
                stats_row = connection.execute(
                    """
                    SELECT
                        total_created_count,
                        total_expired_evicted_count,
                        total_capacity_evicted_count
                    FROM runtime_stats
                    WHERE singleton_id = 1
                    """
                ).fetchone()

            for row in session_rows:
                history_payload = []
                try:
                    history_payload = json.loads(row["step_history_json"])
                except json.JSONDecodeError:
                    history_payload = []
                state = SessionState(
                    session_id=row["session_id"],
                    created_at=row["created_at"],
                    task_text=row["task_text"],
                    last_observation_ref=row["last_observation_ref"],
                    current_step_id=row["current_step_id"],
                    last_feedback_type=row["last_feedback_type"],
                    step_history=[
                        SessionStepHistoryItem.model_validate(item)
                        for item in history_payload
                    ],
                )
                self._sessions[state.session_id] = state
                self._last_touched_utc[state.session_id] = self._parse_iso_datetime(
                    row["last_touched_utc"],
                    fallback=state.created_at,
                )

            if stats_row is not None:
                self._total_created_count = int(stats_row["total_created_count"] or 0)
                self._total_expired_evicted_count = int(stats_row["total_expired_evicted_count"] or 0)
                self._total_capacity_evicted_count = int(stats_row["total_capacity_evicted_count"] or 0)

    def _persist_session_locked(self, state: SessionState) -> None:
        touched_at = self._last_touched_utc.get(state.session_id, datetime.now(timezone.utc)).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_sessions (
                    session_id,
                    created_at,
                    task_text,
                    last_observation_ref,
                    current_step_id,
                    last_feedback_type,
                    step_history_json,
                    last_touched_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    task_text = excluded.task_text,
                    last_observation_ref = excluded.last_observation_ref,
                    current_step_id = excluded.current_step_id,
                    last_feedback_type = excluded.last_feedback_type,
                    step_history_json = excluded.step_history_json,
                    last_touched_utc = excluded.last_touched_utc
                """,
                (
                    state.session_id,
                    state.created_at,
                    state.task_text,
                    state.last_observation_ref,
                    state.current_step_id,
                    state.last_feedback_type,
                    json.dumps([item.model_dump() for item in state.step_history], ensure_ascii=True),
                    touched_at,
                ),
            )
            connection.commit()

    def _delete_session_locked(self, session_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM runtime_sessions WHERE session_id = ?", (session_id,))
            connection.commit()

    def _persist_counters_locked(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runtime_stats
                SET
                    total_created_count = ?,
                    total_expired_evicted_count = ?,
                    total_capacity_evicted_count = ?
                WHERE singleton_id = 1
                """,
                (
                    self._total_created_count,
                    self._total_expired_evicted_count,
                    self._total_capacity_evicted_count,
                ),
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parse_iso_datetime(value: Optional[str], *, fallback: str) -> datetime:
        raw = value or fallback
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.now(timezone.utc)


def _read_positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


session_manager = SessionManager(
    session_ttl_seconds=_read_positive_int_env("WINDOWS_STEP_GUIDE_SESSION_TTL_SECONDS", 60 * 60 * 4),
    max_sessions=_read_positive_int_env("WINDOWS_STEP_GUIDE_SESSION_MAX_COUNT", 500),
)
