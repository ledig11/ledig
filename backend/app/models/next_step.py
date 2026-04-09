from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.contracts import HighlightDto, ObservationDto


class SessionNextStepRequest(BaseModel):
    task_text: str = Field(..., min_length=1, max_length=500)
    observation: ObservationDto


class SessionNextStepResponse(BaseModel):
    session_id: str
    step_id: str
    instruction: str
    message: str
    action_type: str
    requires_user_action: bool
    confidence: float = 0.7
    highlight: Optional[HighlightDto] = None
    observation_summary: Optional[str] = None

