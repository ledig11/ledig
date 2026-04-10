from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from app.api.analyze import (
    classify_observation_quality,
    normalize_bool,
    normalize_int,
    normalize_text,
    parse_actionable_summary_metrics,
)
from app.contracts import AnalyzeRequest, NextStepResponse
from app.orchestrator.session_store_port import SessionStorePort
from app.services.step_planner import StepPlanner
from app.storage.log_store_port import LogStorePort


@dataclass(frozen=True)
class NextStepExecutionResult:
    response: NextStepResponse
    created_at_utc: str
    observation_quality: str
    planner_source: str


class NextStepService:
    def __init__(
        self,
        *,
        step_planner: StepPlanner,
        log_store: LogStorePort,
        session_manager: SessionStorePort,
    ) -> None:
        self._step_planner = step_planner
        self._log_store = log_store
        self._session_manager = session_manager

    def get_session_state(self, session_id: str):
        return self._session_manager.get_session(session_id)

    def run_next_step(self, *, session_id: str, request: AnalyzeRequest) -> NextStepExecutionResult:
        request.observation.session_id = session_id
        created_at_utc = datetime.now(timezone.utc).isoformat()
        planner_result = self._step_planner.analyze(request)
        response = planner_result.response.model_copy(update={"session_id": session_id})

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

        self._log_store.insert_analyze_log(
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
        self._log_store.upsert_session_state_after_analyze(
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
        self._log_store.insert_analyze_diagnostic(
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
        self._session_manager.upsert_from_next_step(
            session_id=session_id,
            task_text=request.task_text,
            step_id=response.step_id,
            action_type=response.action_type,
            message=response.instruction,
            last_observation_ref=normalize_text(request.observation.screenshot_ref),
        )
        return NextStepExecutionResult(
            response=response,
            created_at_utc=created_at_utc,
            observation_quality=observation_quality,
            planner_source=planner_result.planner_source,
        )

    def apply_feedback(
        self,
        *,
        session_id: str,
        step_id: str,
        feedback_type: str,
        comment: str | None,
    ) -> bool:
        state = self._session_manager.apply_feedback(
            session_id=session_id,
            step_id=step_id,
            feedback_type=feedback_type,
            comment=comment,
        )
        return state is not None
