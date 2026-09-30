"""WebSocket connection manager: one channel per analysis session.

Payloads are compact JSON (counts, vehicles, analytics, events). Annotated
video frames travel over the separate MJPEG endpoint, never inside JSON.
"""
from __future__ import annotations

import logging

from fastapi import WebSocket

log = logging.getLogger("ctas.ws")


class ConnectionManager:
    def __init__(self):
        self._conns: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._conns.setdefault(session_id, set()).add(ws)
        log.info("WS connected for session %s (%d clients)",
                 session_id, len(self._conns[session_id]))

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        conns = self._conns.get(session_id)
        if conns and ws in conns:
            conns.discard(ws)

    async def broadcast(self, session_id: str, message: dict) -> None:
        dead = []
        for ws in list(self._conns.get(session_id, set())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


manager_ws = ConnectionManager()
