from fastapi import APIRouter, Depends

from app.contracts import AnalyzeLogEntry, FeedbackLogEntry, SessionSummaryEntry
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


@router.get("/debug/session-summaries", response_model=list[SessionSummaryEntry])
def get_recent_session_summaries(
    log_store: LogStore = Depends(get_log_store),
) -> list[SessionSummaryEntry]:
    return log_store.get_recent_session_summaries()
