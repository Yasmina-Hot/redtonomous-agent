"""Serve file and directory contents to the canvas.

Both endpoints are sandboxed to a configurable root (default: process cwd) to
prevent path traversal. Set ``REDTONOMOUS_FILES_ROOT`` to override.
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from ..auth import require_token

router = APIRouter(tags=["files"], dependencies=[Depends(require_token)])


def _files_root() -> Path:
    raw = os.environ.get("REDTONOMOUS_FILES_ROOT", "").strip()
    base = Path(raw) if raw else Path.cwd()
    return base.resolve(strict=False)


def _resolve_within_root(user_path: str) -> Path:
    root = _files_root()
    # Reject explicit absolute paths and obvious escapes up front.
    candidate = (root / user_path).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Path is outside the allowed root",
        ) from exc
    return candidate


# Cap response sizes so a single bad request can't OOM the server.
_MAX_BYTES = 2 * 1024 * 1024  # 2 MiB
_MAX_ENTRIES = 5000


@router.get("/files")
async def list_files(path: str = "."):
    target = _resolve_within_root(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    entries: list[dict] = []
    for name in sorted(os.listdir(target)):
        full = target / name
        try:
            is_dir = full.is_dir()
            entries.append({
                "name": name,
                "path": str(full.relative_to(_files_root())),
                "type": "dir" if is_dir else "file",
                "size": full.stat().st_size if full.is_file() else None,
            })
        except OSError:
            continue
        if len(entries) >= _MAX_ENTRIES:
            break
    return entries


@router.get("/file", response_class=PlainTextResponse)
async def read_file(path: str):
    target = _resolve_within_root(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        size = target.stat().st_size
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if size > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size} bytes; max {_MAX_BYTES})",
        )
    try:
        with open(target, "r", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))
