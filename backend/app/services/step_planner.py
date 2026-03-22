from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import re
from typing import Callable, Optional

from app.contracts import AnalyzeRequest, HighlightDto, NextStepResponse, ObservationCandidateElementDto, RectDto, SessionStateEntry
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


class SettingsBluetoothScenarioPlanner(StepPlanner):
    def __init__(
        self,
        fallback_planner: StepPlanner,
        session_state_reader: Optional[Callable[[str], Optional[SessionStateEntry]]] = None,
    ) -> None:
        self._fallback_planner = fallback_planner
        self._session_state_reader = session_state_reader

    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        if not self._is_settings_bluetooth_task(request.task_text):
            return self._fallback_planner.analyze(request)

        observation = request.observation
        normalized_task_key = request.task_text.strip().casefold()
        settings_candidate = self._find_settings_candidate(observation.foreground_window_candidate_elements)
        session_state = self._read_session_state(observation.session_id)
        on_settings_window = self._looks_like_settings_window(
            observation.foreground_window_title,
            observation.foreground_window_uia_name,
            observation.foreground_window_uia_automation_id,
            observation.foreground_window_uia_class_name,
            observation.foreground_window_actionable_summary,
        )
        on_bluetooth_page = self._looks_like_bluetooth_page(
            observation.foreground_window_title,
            observation.foreground_window_actionable_summary,
            observation.foreground_window_candidate_elements,
        )

        if (
            session_state is not None
            and session_state.last_feedback_type == "incorrect"
            and session_state.current_action_type in {"open_bluetooth_settings", "recover_bluetooth_navigation"}
            and on_settings_window
            and not on_bluetooth_page
        ):
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-recover-bluetooth-navigation",
                instruction=(
                    "上一步进入“蓝牙和设备”没有成功。"
                    "请先确认当前仍在设置窗口左侧导航区域，"
                    + (
                        f"然后重新点击这个入口：{MockStepPlanner._format_candidate_label(settings_candidate)}。"
                        if settings_candidate is not None
                        else "然后重新查找“蓝牙和设备”入口后再继续。"
                    )
                ),
                action_type="recover_bluetooth_navigation",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(settings_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-bluetooth.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=settings_candidate.ui_path if settings_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(settings_candidate) if settings_candidate is not None else None,
            )

        if not on_settings_window:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-settings",
                instruction="这是“打开设置并进入蓝牙和设备”的场景。请先打开 Windows 设置窗口，再继续下一步分析。",
                action_type="open_settings_app",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(None)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-bluetooth.v2",
                response_schema_version="next-step-response.v1",
            )

        if on_bluetooth_page:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-confirm-bluetooth-page",
                instruction="你已经进入“蓝牙和设备”相关页面。请确认目标开关或入口是否出现，再继续下一步操作。",
                action_type="confirm_bluetooth_page",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(settings_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-bluetooth.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=settings_candidate.ui_path if settings_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(settings_candidate) if settings_candidate is not None else None,
            )

        if settings_candidate is not None:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-bluetooth-settings",
                instruction=(
                    "这是“打开设置并进入蓝牙和设备”的场景。"
                    f"请先点击这个入口：{MockStepPlanner._format_candidate_label(settings_candidate)}。"
                ),
                action_type="open_bluetooth_settings",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(settings_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-bluetooth.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=settings_candidate.ui_path,
                target_candidate_label=MockStepPlanner._format_candidate_label(settings_candidate),
            )

        response = NextStepResponse(
            session_id=MockStepPlanner._build_session_id(normalized_task_key),
            step_id="scenario-search-bluetooth-entry",
            instruction="设置窗口已经打开，但当前还没有识别到“蓝牙和设备”入口。请先在设置窗口中查找“蓝牙和设备”后再继续分析。",
            action_type="search_bluetooth_entry",
            requires_user_action=True,
            highlight=HighlightDto(
                rect=MockStepPlanner._build_highlight_rect(None)
            ),
        )
        return StepPlannerResult(
            response=response,
            planner_source="scenario",
            prompt_version="scenario-settings-bluetooth.v2",
            response_schema_version="next-step-response.v1",
        )

    def _read_session_state(self, session_id: Optional[str]) -> Optional[SessionStateEntry]:
        if session_id is None or self._session_state_reader is None:
            return None

        try:
            return self._session_state_reader(session_id)
        except Exception:
            return None

    @staticmethod
    def _is_settings_bluetooth_task(task_text: str) -> bool:
        normalized = task_text.casefold().replace(" ", "")
        return "设置" in normalized and ("蓝牙" in normalized or "设备" in normalized)

    @staticmethod
    def _looks_like_settings_window(
        window_title: str,
        uia_name: str,
        automation_id: str,
        class_name: str,
        actionable_summary: str,
    ) -> bool:
        combined_text = " ".join(
            value
            for value in (
                window_title,
                uia_name,
                automation_id,
                class_name,
                actionable_summary,
            )
            if value
        ).casefold()
        return "设置" in combined_text or "systemsettings" in combined_text

    @staticmethod
    def _looks_like_bluetooth_page(
        window_title: str,
        actionable_summary: str,
        candidates: list[ObservationCandidateElementDto],
    ) -> bool:
        combined_text = f"{window_title} {actionable_summary}".casefold()
        if "title=蓝牙和设备" in combined_text or "title=bluetooth" in combined_text:
            return True

        bluetooth_page_signals = (
            "添加设备",
            "bluetooth & devices",
            "bluetoothanddevices",
            "bluetoothsettings",
            "蓝牙开关",
            "设备设置",
        )
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            if any(signal in candidate_text for signal in bluetooth_page_signals):
                return True

        return False

    @staticmethod
    def _find_settings_candidate(
        candidates: list[ObservationCandidateElementDto],
    ) -> Optional[ObservationCandidateElementDto]:
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            if "蓝牙和设备" in candidate_text or "bluetooth" in candidate_text:
                if candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                    return candidate
        return None


