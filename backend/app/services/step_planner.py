from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
from typing import Optional

from app.contracts import AnalyzeRequest, HighlightDto, NextStepResponse, ObservationCandidateElementDto, RectDto
from app.services.model_gateway import ModelGateway, ModelGatewayError
from app.services.prompt_builder import StepPlannerPromptBuilder
from app.services.runtime_model import RuntimeModelConfig


@dataclass(frozen=True)
class StepPlannerResult:
    response: NextStepResponse
    planner_source: str
    prompt_version: Optional[str] = None
    response_schema_version: Optional[str] = None
    model_provider: Optional[str] = None
    model_type: Optional[str] = None
    target_candidate_ui_path: Optional[str] = None
    target_candidate_label: Optional[str] = None
    planner_error_code: Optional[str] = None
    planner_error: Optional[str] = None
    raw_model_response_excerpt: Optional[str] = None


class StepPlanner(ABC):
    @abstractmethod
    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        raise NotImplementedError


class MockStepPlanner(StepPlanner):
    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        normalized_task = request.task_text.strip()
        foreground_window_title = request.observation.foreground_window_title.strip()
        foreground_window_uia_name = request.observation.foreground_window_uia_name.strip()
        foreground_window_uia_class_name = request.observation.foreground_window_uia_class_name.strip()
        foreground_window_uia_control_type = request.observation.foreground_window_uia_control_type.strip()
        foreground_window_uia_child_summary = request.observation.foreground_window_uia_child_summary.strip()
        foreground_window_actionable_summary = request.observation.foreground_window_actionable_summary.strip()
        foreground_window_candidate_elements = request.observation.foreground_window_candidate_elements
        normalized_window_title = foreground_window_title.casefold()
        normalized_task_key = normalized_task.casefold()
        preferred_candidate = self._find_preferred_candidate(
            normalized_task,
            foreground_window_candidate_elements,
        )
        window_kind = self._extract_actionable_window_kind(foreground_window_actionable_summary)
        if window_kind == "unknown":
            window_kind = self._classify_window_kind(
                normalized_window_title,
                foreground_window_uia_name.casefold(),
                foreground_window_uia_class_name.casefold(),
                foreground_window_uia_control_type.casefold(),
            )

        if self._looks_task_related(normalized_task_key, normalized_window_title):
            instruction = (
                f"当前前台窗口“{foreground_window_title}”看起来已经与任务“{normalized_task}”相关，请先在这个窗口内确认可继续操作的入口。"
            )
            if preferred_candidate is not None:
                instruction = (
                    f"当前前台窗口“{foreground_window_title}”已经与任务“{normalized_task}”相关。"
                    f"请先检查这个更接近目标的控件：{self._format_candidate_label(preferred_candidate)}。"
                )
            action_type = "confirm_in_window"
        elif window_kind == "settings_window":
            instruction = self._build_settings_instruction(
                normalized_task,
                foreground_window_uia_child_summary,
                foreground_window_actionable_summary,
                preferred_candidate,
            )
            action_type = "refine_in_window"
        elif window_kind == "shell_window":
            instruction = (
                f"当前前台窗口更像启动器或系统外壳环境。请先从这里打开与任务“{normalized_task}”更直接相关的应用窗口。"
            )
            action_type = "open_target_window"
        elif self._looks_like_window_shell(foreground_window_uia_control_type):
            instruction = (
                f"当前前台对象的 UIA 类型是“{foreground_window_uia_control_type}”，更像一个独立窗口外壳。请先把目标应用窗口切到前台，再继续任务“{normalized_task}”。"
            )
            action_type = "switch_window"
        else:
            instruction = (
                f"当前前台窗口是“{foreground_window_title}”，看起来还不是任务“{normalized_task}”的目标窗口。请先切换到更相关的窗口后再继续。"
            )
            action_type = "switch_window"

        return StepPlannerResult(
            response=NextStepResponse(
                session_id=self._build_session_id(normalized_task_key),
                step_id=self._build_step_id(action_type, foreground_window_title),
                instruction=instruction,
                action_type=action_type,
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=self._build_highlight_rect(preferred_candidate)
                ),
            ),
            planner_source="mock",
            prompt_version="mock-heuristic.v1",
            response_schema_version="next-step-response.v1",
            target_candidate_ui_path=preferred_candidate.ui_path if preferred_candidate is not None else None,
            target_candidate_label=self._format_candidate_label(preferred_candidate) if preferred_candidate is not None else None,
        )

    @staticmethod
    def _looks_task_related(normalized_task_key: str, normalized_window_title: str) -> bool:
        if not normalized_window_title or normalized_window_title == "unknown-foreground-window":
            return False

        task_keywords = set(
            keyword
            for keyword in normalized_task_key.replace("，", " ").replace(",", " ").split()
            if keyword
        )

        compact_task = normalized_task_key.replace(" ", "")
        if len(compact_task) >= 2:
            for index in range(len(compact_task) - 1):
                task_keywords.add(compact_task[index:index + 2])

        if not task_keywords:
            return False

        return any(keyword in normalized_window_title for keyword in task_keywords)

    @staticmethod
    def _build_session_id(normalized_task_key: str) -> str:
        digest = hashlib.sha1(normalized_task_key.encode("utf-8")).hexdigest()[:8]
        return f"mock-session-{digest}"

    @staticmethod
    def _build_step_id(action_type: str, foreground_window_title: str) -> str:
        digest_input = f"{action_type}:{foreground_window_title}".encode("utf-8")
        digest = hashlib.sha1(digest_input).hexdigest()[:8]
        return f"step-{digest}"

    @staticmethod
    def _looks_like_window_shell(foreground_window_uia_control_type: str) -> bool:
        normalized_control_type = foreground_window_uia_control_type.casefold()
        return normalized_control_type in {"controltype.window", "controltype.pane"}

    @staticmethod
    def _classify_window_kind(
        normalized_window_title: str,
        normalized_uia_name: str,
        normalized_uia_class_name: str,
        normalized_uia_control_type: str,
    ) -> str:
        combined_text = " ".join(
            value
            for value in (
                normalized_window_title,
                normalized_uia_name,
                normalized_uia_class_name,
                normalized_uia_control_type,
            )
            if value
        )

        if "设置" in combined_text or "systemsettings" in combined_text:
            return "settings_window"

        if any(keyword in combined_text for keyword in ("开始", "start", "searchhost", "taskbar", "launcher")):
            return "shell_window"

        if normalized_uia_control_type in {"controltype.window", "controltype.pane"}:
            return "generic_window"

        return "unknown_window"

    @staticmethod
    def _build_settings_instruction(
        normalized_task: str,
        foreground_window_uia_child_summary: str,
        foreground_window_actionable_summary: str,
        preferred_candidate: Optional[ObservationCandidateElementDto],
    ) -> str:
        if preferred_candidate is not None:
            return (
                f"当前前台窗口像是 Windows 设置窗口。请先优先尝试这个更贴近任务“{normalized_task}”的可见控件："
                f"{MockStepPlanner._format_candidate_label(preferred_candidate)}。"
            )

        matching_entry = MockStepPlanner._find_matching_child_entry(
            normalized_task,
            foreground_window_uia_child_summary,
        )
        if matching_entry is not None:
            return (
                f"当前前台窗口像是 Windows 设置窗口。请先优先尝试这个更贴近任务“{normalized_task}”的可见入口："
                f"{matching_entry}。"
            )

        if foreground_window_uia_child_summary and foreground_window_uia_child_summary not in {
            "unknown-children",
            "child-summary-unavailable",
            "no-direct-children",
        }:
            return (
                f"当前前台窗口像是 Windows 设置窗口。请先优先检查这些可见入口是否与任务“{normalized_task}”相关："
                f"{foreground_window_uia_child_summary}。"
            )

        if foreground_window_actionable_summary:
            return (
                f"当前前台窗口像是 Windows 设置窗口。请先根据当前窗口摘要确认是否已进入与任务“{normalized_task}”更接近的页面："
                f"{foreground_window_actionable_summary}。"
            )

        return (
            f"当前前台窗口像是 Windows 设置窗口，但任务“{normalized_task}”还没有明显落到目标页面。请先在设置窗口内查找更贴近任务的入口。"
        )

    @staticmethod
    def _find_preferred_candidate(
        normalized_task: str,
        candidates: list[ObservationCandidateElementDto],
    ) -> Optional[ObservationCandidateElementDto]:
        if not candidates:
            return None

        task_keywords = MockStepPlanner._extract_task_keywords(normalized_task.casefold())
        best_match: Optional[ObservationCandidateElementDto] = None
        best_score = -1

        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (
                    candidate.name,
                    candidate.automation_id,
                    candidate.class_name,
                    candidate.control_type,
                )
                if value
            ).casefold()

            keyword_score = sum(1 for keyword in task_keywords if keyword in candidate_text)
            visible_score = 1 if not candidate.is_offscreen else 0
            enabled_score = 1 if candidate.is_enabled else 0
            focus_score = 1 if candidate.has_keyboard_focus else 0
            candidate_score = (keyword_score * 10) + (visible_score * 3) + (enabled_score * 2) + focus_score

            if candidate_score > best_score and candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                best_match = candidate
                best_score = candidate_score

        if best_match is not None and best_score > 0:
            return best_match

        for candidate in candidates:
            if candidate.is_enabled and not candidate.is_offscreen:
                if candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                    return candidate

        return None

    @staticmethod
    def _format_candidate_label(candidate: ObservationCandidateElementDto) -> str:
        name = candidate.name.strip() or "unnamed-control"
        return (
            f"{candidate.control_type}:{name}"
            f" (automation_id={candidate.automation_id}, path={candidate.ui_path})"
        )

    @staticmethod
    def _build_highlight_rect(candidate: Optional[ObservationCandidateElementDto]) -> RectDto:
        if candidate is not None:
            rect = candidate.bounding_rect
            if rect.width > 0 and rect.height > 0:
                return RectDto(
                    x=rect.x,
                    y=rect.y,
                    width=rect.width,
                    height=rect.height,
                )

        return RectDto(
            x=640,
            y=320,
            width=280,
            height=120,
        )

    @staticmethod
    def _find_matching_child_entry(
        normalized_task: str,
        foreground_window_uia_child_summary: str,
    ) -> Optional[str]:
        if not foreground_window_uia_child_summary or foreground_window_uia_child_summary in {
            "unknown-children",
            "child-summary-unavailable",
            "no-direct-children",
        }:
            return None

        task_keywords = MockStepPlanner._extract_task_keywords(normalized_task.casefold())
        if not task_keywords:
            return None

        entries = [entry.strip() for entry in foreground_window_uia_child_summary.split("|") if entry.strip()]
        for entry in entries:
            normalized_entry = entry.casefold()
            if any(keyword in normalized_entry for keyword in task_keywords):
                return entry

        return None

    @staticmethod
    def _extract_task_keywords(normalized_task_key: str) -> set[str]:
        keywords = set(
            keyword
            for keyword in normalized_task_key.replace("，", " ").replace(",", " ").split()
            if keyword
        )

        compact_task = normalized_task_key.replace(" ", "")
        if len(compact_task) >= 2:
            for index in range(len(compact_task) - 1):
                keywords.add(compact_task[index:index + 2])

        return keywords

    @staticmethod
    def _extract_actionable_window_kind(foreground_window_actionable_summary: str) -> str:
        prefix = "window_kind="
        if not foreground_window_actionable_summary.startswith(prefix):
            return "unknown"

        kind_part = foreground_window_actionable_summary[len(prefix):].split(";", 1)[0].strip()
        return {
            "settings": "settings_window",
            "shell": "shell_window",
            "window": "generic_window",
        }.get(kind_part, "unknown")


