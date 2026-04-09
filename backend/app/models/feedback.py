from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


FeedbackType = Literal["completed", "incorrect", "reanalyze"]


class SessionFeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    step_id: str = Field(..., min_length=1, max_length=200)
    feedback_type: FeedbackType
    comment: Optional[str] = Field(default=None, max_length=500)


class SessionFeedbackResponse(BaseModel):
    accepted: bool
    session_id: str
    step_id: str
    feedback_type: FeedbackType
    message: str
