from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.contracts import AnalyzeRequest, NextStepResponse
from app.services.step_planner import MockStepPlanner, StepPlanner
from app.storage.log_store import LogStore

router = APIRouter()


def get_step_planner() -> StepPlanner:
    return MockStepPlanner()


def get_log_store() -> LogStore:
    return LogStore()


@router.post("/analyze", response_model=NextStepResponse)
def analyze(
    request: AnalyzeRequest,
    step_planner: StepPlanner = Depends(get_step_planner),
    log_store: LogStore = Depends(get_log_store),
) -> NextStepResponse:
    response = step_planner.analyze(request)
    log_store.insert_analyze_log(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        task_text=request.task_text,
        session_id=response.session_id,
        step_id=response.step_id,
        action_type=response.action_type,
        instruction=response.instruction,
        observation_session_id=request.observation.session_id,
        observation_captured_at_utc=request.observation.captured_at_utc,
        foreground_window_title=request.observation.foreground_window_title,
        screen_width=request.observation.screen_width,
        screen_height=request.observation.screen_height,
        screenshot_ref=request.observation.screenshot_ref,
        highlight_rect={
            "x": response.highlight.rect.x,
            "y": response.highlight.rect.y,
            "width": response.highlight.rect.width,
            "height": response.highlight.rect.height,
        },
    )
    return response
