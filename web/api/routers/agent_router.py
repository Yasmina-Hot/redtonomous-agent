import sys
import os
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..auth import require_token, require_ws_token
from ..ws_manager import manager
from ..agent_runner import run_agent_stream

_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)
from redtonomous import config as cfg_module

router = APIRouter(tags=["agent"])


class RunRequest(BaseModel):
    task: str
    provider: str | None = None
    model: str | None = None
    cwd: str = "."
    max_iterations: int = 100
    config_override: dict | None = None


@router.post("/run", dependencies=[Depends(require_token)])
async def start_run(req: RunRequest):
    run_id = str(uuid.uuid4())
    cfg = req.config_override or cfg_module.load_config()
    provider = req.provider or cfg.get("default_provider", "claude")
    model = req.model or cfg.get("default_model", "claude-sonnet-4-6")
    return {"run_id": run_id, "provider": provider, "model": model}


@router.websocket("/ws/{run_id}")
async def agent_ws(
    ws: WebSocket,
    run_id: str,
    task: str = "",
    provider: str = "",
    model: str = "",
    cwd: str = ".",
    max_iterations: int = 100,
    token: str = "",
):
    if not await require_ws_token(ws, token):
        return
    await manager.connect(run_id, ws)
    try:
        cfg = cfg_module.load_config()
        p = provider or cfg.get("default_provider", "claude")
        m = model or cfg.get("default_model", "claude-sonnet-4-6")

        async for event in run_agent_stream(
            task=task, provider=p, model=m, cwd=cwd,
            config_dict=cfg, max_iterations=max_iterations,
        ):
            await manager.send(run_id, event)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(run_id)
