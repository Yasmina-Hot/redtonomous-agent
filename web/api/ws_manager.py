from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, run_id: str, ws: WebSocket):
        await ws.accept()
        self.active[run_id] = ws

    def disconnect(self, run_id: str):
        self.active.pop(run_id, None)

    async def send(self, run_id: str, data: dict):
        ws = self.active.get(run_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(run_id)


manager = ConnectionManager()
