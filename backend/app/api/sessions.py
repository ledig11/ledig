from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.analyze import get_log_store, get_runtime_model_config, get_step_planner, normalize_text
from app.contracts import AnalyzeRequest, ObservationDto, RealtimeEventEntry
from app.models.feedback import SessionFeedbackRequest, SessionFeedbackResponse
from app.models.next_step import SessionNextStepRequest, SessionNextStepResponse
from app.models.session import CreateSessionRequest, CreateSessionResponse, SessionState
from app.orchestrator.session_manager import SessionManager, session_manager
from app.services.next_step_service import NextStepService
from app.services.realtime_hub import realtime_event_hub
from app.services.runtime_model import RuntimeModelConfig
from app.services.step_planner import StepPlanner
from app.storage.log_store_port import LogStorePort

router = APIRouter()


def get_session_manager() -> SessionManager:
    return session_manager


def get_next_step_service(
    runtime_model_config: RuntimeModelConfig = Depends(get_runtime_model_config),
    log_store: LogStorePort = Depends(get_log_store),
    manager: SessionManager = Depends(get_session_manager),
) -> NextStepService:
    planner: StepPlanner = get_step_planner(runtime_model_config=runtime_model_config, log_store=log_store)
    return NextStepService(
        step_planner=planner,
        log_store=log_store,
        session_manager=manager,
    )


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(
    request: Optional[CreateSessionRequest] = None,
    manager: SessionManager = Depends(get_session_manager),
) -> CreateSessionResponse:
    state = manager.create_session(task_text=request.task_text if request is not None else None)
    return CreateSessionResponse(
        session_id=state.session_id,
        created_at=state.created_at,
    )


@router.get("/sessions/runtime-stats")
def get_runtime_stats(
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, int]:
    return manager.get_runtime_stats()


@router.get("/sessions/{session_id}", response_model=SessionState)
def get_session(
    session_id: str = Path(..., min_length=1),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionState:
    state = manager.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    return state


@router.post("/sessions/{session_id}/next-step", response_model=SessionNextStepResponse)
async def next_step(
    request: SessionNextStepRequest,
    session_id: str = Path(..., min_length=1),
    service: NextStepService = Depends(get_next_step_service),
) -> SessionNextStepResponse:
    current_state = service.get_session_state(session_id)
    if current_state is None:
        raise HTTPException(status_code=404, detail="session not found")

    analyze_request = AnalyzeRequest(
        task_text=request.task_text,
        observation=ObservationDto.model_validate(
            request.observation.model_dump() | {"session_id": session_id}
        ),
    )
    result = service.run_next_step(
        session_id=session_id,
        request=analyze_request,
    )
    await realtime_event_hub.publish(
        RealtimeEventEntry(
            event_type="analyze",
            created_at_utc=result.created_at_utc,
            session_id=session_id,
            step_id=result.response.step_id,
            action_type=result.response.action_type,
            feedback_type=None,
            planner_source=result.planner_source,
            observation_quality=result.observation_quality,
            screenshot_ref=normalize_text(request.observation.screenshot_ref),
            note="next_step_generated_from_session",
        )
    )
    return SessionNextStepResponse(
        session_id=result.response.session_id,
        step_id=result.response.step_id,
        instruction=result.response.instruction,
        message=result.response.instruction,
        action_type=result.response.action_type,
        requires_user_action=result.response.requires_user_action,
        confidence=0.7,
        highlight=result.response.highlight,
        observation_summary=request.observation.foreground_window_actionable_summary,
    )


@router.post("/sessions/{session_id}/feedback", response_model=SessionFeedbackResponse)
async def feedback(
    request: SessionFeedbackRequest,
    session_id: str = Path(..., min_length=1),
    service: NextStepService = Depends(get_next_step_service),
    log_store: LogStorePort = Depends(get_log_store),
) -> SessionFeedbackResponse:
    if request.session_id is not None and request.session_id != session_id:
        raise HTTPException(status_code=400, detail="session_id mismatch")

    session_state = service.get_session_state(session_id)
    if session_state is None:
        raise HTTPException(status_code=404, detail="session not found")

    accepted = service.apply_feedback(
        session_id=session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
    )
    created_at_utc = datetime.now(timezone.utc).isoformat()
    message = "feedback received" if accepted else "feedback rejected"
    log_store.insert_feedback_log(
        created_at_utc=created_at_utc,
        session_id=session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        comment=request.comment,
        accepted=accepted,
        message=message,
    )
    log_store.update_session_state_after_feedback(
        session_id=session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        last_updated_at_utc=created_at_utc,
    )
    await realtime_event_hub.publish(
        RealtimeEventEntry(
            event_type="feedback",
            created_at_utc=created_at_utc,
            session_id=session_id,
            step_id=request.step_id,
            action_type=None,
            feedback_type=request.feedback_type,
            planner_source=None,
            observation_quality=None,
            screenshot_ref=None,
            note=message,
        )
    )
    return SessionFeedbackResponse(
        accepted=accepted,
        session_id=session_id,
        step_id=request.step_id,
        feedback_type=request.feedback_type,
        message=message,
    )


@router.get("/sessions-runtime/stats")
def runtime_stats(
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, int]:
    return manager.get_runtime_stats()