class SettingsNetworkScenarioPlanner(StepPlanner):
    def __init__(
        self,
        fallback_planner: StepPlanner,
        session_state_reader: Optional[Callable[[str], Optional[SessionStateEntry]]] = None,
    ) -> None:
        self._fallback_planner = fallback_planner
        self._session_state_reader = session_state_reader

    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        if not self._is_settings_network_task(request.task_text):
            return self._fallback_planner.analyze(request)

        observation = request.observation
        normalized_task_key = request.task_text.strip().casefold()
        network_candidate = self._find_network_candidate(observation.foreground_window_candidate_elements)
        session_state = self._read_session_state(observation.session_id)
        on_settings_window = SettingsBluetoothScenarioPlanner._looks_like_settings_window(
            observation.foreground_window_title,
            observation.foreground_window_uia_name,
            observation.foreground_window_uia_automation_id,
            observation.foreground_window_uia_class_name,
            observation.foreground_window_actionable_summary,
        )
        on_network_page = self._looks_like_network_page(
            observation.foreground_window_title,
            observation.foreground_window_actionable_summary,
            observation.foreground_window_candidate_elements,
        )

        if (
            session_state is not None
            and session_state.last_feedback_type == "incorrect"
            and session_state.current_action_type in {"open_network_settings", "recover_network_navigation"}
            and on_settings_window
            and not on_network_page
        ):
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-recover-network-navigation",
                instruction=(
                    "上一步进入“网络和 Internet”没有成功。"
                    "请先确认仍在设置窗口的导航区域，"
                    + (
                        f"然后重新点击这个入口：{MockStepPlanner._format_candidate_label(network_candidate)}。"
                        if network_candidate is not None
                        else "然后重新查找“网络和 Internet / Wi-Fi”入口后再继续。"
                    )
                ),
                action_type="recover_network_navigation",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(network_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-network.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=network_candidate.ui_path if network_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(network_candidate) if network_candidate is not None else None,
            )

        if not on_settings_window:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-settings-for-network",
                instruction="这是“打开设置并进入网络和 Internet”的场景。请先打开 Windows 设置窗口，再继续下一步分析。",
                action_type="open_settings_app",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(None)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-network.v2",
                response_schema_version="next-step-response.v1",
            )

        if on_network_page:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-confirm-network-page",
                instruction="你已经进入“网络和 Internet”相关页面。请确认目标网络入口或开关后继续下一步操作。",
                action_type="confirm_network_page",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(network_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-network.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=network_candidate.ui_path if network_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(network_candidate) if network_candidate is not None else None,
            )

        if network_candidate is not None:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-network-settings",
                instruction=(
                    "这是“打开设置并进入网络和 Internet”的场景。"
                    f"请先点击这个入口：{MockStepPlanner._format_candidate_label(network_candidate)}。"
                ),
                action_type="open_network_settings",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(network_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-network.v2",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=network_candidate.ui_path,
                target_candidate_label=MockStepPlanner._format_candidate_label(network_candidate),
            )

        response = NextStepResponse(
            session_id=MockStepPlanner._build_session_id(normalized_task_key),
            step_id="scenario-search-network-entry",
            instruction="设置窗口已经打开，但当前还没有识别到“网络和 Internet / Wi‑Fi”入口。请先在设置窗口中查找相关入口后再继续分析。",
            action_type="search_network_entry",
            requires_user_action=True,
            highlight=HighlightDto(
                rect=MockStepPlanner._build_highlight_rect(None)
            ),
        )
        return StepPlannerResult(
            response=response,
            planner_source="scenario",
            prompt_version="scenario-settings-network.v2",
            response_schema_version="next-step-response.v1",
        )

    def _read_session_state(self, session_id: Optional[str]) -> Optional[SessionStateEntry]:
        if session_id is None or self._session_state_reader is None:
            return None

        try:
            return self._session_state_reader(session_id)
        except Exception:
            return None

    @staticmethod
    def _is_settings_network_task(task_text: str) -> bool:
        normalized = task_text.casefold().replace(" ", "")
        contains_settings = "设置" in normalized or "settings" in normalized
        contains_network = any(
            keyword in normalized
            for keyword in ("网络", "internet", "wifi", "wi-fi", "wi‑fi", "无线")
        )
        return contains_settings and contains_network

    @staticmethod
    def _looks_like_network_page(
        window_title: str,
        actionable_summary: str,
        candidates: list[ObservationCandidateElementDto],
    ) -> bool:
        combined_text = f"{window_title} {actionable_summary}".casefold()
        if "title=网络和internet" in combined_text or "title=network and internet" in combined_text:
            return True

        network_page_signals = (
            "wi-fi",
            "wifi",
            "wlan",
            "vpn",
            "以太网",
            "ethernet",
            "代理",
            "proxy",
        )
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            if any(signal in candidate_text for signal in network_page_signals):
                return True

        return False

    @staticmethod
    def _find_network_candidate(
        candidates: list[ObservationCandidateElementDto],
    ) -> Optional[ObservationCandidateElementDto]:
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            compact_text = candidate_text.replace(" ", "")
            if any(
                keyword in compact_text
                for keyword in (
                    "网络和internet",
                    "networkandinternet",
                    "network&internet",
                    "wi-fi",
                    "wifi",
                    "wlan",
                    "ethernet",
                )
            ):
                if candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                    return candidate
        return None


