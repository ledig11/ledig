from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SessionStepHistoryItem(BaseModel):
    created_at: str
    step_id: str
    action_type: str
    message: str
    feedback_type: Optional[str] = None


class SessionState(BaseModel):
    session_id: str
    created_at: str
    task_text: Optional[str] = None
    last_observation_ref: Optional[str] = None
    current_step_id: Optional[str] = None
    last_feedback_type: Optional[str] = None
    step_history: list[SessionStepHistoryItem] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    task_text: Optional[str] = Field(default=None, min_length=1, max_length=500)


class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: str

