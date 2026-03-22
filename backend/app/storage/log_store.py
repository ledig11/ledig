from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from app.contracts import AnalyzeDiagnosticEntry, AnalyzeLogEntry, FeedbackLogEntry, ObservationTraceEntry, SessionStateEntry, SessionSummaryEntry


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
                    foreground_window_uia_name TEXT NOT NULL DEFAULT '',
                    foreground_window_uia_automation_id TEXT NOT NULL DEFAULT '',
                    foreground_window_uia_class_name TEXT NOT NULL DEFAULT '',
                    foreground_window_uia_control_type TEXT NOT NULL DEFAULT '',
                    foreground_window_uia_is_enabled INTEGER NOT NULL DEFAULT 0,
                    foreground_window_uia_child_count INTEGER NOT NULL DEFAULT 0,
                    foreground_window_uia_child_summary TEXT NOT NULL DEFAULT '',
                    foreground_window_actionable_summary TEXT NOT NULL DEFAULT '',
                    foreground_window_candidate_elements_json TEXT NOT NULL DEFAULT '[]',
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyze_diagnostics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    planner_source TEXT NOT NULL,
                    prompt_version TEXT,
                    response_schema_version TEXT,
                    model_provider TEXT,
                    model_type TEXT,
                    target_candidate_ui_path TEXT,
                    target_candidate_label TEXT,
                    planner_error_code TEXT,
                    planner_error TEXT,
                    raw_model_response_excerpt TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_states (
                    session_id TEXT PRIMARY KEY,
                    task_text TEXT,
                    current_step_id TEXT,
                    current_action_type TEXT,
                    current_instruction TEXT,
                    last_feedback_type TEXT,
                    session_status TEXT NOT NULL DEFAULT 'active',
                    planner_source TEXT,
                    prompt_version TEXT,
                    response_schema_version TEXT,
                    model_provider TEXT,
                    model_type TEXT,
                    target_candidate_ui_path TEXT,
                    target_candidate_label TEXT,
                    last_planner_error_code TEXT,
                    last_planner_error TEXT,
                    completed_step_count INTEGER NOT NULL DEFAULT 0,
                    incorrect_feedback_count INTEGER NOT NULL DEFAULT 0,
                    reanalyze_feedback_count INTEGER NOT NULL DEFAULT 0,
                    last_foreground_window_title TEXT,
                    last_screenshot_ref TEXT,
                    last_updated_at_utc TEXT NOT NULL
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
                "foreground_window_uia_name",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_automation_id",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_class_name",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_control_type",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_is_enabled",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_child_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_uia_child_summary",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_actionable_summary",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(
                connection,
                "analyze_logs",
                "foreground_window_candidate_elements_json",
                "TEXT NOT NULL DEFAULT '[]'",
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
            self._ensure_column(connection, "session_states", "task_text", "TEXT")
            self._ensure_column(connection, "session_states", "current_step_id", "TEXT")
            self._ensure_column(connection, "session_states", "current_action_type", "TEXT")
            self._ensure_column(connection, "session_states", "current_instruction", "TEXT")
            self._ensure_column(connection, "session_states", "last_feedback_type", "TEXT")
            self._ensure_column(
                connection,
                "session_states",
                "session_status",
                "TEXT NOT NULL DEFAULT 'active'",
            )
            self._ensure_column(connection, "session_states", "planner_source", "TEXT")
            self._ensure_column(connection, "session_states", "prompt_version", "TEXT")
            self._ensure_column(connection, "session_states", "response_schema_version", "TEXT")
            self._ensure_column(connection, "session_states", "model_provider", "TEXT")
            self._ensure_column(connection, "session_states", "model_type", "TEXT")
            self._ensure_column(connection, "session_states", "target_candidate_ui_path", "TEXT")
            self._ensure_column(connection, "session_states", "target_candidate_label", "TEXT")
            self._ensure_column(connection, "session_states", "last_planner_error_code", "TEXT")
            self._ensure_column(connection, "session_states", "last_planner_error", "TEXT")
            self._ensure_column(
                connection,
                "session_states",
                "completed_step_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "session_states",
                "incorrect_feedback_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "session_states",
                "reanalyze_feedback_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(connection, "session_states", "last_foreground_window_title", "TEXT")
            self._ensure_column(connection, "session_states", "last_screenshot_ref", "TEXT")
            self._ensure_column(
                connection,
                "session_states",
                "last_updated_at_utc",
                "TEXT NOT NULL DEFAULT ''",
            )
            self._ensure_column(connection, "analyze_diagnostics", "prompt_version", "TEXT")
            self._ensure_column(connection, "analyze_diagnostics", "response_schema_version", "TEXT")
            self._ensure_column(connection, "analyze_diagnostics", "target_candidate_ui_path", "TEXT")
            self._ensure_column(connection, "analyze_diagnostics", "target_candidate_label", "TEXT")
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
        observation_session_id: Optional[str],
        observation_captured_at_utc: str,
        foreground_window_title: str,
        foreground_window_uia_name: str,
        foreground_window_uia_automation_id: str,
        foreground_window_uia_class_name: str,
        foreground_window_uia_control_type: str,
        foreground_window_uia_is_enabled: bool,
        foreground_window_uia_child_count: int,
        foreground_window_uia_child_summary: str,
        foreground_window_actionable_summary: str,
        foreground_window_candidate_elements_json: str,
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
                        foreground_window_uia_name,
                        foreground_window_uia_automation_id,
                        foreground_window_uia_class_name,
                        foreground_window_uia_control_type,
                        foreground_window_uia_is_enabled,
                        foreground_window_uia_child_count,
                        foreground_window_uia_child_summary,
                        foreground_window_actionable_summary,
                        foreground_window_candidate_elements_json,
                        screen_width,
                        screen_height,
                        screenshot_ref,
                        highlight_rect_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        foreground_window_uia_name,
                        foreground_window_uia_automation_id,
                        foreground_window_uia_class_name,
                        foreground_window_uia_control_type,
                        int(foreground_window_uia_is_enabled),
                        foreground_window_uia_child_count,
                        foreground_window_uia_child_summary,
                        foreground_window_actionable_summary,
                        foreground_window_candidate_elements_json,
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
        comment: Optional[str],
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

    def insert_analyze_diagnostic(
        self,
        *,
        created_at_utc: str,
        session_id: str,
        step_id: str,
        planner_source: str,
        prompt_version: Optional[str],
        response_schema_version: Optional[str],
        model_provider: Optional[str],
        model_type: Optional[str],
        target_candidate_ui_path: Optional[str],
        target_candidate_label: Optional[str],
        planner_error_code: Optional[str],
        planner_error: Optional[str],
        raw_model_response_excerpt: Optional[str],
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO analyze_diagnostics (
                        created_at_utc,
                        session_id,
                        step_id,
                        planner_source,
                        prompt_version,
                        response_schema_version,
                        model_provider,
                        model_type,
                        target_candidate_ui_path,
                        target_candidate_label,
                        planner_error_code,
                        planner_error,
                        raw_model_response_excerpt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at_utc,
                        session_id,
                        step_id,
                        planner_source,
                        prompt_version,
                        response_schema_version,
                        model_provider,
                        model_type,
                        target_candidate_ui_path,
                        target_candidate_label,
                        planner_error_code,
                        planner_error,
                        raw_model_response_excerpt,
                    ),
                )
                connection.commit()

    def upsert_session_state_after_analyze(
        self,
        *,
        session_id: str,
        task_text: str,
        current_step_id: str,
        current_action_type: str,
        current_instruction: str,
        planner_source: str,
        prompt_version: Optional[str],
        response_schema_version: Optional[str],
        model_provider: Optional[str],
        model_type: Optional[str],
        target_candidate_ui_path: Optional[str],
        target_candidate_label: Optional[str],
        last_planner_error_code: Optional[str],
        last_planner_error: Optional[str],
        last_foreground_window_title: str,
        last_screenshot_ref: str,
        last_updated_at_utc: str,
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO session_states (
                        session_id,
                        task_text,
                        current_step_id,
                        current_action_type,
                        current_instruction,
                        session_status,
                        planner_source,
                        prompt_version,
                        response_schema_version,
                        model_provider,
                        model_type,
                        target_candidate_ui_path,
                        target_candidate_label,
                        last_planner_error_code,
                        last_planner_error,
                        last_foreground_window_title,
                        last_screenshot_ref,
                        last_updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        task_text = excluded.task_text,
                        current_step_id = excluded.current_step_id,
                        current_action_type = excluded.current_action_type,
                        current_instruction = excluded.current_instruction,
                        session_status = 'active',
                        planner_source = excluded.planner_source,
                        prompt_version = excluded.prompt_version,
                        response_schema_version = excluded.response_schema_version,
                        model_provider = excluded.model_provider,
                        model_type = excluded.model_type,
                        target_candidate_ui_path = excluded.target_candidate_ui_path,
                        target_candidate_label = excluded.target_candidate_label,
                        last_planner_error_code = excluded.last_planner_error_code,
                        last_planner_error = excluded.last_planner_error,
                        last_foreground_window_title = excluded.last_foreground_window_title,
                        last_screenshot_ref = excluded.last_screenshot_ref,
                        last_updated_at_utc = excluded.last_updated_at_utc
                    """,
                    (
                        session_id,
                        task_text,
                        current_step_id,
                        current_action_type,
                        current_instruction,
                        "active",
                        planner_source,
                        prompt_version,
                        response_schema_version,
                        model_provider,
                        model_type,
                        target_candidate_ui_path,
                        target_candidate_label,
                        last_planner_error_code,
                        last_planner_error,
                        last_foreground_window_title,
                        last_screenshot_ref,
                        last_updated_at_utc,
                    ),
                )
                connection.commit()

    def update_session_state_after_feedback(
        self,
        *,
        session_id: str,
        step_id: str,
        feedback_type: str,
        last_updated_at_utc: str,
    ) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO session_states (
                        session_id,
                        current_step_id,
                        last_feedback_type,
                        session_status,
                        completed_step_count,
                        incorrect_feedback_count,
                        reanalyze_feedback_count,
                        last_updated_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        current_step_id = excluded.current_step_id,
                        last_feedback_type = excluded.last_feedback_type,
                        session_status = CASE
                            WHEN excluded.last_feedback_type = 'completed' THEN 'completed'
                            WHEN excluded.last_feedback_type = 'incorrect' THEN 'needs_review'
                            ELSE 'active'
                        END,
                        completed_step_count = session_states.completed_step_count + CASE
                            WHEN excluded.last_feedback_type = 'completed' THEN 1
                            ELSE 0
                        END,
                        incorrect_feedback_count = session_states.incorrect_feedback_count + CASE
                            WHEN excluded.last_feedback_type = 'incorrect' THEN 1
                            ELSE 0
                        END,
                        reanalyze_feedback_count = session_states.reanalyze_feedback_count + CASE
                            WHEN excluded.last_feedback_type = 'reanalyze' THEN 1
                            ELSE 0
                        END,
                        last_updated_at_utc = excluded.last_updated_at_utc
                    """,
                    (
                        session_id,
                        step_id,
                        feedback_type,
                        self._feedback_type_to_session_status(feedback_type),
                        1 if feedback_type == "completed" else 0,
                        1 if feedback_type == "incorrect" else 0,
                        1 if feedback_type == "reanalyze" else 0,
                        last_updated_at_utc,
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
                    foreground_window_uia_name,
                    foreground_window_uia_automation_id,
                    foreground_window_uia_class_name,
                    foreground_window_uia_control_type,
                    foreground_window_uia_is_enabled,
                    foreground_window_uia_child_count,
                    foreground_window_uia_child_summary,
                    foreground_window_actionable_summary,
                    foreground_window_candidate_elements_json,
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
                foreground_window_uia_name=row[9],
                foreground_window_uia_automation_id=row[10],
                foreground_window_uia_class_name=row[11],
                foreground_window_uia_control_type=row[12],
                foreground_window_uia_is_enabled=bool(row[13]),
                foreground_window_uia_child_count=row[14],
                foreground_window_uia_child_summary=row[15],
                foreground_window_actionable_summary=row[16],
                foreground_window_candidate_elements=self._deserialize_candidate_elements(row[17]),
                screen_width=row[18],
                screen_height=row[19],
                screenshot_ref=row[20],
                highlight_rect=json.loads(row[21]),
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

    def get_recent_analyze_diagnostics(self, limit: int = 20) -> list[AnalyzeDiagnosticEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    created_at_utc,
                    session_id,
                    step_id,
                    planner_source,
                    prompt_version,
                    response_schema_version,
                    model_provider,
                    model_type,
                    target_candidate_ui_path,
                    target_candidate_label,
                    planner_error_code,
                    planner_error,
                    raw_model_response_excerpt
                FROM analyze_diagnostics
                ORDER BY created_at_utc DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            AnalyzeDiagnosticEntry(
                created_at_utc=row[0],
                session_id=row[1],
                step_id=row[2],
                planner_source=row[3],
                prompt_version=row[4],
                response_schema_version=row[5],
                model_provider=row[6],
                model_type=row[7],
                target_candidate_ui_path=row[8],
                target_candidate_label=row[9],
                planner_error_code=row[10],
                planner_error=row[11],
                raw_model_response_excerpt=row[12],
            )
            for row in rows
        ]

    def get_recent_observation_traces(
        self,
        limit: int = 20,
        session_id: Optional[str] = None,
        screenshot_ref: Optional[str] = None,
    ) -> list[ObservationTraceEntry]:
        where_clauses: list[str] = []
        parameters: list[Any] = []

        if session_id:
            where_clauses.append("session_id = ?")
            parameters.append(session_id)

        if screenshot_ref:
            where_clauses.append("screenshot_ref = ?")
            parameters.append(screenshot_ref)

        where_sql = ""
        if where_clauses:
            where_sql = f"WHERE {' AND '.join(where_clauses)}"

        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    created_at_utc,
                    task_text,
                    session_id,
                    step_id,
                    action_type,
                    observation_captured_at_utc,
                    foreground_window_title,
                    foreground_window_uia_name,
                    foreground_window_uia_automation_id,
                    foreground_window_uia_class_name,
                    foreground_window_uia_control_type,
                    foreground_window_uia_is_enabled,
                    foreground_window_uia_child_count,
                    foreground_window_uia_child_summary,
                    foreground_window_actionable_summary,
                    foreground_window_candidate_elements_json,
                    screen_width,
                    screen_height,
                    screenshot_ref
                FROM analyze_logs
                {where_sql}
                ORDER BY created_at_utc DESC, id DESC
                LIMIT ?
                """,
                tuple(parameters),
            ).fetchall()

        return [
            ObservationTraceEntry(
                created_at_utc=row[0],
                task_text=row[1],
                session_id=row[2],
                step_id=row[3],
                action_type=row[4],
                observation_captured_at_utc=row[5],
                foreground_window_title=row[6],
                foreground_window_uia_name=row[7],
                foreground_window_uia_automation_id=row[8],
                foreground_window_uia_class_name=row[9],
                foreground_window_uia_control_type=row[10],
                foreground_window_uia_is_enabled=bool(row[11]),
                foreground_window_uia_child_count=row[12],
                foreground_window_uia_child_summary=row[13],
                foreground_window_actionable_summary=row[14],
                foreground_window_candidate_elements=self._deserialize_candidate_elements(row[15]),
                screen_width=row[16],
                screen_height=row[17],
                screenshot_ref=row[18],
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

    def get_recent_session_states(self, limit: int = 20) -> list[SessionStateEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    task_text,
                    current_step_id,
                    current_action_type,
                    current_instruction,
                    last_feedback_type,
                    session_status,
                    planner_source,
                    prompt_version,
                    response_schema_version,
                    model_provider,
                    model_type,
                    target_candidate_ui_path,
                    target_candidate_label,
                    last_planner_error_code,
                    last_planner_error,
                    completed_step_count,
                    incorrect_feedback_count,
                    reanalyze_feedback_count,
                    last_foreground_window_title,
                    last_screenshot_ref,
                    last_updated_at_utc
                FROM session_states
                ORDER BY last_updated_at_utc DESC, session_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            SessionStateEntry(
                session_id=row[0],
                task_text=row[1],
                current_step_id=row[2],
                current_action_type=row[3],
                current_instruction=row[4],
                last_feedback_type=row[5],
                session_status=row[6],
                planner_source=row[7],
                prompt_version=row[8],
                response_schema_version=row[9],
                model_provider=row[10],
                model_type=row[11],
                target_candidate_ui_path=row[12],
                target_candidate_label=row[13],
                last_planner_error_code=row[14],
                last_planner_error=row[15],
                completed_step_count=row[16],
                incorrect_feedback_count=row[17],
                reanalyze_feedback_count=row[18],
                last_foreground_window_title=row[19],
                last_screenshot_ref=row[20],
                last_updated_at_utc=row[21],
            )
            for row in rows
        ]

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

    @staticmethod
    def _deserialize_candidate_elements(raw_json: str) -> list[dict[str, Any]]:
        try:
            loaded = json.loads(raw_json)
        except json.JSONDecodeError:
            return []

        return loaded if isinstance(loaded, list) else []

    @staticmethod
    def _feedback_type_to_session_status(feedback_type: str) -> str:
        return {
            "completed": "completed",
            "incorrect": "needs_review",
            "reanalyze": "active",
        }.get(feedback_type, "active")
