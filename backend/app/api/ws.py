from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.realtime_hub import realtime_event_hub

router = APIRouter()


@router.websocket("/ws/events")
async def stream_realtime_events(
    websocket: WebSocket,
    session_id: Optional[str] = Query(default=None, min_length=1, max_length=200),
) -> None:
    await realtime_event_hub.connect(websocket, session_id_filter=session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_event_hub.disconnect(websocket)
    except Exception:
        await realtime_event_hub.disconnect(websocket)
