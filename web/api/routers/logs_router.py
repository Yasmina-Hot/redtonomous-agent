import sys, os, json
_PYTHON_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "python", "src"))
if _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)

from fastapi import APIRouter, HTTPException
from redtonomous import config as cfg_module

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def list_logs():
    logs_dir = cfg_module.ensure_logs_dir()
    files = sorted(os.listdir(logs_dir), reverse=True)
    result = []
    for fname in files:
        if not fname.endswith(".json"):
            continue
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
        except Exception:
            continue
    return result


@router.get("/{log_id}")
async def get_log(log_id: str):
    logs_dir = cfg_module.ensure_logs_dir()
    fpath = os.path.join(logs_dir, f"{log_id}.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Log not found")
    with open(fpath) as f:
        return json.load(f)
