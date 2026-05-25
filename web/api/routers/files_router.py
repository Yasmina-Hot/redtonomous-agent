"""Serve file and directory contents to the canvas."""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["files"])


@router.get("/files")
async def list_files(path: str = "."):
    try:
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            entries.append({
                "name": name,
                "path": full,
                "type": "dir" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None,
            })
        return entries
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/file", response_class=PlainTextResponse)
async def read_file(path: str):
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
