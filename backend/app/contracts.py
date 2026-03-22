from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CandidateRectDto(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ObservationCandidateElementDto(BaseModel):
    name: str
    automation_id: str
    class_name: str
    control_type: str
    is_enabled: bool
    is_offscreen: bool
    is_keyboard_focusable: bool
    has_keyboard_focus: bool
    ui_path: str
    bounding_rect: CandidateRectDto


class ObservationDto(BaseModel):
    session_id: Optional[str] = None
    captured_at_utc: str
    foreground_window_title: str
    foreground_window_uia_name: str
    foreground_window_uia_automation_id: str
    foreground_window_uia_class_name: str
    foreground_window_uia_control_type: str
    foreground_window_uia_is_enabled: bool
    foreground_window_uia_child_count: int
    foreground_window_uia_child_summary: str
    foreground_window_actionable_summary: str
    foreground_window_candidate_elements: list[ObservationCandidateElementDto]
    screen_width: int
    screen_height: int
    screenshot_ref: str


class AnalyzeRequest(BaseModel):
    task_text: str = Field(..., min_length=1, max_length=500)
    observation: ObservationDto


class RectDto(BaseModel):
    x: int
    y: int
    width: int
    height: int


class HighlightDto(BaseModel):
    rect: RectDto


class NextStepResponse(BaseModel):
    session_id: str
    step_id: str
    instruction: str
    action_type: str
    requires_user_action: bool
    highlight: HighlightDto


class StepFeedbackRequest(BaseModel):
    session_id: str
    step_id: str
    feedback_type: str
    comment: Optional[str] = Field(default=None, max_length=500)


class StepFeedbackResponse(BaseModel):
    accepted: bool
    session_id: str
    step_id: str
    feedback_type: str
    message: str


class AnalyzeLogEntry(BaseModel):
    created_at_utc: str
    task_text: str
    session_id: str
    step_id: str
    action_type: str
    instruction: str
    observation_session_id: Optional[str]
    observation_captured_at_utc: str
    foreground_window_title: str
    foreground_window_uia_name: str
    foreground_window_uia_automation_id: str
    foreground_window_uia_class_name: str
    foreground_window_uia_control_type: str
    foreground_window_uia_is_enabled: bool
    foreground_window_uia_child_count: int
    foreground_window_uia_child_summary: str
    foreground_window_actionable_summary: str
    foreground_window_candidate_elements: list[ObservationCandidateElementDto]
    screen_width: int
    screen_height: int
    screenshot_ref: str
    highlight_rect: dict[str, int]


class ObservationTraceEntry(BaseModel):
    created_at_utc: str
    task_text: str
    session_id: str
    step_id: str
    action_type: str
    observation_captured_at_utc: str
    foreground_window_title: str
    foreground_window_uia_name: str
    foreground_window_uia_automation_id: str
    foreground_window_uia_class_name: str
    foreground_window_uia_control_type: str
    foreground_window_uia_is_enabled: bool
    foreground_window_uia_child_count: int
    foreground_window_uia_child_summary: str
    foreground_window_actionable_summary: str
    foreground_window_candidate_elements: list[ObservationCandidateElementDto]
    screen_width: int
    screen_height: int
    screenshot_ref: str


class FeedbackLogEntry(BaseModel):
    created_at_utc: str
    session_id: str
    step_id: str
    feedback_type: str
    comment: Optional[str]
    accepted: bool
    message: str


class AnalyzeDiagnosticEntry(BaseModel):
    created_at_utc: str
    session_id: str
    step_id: str
    planner_source: str
    prompt_version: Optional[str]
    response_schema_version: Optional[str]
    model_provider: Optional[str]
    model_type: Optional[str]
    target_candidate_ui_path: Optional[str]
    target_candidate_label: Optional[str]
    planner_error_code: Optional[str]
    planner_error: Optional[str]
    raw_model_response_excerpt: Optional[str]


class SessionSummaryEntry(BaseModel):
    session_id: str
    last_task_text: Optional[str]
    last_step_id: Optional[str]
    last_action_type: Optional[str]
    last_feedback_type: Optional[str]
    last_updated_at_utc: str


class SessionStateEntry(BaseModel):
    session_id: str
    task_text: Optional[str]
    current_step_id: Optional[str]
    current_action_type: Optional[str]
    current_instruction: Optional[str]
    last_feedback_type: Optional[str]
    session_status: str
    planner_source: Optional[str]
    prompt_version: Optional[str]
    response_schema_version: Optional[str]
    model_provider: Optional[str]
    model_type: Optional[str]
    target_candidate_ui_path: Optional[str]
    target_candidate_label: Optional[str]
    last_planner_error_code: Optional[str]
    last_planner_error: Optional[str]
    completed_step_count: int
    incorrect_feedback_count: int
    reanalyze_feedback_count: int
    last_foreground_window_title: Optional[str]
    last_screenshot_ref: Optional[str]
    last_updated_at_utc: str
