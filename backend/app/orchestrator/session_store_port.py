from __future__ import annotations

from typing import Optional, Protocol

from app.models.session import SessionState


class SessionStorePort(Protocol):
    def create_session(self, task_text: Optional[str] = None) -> SessionState:
        ...

    def get_session(self, session_id: str) -> Optional[SessionState]:
        ...

    def upsert_from_next_step(
        self,
        *,
        session_id: str,
        task_text: str,
        step_id: str,
        action_type: str,
        message: str,
        last_observation_ref: Optional[str],
    ) -> SessionState:
        ...

    def apply_feedback(
        self,
        *,
        session_id: str,
        step_id: str,
        feedback_type: str,
        comment: Optional[str],
    ) -> Optional[SessionState]:
        ...

    def get_runtime_stats(self) -> dict[str, int]:
        ...

    def clear_all(self) -> None:
        ...

