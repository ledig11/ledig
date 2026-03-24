from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CandidateRectDto(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class ObservationCandidateElementDto(BaseModel):
    name: Optional[str] = ""
    automation_id: Optional[str] = ""
    class_name: Optional[str] = ""
    control_type: Optional[str] = ""
    is_enabled: Optional[bool] = False
    is_offscreen: Optional[bool] = False
    is_keyboard_focusable: Optional[bool] = False
    has_keyboard_focus: Optional[bool] = False
    ui_path: Optional[str] = ""
    bounding_rect: CandidateRectDto = Field(default_factory=CandidateRectDto)


class ObservationDto(BaseModel):
    session_id: Optional[str] = None
    captured_at_utc: Optional[str] = ""
    foreground_window_title: Optional[str] = ""
    foreground_window_uia_name: Optional[str] = ""
    foreground_window_uia_automation_id: Optional[str] = ""
    foreground_window_uia_class_name: Optional[str] = ""
    foreground_window_uia_control_type: Optional[str] = ""
    foreground_window_uia_is_enabled: Optional[bool] = False
    foreground_window_uia_child_count: Optional[int] = 0
    foreground_window_uia_child_summary: Optional[str] = ""
    foreground_window_actionable_summary: Optional[str] = ""
    foreground_window_candidate_count: Optional[int] = None
    foreground_window_scan_node_count: Optional[int] = None
    foreground_window_scan_depth: Optional[int] = None
    foreground_window_candidate_elements: list[ObservationCandidateElementDto] = Field(default_factory=list)
    screen_width: Optional[int] = 0
    screen_height: Optional[int] = 0
    screenshot_ref: Optional[str] = ""
    screenshot_status: Optional[str] = None
    screenshot_local_path: Optional[str] = None


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
    observation_candidate_count: int
    observation_scan_node_count: Optional[int]
    observation_scan_depth: Optional[int]
    observation_quality: str
    planner_error_code: Optional[str]
    planner_error: Optional[str]
    raw_model_response_excerpt: Optional[str]


class DiagnosticTimelineEntry(BaseModel):
    diagnostic_created_at_utc: str
    observation_captured_at_utc: Optional[str]
    task_text: Optional[str]
    session_id: str
    step_id: str
    action_type: Optional[str]
    planner_source: str
    prompt_version: Optional[str]
    response_schema_version: Optional[str]
    model_provider: Optional[str]
    model_type: Optional[str]
    target_candidate_ui_path: Optional[str]
    target_candidate_label: Optional[str]
    observation_candidate_count: int
    observation_scan_node_count: Optional[int]
    observation_scan_depth: Optional[int]
    observation_quality: str
    foreground_window_title: Optional[str]
    screenshot_ref: Optional[str]
    planner_error_code: Optional[str]
    planner_error: Optional[str]


class SessionSummaryEntry(BaseModel):
    session_id: str
    last_task_text: Optional[str]
    last_step_id: Optional[str]
    last_action_type: Optional[str]
    last_feedback_type: Optional[str]
    last_updated_at_utc: str


class SessionReplayEventEntry(BaseModel):
    created_at_utc: str
    event_type: str
    session_id: str
    step_id: Optional[str]
    action_type: Optional[str]
    feedback_type: Optional[str]
    planner_source: Optional[str]
    observation_quality: Optional[str]
    screenshot_ref: Optional[str]
    note: Optional[str]


class RealtimeEventEntry(BaseModel):
    event_type: str
    created_at_utc: str
    session_id: str
    step_id: Optional[str]
    action_type: Optional[str]
    feedback_type: Optional[str]
    planner_source: Optional[str]
    observation_quality: Optional[str]
    screenshot_ref: Optional[str]
    note: Optional[str]


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
