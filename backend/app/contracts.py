from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    task_text: str = Field(..., min_length=1, max_length=500)


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