class SettingsDisplayScenarioPlanner(StepPlanner):
    def __init__(
        self,
        fallback_planner: StepPlanner,
        session_state_reader: Optional[Callable[[str], Optional[SessionStateEntry]]] = None,
    ) -> None:
        self._fallback_planner = fallback_planner
        self._session_state_reader = session_state_reader

    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        if not self._is_settings_display_task(request.task_text):
            return self._fallback_planner.analyze(request)

        observation = request.observation
        normalized_task_key = request.task_text.strip().casefold()
        display_candidate = self._find_display_candidate(observation.foreground_window_candidate_elements)
        session_state = self._read_session_state(observation.session_id)
        on_settings_window = SettingsBluetoothScenarioPlanner._looks_like_settings_window(
            observation.foreground_window_title,
            observation.foreground_window_uia_name,
            observation.foreground_window_uia_automation_id,
            observation.foreground_window_uia_class_name,
            observation.foreground_window_actionable_summary,
        )
        on_display_page = self._looks_like_display_page(
            observation.foreground_window_title,
            observation.foreground_window_actionable_summary,
            observation.foreground_window_candidate_elements,
        )

        if (
            session_state is not None
            and session_state.last_feedback_type == "incorrect"
            and session_state.current_action_type in {"open_display_settings", "recover_display_navigation"}
            and on_settings_window
            and not on_display_page
        ):
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-recover-display-navigation",
                instruction=(
                    "上一步进入“显示”页面没有成功。"
                    "请先确认仍在设置窗口导航区域，"
                    + (
                        f"然后重新点击这个入口：{MockStepPlanner._format_candidate_label(display_candidate)}。"
                        if display_candidate is not None
                        else "然后重新查找“系统 -> 显示”入口后再继续。"
                    )
                ),
                action_type="recover_display_navigation",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(display_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-display.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=display_candidate.ui_path if display_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(display_candidate) if display_candidate is not None else None,
            )

        if not on_settings_window:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-settings-for-display",
                instruction="这是“打开设置并进入显示页面”的场景。请先打开 Windows 设置窗口，再继续下一步分析。",
                action_type="open_settings_app",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(None)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-display.v1",
                response_schema_version="next-step-response.v1",
            )

        if on_display_page:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-confirm-display-page",
                instruction="你已经进入“显示”相关页面。请确认目标设置（如缩放、分辨率或亮度）后继续下一步操作。",
                action_type="confirm_display_page",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(display_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-display.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=display_candidate.ui_path if display_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(display_candidate) if display_candidate is not None else None,
            )

        if display_candidate is not None:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-display-settings",
                instruction=(
                    "这是“打开设置并进入显示页面”的场景。"
                    f"请先点击这个入口：{MockStepPlanner._format_candidate_label(display_candidate)}。"
                ),
                action_type="open_display_settings",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(display_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-display.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=display_candidate.ui_path,
                target_candidate_label=MockStepPlanner._format_candidate_label(display_candidate),
            )

        response = NextStepResponse(
            session_id=MockStepPlanner._build_session_id(normalized_task_key),
            step_id="scenario-search-display-entry",
            instruction="设置窗口已经打开，但当前还没有识别到“系统 -> 显示”入口。请先在设置窗口中定位显示入口后再继续分析。",
            action_type="search_display_entry",
            requires_user_action=True,
            highlight=HighlightDto(
                rect=MockStepPlanner._build_highlight_rect(None)
            ),
        )
        return StepPlannerResult(
            response=response,
            planner_source="scenario",
            prompt_version="scenario-settings-display.v1",
            response_schema_version="next-step-response.v1",
        )

    def _read_session_state(self, session_id: Optional[str]) -> Optional[SessionStateEntry]:
        if session_id is None or self._session_state_reader is None:
            return None

        try:
            return self._session_state_reader(session_id)
        except Exception:
            return None

    @staticmethod
    def _is_settings_display_task(task_text: str) -> bool:
        normalized = task_text.casefold().replace(" ", "")
        contains_settings = "设置" in normalized or "settings" in normalized
        contains_display = any(
            keyword in normalized
            for keyword in ("显示", "display", "分辨率", "缩放", "亮度", "screen")
        )
        return contains_settings and contains_display

    @staticmethod
    def _looks_like_display_page(
        window_title: str,
        actionable_summary: str,
        candidates: list[ObservationCandidateElementDto],
    ) -> bool:
        combined_text = f"{window_title} {actionable_summary}".casefold()
        if "title=显示" in combined_text or "title=display" in combined_text:
            return True

        page_signals = (
            "显示分辨率",
            "display resolution",
            "缩放",
            "scale",
            "亮度",
            "brightness",
            "夜间模式",
            "night light",
        )
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            if any(signal in candidate_text for signal in page_signals):
                return True

        return False

    @staticmethod
    def _find_display_candidate(
        candidates: list[ObservationCandidateElementDto],
    ) -> Optional[ObservationCandidateElementDto]:
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            compact_text = candidate_text.replace(" ", "")
            if any(
                keyword in compact_text
                for keyword in (
                    "显示",
                    "display",
                    "systemsettings_display",
                    "分辨率",
                    "缩放",
                )
            ):
                if candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                    return candidate
        return None


