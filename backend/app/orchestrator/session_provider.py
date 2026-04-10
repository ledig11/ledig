from __future__ import annotations

from app.orchestrator.session_manager import session_manager
from app.orchestrator.session_store_port import SessionStorePort


def get_session_store() -> SessionStorePort:
    return session_manager

