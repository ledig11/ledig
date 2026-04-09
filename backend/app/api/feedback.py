from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.contracts import RealtimeEventEntry, StepFeedbackRequest, StepFeedbackResponse
from app.orchestrator.session_manager import session_manager
from app.services.realtime_hub import realtime_event_hub
from app.storage.log_store import LogStore
from app.storage.log_store_port import LogStorePort

router = APIRouter()


def get_log_store() -> LogStorePort:
    return LogStore()


@router.post("/feedback", response_model=StepFeedbackResponse)
async def submit_feedback(
    request: StepFeedbackRequest,
    log_store: LogStorePort = Depends(get_log_store),
) -> StepFeedbackResponse:
    created_at_utc = datetime.now(timezone.utc).isoformat()
    response = StepFeedbackResponse(
        accepted=True,
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        message="feedback received",
    )
    log_store.insert_feedback_log(
        created_at_utc=created_at_utc,
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
        accepted=response.accepted,
        message=response.message,
    )
    log_store.update_session_state_after_feedback(
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        last_updated_at_utc=created_at_utc,
    )
    session_manager.apply_feedback(
        session_id=request.session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
    )
    await realtime_event_hub.publish(
        RealtimeEventEntry(
            event_type="feedback",
            created_at_utc=created_at_utc,
            session_id=request.session_id,
            step_id=request.step_id,
            action_type=None,
            feedback_type=request.feedback_type,
            planner_source=None,
            observation_quality=None,
            screenshot_ref=None,
            note=response.message,
        )
    )
    return response
