from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.contracts import AnalyzeDiagnosticEntry, AnalyzeLogEntry, FeedbackLogEntry, ObservationTraceEntry, SessionStateEntry, SessionSummaryEntry
from app.storage.log_store import LogStore

router = APIRouter()


def get_log_store() -> LogStore:
    return LogStore()


@router.get("/debug/analyze-logs", response_model=list[AnalyzeLogEntry])
def get_recent_analyze_logs(
    log_store: LogStore = Depends(get_log_store),
) -> list[AnalyzeLogEntry]:
    return log_store.get_recent_analyze_logs()


@router.get("/debug/feedback-logs", response_model=list[FeedbackLogEntry])
def get_recent_feedback_logs(
    log_store: LogStore = Depends(get_log_store),
) -> list[FeedbackLogEntry]:
    return log_store.get_recent_feedback_logs()


@router.get("/debug/analyze-diagnostics", response_model=list[AnalyzeDiagnosticEntry])
def get_recent_analyze_diagnostics(
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStore = Depends(get_log_store),
) -> list[AnalyzeDiagnosticEntry]:
    return log_store.get_recent_analyze_diagnostics(limit=limit)


@router.get("/debug/observation-traces", response_model=list[ObservationTraceEntry])
def get_recent_observation_traces(
    session_id: Optional[str] = Query(default=None, min_length=1, max_length=200),
    screenshot_ref: Optional[str] = Query(default=None, min_length=1, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStore = Depends(get_log_store),
) -> list[ObservationTraceEntry]:
    return log_store.get_recent_observation_traces(
        limit=limit,
        session_id=session_id,
        screenshot_ref=screenshot_ref,
    )


@router.get("/debug/session-summaries", response_model=list[SessionSummaryEntry])
def get_recent_session_summaries(
    log_store: LogStore = Depends(get_log_store),
) -> list[SessionSummaryEntry]:
    return log_store.get_recent_session_summaries()


@router.get("/debug/session-states", response_model=list[SessionStateEntry])
def get_recent_session_states(
    limit: int = Query(default=20, ge=1, le=100),
    log_store: LogStore = Depends(get_log_store),
) -> list[SessionStateEntry]:
    return log_store.get_recent_session_states(limit=limit)
