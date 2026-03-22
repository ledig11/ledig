from datetime import datetime, timezone
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.contracts import AnalyzeRequest, NextStepResponse
from app.services.model_gateway import OpenAIResponsesGateway
from app.services.prompt_builder import StepPlannerPromptBuilder
from app.services.runtime_model import RuntimeModelConfig, resolve_runtime_model_config
from app.services.step_planner import ModelStepPlanner, MockStepPlanner, StepPlanner
from app.storage.log_store import LogStore

router = APIRouter()


def get_runtime_model_config(
    x_model_type: Optional[str] = Header(default=None, alias="X-Model-Type"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> RuntimeModelConfig:
    return resolve_runtime_model_config(
        model_type_header=x_model_type,
        api_key_header=x_api_key,
    )


def get_step_planner(
    runtime_model_config: RuntimeModelConfig = Depends(get_runtime_model_config),
) -> StepPlanner:
    fallback_planner = MockStepPlanner()
    if runtime_model_config.provider != "openai":
        return fallback_planner

    return ModelStepPlanner(
        runtime_model_config=runtime_model_config,
        prompt_builder=StepPlannerPromptBuilder(),
        model_gateway=OpenAIResponsesGateway(),
        fallback_planner=fallback_planner,
    )


def get_log_store() -> LogStore:
    return LogStore()


@router.post("/analyze", response_model=NextStepResponse)
def analyze(
    request: AnalyzeRequest,
    step_planner: StepPlanner = Depends(get_step_planner),
    log_store: LogStore = Depends(get_log_store),
) -> NextStepResponse:
    created_at_utc = datetime.now(timezone.utc).isoformat()
    planner_result = step_planner.analyze(request)
    response = planner_result.response
    log_store.insert_analyze_log(
        created_at_utc=created_at_utc,
        task_text=request.task_text,
        session_id=response.session_id,
        step_id=response.step_id,
        action_type=response.action_type,
        instruction=response.instruction,
        observation_session_id=request.observation.session_id,
        observation_captured_at_utc=request.observation.captured_at_utc,
        foreground_window_title=request.observation.foreground_window_title,
        foreground_window_uia_name=request.observation.foreground_window_uia_name,
        foreground_window_uia_automation_id=request.observation.foreground_window_uia_automation_id,
        foreground_window_uia_class_name=request.observation.foreground_window_uia_class_name,
        foreground_window_uia_control_type=request.observation.foreground_window_uia_control_type,
        foreground_window_uia_is_enabled=request.observation.foreground_window_uia_is_enabled,
        foreground_window_uia_child_count=request.observation.foreground_window_uia_child_count,
        foreground_window_uia_child_summary=request.observation.foreground_window_uia_child_summary,
        foreground_window_actionable_summary=request.observation.foreground_window_actionable_summary,
        foreground_window_candidate_elements_json=json.dumps(
            [candidate.model_dump() for candidate in request.observation.foreground_window_candidate_elements],
            ensure_ascii=True,
        ),
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
    log_store.upsert_session_state_after_analyze(
        session_id=response.session_id,
        task_text=request.task_text,
        current_step_id=response.step_id,
        current_action_type=response.action_type,
        current_instruction=response.instruction,
        planner_source=planner_result.planner_source,
        prompt_version=planner_result.prompt_version,
        response_schema_version=planner_result.response_schema_version,
        model_provider=planner_result.model_provider,
        model_type=planner_result.model_type,
        target_candidate_ui_path=planner_result.target_candidate_ui_path,
        target_candidate_label=planner_result.target_candidate_label,
        last_planner_error_code=planner_result.planner_error_code,
        last_planner_error=planner_result.planner_error,
        last_foreground_window_title=request.observation.foreground_window_title,
        last_screenshot_ref=request.observation.screenshot_ref,
        last_updated_at_utc=created_at_utc,
    )
    log_store.insert_analyze_diagnostic(
        created_at_utc=created_at_utc,
        session_id=response.session_id,
        step_id=response.step_id,
        planner_source=planner_result.planner_source,
        prompt_version=planner_result.prompt_version,
        response_schema_version=planner_result.response_schema_version,
        model_provider=planner_result.model_provider,
        model_type=planner_result.model_type,
        target_candidate_ui_path=planner_result.target_candidate_ui_path,
        target_candidate_label=planner_result.target_candidate_label,
        planner_error_code=planner_result.planner_error_code,
        planner_error=planner_result.planner_error,
        raw_model_response_excerpt=planner_result.raw_model_response_excerpt,
    )
    return response