class ModelStepPlanner(StepPlanner):
    def __init__(
        self,
        runtime_model_config: RuntimeModelConfig,
        prompt_builder: StepPlannerPromptBuilder,
        model_gateway: ModelGateway,
        fallback_planner: StepPlanner,
    ) -> None:
        self._runtime_model_config = runtime_model_config
        self._prompt_builder = prompt_builder
        self._model_gateway = model_gateway
        self._fallback_planner = fallback_planner

    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        if not self._runtime_model_config.has_model_access:
            fallback_result = self._fallback_planner.analyze(request)
            return StepPlannerResult(
                response=fallback_result.response,
                planner_source="mock_fallback",
                prompt_version=fallback_result.prompt_version,
                response_schema_version=fallback_result.response_schema_version,
                model_provider=self._runtime_model_config.provider,
                model_type=self._runtime_model_config.model_type,
                target_candidate_ui_path=fallback_result.target_candidate_ui_path,
                target_candidate_label=fallback_result.target_candidate_label,
                planner_error_code="model_access_not_configured",
                planner_error="model access not configured",
            )

        prompt_bundle = self._prompt_builder.build(request)

        try:
            payload = self._model_gateway.generate_next_step(
                runtime_model_config=self._runtime_model_config,
                prompt_bundle=prompt_bundle,
            )
            response = NextStepResponse.model_validate(payload)
            target_candidate = self._match_highlight_candidate(request, response)
            return StepPlannerResult(
                response=response,
                planner_source="model",
                prompt_version=prompt_bundle.prompt_version,
                response_schema_version=getattr(self._model_gateway, "response_schema_version", None),
                model_provider=self._runtime_model_config.provider,
                model_type=self._runtime_model_config.model_type,
                target_candidate_ui_path=target_candidate.ui_path if target_candidate is not None else None,
                target_candidate_label=self._format_candidate_label(target_candidate) if target_candidate is not None else None,
            )
        except (ModelGatewayError, ValueError, TypeError) as exc:
            fallback_result = self._fallback_planner.analyze(request)
            return StepPlannerResult(
                response=fallback_result.response,
                planner_source="mock_fallback",
                prompt_version=prompt_bundle.prompt_version,
                response_schema_version=getattr(self._model_gateway, "response_schema_version", None),
                model_provider=self._runtime_model_config.provider,
                model_type=self._runtime_model_config.model_type,
                target_candidate_ui_path=fallback_result.target_candidate_ui_path,
                target_candidate_label=fallback_result.target_candidate_label,
                planner_error_code=exc.code if isinstance(exc, ModelGatewayError) else "response_validation_error",
                planner_error=str(exc),
                raw_model_response_excerpt=exc.raw_response_excerpt if isinstance(exc, ModelGatewayError) else None,
            )

    @staticmethod
    def _match_highlight_candidate(
        request: AnalyzeRequest,
        response: NextStepResponse,
    ) -> Optional[ObservationCandidateElementDto]:
        highlight_rect = response.highlight.rect
        for candidate in request.observation.foreground_window_candidate_elements:
            rect = candidate.bounding_rect
            if (
                rect.x == highlight_rect.x
                and rect.y == highlight_rect.y
                and rect.width == highlight_rect.width
                and rect.height == highlight_rect.height
            ):
                return candidate
        return None
