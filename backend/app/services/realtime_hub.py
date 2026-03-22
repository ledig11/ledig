from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket

from app.contracts import RealtimeEventEntry


@dataclass(frozen=True)
class _Subscriber:
    websocket: WebSocket
    session_id_filter: Optional[str]


class RealtimeEventHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: dict[int, _Subscriber] = {}

    async def connect(self, websocket: WebSocket, session_id_filter: Optional[str]) -> None:
        await websocket.accept()
        async with self._lock:
            self._subscribers[id(websocket)] = _Subscriber(
                websocket=websocket,
                session_id_filter=session_id_filter,
            )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.pop(id(websocket), None)

    async def publish(self, event: RealtimeEventEntry) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.values())

        if not subscribers:
            return

        stale_connections: list[WebSocket] = []
        payload = event.model_dump()
        for subscriber in subscribers:
            if subscriber.session_id_filter and subscriber.session_id_filter != event.session_id:
                continue
            try:
                await subscriber.websocket.send_json(payload)
            except Exception:
                stale_connections.append(subscriber.websocket)

        if stale_connections:
            async with self._lock:
                for websocket in stale_connections:
                    self._subscribers.pop(id(websocket), None)


realtime_event_hub = RealtimeEventHub()
