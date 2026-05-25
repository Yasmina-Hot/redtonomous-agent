import asyncio
import logging
from typing import Dict

from fastapi import WebSocket

log = logging.getLogger("redtonomous.api.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active[run_id] = ws

    async def disconnect(self, run_id: str) -> None:
        async with self._lock:
            self.active.pop(run_id, None)

    async def send(self, run_id: str, data: dict) -> None:
        async with self._lock:
            ws = self.active.get(run_id)
        if ws is None:
            return
        try:
            await ws.send_json(data)
        except Exception as e:
            log.warning("ws send failed for run %s: %s", run_id, e)
            await self.disconnect(run_id)


manager = ConnectionManager()
