import sys
import os

_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from redtonomous import config as cfg_module

from ..auth import require_token

router = APIRouter(prefix="/config", tags=["config"], dependencies=[Depends(require_token)])

_ALLOWED_TOP_LEVEL = {"default_provider", "default_model", "wake_word", "providers", "claude"}


def _mask_keys(data: dict[str, Any]) -> dict[str, Any]:
    masked = dict(data)
    masked["providers"] = {}
    for name, pdata in (data.get("providers") or {}).items():
        p = dict(pdata)
        if p.get("api_key") and p["api_key"] not in ("none", ""):
            p["api_key"] = p["api_key"][:8] + "…"
        masked["providers"][name] = p
    return masked


@router.get("")
async def get_config():
    return _mask_keys(cfg_module.load_config())


class ConfigPayload(BaseModel):
    raw: dict[str, Any] = Field(default_factory=dict)


@router.post("")
async def set_config(payload: ConfigPayload):
    unknown = set(payload.raw.keys()) - _ALLOWED_TOP_LEVEL
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown config keys: {sorted(unknown)}",
        )
    providers = payload.raw.get("providers", {})
    if not isinstance(providers, dict):
        raise HTTPException(status_code=400, detail="'providers' must be an object")
    for name, pdata in providers.items():
        if not isinstance(pdata, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{name}' must be an object",
            )
    try:
        cfg_module.save_config(payload.raw)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
