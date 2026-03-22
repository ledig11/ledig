from __future__ import annotations

from dataclasses import dataclass

from app.contracts import AnalyzeRequest, ObservationCandidateElementDto


@dataclass(frozen=True)
class PromptBundle:
    system_prompt: str
    user_prompt: str
    prompt_version: str


class StepPlannerPromptBuilder:
    PROMPT_VERSION = "step-planner.v1"

    def build(self, request: AnalyzeRequest) -> PromptBundle:
        observation = request.observation
        candidate_lines = self._format_candidates(observation.foreground_window_candidate_elements)
        user_prompt = (
            "Task:\n"
            f"{request.task_text.strip()}\n\n"
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
            "Candidate Elements:\n"
            f"{candidate_lines}"
        )

        system_prompt = (
            "You are a Windows-first step guidance planner. "
            "Return only the next best safe human-in-the-loop step. "
            "Prefer the foreground window when it is already relevant. "
            "Use candidate elements when available, and place highlight.rect on the most relevant candidate element. "
            "If the observation is insufficient, return a conservative next step that asks the user to switch windows or confirm context. "
            "Never suggest automatic control. Always set requires_user_action to true."
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
