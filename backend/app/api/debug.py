from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

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
from app.storage.log_store import LogStore
from app.storage.log_store_port import LogStorePort

router = APIRouter()


def get_log_store() -> LogStorePort:
    return LogStore()


@router.get("/debug/analyze-logs", response_model=list[AnalyzeLogEntry])
def get_recent_analyze_logs(
    log_store: LogStorePort = Depends(get_log_store),
) -> list[AnalyzeLogEntry]:
    return log_store.get_recent_analyze_logs()


@router.get("/debug/feedback-logs", response_model=list[FeedbackLogEntry])
def get_recent_feedback_logs(
    log_store: LogStorePort = Depends(get_log_store),
) -> list[FeedbackLogEntry]:
    return log_store.get_recent_feedback_logs()


@router.get("/debug/analyze-diagnostics", response_model=list[AnalyzeDiagnosticEntry])
def get_recent_analyze_diagnostics(
    limit: int = Query(default=20, ge=1, le=100),
    observation_quality: Optional[str] = Query(default=None, min_length=1, max_length=20),
    min_observation_candidate_count: int = Query(default=0, ge=0, le=200),
    planner_source: Optional[str] = Query(default=None, min_length=1, max_length=30),
    planner_error_code: Optional[str] = Query(default=None, min_length=1, max_length=60),
    log_store: LogStorePort = Depends(get_log_store),
) -> list[AnalyzeDiagnosticEntry]:
    return log_store.get_recent_analyze_diagnostics(
        limit=limit,
        observation_quality=observation_quality,
        min_observation_candidate_count=min_observation_candidate_count,
        planner_source=planner_source,
        planner_error_code=planner_error_code,
    )


@router.get("/debug/observation-traces", response_model=list[ObservationTraceEntry])
def get_recent_observation_traces(
    session_id: Optional[str] = Query(default=None, min_length=1, max_length=200),
    screenshot_ref: Optional[str] = Query(default=None, min_length=1, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStorePort = Depends(get_log_store),
) -> list[ObservationTraceEntry]:
    return log_store.get_recent_observation_traces(
        limit=limit,
        session_id=session_id,
        screenshot_ref=screenshot_ref,
    )


@router.get("/debug/diagnostic-timeline", response_model=list[DiagnosticTimelineEntry])
def get_recent_diagnostic_timeline(
    session_id: Optional[str] = Query(default=None, min_length=1, max_length=200),
    screenshot_ref: Optional[str] = Query(default=None, min_length=1, max_length=500),
    observation_quality: Optional[str] = Query(default=None, min_length=1, max_length=20),
    min_observation_candidate_count: int = Query(default=0, ge=0, le=200),
    planner_source: Optional[str] = Query(default=None, min_length=1, max_length=30),
    planner_error_code: Optional[str] = Query(default=None, min_length=1, max_length=60),
    errors_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStorePort = Depends(get_log_store),
) -> list[DiagnosticTimelineEntry]:
    return log_store.get_recent_diagnostic_timeline(
        limit=limit,
        session_id=session_id,
        screenshot_ref=screenshot_ref,
        observation_quality=observation_quality,
        min_observation_candidate_count=min_observation_candidate_count,
        planner_source=planner_source,
        planner_error_code=planner_error_code,
        errors_only=errors_only,
    )


@router.get("/debug/session-summaries", response_model=list[SessionSummaryEntry])
def get_recent_session_summaries(
    log_store: LogStorePort = Depends(get_log_store),
) -> list[SessionSummaryEntry]:
    return log_store.get_recent_session_summaries()


@router.get("/debug/session-states", response_model=list[SessionStateEntry])
def get_recent_session_states(
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStorePort = Depends(get_log_store),
) -> list[SessionStateEntry]:
    return log_store.get_recent_session_states(limit=limit)


@router.get("/debug/session-replay", response_model=list[SessionReplayEventEntry])
def get_session_replay_events(
    session_id: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=200, ge=1, le=1000),
    log_store: LogStorePort = Depends(get_log_store),
) -> list[SessionReplayEventEntry]:
    return log_store.get_session_replay_events(
        session_id=session_id,
        limit=limit,
    )
