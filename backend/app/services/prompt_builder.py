from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.contracts import AnalyzeRequest, ObservationCandidateElementDto


@dataclass(frozen=True)
class PromptBundle:
    system_prompt: str
    user_prompt: str
    prompt_version: str


class StepPlannerPromptBuilder:
    PROMPT_VERSION = "step-planner.v2"

    def build(self, request: AnalyzeRequest) -> PromptBundle:
        observation = request.observation
        task_text = request.task_text.strip()
        task_intent_tags = self._infer_task_intent_tags(task_text)
        action_constraints = self._build_action_constraints()
        candidate_lines = self._format_candidates(observation.foreground_window_candidate_elements)
        visual_fallback_hint = self._build_visual_fallback_hint(
            screenshot_status=observation.screenshot_status,
            screenshot_local_path=observation.screenshot_local_path,
        )
        user_prompt = (
            "Task:\n"
            f"{task_text}\n\n"
            "Task Intent Tags:\n"
            f"- {task_intent_tags}\n\n"
            "Action Constraints:\n"
            f"{action_constraints}\n\n"
            "Current Observation:\n"
            f"- foreground_window_title: {observation.foreground_window_title}\n"
            f"- foreground_window_uia_name: {observation.foreground_window_uia_name}\n"
            f"- foreground_window_uia_automation_id: {observation.foreground_window_uia_automation_id}\n"
            f"- foreground_window_uia_class_name: {observation.foreground_window_uia_class_name}\n"
            f"- foreground_window_uia_control_type: {observation.foreground_window_uia_control_type}\n"
            f"- foreground_window_uia_is_enabled: {observation.foreground_window_uia_is_enabled}\n"
            f"- foreground_window_uia_child_count: {observation.foreground_window_uia_child_count}\n"
            f"- foreground_window_uia_child_summary: {observation.foreground_window_uia_child_summary}\n"
            f"- foreground_window_actionable_summary: {observation.foreground_window_actionable_summary}\n"
            f"- screen: {observation.screen_width}x{observation.screen_height}\n"
            f"- screenshot_ref: {observation.screenshot_ref}\n\n"
            f"- screenshot_status: {observation.screenshot_status}\n"
            f"- screenshot_local_path: {observation.screenshot_local_path}\n\n"
            "Visual Fallback Hint:\n"
            f"{visual_fallback_hint}\n\n"
            "Candidate Elements:\n"
            f"{candidate_lines}"
        )

        system_prompt = (
            "You are a Windows-first step guidance planner. "
            "Return only the next best safe human-in-the-loop step. "
            "Prefer the foreground window when it is already relevant. "
            "Use candidate elements when available, and place highlight.rect on the most relevant candidate element. "
            "If the observation is insufficient, return a conservative next step that asks the user to switch windows or confirm context. "
            "When UI Automation signal is weak but screenshot_status is captured, prefer a visual confirmation style instruction. "
            "Never suggest automatic control. "
            "The output action_type must be a safe snake_case label and must not imply automatic execution. "
            "Always set requires_user_action to true."
        )

        return PromptBundle(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_version=self.PROMPT_VERSION,
        )

    @staticmethod
    def _format_candidates(candidates: list[ObservationCandidateElementDto]) -> str:
        if not candidates:
            return "- none"

        lines: list[str] = []
        for index, candidate in enumerate(candidates, start=1):
            lines.append(
                f"- [{index}] name={candidate.name}; automation_id={candidate.automation_id}; "
                f"class_name={candidate.class_name}; control_type={candidate.control_type}; "
                f"is_enabled={candidate.is_enabled}; is_offscreen={candidate.is_offscreen}; "
                f"has_keyboard_focus={candidate.has_keyboard_focus}; ui_path={candidate.ui_path}; "
                f"rect=({candidate.bounding_rect.x},{candidate.bounding_rect.y},{candidate.bounding_rect.width},{candidate.bounding_rect.height})"
            )
        return "\n".join(lines)

    @staticmethod
    def _infer_task_intent_tags(task_text: str) -> str:
        normalized = task_text.casefold().replace(" ", "")
        tags: list[str] = []

        if "设置" in normalized or "settings" in normalized:
            tags.append("settings")
        if any(keyword in normalized for keyword in ("蓝牙", "bluetooth", "设备")):
            tags.append("bluetooth")
        if any(keyword in normalized for keyword in ("网络", "internet", "wifi", "wi-fi", "无线")):
            tags.append("network")
        if any(keyword in normalized for keyword in ("显示", "display", "分辨率", "缩放", "亮度")):
            tags.append("display")
        if any(keyword in normalized for keyword in ("个性化", "personalization", "主题", "背景")):
            tags.append("personalization")

        if not tags:
            tags.append("general_windows_task")

        return ", ".join(tags)

    @staticmethod
    def _build_action_constraints() -> str:
        return (
            "- action_type should follow snake_case, e.g. `open_target_window`, `confirm_in_window`, `search_entry`\n"
            "- action_type must not contain auto-click/auto-type/execute/remote-control semantics\n"
            "- action_type must represent one safe user step only"
        )

    @staticmethod
    def _build_visual_fallback_hint(
        *,
        screenshot_status: str | None,
        screenshot_local_path: str | None,
    ) -> str:
        status = (screenshot_status or "").strip() or "unknown"
        raw_path = (screenshot_local_path or "").strip()
        if not raw_path:
            return f"- screenshot_available: false\n- screenshot_status: {status}"

        screenshot_name = Path(raw_path).name
        return (
            "- screenshot_available: true\n"
            f"- screenshot_status: {status}\n"
            f"- screenshot_file_name: {screenshot_name}\n"
            "- guidance: when UIA candidates are weak, use a conservative visual-confirmation step"
        )
