from datetime import datetime, timezone
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.contracts import AnalyzeRequest, NextStepResponse, RealtimeEventEntry
from app.services.model_gateway import OpenAIResponsesGateway
from app.services.prompt_builder import StepPlannerPromptBuilder
from app.services.realtime_hub import realtime_event_hub
from app.services.runtime_model import RuntimeModelConfig, resolve_runtime_model_config
from app.services.step_planner import (
    ModelStepPlanner,
    MockStepPlanner,
    SettingsBluetoothScenarioPlanner,
    SettingsDisplayScenarioPlanner,
    SettingsNetworkScenarioPlanner,
    SettingsPersonalizationScenarioPlanner,
    StepPlanner,
)
from app.storage.log_store import LogStore
from app.storage.log_store_port import LogStorePort

router = APIRouter()


def get_runtime_model_config(
    x_model_type: Optional[str] = Header(default=None, alias="X-Model-Type"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> RuntimeModelConfig:
    return resolve_runtime_model_config(
        model_type_header=x_model_type,
        api_key_header=x_api_key,
    )


def get_log_store() -> LogStorePort:
    return LogStore()


def parse_actionable_summary_metrics(actionable_summary: str) -> dict[str, Optional[int]]:
    result: dict[str, Optional[int]] = {
        "candidate_count": None,
        "scanned_nodes": None,
        "scan_depth": None,
    }
    if not actionable_summary:
        return result

    for raw_part in actionable_summary.split(";"):
        part = raw_part.strip()
        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        normalized_key = key.strip().casefold()
        normalized_value = value.strip()
        if not normalized_value:
            continue

        try:
            parsed_value = int(normalized_value)
        except ValueError:
            continue

        if normalized_key == "candidate_count":
            result["candidate_count"] = parsed_value
        elif normalized_key == "scanned_nodes":
            result["scanned_nodes"] = parsed_value
        elif normalized_key == "scan_depth":
            result["scan_depth"] = parsed_value

    return result


def normalize_text(value: Optional[str]) -> str:
    return value or ""


def normalize_int(value: Optional[int], fallback: int = 0) -> int:
    return value if value is not None else fallback


def normalize_bool(value: Optional[bool], fallback: bool = False) -> bool:
    return value if value is not None else fallback


def classify_observation_quality(
    *,
    candidate_count: int,
    scanned_nodes: Optional[int],
    scan_depth: Optional[int],
) -> str:
    if candidate_count <= 0:
        return "low"

    if scanned_nodes is None or scan_depth is None:
        return "medium"

    if scanned_nodes >= 80 and scan_depth >= 3 and candidate_count >= 5:
        return "high"

    if scanned_nodes >= 20 and scan_depth >= 2 and candidate_count >= 2:
        return "medium"

    return "low"


def get_step_planner(
    runtime_model_config: RuntimeModelConfig = Depends(get_runtime_model_config),
    log_store: LogStorePort = Depends(get_log_store),
) -> StepPlanner:
    fallback_planner = SettingsPersonalizationScenarioPlanner(
        fallback_planner=SettingsDisplayScenarioPlanner(
            fallback_planner=SettingsNetworkScenarioPlanner(
                fallback_planner=SettingsBluetoothScenarioPlanner(
                    fallback_planner=MockStepPlanner(),
                    session_state_reader=log_store.get_session_state,
                ),
                session_state_reader=log_store.get_session_state,
            ),
            session_state_reader=log_store.get_session_state,
        ),
        session_state_reader=log_store.get_session_state,
    )
    if runtime_model_config.provider != "openai":
        return fallback_planner

    return ModelStepPlanner(
        runtime_model_config=runtime_model_config,
        prompt_builder=StepPlannerPromptBuilder(),
        model_gateway=OpenAIResponsesGateway(),
        fallback_planner=fallback_planner,
    )


@router.post("/analyze", response_model=NextStepResponse)
async def analyze(
    request: AnalyzeRequest,
    step_planner: StepPlanner = Depends(get_step_planner),
    log_store: LogStorePort = Depends(get_log_store),
) -> NextStepResponse:
    created_at_utc = datetime.now(timezone.utc).isoformat()
    planner_result = step_planner.analyze(request)
    response = planner_result.response
    normalized_actionable_summary = normalize_text(request.observation.foreground_window_actionable_summary)
    observation_metrics = parse_actionable_summary_metrics(normalized_actionable_summary)
    observation_candidate_count = (
        request.observation.foreground_window_candidate_count
        if request.observation.foreground_window_candidate_count is not None
        else len(request.observation.foreground_window_candidate_elements)
    )
    observation_scan_node_count = (
        request.observation.foreground_window_scan_node_count
        if request.observation.foreground_window_scan_node_count is not None
        else observation_metrics["scanned_nodes"]
    )
    observation_scan_depth = (
        request.observation.foreground_window_scan_depth
        if request.observation.foreground_window_scan_depth is not None
        else observation_metrics["scan_depth"]
    )
    observation_quality = classify_observation_quality(
        candidate_count=observation_candidate_count,
        scanned_nodes=observation_scan_node_count,
        scan_depth=observation_scan_depth,
    )
    log_store.insert_analyze_log(
        created_at_utc=created_at_utc,
        task_text=request.task_text,
        session_id=response.session_id,
        step_id=response.step_id,
        action_type=response.action_type,
        instruction=response.instruction,
        observation_session_id=request.observation.session_id,
        observation_captured_at_utc=normalize_text(request.observation.captured_at_utc),
        foreground_window_title=normalize_text(request.observation.foreground_window_title),
        foreground_window_uia_name=normalize_text(request.observation.foreground_window_uia_name),
        foreground_window_uia_automation_id=normalize_text(request.observation.foreground_window_uia_automation_id),
        foreground_window_uia_class_name=normalize_text(request.observation.foreground_window_uia_class_name),
        foreground_window_uia_control_type=normalize_text(request.observation.foreground_window_uia_control_type),
        foreground_window_uia_is_enabled=normalize_bool(request.observation.foreground_window_uia_is_enabled),
        foreground_window_uia_child_count=normalize_int(request.observation.foreground_window_uia_child_count),
        foreground_window_uia_child_summary=normalize_text(request.observation.foreground_window_uia_child_summary),
        foreground_window_actionable_summary=normalized_actionable_summary,
        foreground_window_candidate_elements_json=json.dumps(
            [candidate.model_dump() for candidate in request.observation.foreground_window_candidate_elements],
            ensure_ascii=True,
        ),
        screen_width=normalize_int(request.observation.screen_width),
        screen_height=normalize_int(request.observation.screen_height),
        screenshot_ref=normalize_text(request.observation.screenshot_ref),
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
        last_foreground_window_title=normalize_text(request.observation.foreground_window_title),
        last_screenshot_ref=normalize_text(request.observation.screenshot_ref),
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
        observation_candidate_count=observation_candidate_count,
        observation_scan_node_count=observation_scan_node_count,
        observation_scan_depth=observation_scan_depth,
        observation_quality=observation_quality,
        planner_error_code=planner_result.planner_error_code,
        planner_error=planner_result.planner_error,
        raw_model_response_excerpt=planner_result.raw_model_response_excerpt,
    )
    await realtime_event_hub.publish(
        RealtimeEventEntry(
            event_type="analyze",
            created_at_utc=created_at_utc,
            session_id=response.session_id,
            step_id=response.step_id,
            action_type=response.action_type,
            feedback_type=None,
            planner_source=planner_result.planner_source,
            observation_quality=observation_quality,
            screenshot_ref=normalize_text(request.observation.screenshot_ref),
            note="next_step_generated",
        )
    )
    return response
