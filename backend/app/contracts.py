from pydantic import BaseModel, Field


class ObservationDto(BaseModel):
    session_id: str | None = None
    captured_at_utc: str
    foreground_window_title: str
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
    comment: str | None = Field(default=None, max_length=500)


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
    observation_session_id: str | None
    observation_captured_at_utc: str
    foreground_window_title: str
    screen_width: int
    screen_height: int
    screenshot_ref: str
    highlight_rect: dict[str, int]


class FeedbackLogEntry(BaseModel):
    created_at_utc: str
    session_id: str
    step_id: str
    feedback_type: str
    comment: str | None
    accepted: bool
    message: str


class SessionSummaryEntry(BaseModel):
    session_id: str
    last_task_text: str | None
    last_step_id: str | None
    last_action_type: str | None
    last_feedback_type: str | None
    last_updated_at_utc: str
