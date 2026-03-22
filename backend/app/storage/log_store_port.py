from __future__ import annotations

from typing import Any, Optional, Protocol

from app.contracts import (
    AnalyzeDiagnosticEntry,
    AnalyzeLogEntry,
    DiagnosticTimelineEntry,
    FeedbackLogEntry,
    ObservationTraceEntry,
    SessionReplayEventEntry,
    SessionStateEntry,
    SessionSummaryEntry,
)


class LogStorePort(Protocol):
    def initialize(self) -> None:
        ...

    def insert_analyze_log(self, **kwargs: Any) -> None:
        ...

    def insert_feedback_log(self, **kwargs: Any) -> None:
        ...

    def insert_analyze_diagnostic(self, **kwargs: Any) -> None:
        ...

    def upsert_session_state_after_analyze(self, **kwargs: Any) -> None:
        ...

    def update_session_state_after_feedback(self, **kwargs: Any) -> None:
        ...

    def get_recent_analyze_logs(self, limit: int = 10) -> list[AnalyzeLogEntry]:
        ...

    def get_recent_feedback_logs(self, limit: int = 10) -> list[FeedbackLogEntry]:
        ...

    def get_recent_analyze_diagnostics(
        self,
        *,
        limit: int = 20,
        observation_quality: Optional[str] = None,
        min_observation_candidate_count: int = 0,
        planner_source: Optional[str] = None,
        planner_error_code: Optional[str] = None,
    ) -> list[AnalyzeDiagnosticEntry]:
        ...

    def get_recent_observation_traces(
        self,
        *,
        limit: int = 20,
        session_id: Optional[str] = None,
        screenshot_ref: Optional[str] = None,
    ) -> list[ObservationTraceEntry]:
        ...

    def get_recent_diagnostic_timeline(
        self,
        *,
        limit: int = 20,
        session_id: Optional[str] = None,
        screenshot_ref: Optional[str] = None,
        observation_quality: Optional[str] = None,
        min_observation_candidate_count: int = 0,
        planner_source: Optional[str] = None,
        planner_error_code: Optional[str] = None,
        errors_only: bool = False,
    ) -> list[DiagnosticTimelineEntry]:
        ...

    def get_recent_session_summaries(self, limit: int = 10) -> list[SessionSummaryEntry]:
        ...

    def get_recent_session_states(self, limit: int = 20) -> list[SessionStateEntry]:
        ...

    def get_session_replay_events(self, session_id: str, limit: int = 200) -> list[SessionReplayEventEntry]:
        ...

    def get_session_state(self, session_id: str) -> Optional[SessionStateEntry]:
        ...
