from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from app.contracts import AnalyzeLogEntry, FeedbackLogEntry, SessionSummaryEntry


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "data" / "app.db"


class LogStore:
    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self._database_path = database_path
        self._lock = Lock()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyze_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    task_text TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    observation_session_id TEXT,
                    observation_captured_at_utc TEXT NOT NULL DEFAULT '',
                    foreground_window_title TEXT NOT NULL DEFAULT '',
                    screen_width INTEGER NOT NULL DEFAULT 0,
                    screen_height INTEGER NOT NULL DEFAULT 0,
                    screenshot_ref TEXT NOT NULL DEFAULT '',
                    highlight_rect_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    comment TEXT,
                    accepted INTEGER NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            self._ensure_column(connection, "analyze_logs", "observation_session_id", "TEXT")
            self._ensure_column(
                connection,
                "analyze_logs",
                "observation_captured_at_utc",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_title",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "screen_width",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "screen_height",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "screenshot_ref",
                "TEXT NOT NULL DEFAULT ''",
            )
            connection.commit()

    def insert_analyze_log(
        self,
        *,
        created_at_utc: str,
        task_text: str,
        session_id: str,
        step_id: str,
        action_type: str,
        instruction: str,
        observation_session_id: str | None,
        observation_captured_at_utc: str,
        foreground_window_title: str,
        screen_width: int,
        screen_height: int,
        screenshot_ref: str,
        highlight_rect: dict[str, Any],
    ) -> None:
        highlight_rect_json = json.dumps(highlight_rect, ensure_ascii=True)

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO analyze_logs (
                        created_at_utc,
                        task_text,
                        session_id,
                        step_id,
                        action_type,
                        instruction,
                        observation_session_id,
                        observation_captured_at_utc,
                        foreground_window_title,
                        screen_width,
                        screen_height,
                        screenshot_ref,
                        highlight_rect_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at_utc,
                        task_text,
                        session_id,
                        step_id,
                        action_type,
                        instruction,
                        observation_session_id,
                        observation_captured_at_utc,
                        foreground_window_title,
                        screen_width,
                        screen_height,
                        screenshot_ref,
                        highlight_rect_json,
                    ),
                )
                connection.commit()

    def insert_feedback_log(
        self,
        *,
        created_at_utc: str,
        session_id: str,
        step_id: str,
        feedback_type: str,
        comment: str | None,
        accepted: bool,
        message: str,
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO feedback_logs (
                        created_at_utc,
                        session_id,
                        step_id,
                        feedback_type,
                        comment,
                        accepted,
                        message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at_utc,
                        session_id,
                        step_id,
                        feedback_type,
                        comment,
                        int(accepted),
                        message,
                    ),
                )
                connection.commit()

    def get_recent_analyze_logs(self, limit: int = 10) -> list[AnalyzeLogEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    created_at_utc,
                    task_text,
                    session_id,
                    step_id,
                    action_type,
                    instruction,
                    observation_session_id,
                    observation_captured_at_utc,
                    foreground_window_title,
                    screen_width,
                    screen_height,
                    screenshot_ref,
                    highlight_rect_json
                FROM analyze_logs
                ORDER BY created_at_utc DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            AnalyzeLogEntry(
                created_at_utc=row[0],
                task_text=row[1],
                session_id=row[2],
                step_id=row[3],
                action_type=row[4],
                instruction=row[5],
                observation_session_id=row[6],
                observation_captured_at_utc=row[7],
                foreground_window_title=row[8],
                screen_width=row[9],
                screen_height=row[10],
                screenshot_ref=row[11],
                highlight_rect=json.loads(row[12]),
            )
            for row in rows
        ]

    def get_recent_feedback_logs(self, limit: int = 10) -> list[FeedbackLogEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    created_at_utc,
                    session_id,
                    step_id,
                    feedback_type,
                    comment,
                    accepted,
                    message
                FROM feedback_logs
                ORDER BY created_at_utc DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            FeedbackLogEntry(
                created_at_utc=row[0],
                session_id=row[1],
                step_id=row[2],
                feedback_type=row[3],
                comment=row[4],
                accepted=bool(row[5]),
                message=row[6],
            )
            for row in rows
        ]

    def get_recent_session_summaries(self, limit: int = 10) -> list[SessionSummaryEntry]:
        with self._connect() as connection:
            session_rows = connection.execute(
                """
                SELECT session_id, MAX(created_at_utc) AS last_updated_at_utc
                FROM (
                    SELECT session_id, created_at_utc FROM analyze_logs
                    UNION ALL
                    SELECT session_id, created_at_utc FROM feedback_logs
                )
                GROUP BY session_id
                ORDER BY last_updated_at_utc DESC, session_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            summaries: list[SessionSummaryEntry] = []
            for session_id, last_updated_at_utc in session_rows:
                latest_analyze = connection.execute(
                    """
                    SELECT task_text, step_id, action_type
                    FROM analyze_logs
                    WHERE session_id = ?
                    ORDER BY created_at_utc DESC, id DESC
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()
                latest_feedback = connection.execute(
                    """
                    SELECT step_id, feedback_type
                    FROM feedback_logs
                    WHERE session_id = ?
                    ORDER BY created_at_utc DESC, id DESC
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()

                last_task_text = latest_analyze[0] if latest_analyze else None
                analyze_step_id = latest_analyze[1] if latest_analyze else None
                last_action_type = latest_analyze[2] if latest_analyze else None
                feedback_step_id = latest_feedback[0] if latest_feedback else None
                last_feedback_type = latest_feedback[1] if latest_feedback else None

                summaries.append(
                    SessionSummaryEntry(
                        session_id=session_id,
                        last_task_text=last_task_text,
                        last_step_id=feedback_step_id or analyze_step_id,
                        last_action_type=last_action_type,
                        last_feedback_type=last_feedback_type,
                        last_updated_at_utc=last_updated_at_utc,
                    )
                )

        return summaries

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        existing_columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in existing_columns:
            return

        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
