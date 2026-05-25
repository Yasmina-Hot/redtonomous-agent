import sys
import os
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_token

_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from redtonomous import config as cfg_module

router = APIRouter(prefix="/logs", tags=["logs"], dependencies=[Depends(require_token)])


@router.get("")
async def list_logs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    logs_dir = cfg_module.ensure_logs_dir()
    files = sorted(os.listdir(logs_dir), reverse=True)
    files = [f for f in files if f.endswith(".json")]
    total = len(files)
    page = files[offset : offset + limit]
    result = []
    for fname in page:
        fpath = os.path.join(logs_dir, fname)
        try:
            with open(fpath) as f:
                data = json.load(f)
            result.append({
                "id": fname.replace(".json", ""),
                "file": fname,
                "task": data.get("task", ""),
                "provider": data.get("provider", ""),
                "model": data.get("model", ""),
                "cwd": data.get("cwd", ""),
                "steps": len(data.get("log", [])),
                "mtime": os.path.getmtime(fpath),
            })
        except (OSError, json.JSONDecodeError):
            continue
    return {"total": total, "offset": offset, "limit": limit, "items": result}


@router.get("/{log_id}")
async def get_log(log_id: str):
    # Reject any path-traversal attempt in the log id.
    if "/" in log_id or "\\" in log_id or ".." in log_id:
        raise HTTPException(status_code=400, detail="Invalid log id")
    logs_dir = cfg_module.ensure_logs_dir()
    fpath = os.path.join(logs_dir, f"{log_id}.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Log not found")
    with open(fpath) as f:
        return json.load(f)
