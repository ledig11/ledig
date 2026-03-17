from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.contracts import StepFeedbackRequest, StepFeedbackResponse
from app.storage.log_store import LogStore

router = APIRouter()


def get_log_store() -> LogStore:
    return LogStore()


@router.post("/feedback", response_model=StepFeedbackResponse)
def submit_feedback(
    request: StepFeedbackRequest,
    log_store: LogStore = Depends(get_log_store),
) -> StepFeedbackResponse:
    response = StepFeedbackResponse(
        accepted=True,
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        message="feedback received",
    )
    log_store.insert_feedback_log(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
        accepted=response.accepted,
        message=response.message,
    )
    return response