class SettingsPersonalizationScenarioPlanner(StepPlanner):
    def __init__(
        self,
        fallback_planner: StepPlanner,
        session_state_reader: Optional[Callable[[str], Optional[SessionStateEntry]]] = None,
    ) -> None:
        self._fallback_planner = fallback_planner
        self._session_state_reader = session_state_reader

    def analyze(self, request: AnalyzeRequest) -> StepPlannerResult:
        if not self._is_settings_personalization_task(request.task_text):
            return self._fallback_planner.analyze(request)

        observation = request.observation
        normalized_task_key = request.task_text.strip().casefold()
        personalization_candidate = self._find_personalization_candidate(observation.foreground_window_candidate_elements)
        session_state = self._read_session_state(observation.session_id)
        on_settings_window = SettingsBluetoothScenarioPlanner._looks_like_settings_window(
            observation.foreground_window_title,
            observation.foreground_window_uia_name,
            observation.foreground_window_uia_automation_id,
            observation.foreground_window_uia_class_name,
            observation.foreground_window_actionable_summary,
        )
        on_personalization_page = self._looks_like_personalization_page(
            observation.foreground_window_title,
            observation.foreground_window_actionable_summary,
            observation.foreground_window_candidate_elements,
        )

        if (
            session_state is not None
            and session_state.last_feedback_type == "incorrect"
            and session_state.current_action_type in {"open_personalization_settings", "recover_personalization_navigation"}
            and on_settings_window
            and not on_personalization_page
        ):
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-recover-personalization-navigation",
                instruction=(
                    "上一步进入“个性化”页面没有成功。"
                    "请先确认仍在设置窗口导航区域，"
                    + (
                        f"然后重新点击这个入口：{MockStepPlanner._format_candidate_label(personalization_candidate)}。"
                        if personalization_candidate is not None
                        else "然后重新查找“个性化”入口后再继续。"
                    )
                ),
                action_type="recover_personalization_navigation",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(personalization_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-personalization.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=personalization_candidate.ui_path if personalization_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(personalization_candidate) if personalization_candidate is not None else None,
            )

        if not on_settings_window:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-settings-for-personalization",
                instruction="这是“打开设置并进入个性化页面”的场景。请先打开 Windows 设置窗口，再继续下一步分析。",
                action_type="open_settings_app",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(None)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-personalization.v1",
                response_schema_version="next-step-response.v1",
            )

        if on_personalization_page:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-confirm-personalization-page",
                instruction="你已经进入“个性化”相关页面。请确认目标设置（主题、背景、锁屏等）后继续下一步操作。",
                action_type="confirm_personalization_page",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(personalization_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-personalization.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=personalization_candidate.ui_path if personalization_candidate is not None else None,
                target_candidate_label=MockStepPlanner._format_candidate_label(personalization_candidate) if personalization_candidate is not None else None,
            )

        if personalization_candidate is not None:
            response = NextStepResponse(
                session_id=MockStepPlanner._build_session_id(normalized_task_key),
                step_id="scenario-open-personalization-settings",
                instruction=(
                    "这是“打开设置并进入个性化页面”的场景。"
                    f"请先点击这个入口：{MockStepPlanner._format_candidate_label(personalization_candidate)}。"
                ),
                action_type="open_personalization_settings",
                requires_user_action=True,
                highlight=HighlightDto(
                    rect=MockStepPlanner._build_highlight_rect(personalization_candidate)
                ),
            )
            return StepPlannerResult(
                response=response,
                planner_source="scenario",
                prompt_version="scenario-settings-personalization.v1",
                response_schema_version="next-step-response.v1",
                target_candidate_ui_path=personalization_candidate.ui_path,
                target_candidate_label=MockStepPlanner._format_candidate_label(personalization_candidate),
            )

        response = NextStepResponse(
            session_id=MockStepPlanner._build_session_id(normalized_task_key),
            step_id="scenario-search-personalization-entry",
            instruction="设置窗口已经打开，但当前还没有识别到“个性化”入口。请先在设置窗口中定位该入口后再继续分析。",
            action_type="search_personalization_entry",
            requires_user_action=True,
            highlight=HighlightDto(
                rect=MockStepPlanner._build_highlight_rect(None)
            ),
        )
        return StepPlannerResult(
            response=response,
            planner_source="scenario",
            prompt_version="scenario-settings-personalization.v1",
            response_schema_version="next-step-response.v1",
        )

    def _read_session_state(self, session_id: Optional[str]) -> Optional[SessionStateEntry]:
        if session_id is None or self._session_state_reader is None:
            return None

        try:
            return self._session_state_reader(session_id)
        except Exception:
            return None

    @staticmethod
    def _is_settings_personalization_task(task_text: str) -> bool:
        normalized = task_text.casefold().replace(" ", "")
        contains_settings = "设置" in normalized or "settings" in normalized
        contains_personalization = any(
            keyword in normalized
            for keyword in ("个性化", "personalization", "主题", "背景", "锁屏", "wallpaper")
        )
        return contains_settings and contains_personalization

    @staticmethod
    def _looks_like_personalization_page(
        window_title: str,
        actionable_summary: str,
        candidates: list[ObservationCandidateElementDto],
    ) -> bool:
        combined_text = f"{window_title} {actionable_summary}".casefold()
        if "title=个性化" in combined_text or "title=personalization" in combined_text:
            return True

        page_signals = (
            "主题",
            "themes",
            "背景",
            "background",
            "锁屏",
            "lock screen",
            "颜色",
            "colors",
        )
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            if any(signal in candidate_text for signal in page_signals):
                return True

        return False

    @staticmethod
    def _find_personalization_candidate(
        candidates: list[ObservationCandidateElementDto],
    ) -> Optional[ObservationCandidateElementDto]:
        for candidate in candidates:
            candidate_text = " ".join(
                value
                for value in (candidate.name, candidate.automation_id, candidate.class_name)
                if value
            ).casefold()
            compact_text = candidate_text.replace(" ", "")
            if any(
                keyword in compact_text
                for keyword in (
                    "个性化",
                    "personalization",
                    "systemsettings_personalization",
                    "主题",
                    "背景",
                )
            ):
                if candidate.bounding_rect.width > 0 and candidate.bounding_rect.height > 0:
                    return candidate
        return None


