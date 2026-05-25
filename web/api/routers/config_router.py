import sys, os
_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from redtonomous import config as cfg_module

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    data = cfg_module.load_config()
    # Mask API keys
    masked = dict(data)
    masked["providers"] = {}
    for name, pdata in data.get("providers", {}).items():
        p = dict(pdata)
        if p.get("api_key") and p["api_key"] not in ("none", ""):
            p["api_key"] = p["api_key"][:8] + "…"
        masked["providers"][name] = p
    return masked


class ConfigPayload(BaseModel):
    raw: dict[str, Any]


@router.post("")
async def set_config(payload: ConfigPayload):
    try:
        cfg_module.save_config(payload.raw)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/raw")
async def get_raw_config():
    """Return full config (unmasked) — used by backend only, not exposed to UI."""
    return cfg_module.load_config()