class ModelStepPlanner(StepPlanner):
    _ACTION_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
    _DISALLOWED_ACTION_TYPE_TERMS = (
        "auto_click",
        "auto_type",
        "auto_press",
        "keyboard_control",
        "mouse_control",
        "execute_script",
        "remote_control",
    )

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
            if not response.instruction.strip():
                raise ValueError("instruction must not be empty")
            if not self._is_safe_action_type(response.action_type):
                raise ValueError(f"unsupported action_type from model: {response.action_type}")

            response, target_candidate = self._enforce_safe_response(request, response)
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
    def _enforce_safe_response(
        request: AnalyzeRequest,
        response: NextStepResponse,
    ) -> tuple[NextStepResponse, Optional[ObservationCandidateElementDto]]:
        safe_response = response
        if not safe_response.requires_user_action:
            safe_response = safe_response.model_copy(
                update={"requires_user_action": True}
            )

        target_candidate = ModelStepPlanner._match_highlight_candidate(request, safe_response)
        if target_candidate is not None:
            return safe_response, target_candidate

        preferred_candidate = MockStepPlanner._find_preferred_candidate(
            request.task_text.strip(),
            request.observation.foreground_window_candidate_elements,
        )
        if preferred_candidate is not None:
            safe_response = safe_response.model_copy(
                update={
                    "highlight": HighlightDto(
                        rect=RectDto(
                            x=preferred_candidate.bounding_rect.x,
                            y=preferred_candidate.bounding_rect.y,
                            width=preferred_candidate.bounding_rect.width,
                            height=preferred_candidate.bounding_rect.height,
                        )
                    )
                }
            )
            return safe_response, preferred_candidate

        safe_rect = ModelStepPlanner._build_safe_default_rect(
            screen_width=request.observation.screen_width,
            screen_height=request.observation.screen_height,
        )
        safe_response = safe_response.model_copy(
            update={"highlight": HighlightDto(rect=safe_rect)}
        )
        return safe_response, None

    @staticmethod
    def _build_safe_default_rect(screen_width: int, screen_height: int) -> RectDto:
        width = min(max(screen_width // 5, 180), 420) if screen_width > 0 else 280
        height = min(max(screen_height // 8, 90), 220) if screen_height > 0 else 120

        safe_x = max((screen_width - width) // 2, 0) if screen_width > 0 else 640
        safe_y = max((screen_height - height) // 2, 0) if screen_height > 0 else 320

        return RectDto(
            x=safe_x,
            y=safe_y,
            width=width,
            height=height,
        )

    @classmethod
    def _is_safe_action_type(cls, action_type: str) -> bool:
        normalized = action_type.strip().casefold()
        if not normalized:
            return False

        if cls._ACTION_TYPE_PATTERN.match(normalized) is None:
            return False

        return all(term not in normalized for term in cls._DISALLOWED_ACTION_TYPE_TERMS)

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
